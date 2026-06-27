# forge-topology — Python Mesh-Processing Libraries Reference

## Contents
- §1. Library roles & install
- §2. trimesh — load, inspect, repair, decimate
- §3. Open3D — load, inspect, decimate, headless render
- §4. PyMeshLab — comprehensive repair & remesh pipeline
- §5. Watertight / manifold checks (all three libs)
- §6. Decimation comparison
- §7. Headless visual QA (no display)
- §8. Programmatic validation function
- §9. Gotchas → fixes

---

## §1. Library Roles & Install

| Library | Role | License | Install |
|---|---|---|---|
| trimesh | Repair, watertight check, boolean, voxelize, ray cast, quick render | MIT | `pip install "trimesh[easy]"` |
| manifold3d | Fast robust booleans, guaranteed manifold output | Apache-2.0 | `pip install manifold3d` |
| embreex | Fast ray queries (600k+ rays/sec vs pure-Python fallback) | Apache-2.0 | `pip install embreex` |
| fast-simplification | MIT, faster than pyfqmr for decimation | MIT | `pip install fast-simplification` |
| Open3D | QEM decimation, normal estimation, OffscreenRenderer (Windows, no display needed) | MIT | `pip install open3d` |
| PyMeshLab | 200+ MeshLab filters: complex hole closing, isotropic remesh | GPL-3.0 | `pip install pymeshlab` |

**Version pins for production:**
```
trimesh==4.12.2
manifold3d>=2.3.0
embreex>=0.1.0
fast-simplification==0.1.13
open3d==0.19.0
pymeshlab==2025.7.post1
```

**Default for most Forge work:** trimesh + manifold3d.
Add Open3D for QEM decimation and headless color renders.
Add PyMeshLab only for complex holes (> 4 edges) or isotropic remeshing.

---

## §2. trimesh — Load, Inspect, Repair, Decimate

```python
import trimesh, trimesh.repair as repair, numpy as np

# Load — format auto-detected by extension
mesh = trimesh.load("model.stl")

# Multi-body STL/GLTF may return a Scene, not a Trimesh — always handle:
if isinstance(mesh, trimesh.Scene):
    mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

# Inspect
print(f"Verts: {len(mesh.vertices)}, Faces: {len(mesh.faces)}")
print(f"Bounds: {mesh.bounds}")         # (2,3) [[min_x,y,z],[max_x,y,z]]
print(f"is_watertight: {mesh.is_watertight}")
print(f"is_winding_consistent: {mesh.is_winding_consistent}")
print(f"is_volume: {mesh.is_volume}")   # watertight + positive volume

# Save
mesh.export("output.glb")   # preferred: binary, fast, preserves UVs/materials
mesh.export("output.stl")
mesh.export("output.obj")

# Repair pipeline
mesh.process(validate=True)            # merge duplicate verts, remove degenerate/NaN
repair.fix_normals(mesh, multibody=True)
was_watertight = mesh.fill_holes()     # handles single-tri and single-quad holes only
# For larger holes → use PyMeshLab (see §4)

# Decimation via fast-simplification
import fast_simplification
pts, faces = fast_simplification.simplify(
    np.array(mesh.vertices, dtype=np.float32),
    np.array(mesh.faces,    dtype=np.int32),
    target_reduction=0.9   # remove 90% of faces
)
mesh_lod = trimesh.Trimesh(vertices=pts, faces=faces, process=False)
```

---

## §3. Open3D — Load, Inspect, Decimate, Headless Render

```python
import open3d as o3d
import numpy as np

mesh = o3d.io.read_triangle_mesh("model.ply")
mesh.compute_vertex_normals()   # required before most operations

# Inspect
print(f"Verts: {len(mesh.vertices)}, Tris: {len(mesh.triangles)}")
print(f"edge_manifold: {mesh.is_edge_manifold(allow_boundary_edges=False)}")
print(f"vertex_manifold: {mesh.is_vertex_manifold()}")
print(f"self_intersecting: {mesh.is_self_intersecting()}")
print(f"watertight: {mesh.is_watertight()}")
print(f"orientable: {mesh.is_orientable()}")

# Repair
mesh.remove_duplicated_vertices()
mesh.remove_duplicated_triangles()
mesh.remove_degenerate_triangles()
mesh.remove_non_manifold_edges()
mesh.remove_unreferenced_vertices()
mesh.orient_triangles()

# QEM decimation — best quality, preserves silhouette
lod = mesh.simplify_quadric_decimation(target_number_of_triangles=5000)
lod.compute_vertex_normals()
o3d.io.write_triangle_mesh("lod_qem.ply", lod)

# Vertex clustering — O(N), faster for >10x reduction
voxel_size = max(mesh.get_max_bound() - mesh.get_min_bound()) / 32
coarse = mesh.simplify_vertex_clustering(
    voxel_size, o3d.geometry.SimplificationContraction.Average
)

# Headless color render — OffscreenRenderer works on Windows pip wheel WITHOUT headless=True
renderer = o3d.visualization.rendering.OffscreenRenderer(1920, 1080)  # no headless kwarg!
mat = o3d.visualization.rendering.MaterialRecord()
mat.shader = "defaultLit"
renderer.scene.add_geometry("mesh", mesh, mat)
renderer.scene.set_background([0.2, 0.2, 0.2, 1.0])

bbox = mesh.get_axis_aligned_bounding_box()
c    = bbox.get_center()
ext  = np.linalg.norm(bbox.get_max_bound() - bbox.get_min_bound())
renderer.setup_camera(60.0, c, c + [ext, ext, ext], [0, 1, 0])

img = renderer.render_to_image()
o3d.io.write_image("render.png", img)
```

