# forge-topology — Retopology & LOD Chain Reference

## Contents
- §1. Tool selection & order of operations
- §2. bpy retopo + LOD chain (full script)
- §3. QuadriFlow remesh (headless)
- §4. Voxel remesh via modifier (NOT operator)
- §5. High-to-low normal baking
- §6. gltfpack LOD chain (PowerShell)
- §7. gltf-transform LOD chain (Node.js)
- §8. Open3D / trimesh / PyMeshLab decimation (no Blender)
- §9. Poly budget targets & screen coverage thresholds
- §10. LOD naming conventions (Unity / Unreal)
- §11. Gotchas → fixes

---

## §1. Tool Selection & Order of Operations

**Primary (Blender bpy):** retopo, remesh, LOD chain, H→L bake.
**Secondary (gltfpack):** fast LOD cascade for GLB assets.
**Alternative (Instant Meshes):** quad remesh without Blender.
**No-Blender (trimesh / Open3D / PyMeshLab):** programmatic decimation.

**Correct order — do not skip steps:**
```
1. Apply transforms (scale = 1,1,1)
2. Merge by distance (remove duplicate verts)
3. Recalculate normals outward
4. [Optional] Voxel remesh → clean broken topology (destroys UVs — do BEFORE unwrap)
5. [Optional] QuadriFlow → clean quad retopo (destroys UVs — do BEFORE unwrap)
6. UV unwrap
7. Bake high→low normals (requires UVs on low-poly)
8. Generate LOD chain via cascade Decimate
9. Export
```

---

## §2. bpy Retopo + LOD Chain

