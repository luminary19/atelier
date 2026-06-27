# forge-topology — Boolean / CSG Operations Reference

## Contents
- §1. Tool selection
- §2. Blender boolean — full headless pattern (bpy)
- §3. manifold3d — direct Python API
- §4. trimesh boolean wrapper
- §5. OpenSCAD headless CSG
- §6. Hard-surface patterns (holes, panel lines, emboss, kitbash)
- §7. Post-boolean cleanup checklist
- §8. Solver selection table
- §9. Batch boolean (batching cutters)
- §10. Gotchas → fixes

---

## §1. Tool Selection

| Situation | Tool | Why |
|---|---|---|
| General production (already in Blender) | Blender `EXACT` solver | Handles coplanar faces, overlapping geo, non-manifold with `use_hole_tolerant` |
| Pure Python, no subprocess | `manifold3d` (pip) | Guaranteed manifold output, operator syntax (`-`, `+`, `^`), batching |
| Speed iteration, clean geometry, no coplanar overlap | Blender `FLOAT` solver | 2–4x faster than EXACT |
| Parametric CSG variants from .scad file | OpenSCAD headless | Best for families of variants; pipe STL → trimesh for further processing |
| Avoid Blender 4.5 `MANIFOLD` solver | Skip it | Bug #140590 (coplanar faces break it); wait for 4.6 patch |

**Install manifold3d:**
```powershell
pip install manifold3d     # Apache-2.0, binary wheels for Windows x64
pip install trimesh[easy]  # MIT, includes manifold3d >= 2.3.0
```

---

## §2. Blender Boolean — Full Headless Pattern

```python
"""
boolean_blender.py
Run: blender -b --python boolean_blender.py
Blender 4.5 LTS, EXACT solver.
"""
import bpy

def apply_boolean(target_name: str, cutter_name: str,
                  operation: str = "DIFFERENCE",   # DIFFERENCE | UNION | INTERSECT
                  solver: str = "EXACT",            # EXACT | FLOAT  (avoid MANIFOLD in 4.5)
                  use_self: bool = False,
                  use_hole_tolerant: bool = False,
                  hide_cutter: bool = True):
    target = bpy.data.objects[target_name]
    cutter = bpy.data.objects[cutter_name]

    # Boolean requires Object mode + correct active object
    bpy.ops.object.mode_set(mode="OBJECT")
    bpy.context.view_layer.objects.active = target
    target.select_set(True)

    mod = target.modifiers.new("Boolean_Op", "BOOLEAN")
    mod.operation = operation
    mod.solver    = solver
    mod.object    = cutter
    mod.use_self  = use_self
    mod.use_hole_tolerant = use_hole_tolerant

    result = bpy.ops.object.modifier_apply(modifier=mod.name)
    assert "FINISHED" in result, f"modifier_apply cancelled: {result}"

    if hide_cutter:
        cutter.hide_set(True)
    return target


def cleanup_after_boolean(obj_name: str, merge_threshold: float = 0.0001):
    """Post-boolean: merge doubles, recalc normals, dissolve degenerates."""
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")

    # threshold must be scaled by scene units
    scale = bpy.context.scene.unit_settings.scale_length
    bpy.ops.mesh.remove_doubles(threshold=merge_threshold / scale, use_unselected=False)
    bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.mesh.dissolve_degenerate(threshold=0.0001)
    bpy.ops.object.mode_set(mode="OBJECT")


def validate_manifold_bmesh(obj_name: str) -> dict:
    """Check manifold status BEFORE boolean. Run topo_audit.py for full audit."""
    import bmesh
    obj = bpy.data.objects[obj_name]
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        nm_v = [v for v in bm.verts if not v.is_manifold]
        nm_e = [e for e in bm.edges if not e.is_manifold]
        bnd  = [e for e in bm.edges if e.is_boundary]
        return {
            "non_manifold_verts": len(nm_v),
            "non_manifold_edges": len(nm_e),
            "boundary_edges":     len(bnd),
            "is_manifold": (len(nm_v) == 0 and len(nm_e) == 0),
        }
    finally:
        bm.free()


# Example: cut a cylinder hole through a cube
if __name__ == "__main__":
    bpy.ops.wm.read_factory_settings(use_empty=True)

    bpy.ops.mesh.primitive_cube_add(size=2, location=(0, 0, 0))
    cube = bpy.context.active_object; cube.name = "base"

    bpy.ops.mesh.primitive_cylinder_add(radius=0.4, depth=3, location=(0, 0, 0))
    cyl = bpy.context.active_object; cyl.name = "cutter"

    # Always apply transforms before boolean
    for ob in [cube, cyl]:
        bpy.context.view_layer.objects.active = ob
        bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)

    info = validate_manifold_bmesh("base")
    print(f"[PRE-BOOL] base: {info}")

    apply_boolean("base", "cutter", operation="DIFFERENCE", solver="EXACT")
    cleanup_after_boolean("base")

    bpy.ops.wm.obj_export(filepath="C:/Temp/bool_result.obj")
    print("[DONE]")
```

