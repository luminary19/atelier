# forge-topology — Transform Math & Coordinate Systems Reference

## Contents
- §1. Per-application convention table
- §2. Blender → glTF / Three.js swizzle (Z-up RH → Y-up RH)
- §3. Blender → Unreal (Z-up RH → Z-up LH + centimeters)
- §4. TRS matrix fundamentals
- §5. Apply transforms in bpy (low-level, no ops)
- §6. Rotation representations: Euler, quaternion, axis-angle
- §7. Quaternion serialization (component order by app)
- §8. Pivot / origin placement rules
- §9. Validation: round-trip tests
- §10. Gotchas → fixes

---

## §1. Per-Application Convention Table

| App | Up | Handedness | Unit | Forward | Quaternion order |
|---|---|---|---|---|---|
| **Blender** | +Z | Right (RH) | 1 BU = 1 m | −Y | w,x,y,z |
| **glTF 2.0 / Three.js** | +Y | Right (RH) | 1 unit = 1 m | +Z | x,y,z,w |
| **Unity** | +Y | Left (LH) | 1 unit = 1 m | +Z | x,y,z,w |
| **Unreal Engine** | +Z | Left (LH) | 1 UU = 1 cm | +X | x,y,z,w |
| **Maya (default)** | +Y | Right (RH) | 1 unit = 1 cm | +Z | x,y,z,w |
| **FBX SDK default** | +Y | Right (RH) | (stores axis metadata) | +Z | x,y,z,w |
| **OpenGL** | +Y (convention) | Right (RH) | unitless | −Z | x,y,z,w |

**Three questions to answer before any export:**
1. What is the source app's up-axis and handedness?
2. What are the source units in real-world meters?
3. Does the target app auto-convert, or must the exporter bake the change?

---

## §2. Blender → glTF / Three.js Swizzle

The to_yup matrix (Z-up RH → Y-up RH) is self-inverse (applying it twice = identity):
```
to_yup = [
    [1,  0,  0, 0],   # X → X
    [0,  0,  1, 0],   # Z → Y  (Blender up → glTF up)
    [0, -1,  0, 0],   # -Y → Z (Blender forward → glTF forward)
    [0,  0,  0, 1]
]
```

Component-wise swizzle per data type:
```python
# Location:  (x, y, z)  → (x, z, -y)   — Y flipped
gltf_pos   = (blender_x, blender_z, -blender_y)

# Scale:     (x, y, z)  → (x, z, y)    — NO sign flip
gltf_scale = (blender_x, blender_z, blender_y)

# Quaternion: Blender (w,x,y,z) → glTF wire (x,z,-y,w)
```

```python
# convert_blender_to_gltf.py — run inside Blender headless
import bpy, mathutils, json

def blender_loc_to_gltf(v):
    return [v.x, v.z, -v.y]

def blender_scale_to_gltf(v):
    return [v.x, v.z, v.y]   # no sign flip!

def blender_quat_to_gltf(q):
    """
    Step 1: swizzle axes for Y-up: (w,x,y,z) → (w, x, z, -y)
    Step 2: glTF wire order:        (w, x, z, -y) → [x, z, -y, w]
    """
    w, x, y, z = q.w, q.x, q.y, q.z
    sw, sx, sy, sz = w, x, z, -y
    return [sx, sy, sz, sw]

def export_node(obj):
    loc, rot, scale = obj.matrix_world.decompose()
    return {
        "name": obj.name,
        "translation": blender_loc_to_gltf(loc),
        "rotation":    blender_quat_to_gltf(rot),
        "scale":       blender_scale_to_gltf(scale),
    }

nodes = [export_node(o) for o in bpy.context.scene.objects if o.type == 'MESH']
print(json.dumps(nodes, indent=2))
```

---

## §3. Blender → Unreal (RH → LH + cm)

Unreal is left-handed: flip Y axis to convert RH→LH.

```python
def blender_to_unreal_loc(x_m, y_m, z_m):
    """Blender (x,y,z) meters → Unreal (x,-y,z) centimeters."""
    return (x_m * 100.0, -y_m * 100.0, z_m * 100.0)

def blender_quat_to_unreal(q):
    """
    Blender RH (w,x,y,z) → Unreal LH (x,y,z,w) wire order.
    Flipping Y axis means negate qy and qw.
    """
    return (q.x, -q.y, q.z, -q.w)
```

