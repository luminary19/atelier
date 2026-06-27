# forge-rig — Blend Shapes / Morph Targets / Shape Keys

# Contents
- §1. Pipeline position and format naming
- §2. Creating shape keys via bpy
- §3. In-between shape keys (non-linear interpolation)
- §4. Corrective shape keys (pose-driven)
- §5. ARKit 52 canonical name list
- §6. Bulk shape key inspection
- §7. Export to glTF (headless)
- §8. Export to FBX (headless)
- §9. Writing USD blend shapes via pxr
- §10. Best-practice rules
- §11. Validation scripts
- §12. Gotcha → fix table

---

## §1. Pipeline position and format naming

```
Modeling → UV Unwrap → Rigging → SHAPE KEYS (this section) → Export → Validation render
```

Blend-shape data is authored **after** topology is locked and **before** final export.
Topology changes after key creation corrupt all delta data.

**Cross-format naming:**

| Blender | glTF 2.0 | FBX | USD |
|---------|---------|-----|-----|
| Shape key | Morph target | BlendShape / BlendShapeDeformer | UsdSkelBlendShape |
| `sk.value` (0–1) | weights[] (0–1) | DeformPercent (0–100) | weights[] (0–1) |
| Relative key | — | — | — |
| Absolute key | — | — | — |
| In-between (driver hack) | — | — | Inbetween (native) |

**FBX weight scaling gotcha:** FBX stores morph weights as `DeformPercent` in range [0, 100].
Blender's exporter handles the 100× scaling automatically. If reading FBX via raw SDK, divide by 100.

---

## §2. Creating shape keys via bpy

```python
import bpy
import numpy as np


def ensure_basis(obj: bpy.types.Object) -> bpy.types.ShapeKey:
    """Add Basis shape key if none exist. MUST be first key (index 0)."""
    if obj.data.shape_keys is None:
        return obj.shape_key_add(name="Basis", from_mix=False)
    return obj.data.shape_keys.key_blocks[0]


def add_shape_key_from_positions(
    obj: bpy.types.Object,
    name: str,
    positions: np.ndarray,    # shape (N, 3), float32, object-local space
) -> bpy.types.ShapeKey:
    """
    Add a relative shape key and set vertex positions via bulk foreach_set.
    foreach_set is C-level bulk copy: ~50-200x faster than looping sk.data[i].co.
    For 100k-vert mesh: foreach_set ≈ 5ms vs loop ≈ 800ms.
    """
    ensure_basis(obj)

    sk = obj.shape_key_add(name=name, from_mix=False)
    sk.interpolation = "KEY_LINEAR"
    sk.slider_min    = 0.0
    sk.slider_max    = 1.0
    sk.value         = 0.0

    # MUST pass flat float32 array, not a list of tuples
    sk.data.foreach_set("co", positions.ravel())
    obj.data.update()    # push to GPU buffer
    return sk


# --- Example: read current positions, create jaw-open key ---
obj    = bpy.context.active_object
n      = len(obj.data.vertices)

basis  = np.empty(n * 3, dtype=np.float32)
obj.data.vertices.foreach_get("co", basis)
basis  = basis.reshape(n, 3)

jaw    = basis.copy()
# Crude lower-jaw selection: all verts below z = -0.01
for i, v in enumerate(obj.data.vertices):
    if v.co.z < -0.01:
        jaw[i, 2] -= 0.05

add_shape_key_from_positions(obj, "jawOpen", jaw)
```

**Key invariants:**
- Basis key must be index 0, name `"Basis"` (exact string)
- `from_mix=False` always in scripts (UI default `from_mix=True` bakes current active mix)
- `use_relative=True` (the default) for facial animation; all keys can blend simultaneously
- After key creation, `len(mesh.vertices)` must equal `len(shape_keys.key_blocks[0].data)`

---

## §3. In-between shape keys (non-linear interpolation)

