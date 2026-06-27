# forge-animate — Keyframes, F-Curves, Easing & NLA Reference

Blender 4.4 / 4.5 LTS / 5.0+ | Native Windows 11 | Headless bpy Python

## Contents

- §1. Version guards and data model overview
- §2. `keyframe_insert` — simple insertion
- §3. Low-level F-curve construction (4.4+ / 5.0+)
- §4. Reading and modifying interpolation / easing
- §5. Easing quick-reference table
- §6. F-Curve Modifiers (Cycles, Noise, Generator)
- §7. NLA multi-clip construction
- §8. Scene frame rate and length
- §9. Baking constraints / IK / sims to keyframes
- §10. Post-bake interpolation conversion (LINEAR for export)
- §11. Validation script
- §12. Common gotchas → fix table

---

## §1. Version guards and data model overview

**4.4 introduced slotted Actions. 5.0 removed `action.fcurves`.**

```python
import bpy

BLENDER_44 = bpy.app.version >= (4, 4, 0)
BLENDER_50 = bpy.app.version >= (5, 0, 0)
```

| Object | Meaning |
|--------|---------|
| `bpy.data.actions["Name"]` | Named clip of animation curves |
| `Action.slots[i]` | Binds action to a specific ID type (4.4+) |
| `Action.layers[0].strips[0]` | Infinite keyframe strip (sole strip in current Blender) |
| `ActionChannelbag` | Container of F-Curves for one slot on one strip |
| `FCurve` | Single animated property over time |
| `Keyframe` | One point on an FCurve (co, handle_left, handle_right, interpolation) |
| `FModifier` | Non-destructive layer on top of an FCurve (Cycles, Noise, etc.) |
| `NlaTrack / NlaStrip` | Non-Linear Animation editor rows and clips |

Parse custom script args (mandatory `--` separator):

```python
import sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
```

---

## §2. `keyframe_insert` — simple insertion

Works on any `bpy_struct` property. Auto-creates action/slot/layer/strip/channelbag/FCurve.
Safe across 4.3, 4.4, 4.5, 5.0.

```python
import bpy

obj = bpy.data.objects["Cube"]

obj.location.z = 0.0
obj.keyframe_insert(data_path="location", index=2, frame=1)

obj.location.z = 2.5
obj.keyframe_insert(data_path="location", index=2, frame=30)

# Useful options flags:
#   INSERTKEY_NEEDED      — skip if value unchanged
#   INSERTKEY_REPLACE     — overwrite existing key only
#   INSERTKEY_VISUAL      — capture post-constraint evaluated value
#   INSERTKEY_CYCLE_AWARE — respect Cycles FModifier seam

obj.location.z = 0.0
obj.keyframe_insert(
    data_path="location",
    index=2,
    frame=60,
    options={'INSERTKEY_NEEDED'},
    keytype='KEYFRAME',   # KEYFRAME / BREAKDOWN / MOVING_HOLD / EXTREME / JITTER
)
```

---

## §3. Low-level F-curve construction (4.4+ / 5.0+)

Use for bulk inserts (motion capture, procedural) — avoids per-frame scene evaluation overhead.

```python
import bpy
from bpy_extras import anim_utils

obj    = bpy.data.objects["Cube"]
action = bpy.data.actions.new(name="ProcAnim")
slot   = action.slots.new(obj.id_type, obj.name)
cbag   = action.layers.new("Layer").strips.new(type='KEYFRAME').channelbag(slot, ensure=True)
fcu    = cbag.fcurves.new(data_path="location", index=2)

fcu.keyframe_points.add(120)
for i in range(120):
    kp = fcu.keyframe_points[i]
    kp.co = float(i + 1), float(i) * 0.05
    kp.interpolation = 'BEZIER'
    kp.handle_left_type = kp.handle_right_type = 'AUTO_CLAMPED'

fcu.update()   # MANDATORY: sort + recalc handles after bulk add

adt = obj.animation_data_create()
adt.action = action; adt.action_slot = slot   # 4.4+ both required

# 5.0+ shortcut (skip manual layer/strip/channelbag):
# fcu = action.fcurve_ensure_for_datablock(obj, "location", index=2, group_name="Location")
```

