# Coordinate Systems, Handedness & Axis-Swap — forge-standards reference

## Contents
- §1. Per-application convention table
- §2. Axis-swap matrices (Blender ↔ glTF / Unreal / Unity / Maya)
- §3. Python conversion functions (bpy + standalone)
- §4. FBX exporter settings (headless PowerShell)
- §5. Quaternion order & wire-format table
- §6. Transform apply (headless, no ops)
- §7. Critical gotchas

---

## §1. Per-application convention table

| App | Up axis | Handedness | 1 unit = | Forward | Quat order |
|-----|---------|-----------|---------|---------|-----------|
| **Blender** | +Z | RH | 1 m | -Y | w,x,y,z |
| **glTF 2.0 / Three.js / R3F** | +Y | RH | 1 m | +Z | x,y,z,w |
| **Unity** | +Y | LH | 1 m | +Z | x,y,z,w |
| **Unreal Engine 5** | +Z | LH | 1 cm | +X | x,y,z,w |
| **Godot 4** | +Y | RH | 1 m | -Z | x,y,z,w |
| **Maya** | +Y | RH | 1 cm | +Z | x,y,z,w |
| **3ds Max** | +Z | RH | 1 inch (configurable) | +Y | x,y,z,w |
| **FBX SDK default** | +Y | RH | (stores axis metadata) | +Z | x,y,z,w |
| **OpenGL** | +Y (convention) | RH | unitless | -Z | x,y,z,w |
| **DirectX / HLSL** | +Y | LH | unitless | +Z | x,y,z,w |

**Ground rule:** Always author in Blender Z-up RH meters. Never change the Blender scene coordinate
system mid-project. Bake axis changes at export only.

---

## §2. Axis-swap matrices

### Blender Z-up RH → glTF Y-up RH

The official glTF-Blender-IO exporter uses this 4×4 matrix. It is an **orthogonal rotation**
(+90° about X), so its inverse is its **transpose** — use `to_yup.transposed()` for the reverse
direction (glTF → Blender), **not** the matrix itself.

```
to_yup = [
    [1,  0,  0, 0],   # X → X
    [0,  0,  1, 0],   # Z → Y  (Blender up becomes glTF up)
    [0, -1,  0, 0],   # -Y → Z (Blender forward becomes glTF forward)
    [0,  0,  0, 1],
]
# Inverse = transpose.  NOT self-inverse: to_yup @ to_yup == diag(1, -1, -1, 1)
# (a 180° rotation about X), so applying it twice does NOT return identity.
```

Component-wise swizzle (faster for large arrays):
```
Location  (x, y, z)_blender → (x, z, -y)_gltf
Scale     (x, y, z)_blender → (x, z,  y)_gltf   # NO sign flip — scale is magnitude
Rotation  Blender (w,x,y,z) → step1 (w, x, z, -y) → glTF wire [x, z, -y, w]
```

### Blender Z-up RH → Unreal Z-up LH + cm

Unreal is left-handed: negating Y converts RH → LH. Plus 100× unit scale (Blender meters → UE cm).

```
Location  (x, y, z)_m → (x*100, -y*100, z*100)_UE_cm
Scale     uniform ×100 on all axes
Rotation  Blender quat (w,x,y,z) → UE (x, -y, z, -w)  (negate qy and qw)
```

**Practical note:** For static meshes the Blender FBX exporter handles this automatically:
`Forward = -Y, Up = Z` + `apply_scale_options='FBX_SCALE_ALL'` + `apply_unit_scale=True`.
For skeletal meshes, set `unit_settings.scale_length = 0.01` and export with
`apply_scale_options='FBX_SCALE_UNITS'` instead (avoids the 100× bone bug).

### Maya Y-up RH → Blender Z-up RH

```python
def maya_to_blender_loc(x, y, z, unit='cm'):
    """Maya Y-up RH (cm) → Blender Z-up RH (m)."""
    s = 0.01 if unit == 'cm' else 1.0
    return (x * s, -z * s, y * s)   # swap Y↔Z, negate new Y

def maya_to_blender_scale(x, y, z, unit='cm'):
    s = 0.01 if unit == 'cm' else 1.0
    return (x * s, z * s, y * s)    # swap Y↔Z, no sign flip
```

---

## §3. Python conversion functions (bpy, headless-ready)

### Blender → glTF full TRS export

