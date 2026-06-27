# Pivot / Origin Placement Rules — forge-standards reference

## Contents
- §1. Pivot placement table by object class
- §2. Instancing rule
- §3. Blender bpy snippets (headless-safe)
- §4. Common pivot gotchas

---

## §1. Pivot placement table by object class

The object origin in Blender maps directly to the actor/component transform origin in the target engine.
All instances are placed by this origin in the level editor. Misplaced pivots multiply across every
instance — fix them in the source .blend, not per-instance in the engine.

| Object class | Origin / pivot placement | Rationale |
|-------------|--------------------------|-----------|
| Ground-resting props (chair, barrel, crate, rock) | **Bottom-center** of bounding box | Sits on floor at Y=0 without manual offset; snaps cleanly |
| Architectural modular pieces (wall, floor tile, stair) | **Bottom-left corner** OR world origin corner | Grid snapping in the level editor; tile repetition |
| Doors, hinged lids, drawers, trapdoors | **Hinge axis** (edge of the rotating face) | Rotation axis is physically correct; no offset jitter |
| Wheels, fans, turbines, rotating machinery | **Axle center** (mechanical rotation center) | Physics and animation are correct by construction |
| Weapons — FPS (in-hand) | **Grip / attachment socket point** | Matches the hand socket in the character rig |
| Weapons — TPS / world-dropped | **Bottom-center** | Rests on floor; pickup logic uses world location |
| Character / skeletal mesh | **Floor level, centered on root bone XY** | Root motion extracted from root bone; IK resolves down |
| Ceiling-mounted objects (pendant light, stalactite) | **Top mounting point** | Attaches to ceiling face naturally |
| Trees / foliage | **Ground level, trunk center** | Placed by trunk base; wind pivot is tree center |
| Particles / spawn-point objects | **World origin (0,0,0)** | Spawner places these; origin is the spawn location |
| Vehicle — body | **Center-bottom of chassis** | Gravity correct; wheel positions offset from here |
| Modular environment sub-pieces | **Consistent reference corner** | Allows procedural placement / tiling without gaps |

---

## §2. Instancing rule

For object instancing to work correctly, each unique mesh must have its origin at a **predictable,
documented location**. Engines place instances by the origin. Two instances of the same mesh at
different locations means two calls to the engine's instance transform API — both offsets from the
same origin. If the origin is wrong, every instance requires an individual manual offset correction,
which is a maintenance nightmare.

**Rule: origin placement is documented in `FORGE_STANDARDS.json` under `pivot_rule`.**
The `forge-validate` check reads this field and flags any mesh whose bounding-box base-center is
not within `pivot_tolerance` (default 0.005 m) of the world origin for ground-resting props.

---

## §3. Blender bpy snippets (headless-safe)

All snippets use `bpy.context.temp_override()` (Blender 3.2+) to avoid the context requirement
for `bpy.ops.*` in headless `-b` mode.

### Set origin to bottom-center of bounding box (ground props)

```python
# set_origin_bottom_center.py — run via: blender -b scene.blend -P set_origin_bottom_center.py
import bpy, io, sys
from mathutils import Vector

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def set_origin_bottom_center(obj):
    """
    Moves origin to the bottom-center of the object's bounding box.
    The bounding box (bound_box) is in local space — 8 corners, indices 0-7.
    """
    # bound_box: 8 vertices in local space, as (x,y,z) tuples
    local_bbox = [Vector(v) for v in obj.bound_box]
    local_center_x = sum(v.x for v in local_bbox) / 8
    local_center_y = sum(v.y for v in local_bbox) / 8
    local_min_z    = min(v.z for v in local_bbox)

    local_bottom_center = Vector((local_center_x, local_center_y, local_min_z))

    # Convert to world space
    world_bottom_center = obj.matrix_world @ local_bottom_center

    # Move 3D cursor to the target world position, then set origin to cursor
    bpy.context.scene.cursor.location = world_bottom_center

    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')

    print(f"  Origin set to bottom-center: {obj.name}  →  world={world_bottom_center[:]}")

# Apply to all selected mesh objects
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        set_origin_bottom_center(obj)
```

### Set origin to world (0,0,0) — particles / spawn points

