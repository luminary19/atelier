# Mesh Cleanup & QA Reference — forge-intake

Covers: Blender headless retopo + UV + rebake pipeline; trimesh pre-flight; QA checklists.
Used by tracks A (photogrammetry mesh), D (cloud AI), E (local AI), F (raw mesh cleanup).

---

## §1. trimesh Pre-flight (run before any Blender operation)

A non-watertight mesh or one with disconnected islands crashes Blender's remesh modifiers.
Always run this check and repair before feeding into Blender.

**Install:** `pip install "trimesh[easy]"`

```python
import trimesh, json, sys

def preflight(path: str) -> tuple:
    """Quick health check. Returns (report_dict, mesh)."""
    mesh = trimesh.load(path, force='mesh')
    ext = mesh.extents.tolist()
    max_ext = max(ext)
    report = {
        "path": path,
        "faces": len(mesh.faces),
        "vertices": len(mesh.vertices),
        "is_watertight": bool(mesh.is_watertight),
        "body_count": int(mesh.body_count),
        "max_extent_m": max_ext,
        "euler_number": int(mesh.euler_number),
        "has_uvs": hasattr(mesh.visual, 'uv') and mesh.visual.uv is not None,
        "has_vertex_colors": hasattr(mesh.visual, 'vertex_colors'),
    }
    failures = []
    if report["body_count"] > 1:
        failures.append(f"body_count={report['body_count']} (floaters)")
    if not report["is_watertight"]:
        failures.append("not watertight")
    if report["faces"] < 100:
        failures.append(f"faces={report['faces']} < 100 (degenerate)")
    if max_ext > 10.0:
        failures.append(f"max_extent={max_ext:.2f}m > 10m (scale error)")
    if max_ext < 0.01:
        failures.append(f"max_extent={max_ext:.4f}m < 0.01m (scale error)")
    report["failures"] = failures
    return report, mesh

# Usage:
report, mesh = preflight("output_raw.glb")
print(json.dumps(report, indent=2))

# Auto-repair if needed:
if not mesh.is_watertight:
    trimesh.repair.fix_normals(mesh, multibody=True)
    trimesh.repair.fill_holes(mesh)
    trimesh.repair.fix_winding(mesh)
    mesh.export("output_repaired.glb")
```

---

## §2. Blender Headless Cleanup Invocation

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$cleanup = "$env:CLAUDE_CONFIG_DIR\skills\forge-intake\scripts\cleanup.py"
# "--" before script args is MANDATORY — missing it silently passes args to Blender, not the script
# "--python-exit-code 1" makes Python exceptions fail the process; "--factory-startup" = determinism
& $blender -b --factory-startup --python-exit-code 1 `
    -P "$cleanup" `
    -- "input_raw.glb" "output_clean.glb" 2048 20000 --seed 0
# args: <input_path> <output_path> <bake_res_px> <target_tris> [--seed N] [--scale 0.01 for Meshy cm]
```

`scripts/cleanup.py` ships with this skill: import-by-ext → scale fix → transform_apply →
voxel remesh → Quadriflow (pinned `--seed`, idempotent) → smart_project UV → selected-to-active
Cycles diffuse bake → Y-up GLB export. The pinned seed makes reruns reproducible.

---

## §3. Blender Headless Cleanup — Key bpy Operations

The assembled, arg-parsing, exit-coded script ships at `scripts/cleanup.py` (invoke it per §2).
These are the critical operations it performs and their caveats — read them when adapting the
script or debugging a specific stage.

**Import by extension:**
```python
ext = os.path.splitext(INPUT_GLB)[1].lower()
if ext in (".glb", ".gltf"):
    bpy.ops.import_scene.gltf(filepath=INPUT_GLB)   # absolute forward-slash path
elif ext == ".obj":
    bpy.ops.wm.obj_import(filepath=INPUT_GLB)        # Blender 4.x native OBJ importer
                                                     # (import_scene.obj was removed in 4.0)
