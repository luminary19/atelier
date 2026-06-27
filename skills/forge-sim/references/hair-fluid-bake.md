# forge-sim — Hair/Fur & Fluid/Smoke Reference

## Contents
- §1. GN Curves hair: create guide curves · §2. Principled Hair BSDF
- §3. Hair Cycles render settings · §4. Mantaflow domain + flow setup
- §5. Bake ALL cache type (production headless pattern)
- §6. Bake MODULAR (smoke + noise separately) · §7. Fluid cache validation
- §8. Alembic/VDB export (pointer → export-cache.md)
- §9. Decision matrix · §10. Hair gotchas · §11. Fluid gotchas

---

## §1. GN Curves Hair — Create Guide Curves in Python

```python
# create_hair.py — run inside blender -b scene.blend -P create_hair.py
import bpy, random

def create_guide_hair(surface_obj_name="Head", num_guides=20,
                       points_per_guide=8, hair_length=0.15) -> bpy.types.Object:
    """
    Creates a bpy.types.Curves (GN hair) object attached to a surface mesh.
    CRITICAL: apply scale on surface_obj before calling this.
    """
    surface_obj = bpy.data.objects[surface_obj_name]
    # Apply scale — GN hair roots break without this
    bpy.context.view_layer.objects.active = surface_obj
    surface_obj.select_set(True)
    bpy.ops.object.transform_apply(scale=True)
    surface_obj.select_set(False)

    hair_data = bpy.data.hair_curves.new("HairGuides")
    hair_obj  = bpy.data.objects.new("HairGuides", hair_data)
    bpy.context.collection.objects.link(hair_obj)

    # Attach to surface — UV map name MUST match an existing UV layer
    hair_data.surface         = surface_obj
    hair_data.surface_uv_map  = "UVMap"  # verify: [uv.name for uv in surf.data.uv_layers]

    # Add guide curves
    hair_data.add_curves([points_per_guide] * num_guides)

    # Set positions (simplified; real work: sample from surface BVH)
    positions = hair_data.attributes['position'].data
    bb = surface_obj.bound_box
    xs = [bb[i][0] for i in range(8)]; ys = [bb[i][1] for i in range(8)]
    zmax = max(bb[i][2] for i in range(8))
    pt_idx = 0
    for _ in range(num_guides):
        rx = random.uniform(min(xs), max(xs))
        ry = random.uniform(min(ys), max(ys))
        for p in range(points_per_guide):
            t = p / (points_per_guide - 1)
            positions[pt_idx].vector = (rx, ry, zmax + t * hair_length)
            pt_idx += 1

    hair_data.set_types(type='CATMULL_ROM')
    return hair_obj
```

**Production guide settings:**

| Parameter | Prototype | Production | Rationale |
|-----------|-----------|------------|-----------|
| Guide count | 10–20 | 50–200 | More guides → smoother interpolation at partings |
| Points per guide | 5 | 8–12 | Catmull-Rom needs ≥4; 8 stable for most hair |
| Children density | 200/m² | 1000–5000/m² | Film quality; reduce viewport with `Viewport Amount` |
| Child guide count | 2 | 4–6 | Better shape transfer with more guides |

---

## §2. Principled Hair BSDF Material

```python
def create_hair_material(mat_name="HairMat", melanin=0.8,
                          melanin_redness=0.5, roughness=0.3,
                          model='HUANG') -> bpy.types.Material:
    """
    model: 'HUANG' (Blender 4.0+ default, better far-field) or 'CHIANG' (legacy)
    melanin: 0=blonde, 1=black
    """
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    hair = nodes.new('ShaderNodeBsdfHairPrincipled')
    hair.model          = model
    hair.parametrization = 'MELANIN'
    hair.inputs['Melanin'].default_value          = melanin
    hair.inputs['Melanin Redness'].default_value  = melanin_redness
    hair.inputs['Roughness'].default_value        = roughness
    hair.inputs['Random Color'].default_value     = 0.05   # strand colour variance
    hair.inputs['Random Roughness'].default_value = 0.05

    output = nodes.new('ShaderNodeOutputMaterial')
    links.new(hair.outputs['BSDF'], output.inputs['Surface'])
    return mat

def assign_hair_material(curves_obj: bpy.types.Object,
                          mat: bpy.types.Material) -> None:
    if mat.name not in [m.name for m in curves_obj.data.materials]:
        curves_obj.data.materials.append(mat)
```

---

## §3. Hair Cycles Render Settings (Headless)