**O3D large mesh OOM fix:** pre-decimate with vertex clustering before QEM:
```python
coarse = mesh.simplify_vertex_clustering(voxel_size, ...)
fine   = coarse.simplify_quadric_decimation(target_number_of_triangles=50000)
```

---

## §4. PyMeshLab — Comprehensive Repair & Remesh

```python
import pymeshlab

# Compatible shim for PercentageValue (name changed across versions)
PctVal = getattr(pymeshlab, "PercentageValue", None) or getattr(pymeshlab, "Percentage")

ms = pymeshlab.MeshSet()
ms.load_new_mesh("C:/path/to/model.obj")   # forward slashes on Windows

# Full repair pipeline
ms.meshing_remove_unreferenced_vertices()
ms.meshing_remove_duplicate_vertices()
ms.meshing_remove_duplicate_faces()
ms.meshing_remove_null_faces()
ms.meshing_merge_close_vertices(threshold=PctVal(0.1))  # 0.1% of bbox diagonal
ms.meshing_repair_non_manifold_edges(method=0)          # 0=Remove Faces (safer)
ms.meshing_repair_non_manifold_vertices(vertdispratio=0.0)

# Close holes — use PyMeshLab for holes > 4 edges (trimesh cannot)
ms.meshing_close_holes(maxholesize=100, selfintersection=True)

# Remove small disconnected noise components
ms.meshing_remove_connected_component_by_face_number(mincomponentsize=25)

# Inspect
out = ms.get_geometric_measures()
print(f"Volume: {out['mesh_volume']:.6f}")
print(f"Surface area: {out['surface_area']:.6f}")
print(f"Avg edge length: {out['avg_edge_length']:.6f}")

# Topology audit
topo = ms.get_topological_measures()
# Keys: loop_number, connected_components_number, genus, is_two_manifold,
#       boundary_edges_number, non_two_manifold_edges_number, etc.
print(topo)

# QEM decimation with PyMeshLab
ms.meshing_decimation_quadric_edge_collapse(
    targetfacenum=10000,
    preserveboundary=True,
    preservenormal=True,
    optimalplacement=True,
    qualitythr=0.3,
)

# Isotropic remeshing (uniform triangle size — useful before ML/FEM)
ms.meshing_isotropic_explicit_remeshing(
    iterations=3,
    targetlen=PctVal(1.0),   # 1% of bbox diagonal per edge
)

ms.save_current_mesh("C:/path/repaired.obj", save_vertex_normal=True)
```

---

## §5. Watertight / Manifold Checks

```python
# trimesh — fast, comprehensive
mesh = trimesh.load("model.stl")
if isinstance(mesh, trimesh.Scene):
    mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

print(mesh.is_watertight)           # closed + manifold + consistent winding
print(mesh.is_winding_consistent)   # all faces wound same direction
print(mesh.is_volume)               # watertight AND volume > 0

broken = trimesh.repair.broken_faces(mesh)
print(f"Broken faces: {len(broken)}")

# Multi-body: always check body count first
if not mesh.is_watertight:
    bodies = mesh.split()
    for i, body in enumerate(bodies):
        print(f"Body {i}: watertight={body.is_watertight}")

# Open3D — more granular
mesh_o3d = o3d.io.read_triangle_mesh("model.ply")
print(mesh_o3d.is_edge_manifold(allow_boundary_edges=False))
print(mesh_o3d.is_vertex_manifold())
print(mesh_o3d.is_self_intersecting())

# PyMeshLab — full topology report
ms = pymeshlab.MeshSet(); ms.load_new_mesh("model.stl")
topo = ms.get_topological_measures()
print(topo)
```

---

## §6. Decimation Comparison

| Method | Quality | Speed | Boundary preservation | When to use |
|---|---|---|---|---|
| PyMeshLab QEM + `preserveboundary=True` | Best | Slow | Yes | Production; UV-seam-critical assets |
| Open3D QEM `simplify_quadric_decimation` | High | Fast | Moderate | Standard LOD reduction |
| fast-simplification | Good | Fastest | Moderate | Large batches; pipeline speed matters |
| Vertex clustering (O3D) | Low | Very fast | No | Preview LODs; > 10× reduction |