**Reading channelbag (4.4+/5.0+ — replaces `action.fcurves`):**
```python
cbag = anim_utils.action_get_channelbag_for_slot(action, obj.animation_data.action_slot)
fcu  = cbag.fcurves.find("location", index=2)
```

---

## §4. Reading and modifying interpolation / easing

```python
# fcu = cbag.fcurves.find("location", index=2)  (see §3 for channelbag lookup)
for kp in fcu.keyframe_points:
    kp.interpolation = 'BEZIER'; kp.easing = 'EASE_IN_OUT'
# Manual overshoot: push right handle past target value
kp0 = fcu.keyframe_points[0]
kp0.handle_right_type = 'FREE'
kp0.handle_right = (kp0.co.x + 5.0, kp0.co.y + 0.4)
fcu.update()   # always required after manual handle edits
```

---

## §5. Easing quick-reference table

| Use case | Interpolation | Easing | Handle type |
|----------|--------------|--------|-------------|
| General motion | BEZIER | AUTO | AUTO_CLAMPED |
| UI state transition | BEZIER | EASE_IN_OUT | ALIGNED |
| Spring/bounce entrance | BACK or ELASTIC | EASE_OUT | FREE |
| Looping idle (spin) | BEZIER | AUTO | AUTO + Cycles FModifier |
| Game-engine export (glTF LINEAR) | LINEAR | — | VECTOR |
| Camera shake (subtle) | LINEAR base + Noise FModifier | — | — |

**Interpolation enum values for `kp.interpolation`:**
`CONSTANT`, `LINEAR`, `BEZIER`, `SINE`, `QUAD`, `CUBIC`, `QUART`, `QUINT`, `EXPO`, `CIRC`,
`BACK` (overshoot), `BOUNCE` (decaying parabola), `ELASTIC` (decaying sine/spring)

**Disney principle → Blender:** Slow In/Out → BEZIER+EASE_IN_OUT; Anticipation → extra key 3–5f
before move, value slightly past start; Follow-through → Noise FModifier (low strength) on trailing
bones; Squash/Stretch → Scale FCurves on Z; Exaggeration → BACK interp or FREE handles past target;
Arcs → X+Z location keys with offset timing; Secondary Action → separate NLA track, ADD blend.

---

## §6. F-Curve Modifiers (Cycles, Noise, Generator)

FModifiers are **non-destructive** — they do not bake to keys. Bake before FBX/glTF export.

### Cycles modifier (loop / repeat)

```python
# fcu obtained via channelbag (see §3)
mod = fcu.modifiers.new('CYCLES')
mod.mode_before   = 'REPEAT_OFFSET'   # NONE / REPEAT / REPEAT_OFFSET / MIRROR
mod.mode_after    = 'REPEAT_OFFSET'
mod.cycles_before = 0   # 0 = infinite
mod.cycles_after  = 0

# Seamless loop: ensure first and last keyframe values match
last  = fcu.keyframe_points[-1]
first = fcu.keyframe_points[0]
if abs(last.co.y - first.co.y) > 1e-5:
    last.co = (last.co.x, first.co.y)
    fcu.update()
# Use INSERTKEY_CYCLE_AWARE option when inserting subsequent keyframes
```

Cycles modifier MUST be the **first** modifier on the FCurve (Blender enforces this).

### Noise modifier (camera shake, secondary motion)

```python
mod = fcu.modifiers.new('NOISE')
mod.blend_type = 'ADD'       # REPLACE / ADD / SUBTRACT / MULTIPLY
mod.strength   = 0.15        # < 0.2 for subtle camera shake; 0.3–0.8 for stylized
mod.scale      = 8.0         # time scale — higher = slower oscillation
mod.phase      = 42.0        # random seed (change per axis for natural movement)
mod.depth      = 2           # fractal detail (0 = single freq)
mod.roughness  = 0.5
mod.offset     = 0.0
```

---

## §7. NLA multi-clip construction