```python
def setup_hair_render(output_path: str, frame: int = 1,
                       samples: int = 128) -> None:
    """
    EEVEE cannot render headless on Windows — always use CYCLES.
    """
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'GPU'           # fallback to CPU if no GPU in headless
    scene.cycles.samples = samples

    # Hair-specific Cycles settings
    scene.cycles.use_hair        = True
    scene.cycles.hair_shape      = 'THICK'       # RIBBON=fast/flat; THICK=volumetric/correct
    scene.cycles.hair_subdivisions = 3           # 0=jagged; 3=smooth at typical distance

    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = output_path.replace("\\", "/")
    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)
    print(f"Render: {output_path}")
```

**Hair validation before render:**
```python
def validate_hair_setup(curves_obj_name: str) -> list:
    """Returns list of issues; empty = OK."""
    issues = []
    obj = bpy.data.objects.get(curves_obj_name)
    if obj is None:
        return [f"Object '{curves_obj_name}' not found"]
    hd = obj.data
    if not isinstance(hd, bpy.types.Curves):
        return [f"Not a Curves object"]
    if hd.surface is None:
        issues.append("No surface attached")
    elif not hd.surface_uv_map:
        issues.append("surface_uv_map is empty")
    elif hd.surface_uv_map not in [uv.name for uv in hd.surface.data.uv_layers]:
        issues.append(f"UV map '{hd.surface_uv_map}' not found on surface")
    surf = hd.surface
    if surf:
        s = surf.scale
        if abs(s.x-1.0)>0.01 or abs(s.y-1.0)>0.01 or abs(s.z-1.0)>0.01:
            issues.append(f"Surface scale not applied: {tuple(s)}")
    if len(hd.curves) == 0:
        issues.append("No curves — nothing to render")
    if not obj.data.materials:
        issues.append("No material — will render black")
    return issues
```

---

## §4. Mantaflow Fluid/Smoke — Domain + Flow Setup

```python
import pathlib, bpy

def create_smoke_scene(domain_size=2.0, emitter_size=0.2,
                        resolution=64) -> tuple:
    """Returns (domain_obj, flow_obj)."""
    # Domain
    bpy.ops.mesh.primitive_cube_add(size=domain_size)
    domain_obj = bpy.context.active_object
    domain_obj.name = "SmokeDomain"
    domain_mod = domain_obj.modifiers.new("Fluid", 'FLUID')
    domain_mod.fluid_type = 'DOMAIN'
    ds = domain_mod.domain_settings
    ds.domain_type    = 'GAS'
    ds.resolution_max = resolution
    ds.cache_type     = 'ALL'   # CRITICAL: must not be 'REPLAY' for headless bake

    # Flow (emitter)
    bpy.ops.mesh.primitive_uv_sphere_add(radius=emitter_size, location=(0,0,-0.6))
    flow_obj = bpy.context.active_object
    flow_obj.name = "SmokeEmitter"
    flow_mod = flow_obj.modifiers.new("Fluid", 'FLUID')
    flow_mod.fluid_type = 'FLOW'
    fs = flow_mod.flow_settings
    fs.flow_type     = 'BOTH'    # 'BOTH'=Fire+Smoke; 'SMOKE'; 'FIRE'; 'LIQUID'
    fs.flow_behavior = 'INFLOW'
    fs.temperature   = 1.0

    return domain_obj, flow_obj
```

**Fluid domain settings quick reference:**

| Parameter | Cheap test | Production | Notes |
|-----------|-----------|------------|-------|
| `resolution_max` | 32–64 | 128–256 | Memory ∝ res³; 256 ≈ 3–6 GB RAM |
| `cache_type` | ALL | MODULAR | **NEVER 'REPLAY' for headless** — writes nothing |
| `cache_data_format` | OPENVDB | OPENVDB | Interoperable with Houdini/Nuke |
| `use_adaptive_domain` | False | False | Causes VDB origin drift on export |
| `vorticity` | 0.5 | 1.0–2.0 | 0=too smooth; 2=very turbulent |
| `cfl_condition` | 4.0 | 2.0–4.0 | Lower=more substeps=more accurate high-vel sims |
| `noise_scale` | 2 | 2 | 2× upres factor; needs MODULAR bake with `bake_noise()` |

**Memory / time estimates** (CPU, modern 8-core, 2m cube domain):
- res 32: seconds/frame, ~200 MB
- res 64: 30–120 s/frame, ~1.5 GB
- res 128: 5–15 min/frame, ~12 GB
- res 256: 1–4 hr/frame, ~96 GB — final shots with lots of RAM only

---

## §5. Mantaflow ALL Cache Bake (Headless)

