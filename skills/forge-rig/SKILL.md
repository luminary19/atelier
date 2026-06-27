---
name: forge-rig
version: 1.0.0
description: >
  Forge suite — armatures, IK/FK, skinning/weights, and blend shapes / morph targets.
  Build a complete character or mechanical rig: create bone hierarchies, add IK (inverse
  kinematics) or FK (forward kinematics) constraints, bind a mesh with automatic or manual
  weights, enforce the 4-influence game-ready limit, AUTHOR shape keys / morph targets and
  their corrective drivers (facial FACS / ARKit-52 / corrective — the *animation* of those
  shapes is forge-animate), and export a verified rig to glTF / FBX / USD. Use whenever asked
  to rig a character, add bones, weight paint, skin a mesh, set up IK chains, add or author
  blend shapes, morph targets, shape keys, corrective shapes, or pose/deform a mesh for
  animation. Hands off to forge-animate for keyframing, shape-key/morph *animation*, and NLA
  baking; to forge-export for final format export; to forge-validate for the gate.
  HEADLESS-ONLY: driven from code via bpy Python scripts, output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - armature
  - bone hierarchy
  - ik constraint
  - fk rig
  - weight paint
  - skin mesh
  - vertex weights
  - shape keys
  - blend shapes
  - morph targets
  - facial rig
  - arkit 52
  - corrective shape key
  - rig character
  - deform bones
  - rigify
  - skinning
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# forge-rig — Armatures · IK/FK · Skinning · Blend Shapes

The structural skeleton of the character pipeline. A correctly built rig is a hard prerequisite
for animation, cloth simulation, facial capture, and engine import. The discipline: **deform
bones only in the export; every control and IK target is invisible to the game engine.**

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the coordinate system, target engine, poly/bone budget, and output paths for this project.
> If **`ATELIER.md`** also exists, the aesthetic world and signature moment are there.

---

> **Suite map** — forge-rig is the skeleton layer; context:
>
> - **`forge-model`** / **`forge-topology`** → finalized mesh that enters this skill
> - **`forge-rig`** ← YOU ARE HERE: armatures, IK/FK, weights, blend shapes
> - **`forge-animate`** → keyframes, NLA strips, baking IK to FK curves
> - **`forge-sim`** → cloth/hair pinning uses the deform bone set built here
> - **`forge-export`** → format matrix (glTF skins / FBX skeleton / USD UsdSkel)
> - **`forge-validate`** → manifold, weight QA, glTF-Validator gate; escalates to forge-render
> - **`forge-render`** → headless Cycles render; verifies posed-mesh deformation visually
>
> Cross-suite: **`atelier-webgl`** consumes the final `.glb` with embedded skins and morph targets
> via the forge-export → forge-optimize → atelier-webgl handoff chain.
>
> **Run = call the Skill tool with the exact name. Writing "next: forge-validate" runs nothing.**

---

## Decide first: tool + availability

Before any bone or weight work, confirm Blender is reachable:

```powershell
# Verify Blender is available (PowerShell)
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
if (-not (Test-Path $blender)) { Write-Error "Blender not found at $blender" }
& $blender --version
```

If Blender is absent, stop and report the exact path checked. Do NOT fall back to a different
tool — rigging is Blender-only in this suite.

**Pick the rig type** before writing a single bone:

| Scenario | Approach |
|---|---|
| Organic character, games / web | Manual DEF- chain + IK limbs or Rigify generation |
| Mechanical / vehicle | Manual DEF- chain, envelope weights or manual groups |
| Face / facial capture (ARKit) | Shape keys only (no bones required for face deform) |
| Film/VFX character | Rigify full meta-rig; B-bones allowed (bake before export) |
| Corrective shapes for an existing rig | Shape keys with bone-rotation drivers |

---

## The flow

1. **Read FORGE.md** → confirm engine target, coordinate system (Y-up for glTF), scale unit
   (1 Blender unit = 1 m), and bone/influence budget. If absent, ask or write defaults.

2. **Preflight** → verify Blender path; check mesh is topology-locked (apply transforms,
   remove non-manifold, merge duplicate verts) before touching any armature.
   Full mesh-prep checklist: **`references/skinning-weights.md` §Mesh prep**

3. **Build armature** → create deform bone chain in Edit Mode; set DEF-/MCH-/IK- prefixes;
   use `.L` / `.R` bilateral suffixes; set `use_deform` correctly on every bone.
   Full API + naming rules: **`references/rigging-armatures.md`**

4. **IK / FK constraints** → add IK constraints in Pose Mode; set explicit `chain_count`;
   place IK targets outside the chain; set `pole_angle` geometrically.
   Full constraint table + gotchas: **`references/rigging-armatures.md` §Constraints**

5. **Symmetrize** → mirror `.L` bones to `.R` via `bpy.ops.armature.symmetrize()`.

6. **Bind mesh** → parent mesh to armature with Automatic Weights (bone heat); apply
   `weight_cleanup_pipeline(limit=4)` for game-ready output; verify with programmatic
   weight validation script.
   Full skinning pipeline: **`references/skinning-weights.md`**

7. **Blend shapes / morph targets** (if needed) → add Basis key first; build shape keys via
   `foreach_set` (not per-vertex loops); add corrective drivers; validate ARKit names if
   targeting face capture.
   Full blend-shape pipeline: **`references/blendshapes-morphs.md`**

