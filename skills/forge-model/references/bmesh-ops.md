# forge-model — bmesh Operations Reference

## Contents
- §1. Golden rule: bmesh.ops vs bpy.ops.mesh
- §2. Primitives via bmesh.ops
- §3. Extrude (region, discrete, edge-only)
- §4. Inset (individual, region)
- §5. Bevel (destructive one-shot)
- §6. Loop cut via subdivide_edges
- §7. Bridge edge loops
- §8. Triangulate
- §9. Recalc normals
- §10. Lookup table discipline
- §11. Full template: build → validate → render

---

## §1. Golden Rule: bmesh.ops vs bpy.ops.mesh

**Always use `bmesh.ops` in headless Blender scripts.**

`bpy.ops.mesh.*` requires Edit Mode context, which requires an active object in the right mode.
In headless scripts this context is often wrong and produces:

```
RuntimeError: Operator bpy.ops.mesh.extrude_region_move.poll() failed, context is incorrect
```

`bmesh.ops` is context-free — it operates on any `bm` instance regardless of Blender's UI state.

**Safe exceptions** (these DO work headless after setting `bpy.context.view_layer.objects.active`):
- `bpy.ops.object.modifier_apply(modifier=name)`
- `bpy.ops.object.modifier_move_to_index(modifier=name, index=n)`
- `bpy.ops.object.shade_smooth()` / `shade_flat()`

**If you absolutely must use `bpy.ops.mesh.*`** (e.g., for an operator with no bmesh equivalent):
```python
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
# ... bpy.ops.mesh calls here ...
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §2. Primitives via bmesh.ops

```python
import bpy, bmesh
from mathutils import Vector

bm = bmesh.new()

# Cube — size = full edge length (NOT half-extent)
bmesh.ops.create_cube(bm, size=1.0)

# UV sphere
bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=1.0)

# Ico sphere
bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.0)

# Cone
bmesh.ops.create_cone(
    bm,
    cap_ends=True,          # True: close top and bottom; False: open tube
    cap_tris=False,         # True: triangulated caps; False: ngon caps
    segments=32,
    radius1=0.5,            # bottom radius
    radius2=0.0,            # top radius (0 = true cone)
    depth=2.0,
)

# Cylinder (cone with equal top/bottom radii)
bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=32,
                      radius1=0.5, radius2=0.5, depth=2.0)

# Circle (open ring — use for bridge source)
bmesh.ops.create_circle(bm, cap_ends=False, radius=1.0, segments=16)

# Grid
bmesh.ops.create_grid(bm, x_segments=10, y_segments=10, size=2.0)

# Torus (via monkey: use bpy.ops.mesh.primitive_torus_add in edit mode OR roll your own)
# For headless, roll your own or use bmesh.ops.spin:
bmesh.ops.create_circle(bm, cap_ends=False, radius=0.25, segments=12)
bmesh.ops.spin(
    bm,
    geom=bm.verts[:] + bm.edges[:],
    cent=Vector((1.0, 0, 0)),   # center of revolution
    axis=Vector((0, 0, 1)),      # spin axis (Z)
    dvec=Vector((0, 0, 0)),      # translation during spin (helix if nonzero)
    angle=2 * 3.14159,           # full 360 deg
    space=None,
    steps=48,
    use_merge=True,              # merge start and end loops
    use_normal_flip=False,
)

# Always flush to mesh and free
mesh = bpy.data.meshes.new("MyMesh")
bm.to_mesh(mesh)
bm.free()
obj = bpy.data.objects.new("MyObj", mesh)
bpy.context.scene.collection.objects.link(obj)
```

---

## §3. Extrude

### 3A. Extrude face region (most common)
```python
def extrude_faces_along_normal(
    bm: "bmesh.types.BMesh",
    faces: list,
    distance: float,
) -> list:
    """
    Extrude a set of faces and translate the new geometry along the face normal.
    Returns the new vertices.
    """
    bm.faces.ensure_lookup_table()
    ret = bmesh.ops.extrude_face_region(
        bm,
        geom=faces,
        use_keep_orig=False,      # dissolve original face boundary
        use_normal_flip=False,
    )
    new_verts = [e for e in ret["geom"] if isinstance(e, bmesh.types.BMVert)]

    # Translate new verts along the average normal of the source faces
    avg_normal = sum((f.normal for f in faces), Vector((0,0,0))) / len(faces)
    avg_normal.normalize()
    bmesh.ops.translate(bm, vec=avg_normal * distance, verts=new_verts)
    return new_verts