```python
"""
forge_retopo_lod.py — Headless Blender retopo + LOD chain.
Usage: blender.exe --background --python forge_retopo_lod.py -- \
    --input  C:/assets/scan_hipoly.glb \
    --output-dir C:/assets/lods \
    --target-faces 8000 \
    --lod-ratios 1.0 0.5 0.25 0.1 0.05 \
    --seed 42
Produces: MeshName_LOD0.glb ... MeshName_LOD4.glb
Deterministic: same input + ratios + seed + Blender version → byte-identical chain (see ## Determinism).
"""
import bpy, sys, argparse
from pathlib import Path

def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    parser = argparse.ArgumentParser()
    parser.add_argument("--input",       required=True)
    parser.add_argument("--output-dir",  required=True)
    parser.add_argument("--target-faces",type=int,   default=8000)
    parser.add_argument("--lod-ratios",  nargs="+",  type=float, default=[1.0, 0.5, 0.25, 0.1])
    parser.add_argument("--use-quadriflow", action="store_true", default=False)
    parser.add_argument("--preserve-uvs",   action="store_true", default=True)
    parser.add_argument("--seed", type=int, default=42,
                        help="QuadriFlow/Voxel remesh seed — fixed for reproducible output")
    return parser.parse_args(argv)

def import_mesh(path: str):
    ext = Path(path).suffix.lower()
    bpy.ops.object.select_all(action='DESELECT')
    if ext in (".glb", ".gltf"): bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".obj":          bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".fbx":          bpy.ops.import_scene.fbx(filepath=path)
    else:                        raise ValueError(f"Unsupported format: {ext}")
    return next(o for o in bpy.context.selected_objects if o.type == 'MESH')

def prep_mesh(obj):
    """Apply scale, merge by distance, recalculate normals."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.object.mode_set(mode='OBJECT')

def quadriflow_remesh(obj, target_faces: int, seed: int = 42):
    """
    QuadriFlow does NOT guarantee exact face count (±20%).
    Apply fallback Decimate COLLAPSE if result overshoots.
    `seed` is a CLI arg (default 42) so the retopo is reproducible — see ## Determinism.
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.quadriflow_remesh(
        target_faces=target_faces,
        use_preserve_sharp=True,
        use_preserve_boundary=True,
        seed=seed,        # fixed seed → deterministic output
    )
    actual = len(obj.data.polygons)
    if actual > target_faces * 1.2:
        _apply_decimate(obj, target_faces / actual, preserve_uvs=False)
    return obj

def voxel_remesh_modifier(obj, voxel_size: float = 0.02):
    """
    Use REMESH modifier (NOT bpy.ops.object.voxel_remesh which freezes on large meshes).
    """
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new("VoxelRemesh", 'REMESH')
    mod.mode = 'VOXEL'
    mod.voxel_size = voxel_size
    mod.use_smooth_shade = False
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj

def _apply_decimate(obj, ratio: float, preserve_uvs: bool = True):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    mod = obj.modifiers.new("Decimate", 'DECIMATE')
    mod.decimate_type = 'COLLAPSE'
    mod.ratio = max(0.001, min(ratio, 1.0))
    mod.delimit = {'UV', 'SEAM', 'SHARP', 'MATERIAL'} if preserve_uvs else {'NORMAL'}
    mod.use_collapse_triangulate = False
    face_count = mod.face_count
    bpy.ops.object.modifier_apply(modifier=mod.name)
    return obj, face_count

def generate_lod_chain(master_obj, ratios, output_dir: Path, base_name: str, preserve_uvs: bool):
    """
    Cascade decimation: each LOD from the previous LOD (not from source).
    Produces smoother visual transitions and better attribute preservation.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    prev_obj = master_obj

    for i, ratio in enumerate(ratios):
        lod_name = f"{base_name}_LOD{i}"
        if i == 0:
            lod_obj = master_obj
            lod_obj.name = lod_name
        else:
            bpy.ops.object.select_all(action='DESELECT')
            prev_obj.select_set(True)
            bpy.ops.object.duplicate()
            lod_obj = bpy.context.active_object
            lod_obj.name = lod_name
            step_ratio = ratio / ratios[i - 1] if ratios[i - 1] > 0 else ratio
            _apply_decimate(lod_obj, step_ratio, preserve_uvs)

        out_path = str(output_dir / f"{lod_name}.glb")
        bpy.ops.object.select_all(action='DESELECT')
        lod_obj.select_set(True)
        bpy.ops.export_scene.gltf(
            filepath=out_path, use_selection=True, export_format='GLB',
            export_normals=True, export_texcoords=True,
        )
        print(f"[Forge] {lod_name}: {len(lod_obj.data.polygons)} faces → {out_path}")
        prev_obj = lod_obj

def main():
    args = parse_args()
    output_dir = Path(args.output_dir)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    obj = import_mesh(args.input)
    base_name = Path(args.input).stem
    prep_mesh(obj)
    if args.use_quadriflow:
        obj = quadriflow_remesh(obj, target_faces=args.target_faces, seed=args.seed)
    generate_lod_chain(obj, args.lod_ratios, output_dir, base_name, args.preserve_uvs)
    print(f"[Forge] LOD chain complete: {output_dir}")

if __name__ == "__main__":
    main()
```

---

## §3. QuadriFlow Notes

- Does NOT guarantee exact face count — treat `target_faces` as a hint; actual result ±20%
- Shape key meshes are **incompatible** with QuadriFlow (changing topology breaks shape keys)
- Deterministic output requires `seed=42` (or any fixed seed)
- Blender 5.0+ required for Quadify Ultra add-on; built-in QuadriFlow works on 4.5 LTS

---

## §4. Voxel Remesh via Modifier

```python
# WRONG — operator version freezes Blender on meshes > ~15k faces:
bpy.ops.object.voxel_remesh()

# CORRECT — modifier runs in Blender's C stack, non-blocking:
mod = obj.modifiers.new("VoxelRemesh", 'REMESH')
mod.mode = 'VOXEL'
mod.voxel_size = 0.02   # smaller = higher resolution = more faces
bpy.ops.object.modifier_apply(modifier=mod.name)
```

---

## §5. High-to-Low Normal Baking

