# forge-rig — Skinning & Skin Weights

# Contents
- §1. Mesh prep (mandatory before skinning)
- §2. Automatic weights (bone heat)
- §3. Envelope weights
- §4. Read/write vertex group weights via Python
- §5. Game-ready weight cleanup pipeline (4-influence)
- §6. Mirror weights
- §7. Smooth weights
- §8. Dual Quaternion Skinning (DQS)
- §9. Corrective shape key driven by bone angle
- §10. Armature modifier settings
- §11. Weight validation script
- §12. Posed-render verification (headless PNG check)
- §13. Gotcha → fix table

---

## §1. Mesh prep (mandatory before skinning)

Bone heat silently fails on dirty meshes. Run ALL of the following before `parent_set`:

```python
import bpy

def prepare_mesh_for_skinning(mesh_name: str, arm_name: str) -> None:
    mesh_obj = bpy.data.objects[mesh_name]
    arm_obj  = bpy.data.objects[arm_name]

    # 1. Apply all transforms on both objects
    for obj in (mesh_obj, arm_obj):
        bpy.context.view_layer.objects.active = obj
        obj.select_set(True)
        bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
        obj.select_set(False)

    # 2. Remove duplicate vertices
    bpy.context.view_layer.objects.active = mesh_obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.remove_doubles(threshold=0.0001)

    # 3. Check for non-manifold geometry (select it for inspection)
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.select_non_manifold(
        extend=False, use_wire=True, use_boundary=False,
        use_multi_face=True, use_non_contiguous=True, use_verts=True,
    )
    # Count selected verts — if > 0, bone heat may fail
    sel_count = sum(1 for v in bpy.context.active_object.data.vertices if v.select)
    if sel_count > 0:
        print(f"[WARN] {sel_count} non-manifold verts found in {mesh_name} — fix before skinning")

    bpy.ops.object.mode_set(mode='OBJECT')
```

**Checklist before skinning:**
- [ ] Transforms applied (Ctrl+A → All Transforms)
- [ ] No non-manifold edges (multi-face edges, wire edges, non-contiguous normals)
- [ ] No duplicate vertices (Merge by Distance applied)
- [ ] Subdivision modifier applied at the level used for weighting, OR sitting above Armature in stack
- [ ] Rest pose is the intended bind pose (T-pose or A-pose — decide first)

---

## §2. Automatic weights (bone heat)

```python
import bpy

def apply_automatic_weights(mesh_name: str, armature_name: str) -> None:
    """
    Parents mesh to armature using bone-heat automatic weights.
    Blender 4.x: use temp_override instead of context.copy() (removed in 4.x+).
    """
    mesh_obj = bpy.data.objects[mesh_name]
    arm_obj  = bpy.data.objects[armature_name]

    bpy.ops.object.select_all(action='DESELECT')
    mesh_obj.select_set(True)
    arm_obj.select_set(True)
    bpy.context.view_layer.objects.active = arm_obj  # armature must be active/last-selected

    bpy.ops.object.parent_set(type='ARMATURE_AUTO', xmirror=False, keep_transform=False)
    print(f"[skinning] Automatic weights applied: {mesh_name} → {armature_name}")

apply_automatic_weights("Body", "Armature")
```

**Context override variant (Blender 4.0+ for non-standard contexts):**
```python
with bpy.context.temp_override(
    active_object=arm_obj,
    object=arm_obj,
    selected_objects=[mesh_obj, arm_obj],
    selected_editable_objects=[mesh_obj, arm_obj],
):
    bpy.ops.object.parent_set(type='ARMATURE_AUTO')
```

**Bone heat failure fallbacks (in order of preference):**
1. Fix non-manifold topology (most common cause)
2. Scale up temporarily: `obj.scale = (100, 100, 100)` → auto-weight → `obj.scale = (1, 1, 1)` → Apply scale
3. Decimate proxy: Decimate mesh → auto-weight decimated → Data Transfer weights back
4. Separate by loose parts → weight each → re-join
5. Voxel Heat Diffuse Skinning (Blender Market, ~$30) — works on non-manifold meshes

---

## §3. Envelope weights

For mechanical rigs or when topology confuses bone heat:

```python
# Switch existing Armature modifier to envelope mode
arm_mod = next(m for m in bpy.data.objects["Body"].modifiers if m.type == 'ARMATURE')
arm_mod.use_bone_envelopes = True
arm_mod.use_vertex_groups  = False

# Or parent using envelopes from the start:
bpy.ops.object.parent_set(type='ARMATURE_ENVELOPE')
```