```python
def setup_and_bake_smoke(domain_name="SmokeDomain",
                          cache_dir=r"C:\tmp\smoke_cache",
                          resolution=64,
                          frame_start=1, frame_end=60) -> None:
    """
    cache_dir: ASCII-only, no spaces (Mantaflow Windows path limitation).
    Use pathlib.Path(cache_dir).as_posix() when setting ds.cache_directory.
    """
    import pathlib
    pathlib.Path(cache_dir).mkdir(parents=True, exist_ok=True)

    domain_obj = bpy.data.objects[domain_name]
    fluid_mod  = next((m for m in domain_obj.modifiers
                       if m.type == 'FLUID' and m.fluid_type == 'DOMAIN'), None)
    if fluid_mod is None:
        raise RuntimeError(f"No FLUID domain on '{domain_name}'")

    ds = fluid_mod.domain_settings
    ds.domain_type               = 'GAS'
    ds.resolution_max            = resolution
    ds.cache_type                = 'ALL'          # REQUIRED
    ds.cache_directory           = pathlib.Path(cache_dir).as_posix()
    ds.cache_data_format         = 'OPENVDB'
    ds.cache_noise_format        = 'OPENVDB'
    ds.cache_frame_start         = frame_start
    ds.cache_frame_end           = frame_end
    ds.openvdb_cache_compress_type = 'ZIP'
    ds.use_adaptive_domain       = False          # DISABLE for VDB export
    ds.use_noise                 = True
    ds.noise_scale               = 2
    ds.vorticity                 = 1.0

    scene = bpy.context.scene
    scene.frame_start = frame_start
    scene.frame_end   = frame_end

    bpy.context.view_layer.objects.active = domain_obj
    domain_obj.select_set(True)

    # temp_override required in --background mode (no UI = no auto context)
    with bpy.context.temp_override(scene=scene, active_object=domain_obj):
        result = bpy.ops.fluid.bake_all()
        print(f"bake_all result: {result}")

    vdb_files = list(pathlib.Path(cache_dir).rglob("*.vdb"))
    print(f"VDB files written: {len(vdb_files)}")
    bpy.ops.wm.save_mainfile()
```

PowerShell bake + render pipeline:
```powershell
param(
    [string]$BlenderExe = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    [string]$BlendFile  = "C:\Forge\scenes\smoke_scene.blend",
    [string]$BakeScript = "C:\Forge\scripts\bake_fluid_headless.py",
    [string]$OutputDir  = "C:\Forge\renders\smoke"
)

New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

# Step 1: Bake (use --factory-startup to suppress addon crashes in background mode)
Write-Host "Baking fluid..."
& $BlenderExe --factory-startup -b $BlendFile -P $BakeScript
if (-not $?) { Write-Error "Bake failed"; exit 1 }

# Step 2: Render all frames (-a = animate; -s start -e end)
Write-Host "Rendering..."
& $BlenderExe -b $BlendFile -o "$OutputDir\frame_####" -s 1 -e 60 -a
if (-not $?) { Write-Error "Render failed"; exit 1 }

Write-Host "Done: $OutputDir"
```

---

## §6. Mantaflow MODULAR Bake (Smoke + Noise Separately)

```python
def bake_modular_smoke(domain_obj: bpy.types.Object, cache_dir: str) -> None:
    """
    MODULAR = most control. Bake data first, then noise (requires data to exist).
    For liquid: also bake_mesh() and bake_particles() separately.
    """
    import pathlib
    ds = domain_obj.modifiers['Fluid'].domain_settings
    ds.cache_type        = 'MODULAR'
    ds.cache_directory   = pathlib.Path(cache_dir).as_posix()
    ds.cache_data_format = 'OPENVDB'
    ds.cache_noise_format = 'OPENVDB'
    ds.use_noise         = True

    with bpy.context.temp_override(scene=bpy.context.scene,
                                    active_object=domain_obj):
        print("Baking base data...")
        bpy.ops.fluid.bake_data()
        if ds.use_noise:
            print("Baking noise...")
            bpy.ops.fluid.bake_noise()
        # Liquid only:
        # bpy.ops.fluid.bake_mesh()
        # bpy.ops.fluid.bake_particles()
```

---

## §7. Fluid Cache Validation

```python
import pathlib, bpy

def validate_fluid_cache(domain_name: str, expected_frames: int) -> list:
    issues = []
    domain_obj = bpy.data.objects.get(domain_name)
    if not domain_obj: return [f"'{domain_name}' not found"]
    ds = next((m.domain_settings for m in domain_obj.modifiers
               if m.type == 'FLUID' and m.fluid_type == 'DOMAIN'), None)
    if ds is None: return ["No FLUID DOMAIN modifier found"]
    cache_dir = pathlib.Path(ds.cache_directory)
    if not cache_dir.exists(): return [f"Cache dir missing: {cache_dir}"]
    vdb_files = sorted(cache_dir.rglob("*.vdb"))
    if not vdb_files: issues.append("No .vdb files found")
    else:
        data_vdbs = sorted((cache_dir/"data").glob("*.vdb")) \
                    if (cache_dir/"data").exists() else vdb_files
        if len(data_vdbs) < expected_frames:
            issues.append(f"Expected {expected_frames} VDB frames, found {len(data_vdbs)}")
        zero = [f for f in vdb_files if f.stat().st_size == 0]
        if zero: issues.append(f"Zero-size VDB: {[str(f) for f in zero[:3]]}")
    if not ds.has_cache_baked_data: issues.append("has_cache_baked_data is False")
    return issues
```