```python
"""
bake_normals.py — Bake tangent-space normal map: high-poly → low-poly.
Engine MUST be CYCLES — EEVEE cannot bake.
Preconditions: low-poly has UVs; both objects at same world position.
cage_extrusion: 0.02–0.05m; increase for high-detail displacement.
"""
import bpy
from pathlib import Path

def bake_normal_map(high_poly, low_poly, output_path: str,
                    resolution=2048, cage_extrusion=0.04):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = 32
    scene.cycles.seed = 0   # deterministic sampling — same input → byte-identical normal map
    scene.render.bake.use_selected_to_active = True
    scene.render.bake.cage_extrusion = cage_extrusion
    scene.render.bake.margin = 16
    scene.render.bake.margin_type = 'EXTEND'

    img = bpy.data.images.new("BakedNormal", width=resolution, height=resolution,
                               alpha=False, float_buffer=True)
    img.colorspace_settings.name = 'Non-Color'

    for slot in low_poly.material_slots:
        mat = slot.material or bpy.data.materials.new("BakeMat")
        mat.use_nodes = True
        slot.material = mat
        node = mat.node_tree.nodes.new('ShaderNodeTexImage')
        node.image = img
        node.select = True
        mat.node_tree.nodes.active = node

    bpy.ops.object.select_all(action='DESELECT')
    high_poly.select_set(True)
    low_poly.select_set(True)
    bpy.context.view_layer.objects.active = low_poly

    bpy.ops.object.bake(type='NORMAL', use_selected_to_active=True,
                        normal_space='TANGENT', cage_extrusion=cage_extrusion)

    img.filepath_raw = output_path
    img.file_format = 'PNG'
    img.save()
    print(f"[Forge] Baked → {output_path} ({resolution}×{resolution})")
```

**Common failure: RuntimeError "No objects or images found to bake to"**
- Cause (a): active object (low-poly) has no Image Texture node in material
- Cause (b): engine is not CYCLES
- Fix: set `scene.render.engine = 'CYCLES'`; ensure the Image Texture node is active

---

## §6. gltfpack LOD Chain (PowerShell)

```powershell
# forge_lod_gltfpack.ps1
# Requires gltfpack.exe in PATH: https://github.com/zeux/meshoptimizer/releases
# -si R: simplify ratio (fraction of original triangles)
# -sa:   aggressive mode (ignores topology constraints) — use only for LOD3+
# -v:    verbose (shows triangle counts for verification)
param(
    [string]$InputGlb,
    [string]$OutputDir,
    [string]$BaseName = ""
)
if (-not $BaseName) {
    $BaseName = [System.IO.Path]::GetFileNameWithoutExtension($InputGlb)
}
New-Item -ItemType Directory -Force -Path $OutputDir | Out-Null

$lods = @(
    @{ suffix="LOD0"; ratio=1.0;   aggressive=$false },
    @{ suffix="LOD1"; ratio=0.5;   aggressive=$false },
    @{ suffix="LOD2"; ratio=0.25;  aggressive=$false },
    @{ suffix="LOD3"; ratio=0.1;   aggressive=$true  },
    @{ suffix="LOD4"; ratio=0.05;  aggressive=$true  }
)

foreach ($lod in $lods) {
    $out = Join-Path $OutputDir "${BaseName}_$($lod.suffix).glb"
    $a   = @("-i", $InputGlb, "-o", $out, "-si", $lod.ratio, "-v")
    if ($lod.aggressive) { $a += "-sa" }
    Write-Host "[Forge] Generating $($lod.suffix) (ratio=$($lod.ratio))..."
    & gltfpack @a
    if ($LASTEXITCODE -ne 0) { Write-Error "gltfpack failed"; exit 1 }
}
Write-Host "[Forge] LOD chain: $OutputDir"
```

**If gltfpack -si produces no simplification:**
1. Faceted normals / split vertices → weld first:
   `gltf-transform weld input.glb welded.glb --tolerance 0.0001`
2. Error threshold too tight → add `-sa` (aggressive)
3. Non-manifold seams → repair in Blender first

---

## §7. gltf-transform LOD Chain (Node.js alternative)

Use when the pipeline is already Node.js-based. Install:
`npm install @gltf-transform/core @gltf-transform/functions meshoptimizer`

Key pattern: clone the **previous LOD document** for cascade simplification (not the source),
compute `stepRatio = LOD_RATIOS[i] / LOD_RATIOS[i-1]`, then:
```javascript
await lodDoc.transform(
    weld({ tolerance: 0.0001 }),
    simplify({ simplifier: MeshoptSimplifier, ratio: stepRatio, error: 0.001 })
);
```
Prefer the PowerShell gltfpack approach (§6) for simpler Windows pipelines.

---

## §8. Open3D / trimesh / PyMeshLab Decimation (No Blender)

