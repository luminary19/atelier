# forge-animate — Skeletal & Morph Animation Export Reference

Blender 4.5 LTS / 5.0 | glTF 2.0 | FBX | USD 24.08 | gltf-transform 4.x | Windows 11

## Contents

- §1. glTF 2.0 animation spec fundamentals
- §2. Blender → glTF/GLB export (all clips via NLA)
- §3. Blender → FBX export (multi-action / per-action)
- §4. USD SkelAnimation export (pxr Python)
- §5. gltf-transform post-export optimization pipeline
- §6. Validation: gltf_validator, pygltflib, USD, render-to-PNG
- §7. Three.js AnimationMixer consumption
- §8. Per-engine gotcha table

---

## §1. glTF 2.0 animation spec fundamentals

A glTF `animation` object:
- **`samplers[]`**: `{ input: <accessor>, interpolation: "LINEAR"|"STEP"|"CUBICSPLINE", output: <accessor> }`
  - `input` accessor: `SCALAR` float32, monotonically increasing time in **seconds**, `time[0] >= 0`
  - `output` accessor: values matching the animated property type
- **`channels[]`**: `{ sampler: <idx>, target: { node: <idx>, path: "translation"|"rotation"|"scale"|"weights" } }`

**Output element counts (spec-mandated):**
- `LINEAR` / `STEP`: `output_count == input_count`
- `CUBICSPLINE`: `output_count == 3 * input_count` — layout per keyframe:
  `[in_tangent, value, out_tangent]`

**Rotation:** stored as `VEC4 XYZW` unit quaternion. Engines SHOULD use SLERP (not LERP) for `LINEAR`.

**Morph weights:** `path: "weights"`, output `SCALAR` array length `num_morph_targets * num_keyframes`.
Each keyframe stores all morph weights in target-order.

```json
{
  "animations": [{
    "name": "walk_cycle",
    "samplers": [
      { "input": 4, "interpolation": "LINEAR", "output": 5 },
      { "input": 4, "interpolation": "LINEAR", "output": 6 }
    ],
    "channels": [
      { "sampler": 0, "target": { "node": 2, "path": "rotation" } },
      { "sampler": 1, "target": { "node": 1, "path": "weights" } }
    ]
  }]
}
```

---

## §2. Blender → glTF/GLB export (all clips via NLA)

```python
# C:/scripts/export_gltf_anim.py
# Run: blender.exe --background scene.blend --python export_gltf_anim.py
import bpy, os

OUTPUT_DIR = "C:/out/exports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Unmute all NLA tracks so every clip exports
arm_obj = bpy.data.objects.get("Armature")
if arm_obj and arm_obj.animation_data:
    for track in arm_obj.animation_data.nla_tracks:
        track.mute = False

bpy.ops.export_scene.gltf(
    filepath                                  = OUTPUT_DIR + "/character.glb",
    export_format                             = "GLB",
    export_animations                         = True,
    export_animation_mode                     = "ACTIONS",  # one animation per Action
    export_nla_strips                         = True,       # group NLA strips by name
    export_force_sampling                     = False,      # preserve F-curve interpolation
    export_optimize_animation_size            = True,       # lossless dedup
    export_optimize_animation_keep_anim_armature = True,
    export_skins                              = True,
    export_morph                              = True,
    export_morph_normal                       = True,       # delta normals for morphs
    export_morph_tangent                      = False,      # tangent deltas rarely needed
    export_morph_animation                    = True,       # shape key animation as weights
    export_try_sparse_sk                      = True,       # sparse accessors for morphs
    export_apply                              = False,      # do NOT bake modifiers
    export_yup                                = True,       # Z-up Blender → Y-up glTF
    export_def_bones                          = True,       # deform bones only (matches forge-rig invariant; False exports ALL bones incl. IK/MCH/control)
    export_leaf_bone                          = False,      # NEVER add leaf bones
    export_reset_pose_bones                   = True,       # clean bind pose at t=0
)
print("glTF export complete.")
```

**Sampling strategy:**
| Scenario | Flag | Notes |
|----------|------|-------|
| FK-only (clean curves) | `export_force_sampling=False` | Preserves CUBICSPLINE/LINEAR |
| IK, constraints, drivers | `export_force_sampling=True` | Constraints → TRS samples |
| Force sample then reduce | `export_force_sampling=True` + gltf-transform resample | Game delivery |

For IK/constraint animation: also set `export_bake_animation=True` — triggers internal Blender bake.

---

## §3. Blender → FBX export

