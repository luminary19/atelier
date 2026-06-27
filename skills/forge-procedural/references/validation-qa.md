# Procedural Geometry — Validation & QA

Covers: in-script validators, render-verify snippet, PowerShell QA shell.  
Run these checks inside the Blender script (before render) and after export (outside Blender).

---

## In-script validators (run before render)

### Geometry Nodes output validator

```python
import bpy

def validate_gn_output(obj: bpy.types.Object, mod_name: str) -> dict:
    """
    Evaluate the GN modifier and inspect the resulting mesh.
    Call BEFORE render to catch empty/broken modifier output.
    """
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj  = obj.evaluated_get(depsgraph)
    mesh      = eval_obj.to_mesh()

    result = {
        "vertex_count": len(mesh.vertices),
        "face_count":   len(mesh.polygons),
        "has_geometry": len(mesh.vertices) > 0,
        "bounding_box": [list(v) for v in obj.bound_box],
    }
    eval_obj.to_mesh_clear()

    if not result["has_geometry"]:
        raise AssertionError(f"[Forge QA] Modifier '{mod_name}' produced empty geometry!")

    print(f"[Forge QA] {mod_name}: {result['vertex_count']} verts, {result['face_count']} faces")
    return result

def validate_node_tree_links(ng: bpy.types.GeometryNodeTree) -> bool:
    """Check that Group Output has at least one connected Geometry input."""
    out_node = next((n for n in ng.nodes if n.type == 'GROUP_OUTPUT'), None)
    if out_node is None:
        raise AssertionError("No Group Output node!")
    geo_input = out_node.inputs.get("Geometry")
    if geo_input is None or not geo_input.is_linked:
        raise AssertionError("Group Output 'Geometry' input is not connected!")
    return True
```

### L-system validator

```python
def validate_lsystem_output(obj, expected_min_verts=50):
    mesh = obj.data
    n_verts = len(mesh.vertices)
    assert n_verts >= expected_min_verts, f"Too few vertices: {n_verts}"
    assert len(mesh.edges) > 0, "No edges — topology broken"
    bb = [v[:] for v in obj.bound_box]
    extents = [max(bb, key=lambda v: v[i])[i] - min(bb, key=lambda v: v[i])[i] for i in range(3)]
    assert min(extents) > 0.01, f"Degenerate bounding box: {extents}"
    print(f"[QA] L-system OK: {n_verts} verts, {len(mesh.edges)} edges, extents={[f'{e:.2f}' for e in extents]}")
```

### WFC result validator

```python
def validate_wfc_result(result):
    gx=len(result); gy=len(result[0]); gz=len(result[0][0])
    none_count = sum(1 for x in range(gx) for y in range(gy) for z in range(gz)
                     if result[x][y][z] is None)
    assert none_count == 0, f"WFC: {none_count}/{gx*gy*gz} contradiction cells"
    print(f"[QA] WFC OK: {gx*gy*gz} cells, 0 contradictions")
```

### Scatter count validator

```python
def validate_scatter_count(plane_obj, expected_min=10, expected_max=10000):
    depsgraph = bpy.context.evaluated_depsgraph_get()
    eval_obj = plane_obj.evaluated_get(depsgraph)
    instance_count = sum(1 for inst in depsgraph.object_instances if inst.parent == eval_obj)
    assert expected_min <= instance_count <= expected_max, \
        f"Scatter count {instance_count} outside [{expected_min}, {expected_max}]"
    print(f"[QA] Scatter OK: {instance_count} instances")
```

---

## SDF mesh validator (post-export, outside Blender)

```python
import trimesh, numpy as np

def validate_sdf_mesh(path, expected_volume_range=None):
    """Full geometric check on an SDF-derived mesh."""
    mesh = trimesh.load_mesh(path)
    report = {
        'vertices': len(mesh.vertices),
        'faces': len(mesh.faces),
        'is_watertight': mesh.is_watertight,
        'is_winding_consistent': mesh.is_winding_consistent,
        'euler_number': mesh.euler_number,  # 2 = sphere topology
        'volume': mesh.volume if mesh.is_watertight else None,
        'surface_area': mesh.area,
        'bounding_box': mesh.bounding_box.extents.tolist(),
    }
    assert mesh.is_watertight, f"Mesh not watertight: {path}"
    assert mesh.euler_number == 2, f"Unexpected topology (euler={mesh.euler_number})"
    if expected_volume_range:
        lo, hi = expected_volume_range
        assert lo <= mesh.volume <= hi, f"Volume {mesh.volume:.4f} outside {lo}–{hi}"
    areas = mesh.area_faces
    degenerate = np.sum(areas < 1e-10)
    assert degenerate == 0, f"{degenerate} degenerate faces found"
    print(f"[QA] SDF mesh OK: {report['vertices']} verts, {report['faces']} faces, "
          f"watertight={report['is_watertight']}, euler={report['euler_number']}")
    return report
```

---

## Render-verify snippet (in-Blender, uses numpy)