For detailed code, parameter tables, and gotchas see **`references/mesh-libs.md §6`**.
Quick summary:
- **Open3D QEM:** `mesh.simplify_quadric_decimation(target_number_of_triangles=N)` — best quality
- **fast-simplification:** `fast_simplification.simplify(verts, faces, target_reduction=0.9)` — fastest
- **PyMeshLab:** `ms.meshing_decimation_quadric_edge_collapse(targetfacenum=N, preserveboundary=True)` — best boundary preservation

---

## §9. Poly Budget Targets & Screen Coverage Thresholds

| Asset type | LOD0 | LOD1 | LOD2 | LOD3 | LOD4 |
|---|---|---|---|---|---|
| Hero character | 15k–30k tris | 7.5k | 3.75k | 1k | Billboard |
| Env prop (large) | 5k–10k | 2.5k | 1k | 300 | — |
| Env prop (small) | 500–2k | 250 | 100 | — | — |
| Photogrammetry | 100k–500k raw → retopo 10k–30k | cascade | cascade | — | — |
| Vehicle (game) | 30k–50k | 15k | 7.5k | 2k | Billboard |

| LOD | Unity screen height | Unreal screen size |
|---|---|---|
| LOD0 | 50%+ | 1.0 |
| LOD1 | 25–49% | 0.25–0.5 |
| LOD2 | 10–24% | 0.1–0.25 |
| LOD3 | 2–9% | 0.02–0.1 |
| Culled | < 2% | < 0.02 |

---

## §10. LOD Naming Conventions

**Unity (auto-LODGroup on import):**
```
Mesh_LOD0.fbx   ← most detailed
Mesh_LOD1.fbx
Mesh_LOD2.fbx
Mesh_LOD3.fbx
```

**Unreal (Static Mesh):**
```
SM_Mesh_LOD0    ← SM_ prefix = Static Mesh
SM_Mesh_LOD1
SM_Mesh_LOD2
```

---

## Determinism

The whole retopo + LOD chain must be reproducible: **same source mesh + same `--lod-ratios`
+ same `--seed` + same Blender version → byte-identical LOD GLBs and a byte-identical baked
normal map.** This matches forge-model (`cycles.seed=0`) and forge-procedural (isolated RNG +
`assert_reproducible`). What makes it deterministic:

- **QuadriFlow / Voxel remesh** require a fixed seed. `--seed` (default 42) is threaded into
  `quadriflow_remesh()` — never leave the seed as a bare literal that can drift between runs.
- **Normal bake** uses `scene.cycles.seed = 0` (§5) so Cycles sampling noise is identical every
  run; without it the baked normal map carries non-deterministic sampling noise.
- **LOD ratios are deterministic** and decimation is **cascade** (each LOD derived from the
  previous LOD, not re-decimated from source — see §2 `generate_lod_chain`), so the chain is
  reproducible step-by-step.
- **Pin the Blender version in `FORGE.md`.** QuadriFlow, Decimate and the glTF exporter can
  change output across Blender releases; the byte-for-byte guarantee holds only within one
  pinned version. Record it alongside the seed in the pipeline log.

---

## §11. Gotchas → Fixes

| Gotcha | Fix |
|--------|-----|
| `voxel_remesh()` operator freezes on meshes > 15k faces | Use REMESH modifier (C stack, non-blocking) |
| QuadriFlow result overshoots target by 20%+ | Apply fallback Decimate COLLAPSE after |
| Shape key meshes fail QuadriFlow / Voxel remesh | Skip remesh; use Decimate UNSUBDIV only |
| Decimate collapses UV seams | Set `mod.delimit = {'UV', 'SEAM', 'SHARP'}` |
| `modifier_apply()` context error in headless | Always set `view_layer.objects.active = obj` first |
| Bake fails: "No objects or images found to bake to" | Ensure CYCLES engine + Image Texture node active in low-poly material |
| gltfpack `-si` produces no simplification | Weld vertices first with gltf-transform; use `-sa` for aggressive |
| Instant Meshes opens GUI instead of batch mode | Always include `-o output.obj`; batch mode triggered by output flag |
| `vc_redist` missing for Instant Meshes | Install Visual C++ Redistributable 2015+ from Microsoft |