---

## §4. Read/write vertex group weights via Python

```python
import bpy
import bmesh

obj  = bpy.data.objects["Body"]
mesh = obj.data

# --- READ: all weights for a specific vertex ---
def print_vertex_weights(obj, vert_index: int) -> None:
    group_map = {g.index: g.name for g in obj.vertex_groups}
    for vge in obj.data.vertices[vert_index].groups:
        print(f"  bone={group_map[vge.group]!r}  weight={vge.weight:.4f}")

# --- WRITE: assign weights directly (no mode switch needed) ---
def assign_weights(obj, bone_name: str, vertex_indices: list, weight: float) -> None:
    vg = obj.vertex_groups.get(bone_name)
    if vg is None:
        vg = obj.vertex_groups.new(name=bone_name)
    vg.add(vertex_indices, weight, 'REPLACE')   # 'REPLACE' | 'ADD' | 'SUBTRACT'

# --- BULK READ via BMesh deform layer (faster for large meshes) ---
def read_weights_bmesh(obj, group_index: int) -> dict:
    """Returns {vert_index: weight} for a vertex group."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    dvert_lay = bm.verts.layers.deform.active
    weights = {}
    for vert in bm.verts:
        dvert = vert[dvert_lay]
        if group_index in dvert:
            weights[vert.index] = dvert[group_index]
    bm.free()
    return weights

# --- Verify max influences ---
def max_influences(obj) -> int:
    return max(len(list(v.groups)) for v in obj.data.vertices)
```

---

## §5. Game-ready weight cleanup pipeline (4-influence)

Run this sequence before every FBX/glTF export. All `vertex_group_*` operators require
Object mode with the object active and selected.

```python
import bpy

def weight_cleanup_pipeline(
    obj_name: str,
    limit: int = 4,
    clean_threshold: float = 0.005,
) -> None:
    obj = bpy.data.objects[obj_name]
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='OBJECT')

    # Step 1: Remove weights below threshold (keep_single=True = never zero a vertex)
    bpy.ops.object.vertex_group_clean(
        group_select_mode='ALL',
        limit=clean_threshold,
        keep_single=True,
    )

    # Step 2: Trim to N influences per vertex (removes lowest-weight influences first)
    bpy.ops.object.vertex_group_limit_total(
        group_select_mode='ALL',
        limit=limit,
    )

    # Step 3: Normalize so all influences sum to 1.0
    # lock_active=False ensures the active group is included (common gotcha)
    bpy.ops.object.vertex_group_normalize_all(
        group_select_mode='ALL',
        lock_active=False,
    )

    print(f"[skinning] Cleanup done: {obj_name} (limit={limit}, threshold={clean_threshold})")
    print(f"  Max influences now: {max(len(list(v.groups)) for v in obj.data.vertices)}")

weight_cleanup_pipeline("Body", limit=4, clean_threshold=0.005)
```

**Verify before export:**
```python
max_inf = max(len(list(v.groups)) for v in bpy.data.objects["Body"].data.vertices)
assert max_inf <= 4, f"Still {max_inf} influences — re-run cleanup"
```

---

## §6. Mirror weights

Requires mesh to be X-symmetric (vertices at matching ±X positions).

```python
bpy.ops.object.select_all(action='DESELECT')
obj.select_set(True)
bpy.context.view_layer.objects.active = obj

bpy.ops.object.vertex_group_mirror(
    mirror_weights  = True,
    flip_group_names = True,   # "upper_arm.L" ↔ "upper_arm.R"
    all_groups       = True,
    use_topology     = False,  # spatial X-mirror, not topology
)
```

---

## §7. Smooth weights

```python
bpy.ops.object.mode_set(mode='WEIGHT_PAINT')

# Enable vertex selection in weight paint mode
bpy.context.object.data.use_paint_mask_vertex = True
bpy.ops.paint.vert_select_all(action='SELECT')

bpy.ops.object.vertex_group_smooth(
    group_select_mode = 'ALL',
    factor            = 0.5,   # 0.0=no change, 1.0=full local average
    repeat            = 3,     # smoothing passes
    expand            = 0.0,   # 0=uniform
)
bpy.ops.object.mode_set(mode='OBJECT')
```

**Auto-normalize during weight painting:**
```python
bpy.context.tool_settings.use_auto_normalize = True
```
Enable before entering Weight Paint mode — distributes weight automatically across all bones
as you paint, maintaining sum=1.