**PowerShell invocation:**
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b --python "C:/Users/you/Lumicity/scripts/boolean_blender.py"
```

---

## §3. manifold3d — Direct Python API

```python
"""
boolean_manifold3d.py
pip install manifold3d trimesh numpy
Run with: python boolean_manifold3d.py (no Blender needed)
Version: manifold3d 3.5.1
"""
import numpy as np
from manifold3d import Manifold, Mesh, OpType

# Primitives (OpenSCAD-inspired API)
cube   = Manifold.cube([2, 2, 2], center=True)
sphere = Manifold.sphere(radius=1.0, circular_segments=64)
cyl    = Manifold.cylinder(height=3.0, radius_low=0.4, circular_segments=32)

# Operator-overloaded boolean syntax
holed_cube = cube - cyl       # difference: a - b
fused      = cube + sphere    # union:      a + b
core       = cube ^ sphere    # intersection: a ^ b

# Translation / transform before boolean
panel_line = (
    Manifold.cube([0.05, 2.1, 0.05], center=True)
    .translate([0.5, 0, 0.9])
)
panel_with_line = cube - panel_line

# Batch boolean (O(n log n) cascade — far faster than N individual subtractions)
greebles = [
    Manifold.cube([0.2, 0.2, 0.15]).translate([x * 0.3, y * 0.3, 0.925])
    for x in range(-2, 3) for y in range(-2, 3)
]
base_plate = Manifold.cube([2.0, 2.0, 0.1], center=True)
greebled   = Manifold.batch_boolean([base_plate] + greebles, OpType.Add)

# Import custom mesh data
verts = np.array([[0,0,0],[1,0,0],[0,1,0],[0,0,1]], dtype=np.float32)
faces = np.array([[0,1,2],[0,1,3],[0,2,3],[1,2,3]], dtype=np.uint32)
tetra = Manifold(mesh=Mesh(vert_properties=verts, tri_verts=faces))
print("genus:", tetra.genus())   # 0 = sphere topology (solid)
print("volume:", tetra.volume())

# Clean up after chained booleans
result = greebled.as_original().set_tolerance(1e-6)

# Export via trimesh
mesh_out = result.to_mesh()
import trimesh
tm = trimesh.Trimesh(vertices=mesh_out.vert_properties, faces=mesh_out.tri_verts, process=False)
print("Watertight:", tm.is_watertight)   # should be True
tm.export("C:/Temp/result.obj")
```

---

## §4. trimesh Boolean Wrapper

```python
import trimesh
a = trimesh.load("C:/Temp/base.obj",   force="mesh")
b = trimesh.load("C:/Temp/cutter.obj", force="mesh")

# BOTH must be watertight volumes
assert a.is_watertight, "base not watertight"
assert b.is_watertight, "cutter not watertight"

# engine='manifold' → manifold3d backend (fastest, guaranteed manifold output)
result = trimesh.boolean.difference([a, b], engine="manifold")
assert result.is_watertight
print(f"Volume: {result.volume:.4f}")
result.export("C:/Temp/bool_result.stl")
```

---

## §5. OpenSCAD Headless CSG

```scad
// panel_detail.scad
// openscad.com -o out.stl panel_detail.scad
// openscad.com -o out.stl -D "groove_depth=0.15" panel_detail.scad
groove_depth = 0.1;
plate_w = 4.0; plate_h = 0.2; plate_d = 3.0;

module bolt_hole(dia=0.2, depth=0.25) {
    cylinder(h=depth*2, r=dia/2, center=true, $fn=32);
}
module panel_groove(length, width=0.06, depth=groove_depth) {
    cube([width, length, depth*2], center=true);
}

difference() {
    cube([plate_w, plate_d, plate_h], center=true);
    translate([1.0,  0, plate_h/2]) panel_groove(plate_d + 0.1);
    translate([-1.0, 0, plate_h/2]) panel_groove(plate_d + 0.1);
    for (x=[-1.5,1.5], y=[-1.0,1.0]) translate([x,y,0]) bolt_hole();
}
```

```powershell
# openscad.com not openscad.exe (see §10 G7)
$openscad = "C:\Program Files\OpenSCAD\openscad.com"
& $openscad -o "C:\Temp\panel_detail.stl" -D "groove_depth=0.12" "C:\Temp\panel_detail.scad"
Write-Host "Exit: $LASTEXITCODE"
```

---

## §6. Hard-Surface Patterns (manifold3d)

```python
from manifold3d import Manifold, OpType

# Pattern 1: Round hole array — batch union cutters FIRST, then single subtraction
plate = Manifold.cube([10, 6, 0.5], center=True)
holes = [
    Manifold.cylinder(height=1.0, radius_low=0.3, circular_segments=32)
    .translate([x * 1.2, y * 1.2, 0])
    for x in range(-3, 4) for y in range(-2, 3)
]
plate_holed = plate - Manifold.batch_boolean(holes, OpType.Add)