### All actions as AnimStacks (single FBX, multiple takes)

```python
# C:/scripts/export_fbx_anim.py
import bpy, os

OUTPUT_DIR = "C:/out/exports"
os.makedirs(OUTPUT_DIR, exist_ok=True)

bpy.ops.export_scene.fbx(
    filepath                         = OUTPUT_DIR + "/character.fbx",
    object_types                     = {"ARMATURE", "MESH"},
    use_mesh_modifiers               = False,       # NEVER True for rig/morph export — applying modifiers bakes & destroys shape keys (matches forge-rig)
    add_leaf_bones                   = False,       # NEVER — breaks UE5/Unity skeleton
    primary_bone_axis                = "Y",
    secondary_bone_axis              = "X",
    use_armature_deform_only         = True,
    bake_anim                        = True,
    bake_anim_use_all_bones          = True,
    bake_anim_use_all_actions        = True,        # each Action → separate AnimStack
    bake_anim_use_nla_strips         = False,
    bake_anim_force_startend_keying  = True,
    bake_anim_step                   = 1.0,
    bake_anim_simplify_factor        = 0.0,         # 0 = no simplification
    apply_unit_scale                 = True,
    apply_scale_options              = "FBX_SCALE_NONE",
    axis_forward                     = "-Z",
    axis_up                          = "Y",
    use_space_transform              = True,
)
```

**UE5 scale bug:** `FBX_SCALE_NONE + apply_unit_scale=True` → bones 100× in UE5.5.
Fix: use `apply_scale_options="FBX_SCALE_ALL"` OR export as glTF with UE5 Interchange (5.3+).

**Per-action batch export (Unity/Roblox — one .fbx per action):**
Loop over `bpy.data.actions`, assign each to `arm_obj.animation_data.action`,
set `scene.frame_start/end = int(action.frame_range[0/1])`, then call
`bpy.ops.export_scene.fbx(filepath=..., bake_anim_use_all_actions=False, ...)`.
Restore original action after the loop. Filter incompatible actions via:
`{g.name for g in action.groups}.issubset({b.name for b in arm_obj.pose.bones})`.

---

## §4. USD SkelAnimation export (pxr Python)

Requires `pip install usd-core` (OpenUSD 24.08+).

```python
# C:/scripts/export_usd_skel.py
from pxr import Usd, UsdGeom, UsdSkel, Gf, Vt
import numpy as np

STAGE_PATH = "C:/out/exports/character_anim.usda"
FPS = 24

stage = Usd.Stage.CreateNew(STAGE_PATH)
stage.SetMetadata("upAxis", "Y")
stage.SetMetadata("metersPerUnit", 0.01)
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)

skel_root = UsdSkel.Root.Define(stage, "/World/Character")
skeleton  = UsdSkel.Skeleton.Define(stage, "/World/Character/Skeleton")

joint_tokens = ["Hips", "Hips/Spine", "Hips/Spine/Chest"]
skeleton.CreateJointsAttr().Set(joint_tokens)

rest_xforms = Vt.Matrix4dArray([
    Gf.Matrix4d(1),
    Gf.Matrix4d().SetTranslate(Gf.Vec3d(0, 0.5, 0)),
    Gf.Matrix4d().SetTranslate(Gf.Vec3d(0, 0.5, 0)),
])
skeleton.CreateRestTransformsAttr().Set(rest_xforms)
skeleton.CreateBindTransformsAttr().Set(rest_xforms)

anim = UsdSkel.Animation.Define(stage, "/World/Character/Skeleton/walk_cycle")
anim.CreateJointsAttr().Set(joint_tokens)

# CRITICAL: USD uses restTransforms as default, NOT zero, for missing components.
# Always set all three components (T/R/S) per joint per frame.
for frame in range(0, FPS * 2):
    tc = Usd.TimeCode(frame)
    translations = Vt.Vec3fArray([
        Gf.Vec3f(0, 0.01 * frame, 0),
        Gf.Vec3f(0, 0.5, 0),
        Gf.Vec3f(0, 0.5, 0),
    ])
    rotations = Vt.QuatfArray([Gf.Quatf(1, 0, 0, 0)] * 3)
    scales    = Vt.Vec3hArray([Gf.Vec3h(1, 1, 1)] * 3)
    anim.GetTranslationsAttr().Set(translations, tc)
    anim.GetRotationsAttr().Set(rotations, tc)
    anim.GetScalesAttr().Set(scales, tc)

# Morph/blend-shape weights in USD:
anim.CreateBlendShapesAttr().Set(["mouth_open", "eye_blink_L"])
for frame in range(0, FPS * 2):
    weights = Vt.FloatArray([float(frame) / FPS, 0.0])
    anim.GetBlendShapeWeightsAttr().Set(weights, Usd.TimeCode(frame))

binding = UsdSkel.BindingAPI.Apply(skeleton.GetPrim())
binding.CreateAnimationSourceRel().SetTargets([anim.GetPath()])

stage.SetStartTimeCode(0)
stage.SetEndTimeCode(FPS * 2 - 1)
stage.GetRootLayer().framesPerSecond = FPS
stage.Save()
print(f"USD Skel written: {STAGE_PATH}")
```