USD has native in-betweens; Blender approximates them with driven helper keys:

```python
def add_inbetween_key(
    obj: bpy.types.Object,
    primary_key: bpy.types.ShapeKey,
    inbetween_positions: np.ndarray,
    trigger_value: float = 0.5,
) -> bpy.types.ShapeKey:
    """
    Helper key that peaks at trigger_value and returns to 0 at 0 and 1.
    Uses sin(src * pi): 0 at 0, 1 at 0.5, 0 at 1.
    """
    ib = add_shape_key_from_positions(
        obj,
        f"{primary_key.name}_ib_{trigger_value}",
        inbetween_positions,
    )
    fc = ib.driver_add("value")
    fc.driver.type = "SCRIPTED"
    v = fc.driver.variables.new()
    v.name = "src"
    v.type = "SINGLE_PROP"
    v.targets[0].id_type   = "KEY"
    v.targets[0].id        = obj.data.shape_keys
    v.targets[0].data_path = f'key_blocks["{primary_key.name}"].value'
    fc.driver.expression   = "sin(src * 3.14159265)"
    return ib
```

---

## §4. Corrective shape keys (pose-driven)

### Method A: single bone rotation axis (simple)

```python
import bpy, math

def add_corrective_key_driver(
    sk: bpy.types.ShapeKey,
    armature_obj: bpy.types.Object,
    bone_name: str,
    axis: str = "rotation_euler",
    array_index: int = 2,             # Z-axis
    target_angle_rad: float = math.pi / 2,  # 90°
) -> None:
    fc = sk.driver_add("value")
    d  = fc.driver
    d.type = "SCRIPTED"

    v = d.variables.new()
    v.name = "bone_rot"
    v.type = "SINGLE_PROP"
    v.targets[0].id_type   = "OBJECT"
    v.targets[0].id        = armature_obj
    v.targets[0].data_path = f'pose.bones["{bone_name}"].{axis}[{array_index}]'
    # Ramp: 0→1 as bone rotates 0 → target_angle_rad
    d.expression = f"max(0.0, min(1.0, bone_rot / {target_angle_rad}))"
```

### Method B: rotational difference between two bones (more robust)

```python
def add_rotational_difference_driver(
    sk: bpy.types.ShapeKey,
    armature_obj: bpy.types.Object,
    bone_a: str,
    bone_b: str,
    peak_angle_rad: float = math.pi / 2,
) -> None:
    """
    Uses ROTATION_DIFF between two bones.
    Value = 1 when angle=0 (aligned), 0 when angle >= peak_angle_rad.
    """
    fc = sk.driver_add("value")
    d  = fc.driver
    d.type = "SCRIPTED"

    v = d.variables.new()
    v.name = "rot_diff"
    v.type = "ROTATION_DIFF"
    v.targets[0].id = armature_obj
    v.targets[0].bone_target = bone_a
    v.targets[1].id = armature_obj
    v.targets[1].bone_target = bone_b
    d.expression = f"max(0.0, 1.0 - rot_diff / {peak_angle_rad})"
```

### Method C: dot-product pose reader (most control-rig-compatible)

```python
def add_dot_product_driver(
    sk: bpy.types.ShapeKey,
    armature_obj: bpy.types.Object,
    bone_a_index: int,
    bone_b_index: int,
) -> None:
    """
    Drives key by dot product of Y-axis (aim axis) of two pose bones.
    '@' is the Vector dot operator in Blender 4.x — do NOT use '*' (deprecated).
    """
    fc = sk.driver_add("value")
    d  = fc.driver
    d.type = "SCRIPTED"
    v = d.variables.new()
    v.name = "poseBones"
    v.type = "SINGLE_PROP"
    v.targets[0].id_type   = "OBJECT"
    v.targets[0].id        = armature_obj
    v.targets[0].data_path = "pose.bones"
    d.expression = (
        f"poseBones[{bone_a_index}].matrix.col[1] @ "
        f"poseBones[{bone_b_index}].matrix.col[1]"
    )
```

