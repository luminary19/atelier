# forge-rig — Rigging: Armatures, IK/FK, Constraints, Export

# Contents
- §1. Headless invocation patterns
- §2. Armature creation (Edit Mode API)
- §3. Bone naming conventions
- §4. Bone connection rule
- §5. Bone roll
- §6. Control vs deform bone pattern
- §7. IK constraint setup
- §8. Bone constraints reference table
- §9. Rigify headless generation
- §10. Symmetrize / mirror
- §11. Apply rest pose
- §12. IK baking (visual keying)
- §13. Export patterns — glTF / FBX / USD
- §14. Bone count limits by engine
- §15. Rig validation script
- §16. Gotcha → fix table

---

## §1. Headless invocation patterns

```powershell
# PowerShell — run a rigging script against an existing .blend
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

# New scene (no .blend)
& $blender --background --python "C:\scripts\rig_create.py" -- --output "C:\out\rig.png"

# Existing scene
& $blender --background "C:\scenes\character.blend" `
    --python "C:\scripts\add_rig.py" -- --output "C:\out\rig_check.png"
```

The `--` separator is mandatory. Blender reads everything after `--` as user args accessible
via `sys.argv`. Omitting `--` passes your flags to Blender itself (usually breaks it silently).

**Render engine:** use Cycles (`'CYCLES'`) for headless renders on Windows — EEVEE-Next
(`'BLENDER_EEVEE_NEXT'`) is unsupported in headless mode on Windows and will produce a black
or crash output. Set `scene.render.engine = 'CYCLES'` + `scene.cycles.device = 'CPU'`.

**Absolute paths in Blender Python:** use forward slashes or raw strings:
```python
bpy.context.scene.render.filepath = "C:/out/rig_check.png"   # OK
bpy.context.scene.render.filepath = r"C:\out\rig_check.png"  # OK
bpy.context.scene.render.filepath = "C:\out\rig_check.png"   # BROKEN (\r \o)
```

---

## §2. Armature creation (Edit Mode API)

```python
# rig_create.py — headless-safe armature creation
import bpy
import math
from mathutils import Vector

def create_biped_spine(name: str = "CharacterRig") -> bpy.types.Object:
    arm_data = bpy.data.armatures.new(name + "_Armature")
    arm_obj  = bpy.data.objects.new(name, arm_data)
    bpy.context.collection.objects.link(arm_obj)

    # Armature must be active before mode_set
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='OBJECT')  # ensure clean state
    bpy.ops.object.mode_set(mode='EDIT')

    eb = arm_data.edit_bones       # ONLY valid in Edit Mode

    root = eb.new("root")
    root.head = (0, 0, 0)
    root.tail = (0, 0, 0.1)
    root.use_deform = False        # control bone — never exported as skin

    spine = eb.new("DEF-spine")
    spine.head   = (0, 0, 0.9)
    spine.tail   = (0, 0, 1.4)
    spine.parent = root
    spine.use_connect = False      # root is non-deform; don't connect
    spine.use_deform  = True

    chest = eb.new("DEF-chest")
    chest.head   = spine.tail.copy()   # .copy() required — no live refs after mode switch
    chest.tail   = (0, 0, 1.9)
    chest.parent = spine
    chest.use_connect = True           # head snaps to parent tail
    chest.use_deform  = True

    upper_arm_l = eb.new("DEF-upper_arm.L")
    upper_arm_l.head   = (0.3, 0, 1.75)
    upper_arm_l.tail   = (0.7, 0, 1.55)
    upper_arm_l.parent = chest
    upper_arm_l.use_connect = False
    upper_arm_l.use_deform  = True

    forearm_l = eb.new("DEF-forearm.L")
    forearm_l.head   = upper_arm_l.tail.copy()
    forearm_l.tail   = (1.1, 0, 1.55)
    forearm_l.parent = upper_arm_l
    forearm_l.use_connect = True
    forearm_l.use_deform  = True

    # IK target — parent=None, use_deform=False
    ik_hand_l = eb.new("IK-hand.L")
    ik_hand_l.head   = forearm_l.tail.copy()
    ik_hand_l.tail   = (1.1, -0.1, 1.55)
    ik_hand_l.parent = None
    ik_hand_l.use_deform = False

    # Pole target — behind the elbow on -Y
    ik_pole_l = eb.new("IK-pole_arm.L")
    ik_pole_l.head   = (0.7, -0.5, 1.55)
    ik_pole_l.tail   = (0.7, -0.6, 1.55)
    ik_pole_l.parent = None
    ik_pole_l.use_deform = False

    # CRITICAL: copy any vectors you need BEFORE leaving Edit Mode
    # edit_bones are dangling pointers after mode_set(mode='OBJECT')
    bpy.ops.object.mode_set(mode='OBJECT')
    return arm_obj