**Export settings (Blender FBX export dialog):**
```
Forward: -Y Forward
Up:       Z Up
Apply Scalings: FBX Units Scale
Apply Unit: checked
```

**For skeletal meshes to Unreal:** set `bpy.context.scene.unit_settings.scale_length = 0.01`
(1 BU = 1 cm) before export to avoid the 100× skeleton scaling bug.

**Maya → Blender:**
```python
def maya_to_blender_loc(x, y, z):
    """Maya Y-up RH → Blender Z-up RH: swap Y and Z."""
    return (x, -z, y)

def maya_to_blender_scale(x, y, z):
    """Scale: swap Y/Z; unit: Maya 1 unit = 1 cm → Blender meters."""
    return (x * 0.01, z * 0.01, y * 0.01)
```

---

## §4. TRS Matrix Fundamentals

**Column-major 4×4 (OpenGL/glTF convention, glTF 2.0 spec §3.5.3):**
```
M = T * R * S   (scale first, rotate, then translate)
world_pos = T * R * S * local_pos
```

DirectX uses row-major: `world_pos = local_pos * S * R * T` (transposed, same math).

**Translation column in flat float[16] array:** indices 12, 13, 14 (same in both OpenGL column-major and DirectX row-major due to mutual transposition).

**numpy note:** numpy is row-major by default (C order). For OpenGL: `.flatten(order='F')` for column-major output.

```python
import numpy as np

def make_trs_column_major(tx, ty, tz, q_xyzw, sx, sy, sz):
    """Returns float32 array in column-major order for glUniformMatrix4fv."""
    x, y, z, w = q_xyzw
    r = np.array([
        [1-2*(y*y+z*z),   2*(x*y-w*z),   2*(x*z+w*y)],
        [  2*(x*y+w*z), 1-2*(x*x+z*z),   2*(y*z-w*x)],
        [  2*(x*z-w*y),   2*(y*z+w*x), 1-2*(x*x+y*y)],
    ], dtype=np.float32)
    m = np.eye(4, dtype=np.float32)
    m[:3, :3] = r * np.array([sx, sy, sz])
    m[:3, 3]  = [tx, ty, tz]
    return m.flatten(order='F')   # column-major
```

**Parent-child world matrix:**
```python
# Global: parent_world @ child_local
# Child local from world targets: child_local = parent_world.inverted() @ child_world

import bpy, mathutils

def local_to_world(obj, local_pt):
    return obj.matrix_world @ mathutils.Vector(local_pt)

def world_to_local(obj, world_pt):
    return obj.matrix_world.inverted() @ mathutils.Vector(world_pt)

# Decompose world matrix:
loc, rot_quat, scale = obj.matrix_world.decompose()

# Recompose (Blender 3.x+):
mat = mathutils.Matrix.LocRotScale(loc, rot_quat, scale)
```

---

## §5. Apply Transforms in bpy (Low-Level, No ops)

```python
import bpy
from mathutils import Matrix

def apply_transforms(ob, location=True, rotation=True, scale=True):
    """
    Apply object transforms to mesh data without bpy.ops.
    Equivalent to Ctrl+A in viewport; scriptable without context override.
    """
    mb = ob.matrix_basis
    loc, rot, sc = mb.decompose()
    T = Matrix.Translation(loc)
    R = mb.to_3x3().normalized().to_4x4()
    S = Matrix.Diagonal((*sc, 1))

    bake  = Matrix.Identity(4)
    basis = Matrix.Identity(4)

    if location: bake  = T @ bake
    else:        basis = T @ basis
    if rotation: bake  = R @ bake
    else:        basis = R @ basis
    if scale:    bake  = S @ bake
    else:        basis = S @ basis

    if hasattr(ob.data, 'transform'):
        ob.data.transform(bake)
    for child in ob.children:
        child.matrix_local = bake @ child.matrix_local
    ob.matrix_basis = basis

# Usage: apply scale + rotation before export (ALWAYS, no exceptions)
apply_transforms(bpy.context.object, location=False, rotation=True, scale=True)
```