# Example: extrude top face of a cube up by 0.5 units
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bm.faces.ensure_lookup_table()
top = [f for f in bm.faces if f.normal.z > 0.9]
extrude_faces_along_normal(bm, top, 0.5)
```

### 3B. Extrude discrete faces (each face independently)
```python
side_faces = [f for f in bm.faces if abs(f.normal.x) > 0.9]
ret2 = bmesh.ops.extrude_discrete_faces(bm, faces=side_faces)
# ret2["faces"] are the new extruded faces (not verts)
new_face_verts = [v for f in ret2["faces"] for v in f.verts]
bmesh.ops.scale(bm, vec=Vector((1.2, 1.0, 1.0)), verts=list(set(new_face_verts)))
```

### 3C. Extrude edges only (open face strips)
```python
boundary_edges = [e for e in bm.edges if e.is_boundary]
if boundary_edges:
    ret3 = bmesh.ops.extrude_edge_only(bm, edges=boundary_edges)
    new_edge_verts = [e for e in ret3["geom"] if isinstance(e, bmesh.types.BMVert)]
    bmesh.ops.translate(bm, vec=Vector((0, 0, -0.3)), verts=new_edge_verts)
```

---

## §4. Inset

```python
def inset_top_face(bm: "bmesh.types.BMesh", thickness: float = 0.1, depth: float = 0.0):
    """
    Inset the topmost face of the current bmesh.
    thickness: border width
    depth: push inward along normal (negative = push outward)
    """
    bm.faces.ensure_lookup_table()
    top_face = max(bm.faces, key=lambda f: f.calc_center_median().z)

    # inset_individual: each face is inset independently (clean for single face)
    bmesh.ops.inset_individual(
        bm,
        faces=[top_face],
        thickness=thickness,
        depth=depth,
        use_even_offset=True,
        use_interpolate=True,
        use_relative_offset=False,
    )


def inset_region(bm: "bmesh.types.BMesh", faces: list, thickness: float, depth: float = 0.0):
    """
    Inset a region of faces as one unit (preserves shared edges between adjacent selected faces).
    Better than inset_individual when you want the selection to inset as a group.
    """
    bm.faces.ensure_lookup_table()
    bmesh.ops.inset_region(
        bm,
        faces=faces,
        use_boundary=True,     # allow inset to touch mesh boundary
        use_even_offset=True,
        thickness=thickness,
        depth=depth,
        use_outset=False,      # True = outset (opposite direction)
    )
```

**Params comparison:**

| Param | inset_individual | inset_region | Effect |
|---|---|---|---|
| `thickness` | yes | yes | Border width |
| `depth` | yes | yes | Push along normal (+ = in, - = out) |
| `use_even_offset` | yes | yes | Maintain equal offset on non-rectangular faces |
| `use_boundary` | no | yes | Include boundary faces in inset group |
| `use_outset` | no | yes | Flip inset direction |

---

## §5. Bevel (Destructive One-Shot)

Use this for a one-time permanent bevel. For non-destructive iteration, use the Bevel modifier
(see `references/modifier-stack.md §bevel-modifier`).

```python
import math