```python
def set_origin_to_world_zero(obj):
    """
    Moves origin to world (0,0,0), keeping mesh geometry in place.
    Useful for particles and spawners that must be placed at the spawn point.
    """
    from mathutils import Matrix
    mw = obj.matrix_world
    # Offset from current origin to world zero in local space
    offset_local = mw.inverted() @ Vector((0, 0, 0))
    # Shift geometry data by the negative of that offset
    obj.data.transform(Matrix.Translation(-offset_local))
    # Move the origin in world space to (0,0,0)
    mw.translation = Vector((0, 0, 0))
```

### Set origin to hinge point (doors / hinged lids)

For doors, set the origin to the hinge edge. Typically: left edge center of the door face.

```python
def set_origin_to_hinge(obj, hinge_world_pos):
    """
    Set origin to an arbitrary world position (e.g., the hinge axis center).
    hinge_world_pos: mathutils.Vector or (x, y, z) tuple in world space.
    """
    from mathutils import Matrix, Vector
    target = Vector(hinge_world_pos)
    bpy.context.scene.cursor.location = target
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
    print(f"  Origin moved to hinge: {obj.name}  →  {target[:]}")
```

### Verify origin is at correct position after setting

```python
def check_origin_bottom_center(obj, tolerance=0.005):
    """
    Checks whether the object origin is at the bottom-center of its bounding box.
    Returns True if within tolerance meters.
    """
    local_bbox = [Vector(v) for v in obj.bound_box]
    local_center_x = sum(v.x for v in local_bbox) / 8
    local_center_y = sum(v.y for v in local_bbox) / 8
    local_min_z    = min(v.z for v in local_bbox)

    expected_local = Vector((local_center_x, local_center_y, local_min_z))
    expected_world = obj.matrix_world @ expected_local

    # The object origin in world space is obj.matrix_world.translation
    actual_world   = obj.matrix_world.translation.copy()
    diff           = (expected_world - actual_world).length

    if diff > tolerance:
        print(f"  WARN pivot off: {obj.name}  delta={diff:.4f} m  (tolerance={tolerance})")
        return False
    return True
```

### Batch pivot fix (headless script, run against .blend)

```powershell
# PowerShell — run headless pivot fix on a .blend file
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
& $blender -b "C:\project\source\props\SM_Barrel_Oak\SM_Barrel_Oak_v01.blend" `
    -P "C:\project\tools\set_origin_bottom_center.py" `
    -- --save
```

```python
# In set_origin_bottom_center.py, add --save support:
import argparse
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--save", action="store_true")
args = ap.parse_args(argv)

for obj in bpy.data.objects:
    if obj.type == 'MESH' and obj.name.startswith("SM_"):
        set_origin_bottom_center(obj)

if args.save:
    bpy.ops.wm.save_mainfile()
    print("Saved.")
```

---

## §4. Common pivot gotchas

| Gotcha | Symptom | Detect | Fix |
|--------|---------|--------|-----|
| Origin in mesh center (geometry center) not base | Prop floats above floor when placed at Y=0 | `check_origin_bottom_center()` returns False | Re-run `set_origin_bottom_center()` |
| Origin at (0,0,0) for a prop far from world center | Instancing offset is baked in; moving instance shifts it wrong | Object location ≠ (0,0,0) after origin set | Apply location: `bpy.ops.object.transforms_apply(location=True)` after setting origin |
| Transforms not applied after pivot change | Scale/rotation carry the old transform; export is wrong | `obj.scale[:] != (1,1,1)` or `obj.rotation_euler[:] != (0,0,0)` | Apply transforms with `apply_transforms()` from coordinate-systems.md §6 |
| Hinge / door pivot at geometry center | Door rotates from its center, not its hinge | Visual check in render or engine placement | Set origin to hinge edge, then apply transforms |
| Pivot correct in Blender but wrong in engine | Engine moves the object offset from placed position | Check engine-side placement vs expected | Verify Blender origin = engine attachment point; some engines (Unity) invert +X axis — also check handedness |
| `bound_box` is local-space but compared to world | Scale ≠ 1 makes bound_box wrong in world terms | Check if `obj.scale != (1,1,1)` before calling | Apply scale first (`apply_transforms(scale=True)`) then check bound_box |