```

---

## §3. Bone naming conventions

| Prefix | Meaning | `use_deform` | Exported? |
|--------|---------|-------------|-----------|
| `DEF-` | Deformation bone — skins mesh | True | Yes |
| `MCH-` | Mechanism / internal calculation | False | No |
| `ORG-` | Original (Rigify meta-rig positions) | False | No |
| `IK-`  | IK target or pole target | False | No |
| `FK-`  | FK control (for IK/FK switch setups) | False | No |
| `root` | Root controller | False | No |

**Bilateral suffix:** always `bonename.L` / `bonename.R` (dot + uppercase).
- Correct: `upper_arm.L`, `foot.R`
- Wrong: `upper_armL`, `foot_R`, `Left_upper_arm` (Blender mirror won't parse these)

**No spaces in bone names** — FBX tokenizes on spaces; some importers choke.

---

## §4. Bone connection rule

`use_connect=True` snaps the bone's head to its parent's tail. Both conditions must hold:

```python
# WRONG: use_connect set before parent
b.use_connect = True   # no-op — no parent yet
b.parent = prev

# CORRECT: parent first, then use_connect
b.parent      = prev
b.use_connect = True
```

Helper for building chains:

```python
def make_chain(arm_data, names_and_positions):
    """names_and_positions: list of (name, head_vec, tail_vec)"""
    eb   = arm_data.edit_bones
    prev = None
    for name, head, tail in names_and_positions:
        b = eb.new(name)
        b.head = head
        b.tail = tail
        if prev is not None:
            b.parent      = prev
            b.use_connect = True
        prev = b
```

---

## §5. Bone roll

Roll controls the bone's local X/Z orientation — affects IK bending direction and mirror symmetry.

```python
import bpy, math

def recalculate_rolls(arm_obj):
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='EDIT')
    eb = arm_obj.data.edit_bones

    # Manual roll (radians)
    eb["DEF-upper_arm.L"].roll = math.radians(0)
    eb["DEF-forearm.L"].roll   = math.radians(0)

    # Auto-recalculate (equivalent to Ctrl+N → POS_X in UI)
    for b in eb:
        b.select = True
    bpy.ops.armature.calculate_roll(type='POS_X')

    bpy.ops.object.mode_set(mode='OBJECT')
```

Typical IK arm: roll = 0 with bones in the XZ plane gives natural forward-elbow bending.

---

## §6. Control vs deform bone pattern

```python
# Mark all MCH-/IK-/FK-/ORG-/root bones as non-deform
arm_obj = bpy.data.objects["CharacterRig"]
for bone in arm_obj.data.bones:
    if bone.name.startswith(("MCH-", "IK-", "FK-", "ORG-", "root")):
        bone.use_deform = False
    # Also catch IK-constraint-bearing bones by pose inspection
    pb = arm_obj.pose.bones[bone.name]
    if any(c.type == 'IK' for c in pb.constraints):
        bone.use_deform = False
```

Note: `bone.use_deform` is writeable in Object mode (no mode switch needed).
`bone.head` / `bone.tail` are read-only in Object mode — use Edit Mode for position changes.

---

## §7. IK constraint setup

```python
import bpy, math