elif ext == ".fbx":
    bpy.ops.import_scene.fbx(filepath=INPUT_GLB)
```

**Scale check and fix (Meshy = centimeters; TripoSR = [-1,1] cube):**
```python
obj = bpy.context.active_object
extents = [obj.dimensions[i] for i in range(3)]
print(f"Extents: {extents}")
# If chair is ~100 units tall instead of ~1m:
bpy.ops.transform.resize(value=(0.01, 0.01, 0.01))
bpy.ops.object.transform_apply(scale=True)
# Forge standard: 1 unit = 1 meter. max(extents) < 10 for props.
```

**ALWAYS apply transforms before remesh:**
```python
# Quadriflow and Voxel Remesh operate on world-space geometry.
# A mesh with unapplied 100× scale produces incorrect voxel sizes.
bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
```

**Voxel remesh → Quadriflow:**
```python
mod = obj.modifiers.new(name="VoxelRemesh", type='REMESH')
mod.mode = 'VOXEL'
mod.voxel_size = 0.02   # ~1m prop: 0.01-0.02; ~0.1m prop: 0.001-0.002
bpy.ops.object.modifier_apply(modifier="VoxelRemesh")

# Quadriflow counts quads not tris; pass TARGET_TRIS // 2
bpy.ops.object.quadriflow_remesh(
    use_preserve_sharp=True,
    use_preserve_boundary=True,
    mode='FACES',
    target_faces=TARGET_TRIS // 2,
    seed=1,
)
```

**Voxel size calibration:**

| Object bbox | voxel_size | Use case |
|---|---|---|
| ~1m prop | 0.01–0.02 | Standard |
| ~0.1m small prop | 0.001–0.002 | Jewelry, details |
| ~10m large | 0.1–0.2 | Architecture |

Formula: `voxel_size ≈ bbox_max_extent / 100..500`

**UV unwrap:**
```python
bpy.ops.object.mode_set(mode='EDIT')
bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(
    angle_limit=math.radians(66.0),  # RADIANS — passing 66.0 = 66 rad, every face its own island
    island_margin=0.003,             # 3 texels at 1024px; 0.002 at 2048px
    area_weight=0.0,
)
bpy.ops.object.mode_set(mode='OBJECT')
```

**Bake (selected-to-active, Cycles):**
```python
bpy.context.scene.render.engine = 'CYCLES'   # Cycles, never EEVEE — headless-safe on Windows
bpy.context.scene.cycles.samples = 128   # 64 for validation; 128-256 for production
bpy.context.scene.cycles.device = 'CPU'  # headless-safe default. GPU is NOT auto-activated:
# to use GPU you must call prefs.refresh_devices() first (see forge-render cycles-gpu-passes.md).

# cage_extrusion controls light-leak prevention:
# - Hard-surface: 0.02–0.05
# - Organic / high-frequency: 0.10–0.15
# If dark "shadow" patches appear → increase cage_extrusion
bpy.ops.object.bake(
    type='DIFFUSE',
    pass_filter={'COLOR'},
    use_selected_to_active=True,
    cage_extrusion=0.05,
    max_ray_distance=0.1,
)
```

**Export GLB:**
```python
# Use absolute forward-slash paths for filepath in Blender — never "//relative"
bpy.ops.export_scene.gltf(
    filepath=OUTPUT_GLB,     # absolute forward-slash path
    export_format='GLB',
    export_normals=True,
    export_tangents=True,    # required when exporting normal maps
    export_materials='EXPORT',
    export_texcoords=True,
    export_yup=True,         # Forge standard: Y-up for web (three.js / R3F)
)
```

---

## §4. Render-to-PNG Validation (Blender headless, 4 angles)

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$rv = "$env:CLAUDE_CONFIG_DIR\skills\forge-intake\scripts\render_validate.py"
& $blender -b --factory-startup --python-exit-code 1 `
    -P "$rv" `
    -- "output_clean.glb" "C:\Forge\renders\check.png"
# Default engine BLENDER_WORKBENCH (headless-safe, ~1s/frame). Shaded check: add --engine CYCLES --samples 16
# Produces: check_front.png, check_right.png, check_back.png, check_top.png
# Use Read tool on each PNG for visual inspection
```

