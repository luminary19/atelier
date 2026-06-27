# Forge Validate — Mesh Repair Reference
# Contents
- §1. Repair decision tree
- §2. trimesh repair (light — most cases)
- §3. PyMeshLab repair (heavy — complex holes)
- §4. Blender bmesh repair (topology-aware)
- §5. Normals-specific fixes
- §6. Boolean cleanup

---

## §1. Repair Decision Tree

```
Is mesh.is_volume True?
  YES → Pass; skip repair
  NO →
    broken_faces == 0 AND is_winding_consistent == False?
      → Fix winding first: repair.fix_winding(mesh)
    broken_faces > 0 AND count <= 4?
      → trimesh fill_holes (light repair)
    broken_faces > 0 AND count > 4?
      → PyMeshLab meshing_close_holes (heavy repair)
    volume < 0 (all normals inward)?
      → mesh.invert()
    Still failing after PyMeshLab?
      → Alpha wrap (destroys fine detail — last resort)
      → Or: Skill("forge-topology") for manual topology surgery
```

---

## §2. trimesh Repair (Light — Most Cases)

**API note — targets `trimesh>=4.0`.** The standalone `mesh.remove_degenerate_faces()`,
`mesh.remove_duplicate_faces()` and (in older code) `mesh.remove_unreferenced_vertices()`
helpers are DEPRECATED/removed in trimesh 4.x and raise on a modern install — trimesh's own
message: *"`remove_duplicate_faces` is deprecated … replace with
`mesh.update_faces(mesh.unique_faces())`"*. The robust replacement is `mesh.process(validate=True)`,
which already runs `unique_faces() & nondegenerate_faces()` plus `fix_normals()` internally
(verified against trimesh 4.12 source). Lean on it instead of the individual `remove_*` calls.

```python
import trimesh, trimesh.repair as repair, numpy as np  # trimesh>=4.0

def repair_light(path: str, out_path: str) -> dict:
    """Standard repair pass. Use for meshes with minor holes/winding issues."""
    mesh = trimesh.load(path, force="mesh")
    if isinstance(mesh, trimesh.Scene):
        mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

    # Step 1: baseline cleanup (ALWAYS run first — prerequisite for everything else).
    # process(validate=True) merges duplicate verts, drops NaN/Inf, AND removes duplicate +
    # degenerate faces (unique_faces() & nondegenerate_faces()) + fixes normals. This single
    # call replaces the deprecated remove_degenerate_faces()/remove_duplicate_faces() pair.
    mesh.process(validate=True)

    # Step 2: winding consistency
    repair.fix_winding(mesh)

    # Step 3: normals pointing outward
    repair.fix_normals(mesh, multibody=True)

    # Step 4: fill holes (tri/quad only by default)
    was_watertight = mesh.fill_holes()
    if not was_watertight:
        # Try fan mode for slightly larger holes
        repair.fill_holes(mesh, use_fan=True)

    # Step 5: drop any now-unreferenced verts (4.x: still present; else mesh.merge_vertices())
    if hasattr(mesh, "remove_unreferenced_vertices"):
        mesh.remove_unreferenced_vertices()
    else:
        mesh.merge_vertices()

    # Step 6: fix inside-out volume
    if mesh.is_volume and mesh.volume < 0:
        mesh.invert()

    mesh.export(out_path)
    return {
        "is_volume": mesh.is_volume,
        "volume": float(mesh.volume) if mesh.is_volume else None,
        "faces": len(mesh.faces),
        "broken_faces_remaining": len(repair.broken_faces(mesh)),
    }
```

**When trimesh fill_holes fails (holes > 4 edges):**
```python
# Detect which holes are too large
from trimesh.repair import broken_faces
broken = broken_faces(mesh)
print(f"Broken face count: {len(broken)}")
# > 0 after fill_holes → escalate to PyMeshLab
```

---

## §3. PyMeshLab Repair (Heavy — Complex Holes)

**Requires: `pip install pymeshlab` (GPL-3.0 — check license for commercial use)**

```python
import pymeshlab as pml

# PercentageValue name changed in 2022.2 — use this compatible shim:
PctVal = getattr(pml, "PercentageValue", None) or getattr(pml, "Percentage")

def repair_heavy(input_path: str, output_path: str, close_hole_max_size: int = 200) -> dict:
    """
    Full repair pipeline for pathological meshes.
    Filter execution order is critical — do not reorder.
    """
    ms = pml.MeshSet()
    ms.load_new_mesh(input_path)   # use forward slashes: "C:/path/model.obj"

    # Remove noise geometry
    ms.meshing_remove_unreferenced_vertices()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    ms.meshing_merge_close_vertices(threshold=PctVal(0.1))

    # Remove small disconnected components (noise islands)
    ms.meshing_remove_connected_component_by_face_number(mincomponentsize=25)

    # Non-manifold repair (run up to 3 times for stubborn cases)
    for _ in range(3):
        ms.meshing_repair_non_manifold_edges(method=0)      # 0 = Remove Faces
        ms.meshing_repair_non_manifold_vertices(vertdispratio=0)

    # Fill holes
    ms.meshing_close_holes(
        maxholesize=close_hole_max_size,
        newfaceselected=False,
        selfintersection=True,  # prevent self-intersecting patch creation
    )

    # Consistent orientation (normals outward)
    ms.meshing_re_orient_faces_coherently()

    ms.save_current_mesh(output_path)
    measures = ms.get_geometric_measures()
    return {
        "mesh_volume":   measures.get("mesh_volume", 0.0),
        "surface_area":  measures.get("surface_area", 0.0),
        "avg_edge_mm":   measures.get("avg_edge_length", 0.0),
    }
```