# Pattern 2: Panel lines (shallow slot cutters)
def panel_line(length, width=0.04, depth=0.08):
    return Manifold.cube([width, length + 0.1, depth * 2], center=True)

panel = Manifold.cube([8, 5, 0.3], center=True)
v_lines = Manifold.batch_boolean([panel_line(5.1).translate([x, 0, 0.15])
                                   for x in [-3.0,-1.5,0.0,1.5,3.0]], OpType.Add)
h_lines = Manifold.batch_boolean([panel_line(8.1).rotate([0,0,90]).translate([0,y,0.15])
                                   for y in [-2.0,0.0,2.0]], OpType.Add)
panel_detailed = panel - (v_lines + h_lines)

# Pattern 3: Emboss (union) and deboss (subtract)
embossed = panel + Manifold.cylinder(0.15, 1.0).translate([0, 0, 0.15])   # raised
debossed = panel - Manifold.cylinder(0.2,  1.0, circular_segments=64).translate([0, 0, 0.1])

# Pattern 4: Kitbash union + clean
base = Manifold.cube([6, 4, 0.15], center=True)
kit  = Manifold.batch_boolean([
    base,
    Manifold.cube([0.3, 0.5, 0.2]).translate([1, 0, 0.15]),
    Manifold.cylinder(0.3, 0.15, circular_segments=16).translate([2, 1, 0.15]),
], OpType.Add).as_original().set_tolerance(1e-6)
```

---

## §7. Post-Boolean Cleanup Checklist

- [ ] `is_watertight` / `volume > 0` — solid is closed
- [ ] `genus == expected` — 0 for no through-holes; +1 per through-hole
- [ ] 0 non-manifold edges/vertices (bmesh check or topo_audit.py)
- [ ] Render PNG shows correct geometry from two angles
- [ ] Volume within expected range (sanity check)
- [ ] 0 interior faces (use `select_interior_faces` count in Edit mode)

---

## §8. Solver Selection Table

| Solver | bpy literal | Use case |
|--------|-------------|----------|
| Exact | `'EXACT'` | **Default.** Coplanar faces, overlapping geo, non-manifold input. Use `use_hole_tolerant=True` for open meshes |
| Float | `'FLOAT'` | Speed iteration; known clean geometry; no coplanar overlap. 2–4x faster |
| Manifold | `'MANIFOLD'` | **Avoid in Blender 4.5** — bug #140590 breaks coplanar faces. Retry in 4.6+ |
| manifold3d | (Python lib) | Pure Python, no subprocess, guaranteed manifold output |

---

## §9. Batch Boolean

```
# WRONG — N separate modifier_apply calls: slow, accumulates error
result = base - cutter1; result = result - cutter2; ...

# CORRECT — batch union all cutters, then single subtract:
all_cutters = Manifold.batch_boolean(cutters, OpType.Add)
result = base - all_cutters

# Blender equivalent: put all cutters in a Collection, use operand_type='COLLECTION'
mod.operand_type = 'COLLECTION'
mod.collection = bpy.data.collections["CutterCol"]
```

---

## §10. Gotchas → Fixes

| Gotcha | Fix |
|--------|-----|
| Coplanar faces → garbage geometry | Switch `FLOAT` → `EXACT`; or offset cutter by 0.001 BU |
| `MANIFOLD` solver broken in Blender 4.5 | Use `EXACT` until 4.6 fixes bug #140590 |
| Non-manifold input → wrong boolean output | Run `validate_manifold_bmesh()` before; repair with `remove_doubles` + `fill_holes` |
| Unapplied transforms → boolean operates at wrong scale/location | `transform_apply(rotation=True, scale=True)` on BOTH target and cutter before modifier |
| `remove_doubles` removes 0 vertices (unit scale) | Scale threshold: `threshold = desired / bpy.context.scene.unit_settings.scale_length` |
| `modifier_apply()` returns CANCELLED | Set `view_layer.objects.active = target_obj` + `mode_set(mode="OBJECT")` first |
| Windows path backslashes in Python inside Blender | Use forward slashes: `"C:/Users/you/file.blend"` |
| `openscad.exe -o` opens GUI instead of exporting | Use `openscad.com` (console-mode wrapper) not `openscad.exe` |
| manifold3d input not manifold → wrong output | Check `m.genus()`, `m.volume()` after `Manifold(mesh=...)` |
| Interior faces after UNION | Edit mode → `select_interior_faces()` → delete FACE; or add Weld modifier |
| Boolean union requires overlap (not just contact) | Ensure ≥ 0.001 BU overlap between joined pieces |
| `as_original()` not called → degenerate tris accumulate | Call `.as_original().set_tolerance(1e-6)` after final chained boolean |