---

## §5. ARKit 52 canonical name list

These exact camelCase names must be used for ARKit / LiveLink / Unity ARKit Package compatibility.

```python
ARKIT_52 = [
    # Eyes — 14 left + 14 right = 28
    "eyeBlinkLeft",    "eyeLookDownLeft",  "eyeLookInLeft",   "eyeLookOutLeft",
    "eyeLookUpLeft",   "eyeSquintLeft",    "eyeWideLeft",
    "eyeBlinkRight",   "eyeLookDownRight", "eyeLookInRight",  "eyeLookOutRight",
    "eyeLookUpRight",  "eyeSquintRight",   "eyeWideRight",
    # Jaw — 4
    "jawForward", "jawLeft", "jawRight", "jawOpen",
    # Mouth — 24
    "mouthClose",         "mouthFunnel",        "mouthPucker",
    "mouthRight",         "mouthLeft",
    "mouthSmileLeft",     "mouthSmileRight",
    "mouthFrownRight",    "mouthFrownLeft",
    "mouthDimpleLeft",    "mouthDimpleRight",
    "mouthStretchLeft",   "mouthStretchRight",
    "mouthRollLower",     "mouthRollUpper",
    "mouthShrugLower",    "mouthShrugUpper",
    "mouthPressLeft",     "mouthPressRight",
    "mouthLowerDownLeft", "mouthLowerDownRight",
    "mouthUpperUpLeft",   "mouthUpperUpRight",
    # Brow — 5
    "browDownLeft", "browDownRight", "browInnerUp",
    "browOuterUpLeft", "browOuterUpRight",
    # Cheek — 3
    "cheekPuff", "cheekSquintLeft", "cheekSquintRight",
    # Nose — 2
    "noseSneerLeft", "noseSneerRight",
    # Tongue — 1; total = 52
    "tongueOut",
]


def validate_arkit_keys(obj: bpy.types.Object) -> list:
    """Return list of missing ARKit shape key names."""
    if not obj.data.shape_keys:
        return list(ARKIT_52)
    existing = {kb.name for kb in obj.data.shape_keys.key_blocks}
    return [name for name in ARKIT_52 if name not in existing]
```

**Cross-engine naming:**
- Apple ARKit (Swift): `ARFaceAnchor.BlendShapeLocation.jawOpen` → raw string `"jawOpen"`
- Unity ARKit package: `ARKitBlendShapeLocation.JawOpen` (PascalCase enum, same underlying string)
- Unreal LiveLink: same camelCase strings in FBX channels
- Use exact camelCase for round-trip compatibility

---

## §6. Bulk shape key inspection

```python
def list_shape_keys(obj: bpy.types.Object) -> list:
    if not obj.data.shape_keys:
        return []
    results = []
    for kb in obj.data.shape_keys.key_blocks:
        has_driver = False
        if obj.data.shape_keys.animation_data:
            path = f'key_blocks["{kb.name}"].value'
            has_driver = any(
                fc.data_path == path
                for fc in obj.data.shape_keys.animation_data.drivers
            )
        results.append({
            "name":         kb.name,
            "value":        kb.value,
            "min":          kb.slider_min,
            "max":          kb.slider_max,
            "relative_key": kb.relative_key.name if kb.name != "Basis" else None,
            "muted":        kb.mute,
            "has_driver":   has_driver,
            "vertex_group": kb.vertex_group,
        })
    return results
```

---

## §7. Export to glTF (headless)