`scripts/render_validate.py` ships with this skill: it imports the mesh, sets up a camera at
4 angles (front/right/back/top), renders at 512×512, and saves per-angle PNGs. Use `Read` on
each PNG to visually confirm: no exploded geometry, no inverted normals, texture has no baked-in
lighting direction (orbit the view — if bright/dark areas on texture don't change, they're baked in).

**Engine note (Windows headless ground truth):** Use **`BLENDER_WORKBENCH`** for fast geometry
QA and **`CYCLES`** (low samples, e.g. 16–32) for shaded validation. **EEVEE and EEVEE-Next are
UNSUPPORTED headless on Windows** — never set `scene.render.engine = 'EEVEE'` /
`'BLENDER_EEVEE'` / `'BLENDER_EEVEE_NEXT'` for any headless render. `render_validate.py` rejects
EEVEE and falls back to Workbench. (Matches forge-render/SKILL.md and
forge-validate/references/render-qa-guide.md.)

---

## §5. QA Checklist

Before handing off to `forge-validate`:

- [ ] `is_watertight == True` (trimesh pre-flight)
- [ ] `body_count == 1` (no disconnected floaters)
- [ ] Face count within budget for target use case (see forge-standards)
- [ ] `max_extent` in plausible range: 0.01m – 10m for props
- [ ] UV map exists (`has_uvs == True` after cleanup; TripoSR default has none)
- [ ] No inverted normals in render (black patches in backface-culling mode)
- [ ] Texture has no baked-in directional lighting (orbit test in Blender Lookdev)
- [ ] GLB imports cleanly in three.js sandbox / Babylon.js viewer
- [ ] 4-angle contact sheet shows complete, non-exploded geometry

**Target poly counts for final assets:**

| Asset type | Triangle target | Texture res |
|---|---|---|
| Background prop | 500–2,000 | 512 or 1024 |
| Mid-tier prop | 2,000–8,000 | 1024 |
| Hero prop / character | 8,000–30,000 | 2048 |
| Film / vis-dev | 50,000–300,000 | 4096 |
| Web AR / VR | < 30,000 | 1024 |
| Normal bake source | 300K–1M | — |

---

## §6. Gotchas

| Problem | Symptom | Fix |
|---|---|---|
| `--` separator missing | Script args silently ignored | MANDATORY: `blender -b -P script.py -- args` |
| Transforms not applied | Quadriflow wrong voxel density | `transform_apply(scale=True, rotation=True)` before any remesh |
| Quadriflow hangs | Blender hangs on >2M tri input | Pre-decimate with PyMeshLab to <1M tris first |
| Dark bake patches | Shadow artifacts in baked normal | Increase `cage_extrusion` from 0.05 → 0.10–0.15 |
| UV bleed in realtime | Mipmap bleeding between islands | `island_margin ≥ 0.003` at 1024px; ≥ 0.002 at 2048px |
| EEVEE / EEVEE-Next headless | `RuntimeError: EEVEE requires an OpenGL context` (crash) | NEVER set `'BLENDER_EEVEE'` / `'BLENDER_EEVEE_NEXT'` headless on Windows → use `'CYCLES'` (low samples) or `'BLENDER_WORKBENCH'` for geometry-only QA |
| No UVs after TripoSR | Bake produces black | Run TripoSR with `--bake-texture`; or treat as hi-res bake source |
| Meshy scale 100× | Chair is 100 units tall | Apply `resize(0.01, 0.01, 0.01)` + `transform_apply(scale=True)` |