```python
# convert_blender_to_gltf.py — run via: blender -b scene.blend -P convert_blender_to_gltf.py -- --json
import sys, io, json
import bpy, mathutils

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def blender_loc_to_gltf(v):
    """(x,y,z) Blender Z-up → (x,z,-y) glTF Y-up."""
    return [v.x, v.z, -v.y]

def blender_scale_to_gltf(v):
    """Scale: swap Y/Z, no sign flip."""
    return [v.x, v.z, v.y]

def blender_quat_to_gltf(q):
    """
    Blender (w,x,y,z) → axis-swizzled (w,x,z,-y) → glTF wire [x,z,-y,w].
    Identity check: Blender (1,0,0,0) → glTF [0,0,0,1] ✓
    """
    w, x, y, z = q.w, q.x, q.y, q.z
    sw, sx, sy, sz = w, x, z, -y        # axis swizzle
    return [sx, sy, sz, sw]             # glTF [x,y,z,w] wire order

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

### Blender → Unreal location (for direct programmatic pipelines)

```python
def blender_to_unreal_loc(loc_m):
    """(x,y,z) meters → (x*100, -y*100, z*100) UE cm, LH."""
    x, y, z = loc_m
    return (x * 100.0, -y * 100.0, z * 100.0)

def blender_quat_to_unreal(q):
    """Blender (w,x,y,z) → UE (x,-y,z,-w). Negate qy and qw for RH→LH."""
    return (q.x, -q.y, q.z, -q.w)   # UE wire order [x,y,z,w]
```

### Quaternion wire-format serialization

```python
# Blender → glTF/Three.js/Unity
def quat_blender_to_gltf(q):
    return [q.x, q.y, q.z, q.w]    # drop w to end

# glTF → Blender
def quat_gltf_to_blender(xyzw):
    x, y, z, w = xyzw
    return mathutils.Quaternion((w, x, y, z))   # Blender constructor is (w,x,y,z)

# Quaternion identity check:
# Blender: Quaternion((1,0,0,0))   — w=1 in position 0
# glTF:   [0, 0, 0, 1]            — w=1 in position 3
```

### Round-trip self-test (run standalone: `python validate_coords.py`)

```python
# validate_coords.py - pure stdlib, runs ANYWHERE (no Blender, no mathutils/numpy).
# Run standalone:  python validate_coords.py
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# The Blender Z-up RH -> glTF Y-up RH swap matrix (4x4, row-major lists).
TO_YUP = [
    [1,  0, 0, 0],   # X -> X
    [0,  0, 1, 0],   # Z -> Y
    [0, -1, 0, 0],   # -Y -> Z
    [0,  0, 0, 1],
]

def matmul4(a, b):
    """4x4 matrix multiply on plain lists."""
    return [[sum(a[i][k] * b[k][j] for k in range(4)) for j in range(4)]
            for i in range(4)]

def transpose4(m):
    return [[m[j][i] for j in range(4)] for i in range(4)]

IDENT = [[1 if i == j else 0 for j in range(4)] for i in range(4)]

# 1. TO_YUP is an orthogonal rotation, so its INVERSE is its TRANSPOSE
#    (NOT itself - TO_YUP @ TO_YUP is a 180deg X-rotation, diag(1,-1,-1,1), not identity).
inv = transpose4(TO_YUP)
prod = matmul4(TO_YUP, inv)
assert all(abs(prod[i][j] - IDENT[i][j]) < 1e-6
           for i in range(4) for j in range(4)), "transpose is NOT the inverse of TO_YUP!"

# 2. Location round-trip: Blender (x,y,z) -> glTF (x,z,-y) -> back.
bx, by, bz = 1.0, 2.0, 3.0
gltf = (bx, bz, -by)                       # (1, 3, -2)
back = (gltf[0], -gltf[2], gltf[1])        # (1, 2, 3)
assert all(abs(a - b) < 1e-6 for a, b in zip(back, (bx, by, bz))), "Location round-trip failed!"

# 3. Quaternion identity round-trip. Blender constructor order is (w,x,y,z);
#    glTF wire order is [x,y,z,w]. Identity: Blender (1,0,0,0) -> glTF [0,0,0,1].
qw, qx, qy, qz = 1.0, 0.0, 0.0, 0.0        # Blender identity (w,x,y,z)
gltf_q = [qx, qy, qz, qw]                  # -> [0,0,0,1]
gx, gy, gz, gw = gltf_q
back_q = (gw, gx, gy, gz)                  # back to Blender (w,x,y,z)
assert all(abs(a - b) < 1e-6 for a, b in zip(back_q, (qw, qx, qy, qz))), "Quaternion round-trip failed!"

print("All coordinate round-trip tests PASSED")
```

> The matrix above (`TO_YUP`) is the same 4×4 as §2; in Blender you'd build it with
> `mathutils.Matrix(...)`, but this standalone check hand-rolls the multiply so it needs no
> third-party wheel and runs under a bare `python`.

---

## §4. FBX exporter settings (headless bpy)

### Static mesh → Unreal

```python
# run via: blender -b scene.blend -P export_ue5.py -- --out "C:/project/export/SM_Chair_01.fbx"
import bpy, sys, argparse, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--out", required=True)
args = ap.parse_args(argv)