---

## §8. Dual Quaternion Skinning (DQS)

Eliminates candy-wrapper twist artifact at the cost of potential joint bulging.

```python
arm_mod = next(m for m in obj.modifiers if m.type == 'ARMATURE')
arm_mod.use_deform_preserve_volume = True   # DQS on

# Verify
print(f"DQS enabled: {arm_mod.use_deform_preserve_volume}")
```

**LBS vs DQS decision table:**

| Situation | Choice |
|---|---|
| Default game character | LBS (`use_deform_preserve_volume=False`) |
| Twisting forearm > 90° | DQS to prevent candy-wrapper collapse |
| Extreme bend at joint | LBS + corrective shape key (DQS bulges) |
| Film/VFX quality | DQS + corrective shape keys for best of both |

**Corrective shape keys add-on gotcha:** The bundled Corrective Shape Keys add-on "Fast"
method is incompatible with DQS. Use "Slow" method if `use_deform_preserve_volume=True`.

---

## §9. Corrective shape key driven by bone angle

```python
import bpy, math

def add_pose_reader_driver(
    obj_name: str,
    shapekey_name: str,
    armature_name: str,
    bone_a_index: int,
    bone_b_index: int,
    on_at_dot: float = 0.0,
) -> None:
    """
    Drives a corrective shape key by the dot product of two pose bone aim vectors.
    dot=1 → bones parallel; dot=0 → perpendicular; dot=-1 → opposite.
    """
    obj     = bpy.data.objects[obj_name]
    arm_obj = bpy.data.objects[armature_name]

    if obj.data.shape_keys is None:
        obj.shape_key_add(name='Basis', from_mix=False)
    sk = obj.data.shape_keys.key_blocks.get(shapekey_name)
    if sk is None:
        sk = obj.shape_key_add(name=shapekey_name, from_mix=False)

    fcurve = sk.driver_add('value')
    drv = fcurve.driver
    drv.type = 'SCRIPTED'

    var = drv.variables.new()
    var.name   = 'poseBones'
    var.type   = 'SINGLE_PROP'
    tgt = var.targets[0]
    tgt.id_type   = 'OBJECT'
    tgt.id        = arm_obj
    tgt.data_path = 'pose.bones'

    # '@' is the dot product operator for Vectors in Blender 4.x (NOT '*', which is deprecated)
    drv.expression = (
        f"poseBones[{bone_a_index}].matrix.col[1] @ "
        f"poseBones[{bone_b_index}].matrix.col[1]"
    )
    print(f"[skinning] Corrective driver added: {shapekey_name}")
```

---

## §10. Armature modifier settings

```python
arm_mod = next(m for m in obj.modifiers if m.type == 'ARMATURE')
arm_mod.use_vertex_groups          = True    # always
arm_mod.use_bone_envelopes         = False   # unless envelope workflow
arm_mod.use_deform_preserve_volume = False   # start with LBS; toggle for DQS
```

**Modifier stack order (top to bottom):**
1. Mirror (if mesh is symmetric)
2. Armature ← this position is canonical
3. Subdivision Surface (if real-time preview quality needed)
4. Corrective shape keys (handled by Corrective Shape Keys add-on, added automatically)

Never place Armature above Mirror — the Mirror modifier must see the base mesh, not a posed one.

---

## §11. Weight validation script

```python
import bpy

def validate_skin_weights(obj_name: str, max_influences: int = 4) -> dict:
    obj  = bpy.data.objects[obj_name]
    mesh = obj.data

    results = {
        "total_verts":         len(mesh.vertices),
        "unweighted_verts":    [],    # no influences — will not deform
        "over_limit_verts":    [],    # exceeds max_influences
        "non_normalized_verts": [],   # weights sum != 1.0
        "orphan_groups":       [],    # vertex groups with no matching bone
    }

    bone_names = set()
    for mod in obj.modifiers:
        if mod.type == 'ARMATURE' and mod.object:
            bone_names = {b.name for b in mod.object.data.bones}

    for v in mesh.vertices:
        n   = len(list(v.groups))
        tot = sum(vge.weight for vge in v.groups)
        if n == 0:
            results["unweighted_verts"].append(v.index)
        if n > max_influences:
            results["over_limit_verts"].append(v.index)
        if n > 0 and abs(tot - 1.0) > 0.001:
            results["non_normalized_verts"].append((v.index, tot))

    for vg in obj.vertex_groups:
        if vg.name not in bone_names:
            results["orphan_groups"].append(vg.name)

    ok = (
        len(results["unweighted_verts"]) == 0
        and len(results["over_limit_verts"]) == 0
        and len(results["non_normalized_verts"]) == 0
    )
    print(f"\n=== Weight Validation: {obj_name} ===")
    print(f"  Total verts:       {results['total_verts']}")
    print(f"  Unweighted:        {len(results['unweighted_verts'])}")
    print(f"  Over limit ({max_influences}):   {len(results['over_limit_verts'])}")
    print(f"  Non-normalized:    {len(results['non_normalized_verts'])}")
    print(f"  Orphan groups:     {results['orphan_groups']}")
    print(f"  PASS: {ok}\n")
    return results

validate_skin_weights("Body", max_influences=4)
```