---

## §8. Alembic Export for Hair / VDB Export for Fluid

Full export operator details, game-engine scale corrections, VDB cache directory layout, and re-import instructions live in `references/export-cache.md §1` (Alembic), `§4` (VDB copy and import), and `§6` (target quick-reference table).

Key flags in brief:
- Particle hair: `alembic_export(export_hair=True, as_background_job=False, evaluation_mode='RENDER')`
- GN Curves → UE5 Groom: requires GroomExporter add-on; native exporter only handles particle hair
- `global_scale=100.0` for UE5 (metres → cm); `global_scale=1.0` for Unity/Godot
- VDB: copy the Mantaflow `<cache_dir>/data/*.vdb` folder; attribute names: `density` (data VDB), `density_noise` (noise VDB)

---

## §9. Decision Matrix

| Use case | Recommendation | Rationale |
|----------|---------------|-----------|
| Static hero hair | GN Hair + Principled Hair BSDF | No sim needed; guide sculpt + children |
| Animated hair (character motion) | GN Hair + Deform Curves on Surface | Surface deformation = cloth-like without sim |
| Physics-reactive hair | Cloth/spring sim baked to Alembic | Bake once, replay on render |
| Hair for game engine | Hair cards (FBX) or Alembic Groom | Real-time budget demands cards or strands |
| Smoke/fire (1–3 s clip) | Mantaflow bake res 64–128 | Bake time < 1 hr at res 128 |
| Smoke/fire (multi-shot reuse) | Pre-bake once, reuse VDB sequence | VDB portable across shots and software |
| Smoke/fire (background element) | Looping pre-baked VDB | EmberGen exports work |
| Water/ocean surface | Ocean modifier or Mantaflow APIC liquid | Ocean modifier faster for large calm surfaces |
| Complex fluid | Houdini export → VDB import | Far faster, more controllable |

---

## §10. Hair Gotcha → Fix Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| Hair roots float/offset from mesh | Surface scale not applied | `bpy.ops.object.transform_apply(scale=True)` on surface first |
| Interpolate node produces no children | `surface_uv_map` empty or wrong | `hair_data.surface_uv_map = <correct UV name>` |
| GroomExporter crashes `NameError: CreateArchiveWithInfo` | Alembic Python binding API change in Blender 4.2+ | Use latest fork or convert GN Curves → particle system then export natively |
| Native `.abc` import to UE5 shows no groom data | `export_hair=True` only handles particle hair | Install GroomExporter for GN Curves → UE5 Groom |
| Exported hair has jagged curves in UE5 | Low subdivision before export | Add Subdivide Curve GN node BEFORE Interpolate Hair Curves in modifier stack |
| Hair renders black in Cycles | `ShaderNodeBsdfPrincipled` (mesh BSDF) applied to curve geometry | Use `ShaderNodeBsdfHairPrincipled` instead |

---

## §11. Fluid Gotcha → Fix Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `bpy.ops.fluid.bake_all()` crashes (`EXCEPTION_ACCESS_VIOLATION`) | Addon conflict in background mode | Add `--factory-startup` to Blender CLI invocation |
| bake_all completes but no `.vdb` files | `cache_type = 'REPLAY'` | `ds.cache_type = 'ALL'`; save .blend; re-bake |
| `bpy.ops.fluid.free_all()` crash on empty cache | Freeing non-existent cache | Check `ds.has_cache_baked_data` before freeing; point to fresh `cache_directory` instead |
| No VDB files, no error | Path with spaces or Unicode | Use ASCII-only path: `C:\simcache\smoke01\`; no spaces, no Unicode |
| VDB sequence has per-frame origin jitter | `use_adaptive_domain = True` | `ds.use_adaptive_domain = False` for any sim that will be exported |
| Noise VDB looks empty on import | Attribute is `density_noise` not `density` | In Principled Volume shader, use grid attribute names from noise VDB: `density_noise`, `temperature_noise` |
| `Operator bpy.ops.fluid.bake_all.poll() failed` | Missing active-object context in background | `bpy.context.view_layer.objects.active = domain_obj` + `domain_obj.select_set(True)` + `temp_override` |
| Path separator failure in `cache_directory` | Blender expects forward slashes | `pathlib.Path(cache_dir).as_posix()` when setting `ds.cache_directory` |
| Re-loading old VDB after Blender upgrade → crash | OpenVDB format version change | Re-bake from scratch; never resume across major Blender version upgrades |