**Rule: QEM > vertex-clustering for quality.** Use vertex clustering only for previews or
as a pre-pass before QEM when mesh > 1M faces (OOM prevention).

---

## §7. Headless Visual QA (No Display)

```python
"""
Render a depth image headlessly — pure Python, no GPU, no display.
Uses trimesh ray casting + PIL.
"""
import numpy as np, trimesh
from PIL import Image

def render_depth_png(mesh_path: str, out_path: str, resolution=(640, 480)):
    mesh = trimesh.load(mesh_path)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

    scene = mesh.scene()
    scene.camera.resolution = list(resolution)
    scene.camera.fov = 60 * (np.array(resolution) / max(resolution))

    origins, vectors, pixels = scene.camera_rays()
    pts, idx_ray, idx_tri = mesh.ray.intersects_location(
        origins, vectors, multiple_hits=False
    )
    if len(pts) == 0:
        raise ValueError("No ray hits — check mesh orientation/position")

    depth  = trimesh.util.diagonal_dot(pts - origins[0], vectors[idx_ray])
    d_norm = (depth - depth.min()) / np.ptp(depth)
    img    = np.zeros(resolution, dtype=np.uint8)
    img[pixels[idx_ray, 0], pixels[idx_ray, 1]] = (d_norm * 255).astype(np.uint8)

    Image.fromarray(img).save(out_path)
    return out_path
```

---

## §8. Programmatic Validation Function

```python
import trimesh, trimesh.repair as repair, numpy as np

def validate_mesh(path: str, require_watertight: bool = True) -> dict:
    mesh = trimesh.load(path)
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

    n_verts    = len(mesh.vertices)
    n_faces    = len(mesh.faces)
    has_nan    = not np.isfinite(mesh.vertices).all()
    degenerate = int((~mesh.nondegenerate_faces()).sum())

    mesh.process(validate=True)
    repair.fix_normals(mesh, multibody=True)
    mesh.fill_holes()

    result = {
        "path": path,
        "n_verts": n_verts, "n_faces": n_faces,
        "had_nan": has_nan, "degenerate_faces_removed": degenerate,
        "is_watertight": mesh.is_watertight,
        "is_winding_consistent": mesh.is_winding_consistent,
        "is_volume": mesh.is_volume,
        "volume": float(mesh.volume) if mesh.is_volume else None,
        "surface_area": float(mesh.area),
        "center_mass": mesh.center_mass.tolist() if mesh.is_volume else None,
        "bounds": mesh.bounds.tolist(),
    }
    if require_watertight and not mesh.is_volume:
        raise ValueError(
            f"Mesh at {path} is not a valid volume after repair. "
            "Run PyMeshLab meshing_close_holes for complex holes."
        )
    return result
```

---

## §9. Gotchas → Fixes

| Gotcha | Fix |
|--------|-----|
| `mesh.volume < 0` even though `is_watertight` is True | All normals point inward — `repair.fix_inversion(mesh)` |
| `fill_holes()` returns False (holes > 4 edges) | Use `PyMeshLab.meshing_close_holes(maxholesize=100–500)` |
| Boolean fails "Not all meshes are volumes!" | Repair each input first; check `is_volume` before calling |
| `OffscreenRenderer(headless=True)` crashes on Windows | Omit `headless` kwarg — Linux-only flag; Windows pip wheel works without it |
| `draw_geometries()` hangs in headless | Use `OffscreenRenderer` instead; never `draw_geometries()` in scripts |
| `trimesh.scene.save_image()` fails without display (Windows) | Use ray-trace depth render (§7) or Open3D OffscreenRenderer |
| PyMeshLab `PercentageValue` vs `Percentage` class name mismatch | Use compatibility shim: `PctVal = getattr(pymeshlab, "PercentageValue", None) or getattr(pymeshlab, "Percentage")` |
| PyMeshLab filter name mismatch (`close_holes` → `meshing_close_holes`) | Run `ms.filter_list()` to get current names; check pymeshlab.readthedocs.io |
| `embreex` not accelerating ray queries | Verify: `import trimesh; print(trimesh.ray.ray_pyembree)` (should not be None) |
| OOM during QEM on >1M face mesh | Pre-decimate with vertex clustering first, then apply QEM |
| Windows path backslashes in PyMeshLab | Use forward slashes or raw strings: `r"C:\path\model.obj"` |
| `trimesh.load()` returns Scene not Trimesh | Always: `if isinstance(mesh, trimesh.Scene): mesh = trimesh.util.concatenate(...)` |
| `mesh.voxelized()` returns all-empty grid | Mesh not watertight — repair to `is_volume=True` first |
