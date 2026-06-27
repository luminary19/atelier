# forge-model — Modifier Stack Reference

## Contents
- §1. Modifier stack order (correctness invariant)
- §2. Hard-surface stack: full implementation
- §3. Organic stack: Mirror + Subsurf
- §4. SmoothByAngle (Blender 4.1+ replacement for use_auto_smooth)
- §5. WeightedNormal modifier
- §6. Bevel modifier (non-destructive)
- §7. Mirror modifier
- §8. Array modifier
- §9. Solidify modifier
- §10. Boolean modifier
- §11. Shrinkwrap modifier
- §12. Subsurf / Subdivision modifier
- §13. Depsgraph: read post-modifier mesh without applying
- §14. Apply modifiers permanently

---

## §1. Modifier Stack Order (Correctness Invariant)

**Hard-surface stack (memorize this):**
```
Mirror → Array → Solidify → Bevel → WeightedNormal → SmoothByAngle (LAST)
```

**Organic stack:**
```
Mirror → Subsurf → SmoothByAngle (LAST)
```

**Surface projection (decals, conform):**
```
Shrinkwrap → Subsurf → SmoothByAngle (LAST)
```

**Why order matters:**
- Mirror must see the base mesh before solidifying/beveling for clean symmetry.
- Bevel must see the final solid geometry — it reads face angles that Solidify changes.
- WeightedNormal must come after Bevel because it reads the face normals Bevel produces.
- SmoothByAngle MUST be last — it reads geometry from ALL preceding modifiers.
  Placing it above WeightedNormal produces broken shading (Blender regression, tracked issue
  #121620 — still present in 4.5 LTS).

Enforce order programmatically with `bpy.ops.object.modifier_move_to_index`.

---

## §4. SmoothByAngle (Blender 4.1+)

`mesh.use_auto_smooth` was **removed in Blender 4.1**. Accessing it raises:
```
AttributeError: 'Mesh' object has no attribute 'use_auto_smooth'
```

The replacement is the "Smooth by Angle" Geometry Nodes modifier loaded from Blender's
ESSENTIALS asset library. It MUST be placed last in the modifier stack.

```python
import bpy, math, os


def _add_smooth_by_angle(
    obj: "bpy.types.Object",
    angle_degrees: float = 30.0,
) -> None:
    """
    Add the Smooth by Angle GN modifier (Blender 4.1+) at the END of the stack.
    Prerequisites:
    - All faces must be set to smooth shading BEFORE adding this modifier.
    - This modifier must be the LAST in the stack (enforced below).
    """
    # Set all faces to smooth (prerequisite)
    for poly in obj.data.polygons:
        poly.use_smooth = True
    obj.data.update()

    ng_name = "Smooth by Angle"
    node_group = bpy.data.node_groups.get(ng_name)

    if node_group is None:
        # Load from Blender's bundled ESSENTIALS asset library
        essentials_path = os.path.join(
            bpy.utils.resource_path('LOCAL'),
            "datafiles", "assets", "geometry_nodes", "smooth_by_angle.blend"
        )
        if os.path.exists(essentials_path):
            with bpy.data.libraries.load(essentials_path, assets_only=True) as (df, dt):
                if ng_name in df.node_groups:
                    dt.node_groups = [ng_name]
            node_group = bpy.data.node_groups.get(ng_name)

    if node_group is None:
        # Fallback: use the operator (requires active object)
        prev = bpy.context.view_layer.objects.active
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.modifier_add_node_group(
            asset_library_type='ESSENTIALS',
            asset_library_identifier="",
            relative_asset_identifier=(
                r"geometry_nodes\smooth_by_angle.blend\NodeTree\Smooth by Angle"
            )
        )
        mod = obj.modifiers[-1]
        mod["Input_1"] = math.radians(angle_degrees)
        bpy.context.view_layer.objects.active = prev
        return

    mod = obj.modifiers.new(ng_name, 'NODES')
    mod.node_group = node_group
    mod["Input_1"] = math.radians(angle_degrees)

    # Enforce last position in stack
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_move_to_index(
        modifier=mod.name,
        index=len(obj.modifiers) - 1,
    )


# Compatibility wrapper for code that targets both 4.0 and 4.1+
def set_auto_smooth(obj: "bpy.types.Object", angle_degrees: float = 30.0) -> None:
    if bpy.app.version < (4, 1, 0):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(angle_degrees)
    else:
        _add_smooth_by_angle(obj, angle_degrees)
```

---

## §5. WeightedNormal Modifier

Must come AFTER the Bevel modifier. Reads face normals that Bevel produces.

```python
def _add_weighted_normal(
    obj: "bpy.types.Object",
    weight: int = 50,
) -> "bpy.types.WeightedNormalModifier":
    """
    WeightedNormal: makes large flat faces dominant over small bevel faces.
    weight: 1-100; 50=uniform; >50=more contrast on large faces.
    keep_sharp=True: preserves sharp-marked edges.
    use_face_influence=True: uses face strength marks set by the Bevel modifier.
    """
    wn = obj.modifiers.new("WeightedNormal", 'WEIGHTED_NORMAL')
    wn.mode = 'FACE_AREA'                      # 'FACE_AREA'|'CORNER_ANGLE'|'FACE_AREA_AND_ANGLE'
    wn.weight = weight
    wn.keep_sharp = True
    wn.use_face_influence = True               # uses face strength from Bevel's face_strength_mode
    return wn
```

---

## §6. Bevel Modifier (Non-Destructive)

Prefer this over bmesh bevel for iterative work. Apply when exporting.

```python
def _add_bevel_mod(
    obj: "bpy.types.Object",
    width: float = 0.02,
    segments: int = 2,
    profile: float = 0.7,
    angle_limit_deg: float = 30.0,
) -> "bpy.types.BevelModifier":
    """
    Bevel modifier — non-destructive. Only bevels edges beyond angle_limit.
    harden_normals=True: critical for hard-surface look (no shading seam at bevel edge).
    face_strength_mode='FSTR_NEW': marks new bevel faces for WeightedNormal.
    miter_outer='MITER_ARC': better exterior corners (fewer pinching artifacts).
    """
    bevel = obj.modifiers.new("Bevel", 'BEVEL')
    bevel.width = width
    bevel.segments = segments
    bevel.profile = profile                   # 0=flat, 0.5=round, 0.7=slightly convex
    bevel.limit_method = 'ANGLE'
    bevel.angle_limit = math.radians(angle_limit_deg)
    bevel.use_clamp_overlap = True
    bevel.loop_slide = True
    bevel.harden_normals = True               # CRITICAL for hard-surface
    bevel.face_strength_mode = 'FSTR_NEW'    # mark new faces for WeightedNormal
    bevel.miter_outer = 'MITER_ARC'          # 'MITER_SHARP'|'MITER_PATCH'|'MITER_ARC'
    bevel.miter_inner = 'MITER_SHARP'
    return bevel


# Width reference:
# hairline / panel gap:    0.005 – 0.01
# normal hard-surface:     0.02  – 0.05
# visible chamfer:         0.1   – 0.3
```

---

## §7. Mirror Modifier

```python
def _add_mirror(
    obj: "bpy.types.Object",
    axis_x: bool = True,
    axis_y: bool = False,
    axis_z: bool = False,
) -> "bpy.types.MirrorModifier":
    """
    Mirror across specified axes. Merges vertices within merge_threshold at the mirror plane.
    use_clip=True: clamps center vertices exactly at mirror plane (prevents gap).
    """
    mirror = obj.modifiers.new("Mirror", 'MIRROR')
    mirror.use_axis[0] = axis_x
    mirror.use_axis[1] = axis_y
    mirror.use_axis[2] = axis_z
    mirror.use_clip = True
    mirror.merge_threshold = 0.001    # 1mm — do NOT set to 0.01 (causes false merges)
    mirror.use_mirror_merge = True
    return mirror
```

---

## §8. Array Modifier

```python
def _add_array(
    obj: "bpy.types.Object",
    count: int = 3,
    offset_x: float = 1.05,
    offset_y: float = 0.0,
    offset_z: float = 0.0,
) -> "bpy.types.ArrayModifier":
    """
    Array along X with relative offset. count includes the original.
    offset values are in units of the object's bounding box.
    1.0 = flush; 1.05 = 5% gap between instances.
    """
    array = obj.modifiers.new("Array", 'ARRAY')
    array.count = count
    array.fit_type = 'FIXED_COUNT'            # 'FIXED_COUNT'|'FIT_LENGTH'|'FIT_CURVE'
    array.use_relative_offset = True
    array.relative_offset_displace = (offset_x, offset_y, offset_z)
    array.use_merge_vertices = True
    array.merge_threshold = 0.01
    return array


# For FIT_CURVE: set array.fit_type='FIT_CURVE' AND array.curve=bpy.data.objects["MyCurve"]
# The curve object must exist in the scene before assigning.
```

---

## §9. Solidify Modifier

```python
def _add_solidify(
    obj: "bpy.types.Object",
    thickness: float = 0.05,
    offset: float = -1.0,
) -> "bpy.types.SolidifyModifier":
    """
    Add thickness to a shell/surface mesh (panels, thin walls, cloth).
    offset: -1.0 = inward (default), 0.0 = centered, 1.0 = outward.
    use_quality_normals=True: better normals at non-uniform thickness regions.
    """
    solidify = obj.modifiers.new("Solidify", 'SOLIDIFY')
    solidify.solidify_mode = 'EXTRUDE'        # 'EXTRUDE' (simple)|'NON_MANIFOLD' (complex)
    solidify.thickness = thickness
    solidify.offset = offset
    solidify.use_even_offset = True
    solidify.use_rim = True
    solidify.use_quality_normals = True
    return solidify
```

---

## §10. Boolean Modifier

```python
def _add_boolean(
    obj: "bpy.types.Object",
    cutter: "bpy.types.Object",
    operation: str = 'DIFFERENCE',
) -> "bpy.types.BooleanModifier":
    """
    Boolean CSG operation. 'cutter' must be manifold (every edge has exactly 2 faces).
    solver='EXACT': watertight result; use_hole_tolerant=True: handles near-manifold cutters.
    Hides cutter from render (but keeps it as modifier input).
    """
    bool_mod = obj.modifiers.new("Boolean", 'BOOLEAN')
    bool_mod.operation = operation             # 'DIFFERENCE'|'UNION'|'INTERSECT'
    bool_mod.object = cutter
    bool_mod.solver = 'EXACT'                 # 'FAST' (legacy)|'EXACT' (2.91+, recommended)
    bool_mod.use_self = False
    bool_mod.use_hole_tolerant = True
    cutter.hide_render = True
    cutter.hide_viewport = False              # keep visible so modifier can read it
    return bool_mod


def check_manifold(obj: "bpy.types.Object") -> bool:
    """Quick manifold check — prerequisite for Boolean EXACT solver."""
    import bmesh as bm_mod
    bm = bm_mod.new()
    bm.from_mesh(obj.data)
    result = all(len(e.link_faces) == 2 for e in bm.edges)
    bm.free()
    return result
```

---

## §11. Shrinkwrap Modifier

```python
def _add_shrinkwrap(
    obj: "bpy.types.Object",
    target: "bpy.types.Object",
    offset: float = 0.001,
) -> "bpy.types.ShrinkwrapModifier":
    """
    Project obj's surface onto target. Used for decals, surface-conforming details.
    offset: small positive value to prevent z-fighting.
    wrap_method='NEAREST_SURFACEPOINT': projects to closest surface point.
    """
    sw = obj.modifiers.new("Shrinkwrap", 'SHRINKWRAP')
    sw.target = target
    sw.wrap_method = 'NEAREST_SURFACEPOINT'   # 'NEAREST_SURFACEPOINT'|'PROJECT'|'NEAREST_VERTEX'
    sw.wrap_mode = 'ON_SURFACE'
    sw.offset = offset
    sw.subsurf_levels = 0
    return sw
```

---

## §12. Subsurf / Subdivision Modifier

```python
def _add_subsurf(obj, viewport_lvl=2, render_lvl=3):
    ss = obj.modifiers.new("Subdivision", 'SUBSURF')
    ss.subdivision_type = 'CATMULL_CLARK'  # 'CATMULL_CLARK'|'SIMPLE'
    ss.levels = viewport_lvl
    ss.render_levels = render_lvl
    ss.use_limit_surface = True   # most precise placement; 2x slower than simple
    ss.use_creases = True          # respects edge crease weights
    ss.quality = 3
    return ss

# Poly budget: base × 4^levels  (300 quads → 4800 at level 2; 1000 → 16000)
# Hard-surface base: <300 polys. Organic base: <1000 polys.

# Edge crease (prevents subsurf from rounding edges — needs use_creases=True on modifier)
import bmesh as bm_mod
bm = bm_mod.new(); bm.from_mesh(obj.data)
cl = bm.edges.layers.crease.verify()
for e in bm.edges:
    if e.is_boundary or not e.smooth:
        e[cl] = 1.0
bm.to_mesh(obj.data); bm.free()
```

---

## §13–§14. Depsgraph + Apply + Sharp Marks

```python
# Depsgraph: read post-modifier mesh WITHOUT applying modifiers
# NEVER read obj.data.vertices for modifier-applied positions — use depsgraph
depsgraph = bpy.context.evaluated_depsgraph_get()
obj_eval  = obj.evaluated_get(depsgraph)
mesh_eval = None
try:
    mesh_eval = obj_eval.to_mesh(depsgraph=depsgraph)
    poly_count = len(mesh_eval.polygons)
finally:
    if mesh_eval is not None:
        obj_eval.to_mesh_clear()   # ALWAYS — C-level leak if omitted


# Apply all modifiers permanently (destructive — only for exporters that need it)
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
for mod in list(obj.modifiers):   # list copy — list changes during loop
    bpy.ops.object.modifier_apply(modifier=mod.name)


# Mark sharp by angle (pre-4.1 or explicit hard-surface pass before WeightedNormal)
import bmesh as bm_mod, math
bm = bm_mod.new()
bm.from_mesh(obj.data)
threshold = math.radians(30.0)
for edge in bm.edges:
    a = edge.calc_face_angle(math.radians(180.0))
    edge.smooth = (a is None) or (a <= threshold)
bm.to_mesh(obj.data); bm.free()
```