**PyMeshLab filter name pitfall:** names changed in 2022.2.
Old: `close_holes` → New: `meshing_close_holes`. Check current names:
```python
ms.filter_list()   # prints all available filter names
```

**Windows path separator pitfall:** use forward slashes:
```python
ms.load_new_mesh("C:/Users/you/model.obj")    # OK
ms.load_new_mesh(r"C:\Users\you\model.obj")   # also OK
```

---

## §4. Blender bmesh Repair (Topology-Aware)

Use when mesh has complex topology issues that trimesh/PyMeshLab can't fix:
non-manifold edges from boolean operations, T-junctions, high-valence poles.

```python
# Run inside Blender headless: blender -b --python repair_bmesh.py -- --input model.blend
import bpy, bmesh

def repair_object(obj):
    me = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # 1. Merge by distance (removes coincident verts from boolean artifacts)
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        # 2. Delete wire edges and isolated vertices
        wire_edges = [e for e in bm.edges if e.is_wire]
        if wire_edges:
            bmesh.ops.delete(bm, geom=wire_edges, context="EDGES")
        bm.verts.ensure_lookup_table()
        iso_verts = [v for v in bm.verts if not v.link_edges]
        if iso_verts:
            bmesh.ops.delete(bm, geom=iso_verts, context="VERTS")

        # 3. Recalculate normals outward (connectivity-based — better than heuristic)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

        # 4. Write back
        bm.to_mesh(me)
        me.update()
    finally:
        bm.free()   # CRITICAL: always free bmesh — leaks cause OOM

for obj in bpy.data.objects:
    if obj.type == "MESH":
        repair_object(obj)
        print(f"[repair] {obj.name} done")

bpy.ops.wm.save_mainfile()
```

**bmesh index gotcha:** after any `bmesh.ops.*` call that adds/removes geometry, indices
become stale. Always call `ensure_lookup_table()` on verts/edges/faces after topology ops.

---

## §5. Normals-Specific Fixes

**Scenario 1: Consistent winding but normals inward (volume < 0):**
```python
# trimesh — single flip
if mesh.is_volume and mesh.volume < 0:
    mesh.invert()   # flips all face normals + winding in one pass
assert mesh.volume > 0, "Volume should be positive after invert"
```

**Scenario 2: Inconsistent winding (adjacent faces wound differently):**
```python
import trimesh.repair as repair
repair.fix_winding(mesh)         # traverse adjacency, flip mismatched faces
repair.fix_normals(mesh, multibody=True)   # outward-facing normals
```

**Scenario 3: Concave mesh false-positive from heuristic (> 30% faces reported flipped):**
The centroid-dot-product heuristic is unreliable for concave shapes.
Use connectivity-based recalculation instead:
```python
# Inside Blender headless
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
# OR trimesh multibody-aware fix:
repair.fix_normals(mesh, multibody=True)
```

**Scenario 4: DirectX normal map → OpenGL (green channel inversion):**
```python
from PIL import Image
import numpy as np
img = np.array(Image.open("normal_dx.png"))
img[:, :, 1] = 255 - img[:, :, 1]   # flip green (Y) channel
Image.fromarray(img).save("normal_gl.png")
```

---

## §6. Boolean Cleanup

Blender's Boolean modifier and trimesh booleans both routinely produce non-manifold edges,
T-intersections, and co-planar faces. Always run repair after any boolean operation.

```python
# Defensive boolean (trimesh + manifold3d)
import trimesh, trimesh.repair as repair

def safe_difference(a: trimesh.Trimesh, b: trimesh.Trimesh) -> trimesh.Trimesh:
    """Boolean difference with repair on each input and output."""
    for m in [a, b]:
        m.process(validate=True)
        repair.fill_holes(m)
        repair.fix_normals(m)
    if not (a.is_volume and b.is_volume):
        raise ValueError(f"Inputs not volumes: a={a.is_volume}, b={b.is_volume}")
    result = a.difference(b, engine="manifold")
    result.process(validate=True)
    repair.fix_normals(result)
    if result.is_volume and result.volume < 0:
        result.invert()
    return result
```

**manifold3d float32 tolerance pitfall:**
```python
# manifold3d uses float32 internally — precision loss on large coordinates
import numpy as np
from manifold3d import Manifold, Mesh as ManifoldMesh

m = ManifoldMesh(
    vert_properties=np.array(mesh.vertices, dtype=np.float32),  # must be float32
    tri_verts=np.array(mesh.faces, dtype=np.uint32),
)
# Check status: 0 = manifold, non-zero = error
result = Manifold(mesh=m)
print(f"Manifold status: {result.status()}")
```