8. **Visual verification** → write a headless pose-and-render script; run it via Blender `-b`;
   `Read` the output PNG and confirm the mesh deforms (not flat T-pose).
   Render invocation must use Cycles (EEVEE-Next is unsupported headless on Windows):

   ```powershell
   & "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
       --background "C:\project\character.blend" `
       --python "C:\project\scripts\pose_render_check.py" `
       --python-exit-code 1 `
       -- --output "C:\project\.forge-build\out\rig_check.png"
   ```

   The `--` separator is mandatory. Use absolute forward-slash paths in `render.filepath`.
   **Deterministic QA render:** the check script must set `scene.render.engine = 'CYCLES'`,
   `scene.cycles.device = 'CPU'`, a fixed `scene.cycles.samples` (e.g. 32), and a fixed
   `scene.cycles.seed = 0`, so two rig-checks of the same pose render identically (diffable).
   **Guard before Read:** confirm the PNG exists and is **> 1 KB** before `Read` — a missing or
   sub-1 KB file is Blender's error image, not a render. If it's missing/tiny, the render failed
   silently; re-run with `--python-exit-code 1` (above) and inspect stderr instead of `Read`-ing
   a phantom path. Failure triage: **`references/skinning-weights.md` §13** (verify-PNG symptoms).

9. **Rig validation** → run `rig_validate.py` headlessly; confirm zero `[ERROR]` lines; check
   deform bone count is within engine limits (≤ 256 for WebGL, ≤ 128 for mobile).
   Full validation script: **`references/rigging-armatures.md` §Validation**

10. **Hand off** →
    - For animation: invoke `Skill("forge-animate")` with the blend file path.
    - For export: invoke `Skill("forge-export")` — set `export_def_bones=True`,
      `export_bake_animation=True`, `export_influence_nb=4` for glTF; or the FBX
      axis/leaf-bone flags for Unreal/Unity. Export settings table:
      **`references/rigging-armatures.md` §Export**
    - Always gate with `Skill("forge-validate")` before final delivery.

---

## If the verify PNG is wrong

Triage the render before you re-rig. Full 10-row gotcha table: **`references/skinning-weights.md` §13**.

| Symptom in the PNG | Likely cause | Fix |
|---|---|---|
| Flat T-pose (no deformation) | IK not baked, or pose never applied | Bake IK (visual keying) before render — see **Key invariants** / `rigging-armatures.md` §12 |
| Mesh explodes / spikes | Weight cleanup not run (>4 influences, unnormalized) | Run `weight_cleanup_pipeline(limit=4)` — `skinning-weights.md` §5 |
| Joint collapses / candy-wraps | LBS volume loss or rotation interpolation | Helper bones + weight falloff, or DQS — `skinning-weights.md` §13 |
| File missing or < 1 KB | Render failed silently (error image) | Re-run with `--python-exit-code 1`, inspect stderr; do NOT `Read` |

## Key invariants

**Deform bones only in export.** Set `use_deform=False` on every MCH-, IK-, FK-, ORG- bone
before export. The `export_def_bones=True` / `use_armature_deform_only=True` flags read this
flag directly. A single control bone leaking into the export breaks engine retargeting.

**4 influences, always.** Run `vertex_group_limit_total(limit=4)` + `vertex_group_normalize_all`
before any FBX/glTF export. Unity hard-limits at 4; Unreal recommends 4 for performance.
Verify: `max(len(list(v.groups)) for v in obj.data.vertices)` must equal ≤ 4.

**IK must be baked before export.** IK constraint positions are solver-runtime; exported bones
store FK data. Without baking, all exported bones appear at rest pose. Use `nla.bake` with
`visual_keying=True` before export, or set `export_bake_animation=True` in the glTF operator.

**Blend shapes: topology lock first.** Adding or removing vertices after shape key creation
silently corrupts delta data. Confirm `len(mesh.vertices) == len(shape_keys.key_blocks[0].data)`
before authoring keys. `export_apply=False` is mandatory — `True` destroys all keys silently.

**Edit bone refs die on mode switch.** Copy all needed head/tail vectors with `.copy()` BEFORE
calling `mode_set(mode='OBJECT')`. Edit bone Python objects are dangling pointers after leaving
Edit Mode.

**Blender 4.x context:** use `bpy.context.temp_override(...)` — `context.copy()` is removed.

---

## Operating principles

- **Gate before you skin.** Validate mesh topology (non-manifold check, applied transforms,
  merged duplicates) before any bone heat attempt. Bone heat silently fails on dirty meshes.
- **Deform vs control is a binary rule, not a preference.** Every bone must be explicitly marked;
  never leave the default `use_deform=True` on control or IK bones.
- **Bake IK before every export.** IK is a viewport solver; no exporter reads it directly.
  Visual keying + baking is the only way to get correct exported bone transforms.
- **Verify by posing and reading the PNG.** The only headless truth is a rendered PNG with the
  mesh in a non-rest pose. A flat T-pose render means something failed silently — fix before
  declaring done.
- **Run = call the Skill tool.** Handing off to forge-validate, forge-animate, or forge-export
  means invoking `Skill("forge-validate")` / `Skill("forge-animate")` / `Skill("forge-export")`
  via the Skill tool. Writing "next, run forge-validate" in prose runs nothing.