```python
import bpy

def stash_action(obj, action, track_name, start_frame):
    """Push action into a locked/muted NLA track (stashed, not evaluated)."""
    adt   = obj.animation_data
    track = adt.nla_tracks.new(prev=None)
    track.name = track_name
    strip = track.strips.new(action.name, int(start_frame), action)
    track.lock = True
    track.mute = True        # muted = stashed; False = active in mix
    adt.action = None        # detach so next keyframe_insert creates a fresh action
    return strip

# Build actions A and B, stash each, then unmute for NLA-driven playback:
obj = bpy.data.objects["Cube"]
obj.location.z = 0.0;  obj.keyframe_insert("location", index=2, frame=1)
obj.location.z = 1.0;  obj.keyframe_insert("location", index=2, frame=24)
action_a = obj.animation_data.action; action_a.name = "Rise"; action_a.use_fake_user = True
stash_action(obj, action_a, "Rise_track", start_frame=1)

obj.location.z = 1.0;  obj.keyframe_insert("location", index=2, frame=1)
obj.location.z = 0.0;  obj.keyframe_insert("location", index=2, frame=24)
action_b = obj.animation_data.action; action_b.name = "Fall"; action_b.use_fake_user = True
stash_action(obj, action_b, "Fall_track", start_frame=25)

for track in obj.animation_data.nla_tracks:
    track.mute = False; track.lock = False
obj.animation_data.action = None   # let NLA drive

# Strip properties:
strip = obj.animation_data.nla_tracks["Rise_track"].strips[0]
strip.blend_type    = 'REPLACE'    # REPLACE / ADD / SUBTRACT / MULTIPLY / COMBINE
strip.extrapolation = 'HOLD'       # freeze last pose (prevents T-pose snap)
strip.blend_in      = 4.0          # frames of blend-in at 24fps
strip.blend_out     = 4.0
```

**NLA best practices:** one action per motion → one NLA strip. `extrapolation='HOLD'` on final strip.
Stashed: `lock=True, mute=True`. `animation_data.action=None` after stashing.
Avoid `bpy.ops.nla.transition_add` headlessly (requires NLA_EDITOR context) — place strips manually.

---

## §8. Scene frame rate and length

```python
scene = bpy.context.scene
scene.render.fps = 24; scene.render.fps_base = 1.0  # real fps = fps / fps_base
scene.frame_start = 1; scene.frame_end = 120        # 5s at 24fps
```

fps guide: 24=film/cinematic (Blender default); 30=broadcast/Unity; 60=interactive/recordings.
Atelier-motion token mapping: micro 100–200 ms ≈ 3–5 frames @24fps; standard 200–400 ms ≈ 5–10 frames.

---

## §9. Baking constraints / IK / sims to keyframes

### High-level operator (headless-safe — requires POSE mode context)

```python
import bpy

obj = bpy.data.objects["Armature"]
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode='POSE')        # REQUIRED — operator returns CANCELLED if skipped
bpy.ops.pose.select_all(action='SELECT')
bpy.ops.nla.bake(
    frame_start=1, frame_end=120, step=1,
    only_selected=True, visual_keying=True,  # CRITICAL: post-constraint transforms
    clear_constraints=True, clear_parents=False,
    use_current_action=False, clean_curves=True,
    bake_types={'POSE'}, channel_types={'LOCATION', 'ROTATION', 'SCALE'},
)
bpy.ops.object.mode_set(mode='OBJECT')
```

### Low-level API (BakeOptions — 4.4+ mandatory; no operator needed)

```python
import bpy
from bpy_extras.anim_utils import bake_action, BakeOptions

obj    = bpy.data.objects["Armature"]
frames = list(range(1, 121))

opts = BakeOptions(
    only_selected       = False,
    do_pose             = True,
    do_object           = False,
    do_visual_keying    = True,    # capture final world-space transforms
    do_constraint_clear = True,    # remove constraints after bake
    do_parents_clear    = False,
    do_clean            = True,    # drop redundant keys
    do_location         = True,
    do_rotation         = True,
    do_scale            = True,
    do_bbone            = False,
    do_custom_props     = False,
)

baked_action = bake_action(obj, action=None, frames=frames, bake_options=opts)
baked_action.name = "Baked_IK"
baked_action.use_fake_user = True   # prevent orphan deletion
```

**Warning:** `BakeOptions` is a dataclass in 4.4+ — the old keyword-argument form to
`bake_action()` no longer works and raises `TypeError`.