---

## §5. gltf-transform post-export optimization pipeline

Run after Blender export — these steps are additive and safe to combine.

```powershell
# PowerShell — full animation optimization pipeline

# 1. Lossless dedup: remove identical consecutive frames (reduces 40-80% for force-sampled)
gltf-transform resample input.glb step1_resample.glb --tolerance 1e-4

# 2. Remove duplicate accessors, prune unused nodes
gltf-transform dedup step1_resample.glb step2_dedup.glb
gltf-transform prune step2_dedup.glb step3_prune.glb

# 3. Meshopt compression (covers geometry + animation + morph target buffers)
gltf-transform meshopt step3_prune.glb output_final.glb --level medium

# Inspect to verify animation count / channel count / byte size:
gltf-transform inspect output_final.glb
```

**Keyframe reduction priority (cheapest to most destructive):**
1. `gltf-transform resample` — lossless, always run
2. `bake_anim_simplify_factor` in FBX export — 0.0=off, 0.1–0.3 for game delivery
3. `gltf-transform meshopt` — lossy Meshopt quantization
4. Graph Editor → Channel → Decimate in Blender (target 20–30% of original keys)

---

## §6. Validation

### gltf_validator (spec compliance)

```powershell
# Download: https://github.com/KhronosGroup/glTF-Validator/releases (2.0.0-dev.3.10)
.\gltf_validator.exe --validate-resources --all --stdout char.glb | ConvertFrom-Json |
    Select-Object -ExpandProperty issues

# Filter animation-specific issues:
$report = .\gltf_validator.exe --stdout char.glb | ConvertFrom-Json
$report.issues.messages | Where-Object { $_.message -match "animation|sampler|accessor" }
```

Key animation checks: NaN/Inf in accessors, non-monotonic timestamps, CUBICSPLINE < 2 keyframes,
output accessor length mismatch, same node+path targeted by multiple channels.

### Programmatic inspection (pygltflib)

```python
# pip install pygltflib
from pygltflib import GLTF2
gltf = GLTF2().load("character.glb")
for i, anim in enumerate(gltf.animations):
    print(f"[{i}] '{anim.name}' — {len(anim.channels)} channels")
    for ch in anim.channels:
        s   = anim.samplers[ch.sampler]
        acc = gltf.accessors[s.input]
        node_name = gltf.nodes[ch.target.node].name if ch.target.node is not None else "N/A"
        print(f"  {node_name}/{ch.target.path} {s.interpolation} {acc.count}keys "
              f"{acc.max[0]-acc.min[0]:.3f}s")
    for s in anim.samplers:
        if s.interpolation == "CUBICSPLINE":
            in_c, out_c = gltf.accessors[s.input].count, gltf.accessors[s.output].count
            if out_c != in_c * 3:
                print(f"  ERROR: CUBICSPLINE output {out_c} != {in_c*3}")
```

### Headless render-to-PNG verification (Blender)

```python
# C:/scripts/verify_anim_frame.py
# blender.exe --background scene.blend --python verify_anim_frame.py
import bpy, os

FRAME  = 15
OUTPUT = "C:/out/verify/frame_015.png"
os.makedirs(os.path.dirname(OUTPUT), exist_ok=True)

bpy.context.scene.frame_set(FRAME)
bpy.context.scene.render.filepath = OUTPUT
bpy.context.scene.render.image_settings.file_format = "PNG"
bpy.ops.render.render(write_still=True)
print(f"Rendered frame {FRAME} to {OUTPUT}")
```

PowerShell invocation for single-frame verify:

```powershell
$b = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
& $b -b "C:/project/animated.blend" -o "C:/out/verify/frame_" -F PNG -f 15
# Then use Read on C:/out/verify/frame_0015.png to visually inspect pose
```

### USD validation