```python
import bpy, sys

def export_gltf(output_path: str) -> None:
    bpy.ops.export_scene.gltf(
        filepath                 = output_path,
        export_format            = "GLB",
        export_morph             = True,
        export_morph_normal      = True,
        export_morph_tangent     = False,   # skip: halves size, minimal visual difference
        export_morph_animation   = True,    # bake shape key f-curves to weights animation
        export_morph_reset_sk_data = True,  # reset SK between actions
        export_try_sparse_sk     = True,    # sparse accessor (Blender 4.2+): saves 50-80% on facial
        export_try_omit_sparse_sk = False,
        export_animations        = True,
        export_skins             = True,
        export_yup               = True,
        export_apply             = False,   # CRITICAL: False preserves shape keys; True destroys them
    )
    print(f"Exported: {output_path}")
```

**Post-export sparse optimization (run after Blender export):**
```powershell
# Requires: npm install -g @gltf-transform/cli
gltf-transform sparse input.glb output_sparse.glb
```

**Sparse accessor compatibility note:** Sparse accessors are not supported in Unity glTFast < 4.x.
Use `export_try_omit_sparse_sk=True` with `export_try_sparse_sk=True` to skip sparse for all-zero
targets if targeting older importers.

---

## §8. Export to FBX (headless)

```python
bpy.ops.export_scene.fbx(
    filepath             = "C:/out/model.fbx",
    use_selection        = False,
    use_mesh_modifiers   = False,   # MUST be False — True bakes and destroys shape keys
    add_leaf_bones       = False,
    bake_anim            = True,
    bake_anim_use_all_actions = True,
    bake_anim_step       = 1.0,
    axis_forward         = "-Z",
    axis_up              = "Y",
)
# FBX: shape keys exported as BlendShapeDeformer + BlendShapeChannel
# Weight range in FBX: [0, 100] (DeformPercent); Blender exporter scales automatically
# If reading via FBX SDK directly: divide channel.GetDeformPercent() by 100
```

---

## §9. Writing USD blend shapes via pxr

Requires `usd-core` package (`pip install usd-core`) or NVIDIA Omniverse.
Not bundled in Blender — install separately if USD pipeline is needed.

```python
from pxr import UsdSkel, Gf, Vt, Sdf, Usd

def write_blend_shape_usd(stage_path: str) -> None:
    stage = Usd.Stage.CreateNew(stage_path)
    root  = UsdSkel.Root.Define(stage, "/Root")

    # Define a blend shape prim — sparse (pointIndices for <30% affected verts)
    bs = UsdSkel.BlendShape.Define(stage, "/Root/Mesh/jawOpen")

    offsets = Vt.Vec3fArray([
        Gf.Vec3f(0.0, -0.05, 0.0),
        Gf.Vec3f(0.0, -0.03, 0.0),
    ])
    point_indices = Vt.IntArray([42, 43])   # sparse; omit for dense
    bs.CreateOffsetsAttr(offsets)
    bs.CreatePointIndicesAttr(point_indices)

    normal_offsets = Vt.Vec3fArray([
        Gf.Vec3f(0.0, -1.0, 0.0),
        Gf.Vec3f(0.0, -1.0, 0.0),
    ])
    bs.CreateNormalOffsetsAttr(normal_offsets)

    # In-between at weight=0.5 (native USD; Blender fakes this with drivers)
    # Weight MUST be strictly in (0, 1) — 0 and 1 are implicit and illegal to author
    ib = bs.CreateInbetween("half_open")
    ib.SetWeight(0.5)
    ib.SetOffsets(Vt.Vec3fArray([Gf.Vec3f(0.0, -0.02, 0.0), Gf.Vec3f(0.0, -0.015, 0.0)]))
    ib.SetNormalOffsets(Vt.Vec3fArray([Gf.Vec3f(0.0, -0.5, 0.0), Gf.Vec3f(0.0, -0.5, 0.0)]))

    # Bind blend shapes to mesh
    binding = UsdSkel.BindingAPI.Apply(stage.GetPrimAtPath("/Root/Mesh"))
    binding.CreateBlendShapesAttr(Vt.TokenArray(["jawOpen"]))
    binding.CreateBlendShapeTargetsRel().SetTargets([Sdf.Path("/Root/Mesh/jawOpen")])

    # Animated weights
    anim = UsdSkel.Animation.Define(stage, "/Root/Anim")
    anim.CreateBlendShapesAttr(Vt.TokenArray(["jawOpen"]))
    w_attr = anim.CreateBlendShapeWeightsAttr(Vt.FloatArray([0.0]))
    w_attr.Set(Vt.FloatArray([0.0]), 0)
    w_attr.Set(Vt.FloatArray([1.0]), 24)

    stage.GetRootLayer().Save()

# USD validation
def validate_usd_blend_shapes(stage_path: str, mesh_vertex_count: int) -> None:
    from pxr import Usd
    stage = Usd.Stage.Open(stage_path)
    for prim in stage.Traverse():
        if prim.GetTypeName() == "BlendShape":
            bs = UsdSkel.BlendShape(prim)
            offsets = bs.GetOffsetsAttr().Get()
            if offsets is None:
                print(f"ERROR: {prim.GetPath()} has no offsets")
            indices = bs.GetPointIndicesAttr().Get()
            if indices is not None:
                ok = UsdSkel.BlendShape.ValidatePointIndices(indices, mesh_vertex_count)
                if not ok:
                    print(f"ERROR: {prim.GetPath()} invalid point indices")
            for ib in bs.GetInbetweens():
                w = ib.GetWeight()
                if w <= 0.0 or w >= 1.0:
                    print(f"ERROR: {prim.GetPath()} inbetween weight {w} out of (0,1)")
```