**Visual keying (single-frame, per-frame loop):** call `scene.frame_set(frame)` then
`obj.keyframe_insert(data_path="location", frame=frame, options={'INSERTKEY_VISUAL'})`.
`frame_set` advances the depsgraph so `INSERTKEY_VISUAL` reads the post-constraint value.

---

## §10. Post-bake interpolation conversion (LINEAR for export)

glTF expects LINEAR or CUBICSPLINE. Convert after bake if needed:

```python
import bpy
from bpy_extras import anim_utils

obj    = bpy.data.objects["Armature"]
action = obj.animation_data.action
slot   = obj.animation_data.action_slot
cbag   = anim_utils.action_get_channelbag_for_slot(action, slot)

for fcu in cbag.fcurves:
    for kp in fcu.keyframe_points:
        kp.interpolation = 'LINEAR'
    fcu.update()
```

CUBICSPLINE export from Blender: F-curve handles must be BEZIER or AUTO; LINEAR handles in
Blender export as LINEAR interpolation (not CUBICSPLINE).

---

## §11. Validation snippet (run inside bpy before export)

```python
import bpy
from bpy_extras import anim_utils

def get_fcurves(obj):
    adt = obj.animation_data
    if not adt or not adt.action: return []
    if bpy.app.version >= (4, 4, 0):
        cbag = anim_utils.action_get_channelbag_for_slot(adt.action, adt.action_slot)
        return cbag.fcurves if cbag else []
    return adt.action.fcurves

def validate_animation(obj, fs, fe):
    issues = []
    adt = obj.animation_data
    if not adt or not adt.action:
        issues.append(("ERROR", f"{obj.name}: no action")); return issues
    if bpy.app.version >= (4, 4, 0) and adt.action_slot is None:
        issues.append(("ERROR", f"{obj.name}: action_slot is None — won't animate"))
    fcurves = get_fcurves(obj)
    if not fcurves:
        issues.append(("WARN", f"{obj.name}: no F-Curves"))
    for fcu in fcurves:
        kps = fcu.keyframe_points
        if len(kps) < 2:
            issues.append(("WARN", f"{fcu.data_path}[{fcu.array_index}]: {len(kps)} key(s)"))
        elif kps[-1].co.x < fe:
            issues.append(("INFO", f"{fcu.data_path}: last key {kps[-1].co.x} < frame_end {fe}"))
    return issues

scene = bpy.context.scene
for obj in scene.objects:
    if obj.animation_data:
        for sev, msg in validate_animation(obj, scene.frame_start, scene.frame_end):
            print(f"[{sev}] {msg}")
```

---

## §12. Common gotchas → fix table

| Symptom | Root cause | Fix |
|---------|-----------|-----|
| `AttributeError: 'Action' object has no attribute 'fcurves'` | Blender 5.0 removed legacy API | Use `anim_utils.action_get_channelbag_for_slot(action, slot).fcurves` |
| Action assigned but nothing moves (4.4+) | `action_slot` is None | `adt.action_slot = adt.action.slots[0]` |
| `bpy.ops.nla.bake()` returns `CANCELLED` | Not in POSE mode | `bpy.ops.object.mode_set(mode='POSE')` before calling |
| `bpy.ops.nla.transition_add()` context error | Requires NLA_EDITOR area | Place strips manually; avoid this operator headlessly |
| Visible seam/pop in Cycles-looped animation | First/last keyframe values differ | Set `last.co = (last.co.x, first.co.y); fcu.update()` |
| Handles render at wrong positions after bulk add | `fcu.update()` not called | Always call `fcu.update()` once after all `keyframe_points` are set |
| FBX/glTF export: animated bones snap or teleport | Constraints not baked | `visual_keying=True, clear_constraints=True` in `BakeOptions` |
| `TypeError: bake_action() got unexpected keyword argument 'do_visual_keying'` | Old kwarg form removed in 4.4 | Construct `BakeOptions(...)` dataclass explicitly |
| EEVEE engine ID error in Blender 5.0 | Engine string changed | `"BLENDER_EEVEE"` in 5.0+; `"BLENDER_EEVEE_NEXT"` in 4.x |
| Windows path silent export failure | Backslash in bpy filepath | Use forward slashes: `"C:/out/product.fbx"` |