def bevel_sharp_edges(
    bm: "bmesh.types.BMesh",
    offset: float = 0.02,
    segments: int = 2,
    profile: float = 0.5,
    angle_limit_deg: float = 30.0,
) -> None:
    """
    Bevel only edges whose adjacent face angle exceeds angle_limit_deg.
    offset: bevel width
    segments: 1=flat chamfer, 2=slight round, 3+=fully round
    profile: 0=flat, 0.5=round, 1.0=max round
    """
    limit_rad = math.radians(angle_limit_deg)
    sharp_edges = [
        e for e in bm.edges
        if e.calc_face_angle(math.radians(180)) > limit_rad
    ]
    if not sharp_edges:
        return

    bmesh.ops.bevel(
        bm,
        geom=sharp_edges + list({v for e in sharp_edges for v in e.verts}),
        offset=offset,
        offset_type='OFFSET',      # 'OFFSET'|'WIDTH'|'DEPTH'|'PERCENT'|'ABSOLUTE'
        profile_type='SUPERELLIPSE',
        segments=segments,
        profile=profile,
        affect='EDGES',            # 'EDGES'|'VERTICES'
        clamp_overlap=True,
        harden_normals=True,       # match adjacent face normals on new faces (hard-surface)
        miter_outer='SHARP',       # 'SHARP'|'PATCH'|'ARC'
        miter_inner='SHARP',
    )


# Concrete numbers for bevel offset:
# panel gap / hairline:    0.005 – 0.01
# normal hard-surface:     0.02  – 0.05
# visible chamfer:         0.1   – 0.3
# segments: 1=flat chamfer, 2=slight round, 3+=fully round
```

---

## §6. Loop Cut via subdivide_edges

`bmesh.ops` has no direct `loopcut` equivalent. For headless, use `subdivide_edges` on the
target edge ring. `bpy.ops.mesh.loopcut` requires Edit Mode + edge index — not reliable headless.

```python
def add_loop_cut(bm: "bmesh.types.BMesh", ring_edges: list, cuts: int = 1) -> None:
    """
    Add loop cuts on ring_edges. Analogous to the interactive Loop Cut tool.
    ring_edges: edges forming a ring (e.g., all edges at a particular Z height)
    cuts: 1 = one new edge loop, 2 = two loops, etc.
    """
    bmesh.ops.subdivide_edges(
        bm,
        edges=ring_edges,
        cuts=cuts,
        smooth=0.0,              # 0=straight, 1=smooth interpolation
        use_grid_fill=False,
        use_only_quads=False,
        quad_corner_type='STRAIGHT_CUT',
    )
    # IMPORTANT: refresh lookup tables after topology change
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()


# Example: add a horizontal loop at the midpoint of a cube
bm = bmesh.new()
bmesh.ops.create_cube(bm, size=1.0)
bm.edges.ensure_lookup_table()
# Select edges roughly at z=0 (horizontal ring of a unit cube at Z=0)
ring = [e for e in bm.edges if all(abs(v.co.z) < 0.01 for v in e.verts)]
add_loop_cut(bm, ring, cuts=1)
```

---

## §7. Bridge Edge Loops

```python
# Bridge two open edge loops into a tube/funnel:
bmesh.ops.bridge_loops(
    bm,
    edges=bottom_edges + top_edges,   # edges from two open loops
    use_pairs=False,    # auto-detect pairing
    use_cyclic=True,    # close into cylinder
    use_merge=False,
    twist_offset=0,     # rotate matching by N steps
    profile_shape='LINEAR',
    profile_shape_factor=0.0,
)
# Workflow: create two circles (bmesh.ops.create_circle, cap_ends=False),
# translate the second loop up, collect edges from each loop, call bridge_loops.
```

---

## §8-§10. Triangulate, Recalc Normals, Lookup Tables

```python
# Triangulate — run LAST before bm.to_mesh() if exporter requires tris
bmesh.ops.triangulate(bm, faces=bm.faces[:], quad_method='BEAUTY', ngon_method='BEAUTY')

# Recalc normals — after manual vertex edits or boolean ops
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

# Lookup table refresh — AFTER any op that changes element count
bm.verts.ensure_lookup_table()
bm.edges.ensure_lookup_table()
bm.faces.ensure_lookup_table()
# Missing this after subdivide/extrude/delete causes IndexError or stale references.
```

---

## §11. Key Rules Summary

- All bmesh geometry operations → use `bmesh.ops.*`, not `bpy.ops.mesh.*`
- Every `bmesh.new()` → wrapped in `try/finally bm.free()`
- After topology change → `ensure_lookup_table()` on affected sequences
- After vertex edits → `bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])`
- Flush chain: `bm.to_mesh(mesh); mesh.validate(); mesh.update()`
- Full boilerplate template: see **`bpy-patterns.md §1`**