---

## §12. Posed-render verification (headless PNG check)

```python
# pose_and_render_verify.py
import bpy, math, os

def pose_and_render(
    armature_name: str,
    pose_map: dict,        # {"BoneName": (rx_deg, ry_deg, rz_deg)}
    output_path: str,
    frame: int = 1,
) -> None:
    arm_obj = bpy.data.objects[armature_name]
    bpy.context.view_layer.objects.active = arm_obj
    bpy.ops.object.mode_set(mode='POSE')

    for bone_name, (rx, ry, rz) in pose_map.items():
        bone = arm_obj.pose.bones.get(bone_name)
        if bone is None:
            print(f"[warn] Bone not found: {bone_name}")
            continue
        bone.rotation_mode  = 'XYZ'
        bone.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))

    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.scene.frame_set(frame)

    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'          # EEVEE-Next unsupported headless on Windows
    scene.cycles.device = 'CPU'
    scene.render.image_settings.file_format = 'PNG'
    scene.render.filepath = output_path
    bpy.ops.render.render(write_still=True)
    print(f"[verify] Render saved: {output_path}")

pose_and_render(
    armature_name = "Armature",
    pose_map      = {
        "upper_arm.L": (0, 0, -90),    # arm raised 90°
        "forearm.L":   (0, 0, -120),   # elbow bent 120°
    },
    output_path = "C:/project/.forge-build/out/verify_elbow_bend.png",
)
```

**PowerShell invocation:**
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
& $blender --background "C:\project\character.blend" `
    --python "C:\project\scripts\pose_and_render_verify.py"
```

After running, use the `Read` tool on the PNG path. A flat T-pose means IK baking failed or
the pose was not applied. A visibly bent mesh means skinning is working.

---

## §13. Gotcha → fix table

| Symptom | Cause | Fix |
|---|---|---|
| "Bone Heat Weighting: Failed to find solution" | Non-manifold edges, unapplied scale, internal faces, or duplicated verts | Apply transforms; merge by distance; fix non-manifold; scale proxy if needed |
| Candy-wrapper twist at wrist/forearm | LBS can't interpolate rotation matrices correctly | Enable DQS (`use_deform_preserve_volume=True`) |
| Joint collapses at elbow/knee bend | LBS volume loss at folded joint | Add helper bones at joint + gradual weight falloff over 3-4 edge loops |
| Joint pinching — narrow squeezing at fold | Hard weight boundary, no gradient | Smooth operator `factor=0.3, repeat=5` at joint boundary |
| DQS causes joint bulging | DQS creates artificial inflation near joint | Add corrective shape key at 90° bend; sculpt volume back |
| `vertex_group_normalize_all` leaves active group unchanged | `lock_active=True` (default) | Always pass `lock_active=False` |
| Weights silently truncated in Unity/Unreal | `vertex_group_limit_total` never run | Run full cleanup pipeline before every export; verify `max(len(list(v.groups)))<=4` |
| `context.copy()` AttributeError in Blender 4.x | `context.copy()` removed in Blender 4.x | Replace with `bpy.context.temp_override(...)` |
| `vertex_group_*` operator RuntimeError | Wrong mode or object not active/selected | `mode_set(mode='OBJECT')`, `obj.select_set(True)`, `view_layer.objects.active = obj` |
| Windows path backslash crash in render filepath | `\r` or `\n` inside string literal | Use `"C:/path/to/file.png"` or `r"C:\path\to\file.png"` |
| Corrective shape key "Fast" method broken with DQS | Fast method disables DQS internally | Use "Slow" method when `use_deform_preserve_volume=True` |