def add_ik_constraint(arm_obj: bpy.types.Object) -> None:
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    pbone = arm_obj.pose.bones["DEF-forearm.L"]

    ik = pbone.constraints.new('IK')
    ik.name          = "IK_arm_L"
    ik.target        = arm_obj          # self-targeting within same armature
    ik.subtarget     = "IK-hand.L"
    ik.pole_target   = arm_obj
    ik.pole_subtarget = "IK-pole_arm.L"
    ik.pole_angle    = math.radians(0)  # adjust to natural bend; typical arm = -90°
    ik.chain_count   = 2                # forearm + upper_arm; 0 = full chain to root (WRONG)

    # Per-bone IK angle limits
    upper = arm_obj.pose.bones["DEF-upper_arm.L"]
    upper.use_ik_limit_x = True
    upper.ik_min_x = math.radians(-90)
    upper.ik_max_x = math.radians( 90)

    # Stiffness resists rotation (0.0=free, 0.99=stiff) — useful for spine
    upper.ik_stiffness_x = 0.0

    bpy.ops.object.mode_set(mode='OBJECT')
```

**IK rules:**
- `chain_count` must be set explicitly. `chain_count=0` = full chain to root — almost never correct.
- IK target (`IK-hand.L`) must NOT be a child of any bone in the IK chain. Circular dependency → solver resolves unpredictably.
- `pole_angle` is radians. Typical arm: `math.radians(-90)`. Iterate if the elbow pops the wrong way.

**Muting IK for IK/FK switching:**
```python
ik_cns = arm_obj.pose.bones["DEF-forearm.L"].constraints["IK_arm_L"]
ik_cns.mute = True    # FK active
ik_cns.mute = False   # IK active
ik_cns.influence = 0.5  # blend 50/50 (animatable)
```

---

## §8. Bone constraints reference table

All constraints are added via `pose_bone.constraints.new('TYPE_STRING')`.
No mode switch required for `.new()` — works in Object or Pose mode.

| Type string | Common use | Key params |
|---|---|---|
| `'IK'` | Limb IK solver | `target, subtarget, chain_count, pole_target, pole_subtarget, pole_angle` |
| `'COPY_ROTATION'` | Bone copies another's rotation | `target, subtarget, use_x/y/z, target_space, owner_space, influence` |
| `'COPY_TRANSFORMS'` | Full TRS copy (retargeting) | `target, subtarget, target_space, owner_space` |
| `'LIMIT_ROTATION'` | Clamp bone angles | `use_limit_x, min_x, max_x, owner_space` |
| `'TRACK_TO'` | Point bone axis at target (eye tracking) | `target, track_axis, up_axis` |
| `'STRETCH_TO'` | Bone stretches to reach target | `target, subtarget, keep_axis, volume` |
| `'COPY_LOCATION'` | Position following | `target, subtarget, use_x/y/z` |
| `'DAMPED_TRACK'` | Softer track-to (no up-axis flip) | `target, track_axis` |

```python
# COPY ROTATION example
cr = pbone.constraints.new('COPY_ROTATION')
cr.target       = arm
cr.subtarget    = "DEF-chest"
cr.use_x        = True; cr.use_y = False; cr.use_z = True
cr.target_space = 'LOCAL'
cr.owner_space  = 'LOCAL'
cr.influence    = 0.5

# Remove a constraint
pbone.constraints.remove(cr)
```

---

## §9. Rigify headless generation

```python
import bpy

# Enable the Rigify add-on programmatically (required in headless)
bpy.ops.preferences.addon_enable(module='rigify')

# Add a human meta-rig
bpy.ops.object.armature_human_metarig_add()
metarig = bpy.context.active_object

# ... adjust bone positions to match your mesh in Edit Mode ...

# Generate the full rig
bpy.context.view_layer.objects.active = metarig
bpy.ops.pose.rigify_generate()
# Result: a new "rig" object with DEF- / MCH- / ORG- / WGT- bones

# Post-generation: ensure non-deform bones are correctly flagged
rig = bpy.data.objects["rig"]
for bone in rig.data.bones:
    if bone.name.startswith(("MCH-", "ORG-")):
        bone.use_deform = False
    pb = rig.pose.bones[bone.name]
    if any(c.type == 'IK' for c in pb.constraints):
        bone.use_deform = False
```

**Rigify DEF- bone gotcha (Blender 4.0–4.2):** Some Rigify versions leave `use_deform=True` on
MCH- bones. The cleanup loop above is mandatory after `rigify_generate()`.

---

## §10. Symmetrize / mirror

```python
import bpy