**Rule: apply all transforms before export, every time, automated.** Unapplied scale
corrupts physics collision, normal maps, and skeletal animation.

---

## §6. Rotation Representations

### Euler Angles

Common orders by application:
- Blender default: `XYZ` (extrinsic)
- Aerospace (yaw-pitch-roll): `ZYX` intrinsic
- Unreal: `ZYX` (Pitch=Y, Yaw=Z, Roll=X)

Gimbal lock: for `XYZ` order, occurs when Y rotation = ±90°.

```python
import mathutils, math

euler_xyz = mathutils.Euler((math.radians(30), math.radians(45), 0), 'XYZ')
quat = euler_xyz.to_quaternion()       # lossless
euler_back = quat.to_euler('XYZ')     # numerically equivalent

# ALWAYS specify order explicitly — default may differ by Blender version
```

### Quaternions

Unit quaternion: `q = (w, x, y, z)` where `w = cos(θ/2)`, `(x,y,z) = sin(θ/2) * axis`.

```python
import mathutils, math

# Axis-angle → quaternion
axis  = mathutils.Vector((0, 0, 1))   # Z axis
angle = math.radians(90)
q     = mathutils.Quaternion(axis, angle)
# q = (w=0.7071, x=0, y=0, z=0.7071)

# Compose: apply q1 first, then q2
q_combined = q2 @ q1   # NOT commutative; @ = quaternion multiply in Blender 3.x+

# Slerp (smooth interpolation, constant angular velocity)
q_interp = q1.slerp(q2, 0.5)

# Double-cover fix: ensure shortest path before slerp
def slerp_shortest(q1, q2, t):
    if q1.dot(q2) < 0:
        q2 = -q2   # negate for shortest path
    return q1.slerp(q2, t)

# Renormalize after arithmetic chains
q.normalize()   # in-place

# Rotate a vector
v_rotated = q @ mathutils.Vector((1, 0, 0))
```

### Axis-Angle

```python
# Convert axis-angle to quaternion
def axis_angle_to_quat(angle, ax, ay, az):
    s = math.sin(angle / 2)
    return mathutils.Quaternion((math.cos(angle / 2), ax*s, ay*s, az*s))
```

---

## §7. Quaternion Component Order

| System | Order | Identity value |
|--------|-------|----------------|
| Blender (bpy) | w, x, y, z | `Quaternion((1,0,0,0))` |
| glTF 2.0 | x, y, z, w | `[0, 0, 0, 1]` |
| Unity | x, y, z, w | `Quaternion(0,0,0,1)` |
| Three.js | x, y, z, w | `new THREE.Quaternion(0,0,0,1)` |
| Unreal | x, y, z, w | `FQuat(0,0,0,1)` |

```python
# Blender → glTF serialization
def quat_blender_to_gltf(q):
    return [q.x, q.y, q.z, q.w]   # move w to end

# glTF → Blender deserialization
def quat_gltf_to_blender(xyzw):
    x, y, z, w = xyzw
    return mathutils.Quaternion((w, x, y, z))   # w first in Blender constructor
```