```python
import bpy, os
import numpy as np  # available in Blender's bundled Python

def render_and_verify(out_path: str, min_non_black_fraction: float = 0.02) -> bool:
    """
    Render scene to PNG, then load pixel data to verify non-trivial output.
    out_path: absolute forward-slash path.
    """
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    scene = bpy.context.scene
    scene.render.filepath = out_path.replace("\\", "/")
    scene.render.image_settings.file_format = 'PNG'
    bpy.ops.render.render(write_still=True)

    img = bpy.data.images.load(out_path, check_existing=False)
    px  = np.array(img.pixels[:])
    rgb = px.reshape(-1, 4)[:, :3]
    non_black = np.any(rgb > 0.01, axis=1).mean()
    bpy.data.images.remove(img)

    if non_black < min_non_black_fraction:
        raise AssertionError(
            f"[Forge QA] Render appears blank: {non_black*100:.1f}% non-black pixels"
        )
    print(f"[Forge QA] Render OK: {non_black*100:.1f}% non-black at {out_path}")
    return True
```

---

## Render output file validator (after render, no bpy required)

```python
import os

def validate_render_output(filepath):
    assert os.path.exists(filepath), f"Render output missing: {filepath}"
    size = os.path.getsize(filepath)
    assert size > 5000, f"Render suspiciously small ({size} bytes) — likely all-black"
    print(f"[QA] Render OK: {filepath} ({size/1024:.1f} KB)")
```

---

## Determinism check

```python
def assert_reproducible(build_fn, seed: int, out_dir: str, run_count: int = 2):
    """
    Call build_fn(seed) twice, compare vertex counts.
    build_fn must return (obj, mod_name).
    """
    counts = []
    for i in range(run_count):
        bpy.ops.object.select_all(action='SELECT')
        bpy.ops.object.delete(use_global=True)
        obj, mod_name = build_fn(seed)
        result = validate_gn_output(obj, mod_name)
        counts.append(result["vertex_count"])
    assert len(set(counts)) == 1, f"Non-deterministic! Vertex counts: {counts}"
    print(f"[Forge QA] Reproducibility OK: {run_count} runs, {counts[0]} verts each")
```

---

## SDF eikonal check (field self-verification)

```python
def verify_sdf_eikonal(sdf_func, n_samples=10000, bounds=((-2,-2,-2),(2,2,2))):
    """
    Check that SDF approximately satisfies |∇f| ≈ 1 (eikonal equation).
    True SDFs: mean deviation < 0.05. TPMS formulas: deviation ≈ 0.5–1.5 (expected, not a bug).
    """
    lo, hi = map(lambda x: [float(v) for v in x], bounds)
    import numpy as np
    pts = np.random.uniform(lo, hi, (n_samples, 3))
    eps = 1e-4

    d  = sdf_func(pts)
    dx = (sdf_func(pts + [eps,0,0]) - sdf_func(pts - [eps,0,0])) / (2*eps)
    dy = (sdf_func(pts + [0,eps,0]) - sdf_func(pts - [0,eps,0])) / (2*eps)
    dz = (sdf_func(pts + [0,0,eps]) - sdf_func(pts - [0,0,eps])) / (2*eps)
    grad_mag = np.sqrt(dx**2 + dy**2 + dz**2)
    dev = np.abs(grad_mag - 1.0)

    print(f"Gradient magnitude: mean={grad_mag.mean():.4f}, max={grad_mag.max():.4f}")
    print(f"Eikonal deviation:  mean={dev.mean():.4f}, max={dev.max():.4f}")
    # True SDF:  dev.mean() < 0.05
    # Gyroid:    dev.mean() ≈ 0.5–1.5 (this is expected — not an error)
```

---

## PowerShell QA shell

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender\blender.exe"
$script  = "C:\Forge\build_and_verify.py"
$outDir  = "C:\Forge\qa_out"

# Run script with seed
& $blender -b --factory-startup -P $script -- --seed 42 --out "$outDir/test.png"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[Forge QA] Blender exited with code $LASTEXITCODE"
    exit 1
}

# Check PNG was produced
if (-not (Test-Path "$outDir/test.png")) {
    Write-Error "[Forge QA] Expected PNG not found at $outDir/test.png"
    exit 1
}

# Check it's not trivially small (< 5 KB = likely all-black)
$size = (Get-Item "$outDir/test.png").Length
if ($size -lt 5000) {
    Write-Error "[Forge QA] PNG suspiciously small: $size bytes (render may be all-black)"
    exit 1
}

Write-Host "[Forge QA] PASS — $([math]::Round($size/1024, 1)) KB" -ForegroundColor Green
```

---

## Visual failure diagnosis table

After `Read(png_path)` — common failure modes:

| What you see | Cause | Fix |
|-------------|-------|-----|
| All black | `scene.camera` not set, or output path directory missing | `bpy.context.scene.camera = cam_obj`; `os.makedirs(...)` |
| All grey | No lighting | `bpy.ops.object.light_add(type='SUN', location=(5,5,10))` |
| Single dot or point cloud | Instances not realized in viewport evaluation | Add `GeometryNodeRealizeInstances`; or call `bpy.context.view_layer.update()` before render |
| Geometry out of frame | Wrong object scale or camera position | Check `obj.dimensions`; use `bpy.ops.view3d.camera_to_view_selected()` to fit |
| Tiny specks / noise | `cycles.samples` too low | Increase to 64–128; enable `cycles.use_denoising = True` |
| Correct shape, wrong orientation | Y-up vs Z-up mismatch | Check FORGE.md coordinate system; rotate object or camera accordingly |