```python
from pxr import Usd, UsdSkel, UsdUtils
stage = Usd.Stage.Open("C:/out/exports/character_anim.usda")
for e in UsdUtils.ComplianceChecker.GetErrors(stage):
    print(f"ERROR: {e}")
cache = UsdSkel.Cache()
root  = UsdSkel.Root(stage.GetPrimAtPath("/World/Character"))
cache.Populate(root, Usd.TraverseInstanceProxies())
for binding in cache.ComputeSkelBindings(root, Usd.TraverseInstanceProxies()):
    sq = cache.GetSkelQuery(binding.GetSkeleton())
    aq = sq.GetAnimQuery()
    if aq:
        print(f"Joints: {sq.GetJointOrder()}, samples: {len(aq.GetJointTransformTimeSamples())}")
```

---

## §7. Three.js AnimationMixer consumption

```javascript
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';

const draco = new DRACOLoader();
draco.setDecoderPath('/draco/');
const loader = new GLTFLoader();
loader.setDRACOLoader(draco);

loader.load('character.glb', (gltf) => {
    const model = gltf.scene;
    scene.add(model);

    const mixer = new THREE.AnimationMixer(model);
    gltf.animations.forEach((clip) => mixer.clipAction(clip).play());

    // Play by name:
    const walkClip = THREE.AnimationClip.findByName(gltf.animations, 'walk_cycle');
    if (walkClip) mixer.clipAction(walkClip).play();

    // Cross-fade:
    // idleAction.crossFadeTo(walkAction, 0.5, true);

    // Direct morph influence (bypass mixer):
    const mesh = model.getObjectByName('Body');
    if (mesh?.morphTargetDictionary) {
        mesh.morphTargetInfluences[mesh.morphTargetDictionary['mouth_open']] = 0.7;
    }
});

const clock = new THREE.Clock();
function animate() {
    requestAnimationFrame(animate);
    mixer.update(clock.getDelta());
    renderer.render(scene, camera);
}
animate();
```

---

## §8. Per-engine gotcha table

| Symptom | Engine | Fix |
|---------|--------|-----|
| Bones 100× scale in UE5 | Unreal 5.x | `apply_scale_options="FBX_SCALE_ALL"` or export glTF + Interchange |
| All AnimSequences are 1 frame | Unreal 5.x | Ensure 1 glTF node per bone (Blender official exporter does this) |
| Root bone renamed `root_ProxyTrueRootJoint` | Unreal 5.x | Use default Blender glTF exporter, not ARP's glTF path |
| Root motion not working (non-humanoid) | Unity 6 | Import skeletal mesh as glTF, animations as FBX; FBX creates Generic Avatar |
| Scale compensation shearing | Maya→Unity/UE | Set `segmentScaleCompensate=0` on all joints before FBX export |
| Imported bones point wrong direction | Maya (FBX) | `primary_bone_axis="-Y"` for Maya-compatible orientation |
| Leaf bones pollute skeleton | UE5 / Unity | `export_leaf_bone=False` / `add_leaf_bones=False` always |
| Morph weight channel animates wrong node | Three.js / UE | `path: "weights"` targets the **node**, not the mesh; avoid shared/instanced meshes |
| FBX has geometry but no shape keys / BlendShapeDeformer nodes | Any (FBX) | `use_mesh_modifiers=True` baked & dropped morphs — set `use_mesh_modifiers=False` (forge-rig invariant) |
| Control/IK bones leak into exported skeleton | UE5 / Unity / glTF | `export_def_bones=False` exports ALL bones — set `export_def_bones=True` (glTF) / `use_armature_deform_only=True` (FBX) + `use_deform=False` on MCH/IK/FK/ORG bones |
| CUBICSPLINE jitter in custom parser | Any | `output[3*i+1]` = value; `output[3*i]` = in_tan; `output[3*i+2]` = out_tan |
| USD bones snap to origin | Omniverse/Houdini | Set restTransforms = identity+offset, NOT zero; omit static time samples |
| Constraint animation snaps/teleports in glTF | Three.js | Bake with `visual_keying=True, clear_constraints=True` before export |
| Backslash in `--python-expr` breaks path | All | Use forward slashes: `filepath='C:/out/char.glb'` |
| `gltf-transform resample` reduces motion too aggressively | Any | Lower tolerance: `--tolerance 1e-5` or `--tolerance 1e-6` |
| Non-uniform bone scale → child shearing | All | Uniform scale only on bones; use blend shapes for squash/stretch |