> **Component reorder ONLY — not the same as §2.** The `quat_blender_to_gltf` above (and the
> §9 round-trip below) only move `w` to the end of the tuple; they keep the rotation in
> Blender's Z-up frame. This is correct **only when the glTF exporter applies the +Y-up axis
> conversion separately** (Blender's built-in `export_scene.gltf` does this for you). To
> hand-roll the full Z-up→Y-up conversion in one step — re-expressing the rotation in glTF's
> Y-up frame — use §2's `blender_quat_to_gltf`, which returns the axis-swizzled `[x, z, -y, w]`.
> Never mix the two: pick the §2 swizzle **or** the §7 reorder + exporter axis-bake, not both.

---

## §8. Pivot / Origin Placement Rules

| Asset type | Origin placement | Rationale |
|---|---|---|
| Prop / static mesh | Base center (bottom face, XY centered) | Sits on ground at (0,0,0) in engine |
| Door / hinge joint | Hinge axis | Correct rotation in gameplay |
| Wheel / spinning | Center of rotation | Physics and animation correctness |
| Modular env tile | Corner at world origin | Grid snapping in level editor |
| Character root | Ground between feet, facing +Y (Blender) | IK, root motion, retargeting |

```python
import bpy
from mathutils import Vector, Matrix

def set_origin_bottom_center(obj):
    """Move origin to base-center of bounding box."""
    local_bbox_center = 0.125 * sum(
        (Vector(v) for v in obj.bound_box), Vector()
    )
    local_bottom = Vector((local_bbox_center.x, local_bbox_center.y,
                            min(v[2] for v in obj.bound_box)))
    world_bottom = obj.matrix_world @ local_bottom
    bpy.context.scene.cursor.location = world_bottom
    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        bpy.ops.object.origin_set(type='ORIGIN_CURSOR')
```

**Instancing rule:** for instanced meshes, every instance is placed by its origin.
Misplaced origins require individual offset fixes on every instance — avoid.

---

## §9. Validation: Round-Trip Tests

```python
# validate_coords.py — run as: python validate_coords.py (no Blender needed)
import mathutils

def approx_eq(a, b, tol=1e-5):
    return all(abs(x-y) < tol for x, y in zip(a, b))

# to_yup applied twice = identity
def to_yup():
    return mathutils.Matrix([
        [1, 0,  0, 0], [0, 0,  1, 0], [0, -1, 0, 0], [0, 0, 0, 1]
    ])
m = to_yup()
result = m @ m
ident  = mathutils.Matrix.Identity(4)
assert all(abs(result[i][j] - ident[i][j]) < 1e-6 for i in range(4) for j in range(4))

# Location round-trip
bl = mathutils.Vector((1.0, 2.0, 3.0))
gltf = (bl.x, bl.z, -bl.y)       # (1, 3, -2)
back = (gltf[0], -gltf[2], gltf[1])  # (1, 2, 3)
assert approx_eq(back, (1.0, 2.0, 3.0))

# Quaternion identity round-trip — component reorder ONLY (assumes the exporter bakes
# the +Y-up axis conversion; for a manual axis swizzle use §2's blender_quat_to_gltf).
q_bl   = mathutils.Quaternion((1.0, 0.0, 0.0, 0.0))  # Blender identity
gltf_q = [q_bl.x, q_bl.y, q_bl.z, q_bl.w]           # [0,0,0,1]
q_back = mathutils.Quaternion((gltf_q[3], gltf_q[0], gltf_q[1], gltf_q[2]))
assert abs((q_bl - q_back).magnitude) < 1e-6

print("All coordinate round-trip tests PASSED")
```

---

## §10. Gotchas → Fixes

| Gotcha | Fix |
|--------|-----|
| 100× scale bug (skeletal mesh in Unreal) | Set `unit_settings.scale_length = 0.01` before FBX export |
| Sideways mesh (−90° Z rotation in Unreal) | FBX export: Forward=−Y, Up=+Z |
| Quaternion long-path slerp (270° instead of 90°) | `if q1.dot(q2) < 0: q2 = -q2` before slerp |
| Scale swizzle sign error → mirrored object | Scale uses `(x, z, y)` — no sign flip; location uses `(x, z, -y)` |
| `w,x,y,z` copied to glTF field → wrong rotation | glTF is `[x, y, z, w]` — always reorder |
| `matrix.decompose()` garbage with non-uniform parent scale | Apply parent scale first; or work only with local matrices |
| Batch render hangs after first file (Blender 4.5+) | Use `Start-Process -Wait` in PowerShell; add `--factory-startup` |
| Column-major confusion (numpy ↔ OpenGL) | `.flatten(order='F')` for column-major OpenGL output from numpy |
| `apply_transforms` with `bpy.ops.object.transform_apply` fails in headless | Use the low-level `apply_transforms()` function in §5 (no context override needed) |
| Euler order mismatch across apps | Always serialize the order string alongside the angles; never assume default |
| R8 — "Apply Transform (EXPERIMENTAL)" for skeletal FBX | Never use it for skeletal meshes — breaks armature skinning and bind matrices |