bpy.ops.export_scene.fbx(
    filepath=args.out,
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',  # bakes ×100 cm conversion
    apply_unit_scale=True,
    axis_forward='-Y',                    # Blender -Y → UE +X forward
    axis_up='Z',
    mesh_smooth_type='EDGE',              # preserves hard/soft edge data
    use_mesh_modifiers=True,
    bake_anim=False,
    add_leaf_bones=False,
    use_armature_deform_only=True,
)
print(f"Exported: {args.out}")
```

### Skeletal mesh → Unreal (unit-scale approach, avoids 100× bone bug)

```python
# Before export: set scene unit scale to 0.01
bpy.context.scene.unit_settings.scale_length = 0.01
bpy.context.scene.unit_settings.length_unit = 'CENTIMETERS'
# Then export with apply_unit_scale=True, apply_scale_options='FBX_SCALE_UNITS'
# This makes 1 BU = 1 cm without a mesh-to-skeleton mismatch.
```

**NEVER use `apply_scale_options='FBX_SCALE_ALL'` on skeletal meshes** — it bakes the unit/axis
scaling into vertex positions, breaking armature inverse bind matrices and animation retargeting.
For skeletal meshes use `scale_length = 0.01` + `FBX_SCALE_UNITS` (scene-unit scaling only).
Valid enum values: `FBX_SCALE_NONE`, `FBX_SCALE_UNITS`, `FBX_SCALE_CUSTOM`, `FBX_SCALE_ALL`.

### Static or skeletal mesh → glTF/GLB (web, Godot)

```python
bpy.ops.export_scene.gltf(
    filepath="C:/project/export/SM_Barrel_01.glb",
    export_format='GLB',
    use_selection=True,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,   # 0–10; 6 = quality/size balance
    export_apply=True,                        # apply modifiers
    export_materials='EXPORT',
    export_texcoords=True,
    export_normals=True,
)
```

---

## §5. Quaternion wire-format table

| System | Constructor order | Identity value |
|--------|------------------|---------------|
| Blender (bpy mathutils) | w, x, y, z | `Quaternion((1,0,0,0))` |
| glTF 2.0 | x, y, z, w | `[0, 0, 0, 1]` |
| Three.js | x, y, z, w | `new THREE.Quaternion(0,0,0,1)` |
| Unity | x, y, z, w | `Quaternion(0,0,0,1)` |
| Unreal (FQuat) | x, y, z, w | `FQuat(0,0,0,1)` |

**Common mistake:** copying a Blender quaternion directly to a glTF JSON: `Quaternion((1,0,0,0))`
serialized as `[1,0,0,0]` parses in glTF as x=1,y=0,z=0,w=0 — a 180° rotation around X, not identity.
Always use `[q.x, q.y, q.z, q.w]` when writing to glTF.

---

## §6. Apply transforms (headless, no bpy.ops context required)

```python
# apply_transforms.py — safe for headless (-b) Blender invocation
# Equivalent to Ctrl+A in viewport but works without a window context.
import bpy
from mathutils import Matrix

def apply_transforms(ob, location=False, rotation=True, scale=True):
    """
    Bakes rotation and/or scale into mesh data.
    location=False keeps the origin where it is; set True to move origin to world (0,0,0).
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

# Apply to all mesh objects before export:
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        apply_transforms(obj, location=False, rotation=True, scale=True)
        print(f"  Transforms applied: {obj.name}  scale={obj.scale[:]}")
```

---

## §7. Critical gotchas

| Gotcha | Symptom | Fix |
|--------|---------|-----|
| **100× scale (skeletal mesh → UE5)** | Static mesh OK, skeleton at 1% size; scale=(100,100,100) in UE Details | Set `unit_settings.scale_length = 0.01` before FBX export; use `FBX_SCALE_UNITS` not `FBX_SCALE_ALL` |
| **Sideways mesh (Blender → UE5, -90° Z)** | Character faces wrong direction | Exporter: `Forward = -Y`, `Up = Z` |
| **Scale swizzle sign error** | Object appears mirrored after coord conversion | Scale uses `(x, z, y)`, NOT `(x, z, -y)` — no sign flip on scale |
| **Quaternion double-cover / long-way slerp** | Animation takes 270° instead of 90° | Before slerp: if `q1.dot(q2) < 0`, negate q2 |
| **Quaternion component order copy-paste** | Wrong rotation after JSON round-trip | Always serialize as `[q.x, q.y, q.z, q.w]` not `[q.w, q.x, q.y, q.z]` |
| **Non-uniform parent scale → decompose failure** | `decompose()` returns garbage rotation | Apply parent scale before export; work with local matrices only |
| **Blender batch render hangs (4.5+ Windows)** | Script stops after first file | Add `--factory-startup`; use `Start-Process -Wait` in PowerShell |
| **`apply_scale_options='FBX_SCALE_ALL'` on SK** | Skinning breaks, animation retargeting wrong | Use `scale_length=0.01` + `FBX_SCALE_UNITS` for skeletal meshes |