arm = bpy.data.objects["CharacterRig"]
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='EDIT')

# Select .L bones; symmetrize will create matching .R bones
for b in arm.data.edit_bones:
    b.select = b.select_head = b.select_tail = b.name.endswith(".L")

bpy.ops.armature.symmetrize(direction='NEGATIVE_X')  # +X → -X
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §11. Apply rest pose

```python
# Pose the rig to A-pose (or desired rest), then apply as rest pose
bpy.context.view_layer.objects.active = arm_obj
bpy.ops.object.mode_set(mode='POSE')
bpy.ops.pose.armature_apply()   # Apply Pose as Rest Pose (destructive — edits bone positions)
bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §12. IK baking (visual keying)

```python
import bpy

arm = bpy.data.objects["CharacterRig"]
bpy.context.view_layer.objects.active = arm
bpy.ops.object.mode_set(mode='POSE')

# Select all deform pose bones for baking
for pb in arm.pose.bones:
    pb.bone.select = pb.bone.use_deform

bpy.ops.nla.bake(
    frame_start       = bpy.context.scene.frame_start,
    frame_end         = bpy.context.scene.frame_end,
    step              = 1,
    only_selected     = True,
    visual_keying     = True,   # key the VISUAL/IK-solved transform
    clear_constraints = True,   # remove IK constraints after baking
    bake_types        = {'POSE'},
)
bpy.ops.object.mode_set(mode='OBJECT')
```

Alternatively, set `export_bake_animation=True` in `export_scene.gltf()` to bake at export time
(does not modify the .blend file).

---

## §13. Export patterns

### glTF / GLB

```python
bpy.ops.export_scene.gltf(
    filepath                    = "C:/out/character.glb",
    export_format               = "GLB",
    export_skins                = True,
    export_def_bones            = True,       # deform bones only
    export_animations           = True,
    export_bake_animation       = True,       # REQUIRED for IK rigs
    export_force_sampling       = True,
    export_reset_pose_bones     = True,
    export_influence_nb         = 4,          # 4-influence limit for Unity/Godot/WebGL
    export_yup                  = True,       # glTF Y-up convention
    export_apply                = False,      # NEVER True — destroys shape keys
    export_hierarchy_flatten_bones = False,   # set True if non-decomposable matrix error
    export_morph                = True,       # shape keys → morph targets
    export_morph_normal         = True,
    export_morph_tangent        = False,
    export_try_sparse_sk        = True,       # Blender 4.2+ sparse morph accessor
)
```

### FBX (Unreal / Unity)

```python
bpy.ops.export_scene.fbx(
    filepath                 = "C:/out/character.fbx",
    object_types             = {'ARMATURE', 'MESH'},
    use_armature_deform_only = True,          # deform bones only
    add_leaf_bones           = False,         # False for UE/Unity (they add their own)
    primary_bone_axis        = 'Y',
    secondary_bone_axis      = 'X',
    bake_anim                = True,
    bake_anim_use_all_actions = True,
    bake_anim_step           = 1.0,
    axis_forward             = '-Z',          # Unreal: '-Z'; Unity: 'Z'
    axis_up                  = 'Y',
    apply_scale_options      = 'FBX_SCALE_ALL',
    use_mesh_modifiers       = False,         # NEVER True — destroys shape keys
)
```

### USD (film/VFX)

```python
bpy.ops.wm.usd_export(
    filepath         = "C:/out/character.usda",
    export_armatures = True,
    export_def_bones = True,
    export_animation = True,
    # Note: B-bones and shape keys not supported in USD export (Blender 4.2/4.5)
)
```

---

## §14. Bone count limits by engine

| Target | Practical limit | Notes |
|---|---|---|
| Three.js / WebGL | ~256 bones | Uniform array limit; use skeleton texture trick for >256 |
| Mobile (OpenGL ES 3) | 75–128 | Varies by GPU vendor |
| Unity (URP/HDRP) | No hard limit | Default 4 influences; 8 max |
| Unreal Engine 5 | 65,536 | GPU skinning per-LOD: 75 bones |
| Godot 4 | No hard limit | 8 influences per vertex max |

**Influences:** 4 is the universal safe maximum for games. `export_influence_nb=4` in glTF;
FBX defaults to 4. Always run `vertex_group_limit_total(limit=4)` before export.

---

## §15. Rig validation script

```python
# rig_validate.py — run headlessly; exits non-zero on critical errors
import bpy, sys