---

## §10. Best-practice rules summary

| # | Rule | Why |
|---|------|-----|
| 1 | Topology lock first | Adding/removing verts after key creation silently corrupts deltas |
| 2 | Basis is always index 0, named "Basis" | Exporters identify rest pose by position, not name |
| 3 | `foreach_set` for bulk vertex I/O | 50–200× faster than Python loops on high-res meshes |
| 4 | `use_relative=True` for facial animation | Allows simultaneous blending; absolute keys use eval_time |
| 5 | `export_apply=False` always | `True` silently destroys all shape keys |
| 6 | `use_mesh_modifiers=False` for FBX | Same as above — bakes and drops keys |
| 7 | `export_morph_tangent=False` default | Halves morph binary size; enable only if normal-map distortion visible |
| 8 | `export_try_sparse_sk=True` | 50–80% size savings for facial shapes (<10% verts move) |
| 9 | ≤ 52 keys for ARKit; ≤ 256 for games | GPU morph buffers have limits; Bevy hard-caps at 16 per mesh |
| 10 | USD in-betweens for USDZ / Apple Reality | First-class in UsdSkel; more compact than additional keys |
| 11 | FBX DeformPercent ÷ 100 when reading raw SDK | Blender exporter handles scale; raw SDK does not |
| 12 | USD `blendShapes` array order must match `blendShapeTargets` rel order | Mismatch causes wrong shapes on wrong mesh parts |

---

## §11. Validation scripts

### Shape key delta audit

```python
import bpy
import numpy as np

def audit_shape_keys(obj: bpy.types.Object, threshold: float = 1e-5) -> dict:
    if not obj.data.shape_keys:
        return {}
    n     = len(obj.data.shape_keys.key_blocks[0].data)
    basis = np.empty(n * 3, dtype=np.float32)
    obj.data.shape_keys.key_blocks[0].data.foreach_get("co", basis)
    basis = basis.reshape(n, 3)

    results = {}
    for kb in obj.data.shape_keys.key_blocks[1:]:
        co = np.empty(n * 3, dtype=np.float32)
        kb.data.foreach_get("co", co)
        co     = co.reshape(n, 3)
        deltas = np.linalg.norm(co - basis, axis=1)
        mask   = deltas > threshold
        results[kb.name] = {
            "n_affected":  int(mask.sum()),
            "max_delta_m": float(deltas.max()),
            "rms_delta_m": float(np.sqrt((deltas ** 2).mean())),
            "is_empty":    bool(mask.sum() == 0),
        }
    return results
```