def validate_rig(arm_obj: bpy.types.Object) -> list[str]:
    errors = []
    arm = arm_obj.data

    for pb in arm_obj.pose.bones:
        for cns in pb.constraints:
            if cns.type == 'IK':
                if cns.chain_count == 0:
                    errors.append(f"[WARN] IK on '{pb.name}' chain_count=0 (full chain)")
                if cns.target is None:
                    errors.append(f"[ERROR] IK on '{pb.name}' has no target")
                if pb.bone.use_deform:
                    errors.append(f"[WARN] '{pb.name}' is deform AND has IK — exports incorrectly")

    deform_bones = {b.name for b in arm.bones if b.use_deform}
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            for mod in obj.modifiers:
                if mod.type == 'ARMATURE' and mod.object == arm_obj:
                    vg_names = {vg.name for vg in obj.vertex_groups}
                    missing = deform_bones - vg_names
                    if missing:
                        errors.append(f"[WARN] Mesh '{obj.name}' missing VGs: {missing}")

    for b in arm.bones:
        if b.name.startswith("DEF-") and not b.use_deform:
            errors.append(f"[ERROR] '{b.name}' has DEF- prefix but use_deform=False")

    deform_count = sum(1 for b in arm.bones if b.use_deform)
    if deform_count > 256:
        errors.append(f"[WARN] {deform_count} deform bones — exceeds WebGL ~256 limit")

    return errors


if __name__ == "__main__":
    arm_obj = bpy.data.objects.get("CharacterRig")
    if arm_obj is None:
        print("[ERROR] No armature named 'CharacterRig'")
        sys.exit(1)
    errs = validate_rig(arm_obj)
    for e in errs:
        print(e)
    sys.exit(1 if any("[ERROR]" in e for e in errs) else 0)
```

**PowerShell run:**
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    --background "C:\scenes\character.blend" `
    --python "C:\scripts\rig_validate.py"
if ($LASTEXITCODE -ne 0) { Write-Error "Rig validation FAILED"; exit 1 }
```

---

## §16. Gotcha → fix table

| Symptom | Cause | Fix |
|---|---|---|
| `AttributeError: 'EditBone' has no attribute 'head'` after mode switch | Edit bone refs are dangling pointers after leaving Edit Mode | `.copy()` all needed vectors before `mode_set(mode='OBJECT')` |
| Bones float — `use_connect` does nothing | `use_connect=True` set before `parent` | Set `bone.parent` first, then `bone.use_connect = True` |
| IK exports as flat (all bones at origin/rest pose) | IK is runtime-only; no baked FK keys | Bake with `nla.bake(visual_keying=True)` or `export_bake_animation=True` |
| Rigify MCH-/ORG- bones appear in exported glTF | Rigify leaves `use_deform=True` on non-deform bones (4.0–4.2 bug) | Post-generate loop: set `use_deform=False` on all `MCH-` / `ORG-` bones |
| Character rotated 90° in Unreal / Unity | FBX axis mismatch | `axis_forward='-Z', axis_up='Y'` (Unreal) or `axis_forward='Z', axis_up='Y'` (Unity) |
| glTF export error: non-decomposable matrix | Non-uniform scale through Rigify constraints | `export_hierarchy_flatten_bones=True` |
| Smooth deformation in Blender, sharp in engine | B-bones used in rig | Disable B-bones (`bone.bbone_segments=1`) before export; game rigs use twist DEF- bones instead |
| Double leaf-bones in Unreal/Unity after FBX import | `add_leaf_bones=True` | Set `add_leaf_bones=False` for UE/Unity exports |
| `RuntimeError: bpy.ops.armature.X poll() failed` | Context not set correctly | `bpy.context.view_layer.objects.active = arm_obj` before `mode_set` or use `temp_override` |
| Bendy bones (B-bones) in USD export lost | USD does not support B-bones (Blender 4.2/4.5) | Use standard bones; bake B-bone deformation before USD export |