### Pre-export check

```python
def pre_export_check(obj: bpy.types.Object) -> bool:
    audit = audit_shape_keys(obj)
    ok    = True

    if not obj.data.shape_keys or obj.data.shape_keys.key_blocks[0].name != "Basis":
        print("FAIL: No 'Basis' shape key at index 0")
        ok = False

    for name, data in audit.items():
        if data["is_empty"]:
            print(f"WARN: '{name}' has zero deformation — may be a duplicate or bug")

    missing = validate_arkit_keys(obj)
    if missing:
        print(f"INFO: Missing {len(missing)} ARKit keys: {missing[:5]}...")

    return ok
```

### Headless render QA — shape key deformation visible in PNG

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

# Render at value=0 (basis) and value=1 (full deformation)
& $blender "C:\scene.blend" -b -P "C:\scripts\verify_shapekey_render.py" `
    -- "C:\scene.blend" "C:\renders\qa\" "jawOpen" 0.0

& $blender "C:\scene.blend" -b -P "C:\scripts\verify_shapekey_render.py" `
    -- "C:\scene.blend" "C:\renders\qa\" "jawOpen" 1.0

# Pixel diff (requires Pillow: pip install pillow)
python -c "
from PIL import Image
import numpy as np
a = np.array(Image.open('C:/renders/qa/jawOpen_0.00.png').convert('RGB'))
b = np.array(Image.open('C:/renders/qa/jawOpen_1.00.png').convert('RGB'))
diff = np.abs(a.astype(int) - b.astype(int))
print(f'Max pixel diff: {diff.max()}  Mean: {diff.mean():.2f}')
assert diff.max() > 5, 'Shape key produces no visible deformation!'
print('PASS: deformation is visible')
"
```

---

## §12. Gotcha → fix table

| Symptom | Cause | Fix |
|---|---|---|
| `export_apply=True` glTF has no morph targets | Applying modifiers bakes and drops keys | Always pass `export_apply=False` |
| FBX has geometry but no BlendShapeDeformer nodes | `use_mesh_modifiers=True` | Set `use_mesh_modifiers=False` |
| Shape key animates but mesh doesn't deform | `use_relative=False` + driver targets `sk.value` | Use `use_relative=True` for driver-based animation |
| `TypeError: sequence expected` in `foreach_set` | Passing list of tuples or non-float32 array | Use `positions.ravel()` on a `float32` numpy array |
| Shape key desync after undo in Edit Mode | Undo in Edit Mode while key active can desync vertex indices | Avoid undo after entering Edit Mode with keys; save first |
| `from_mix=True` creates unexpected deformation | New key baked from current active mix | Always pass `from_mix=False` in scripts |
| Absolute mode garbles vertex positions | `use_relative=False` set while object in Edit Mode | Call `mode_set(mode='OBJECT')` before toggling `use_relative` |
| Morph broken in older Unity (glTFast < 4.x) | Sparse accessors unsupported | Use `export_try_omit_sparse_sk=True` or disable sparse |
| USD wrong shapes animate on wrong parts | `blendShapes` token array and `blendShapeTargets` rel out of sync | Build both in the same loop; never reorder independently |
| USD inbetween validation error | Weight = 0 or 1 authored explicitly | Use weights strictly in (0, 1) exclusive |
| Normal shading ~50% less pronounced after Godot export | Godot exporter pre-PR#89356 didn't subtract reference normals | Use Blender glTF-Blender-IO exporter as canonical path |
| FBX imported with 100× over-driven morphs (custom SDK) | FBX DeformPercent range [0,100] not [0,1] | `weight = channel.GetDeformPercent() / 100.0` |
| `foreach_set` crashes with wrong array length | Array not exactly `n_verts * 3` floats | Verify `positions.shape == (n_verts, 3)` then `.ravel()` |
