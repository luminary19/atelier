---
name: forge-animate
version: 1.0.0
description: >
  Forge suite — animation craft layer. Authors keyframes and F-curves, sets interpolation
  and easing (BEZIER/BACK/ELASTIC/BOUNCE), builds NLA clip libraries, bakes IK/constraint/sim
  motion to raw TRS keys, and exports skeletal + morph (blend-shape) animation to glTF/GLB,
  FBX, and USD formats — all headlessly from bpy Python.
  Use whenever animating objects or armatures, setting up keyframes, editing F-curve handles,
  choosing easing (ease-in-out, overshoot, bounce, spring), creating looping idles (Cycles
  modifier), adding camera shake (Noise modifier), baking IK/constraints before export,
  building NLA multi-clip sequences, exporting animated GLB for Three.js/R3F/Godot/Unity/UE5,
  or producing USD SkelAnimation. Also use for morph target / shape-key animation. Web/mobile
  compression of the exported GLB is forge-optimize's job (always Meshopt, never Draco, for
  animated/morph assets) — this skill hands off to it, it does not run gltf-transform itself.
  Run = call the Skill tool with the exact name. Saying "now run forge-X" in prose runs nothing.
  HEADLESS-ONLY: driven from code, output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - keyframe
  - f-curve
  - animate
  - bake animation
  - bake constraints
  - bake IK
  - morph animation
  - shape key animation
  - skeletal animation
  - NLA
  - animation export
  - glb animation
  - fbx animation
  - usd skel
  - easing
  - loop animation
  - camera shake
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge — Animation

Keyframes, F-curves, easing, baked constraints, NLA clip libraries, skeletal + morph export.
Everything runs inside Blender headlessly — no GUI, no interaction, output verified by rendering
a frame to PNG and reading it back.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the confirmed tool path, coordinate system (Z-up Blender → Y-up glTF), frame rate, poly budget,
> output paths, and the target engine (Three.js / Unreal / Unity / Godot / USD). Honor every
> setting it records; do not override without updating it.

---

> **Forge suite — animation sits here in the rigtech pipeline:**
>
> **forge** (router) → **forge-brief** (FORGE.md) → **forge-standards** (units/axes) →
> **forge-model** (mesh) → **forge-rig** (armature/IK/skin) → **`forge-animate`** (YOU) →
> **forge-sim** (cloth/hair/particles) → **forge-export** (format matrix) →
> **forge-optimize** (Draco/Meshopt) → **forge-validate** (gate) → **atelier-webgl** (web handoff)
>
> **forge-rig** is the upstream dependency — armatures, IK chains, and blend shapes must exist
> before this skill runs. If rigging is incomplete, invoke **forge-rig** first (Run = Skill tool).
>
> **forge-render** renders verification frames; **forge-validate** is the mandatory exit gate.
> Web handoff: **forge-export** → **forge-optimize** → **atelier-webgl**.
> Atelier connection: easing tokens from **atelier-motion** map directly to Blender Bezier handles
> (cubic-bezier(0.4,0,0.2,1) ≈ BEZIER + EASE_IN_OUT; 100–200 ms ≈ 3–5 frames at 24 fps).

---

## Decide first: tool + availability

Animation in Forge always uses **Blender**. Before writing any script:

1. Confirm `blender.exe` is on PATH or at the path recorded in FORGE.md.
2. Note the Blender version — **4.4+ uses the slotted Action data model** (slot + channelbag);
   **5.0+ removes `action.fcurves`** entirely. Guard with `bpy.app.version`.
3. Confirm the `.blend` file exists and contains the armature/objects to animate.

```powershell
# Quick availability check
& blender --version
```

If Blender is missing, stop and report the gap. Do NOT attempt to animate without it.

Full Windows headless invocation pattern (mandatory `--` separator for script args):

```powershell
$b = "C:\Program Files\Blender Foundation\Blender 5.0\blender.exe"
& $b -b "C:/project/rig.blend" -P "C:/scripts/anim.py" -- --start 1 --end 120 --out "C:/out"
```

Use **absolute forward-slash paths** inside bpy filepath parameters (never `//` relative paths).
Use `--python-exit-code 1` in production runs so Python errors fail the process.

---

## The flow

1. **Read FORGE.md** — confirm engine target, coordinate system, frame rate, output paths.

2. **Assess animation goal** — choose one of four tracks:
   - **A. Author keyframes/F-curves** from scratch (product spin, UI state, camera dolly)
   - **B. Edit interpolation/easing** on existing curves (make it snappier, add overshoot)
   - **C. Bake + export** — IK/constraint rig already authored; collapse to raw TRS for export
   - **D. NLA multi-clip library** — multiple actions → NLA tracks → single export

3. **Write the bpy script** — keep all real logic in the script file (not inline in this
   skill body). See `references/keyframes-fcurves.md` for all keyframe/F-curve patterns and
   `references/skeletal-morph-export.md` for export + validation patterns.

4. **Run headlessly** via PowerShell:
   ```powershell
   & $blender -b "C:/project/scene.blend" -P "C:/scripts/anim.py" -- <args>
   ```
   Capture stdout/stderr; a non-zero exit means the Python script failed.

5. **Bake step** (tracks B/C/D — always required before glTF/FBX export):
   - Use `bpy_extras.anim_utils.bake_action` with `BakeOptions` (4.4+ API) or
     `bpy.ops.nla.bake` (requires POSE mode context override).
   - `do_visual_keying=True` — captures post-constraint evaluated transforms.
   - `do_constraint_clear=True` — removes IK/Copy constraints after bake.
   - After bake: convert interpolation to `LINEAR` if the target engine requires it
     (glTF LINEAR is the safe default; CUBICSPLINE only when F-curve handles are BEZIER).
   - Full patterns: **`references/keyframes-fcurves.md §3.7–3.9`**.

6. **Export** — pick format from FORGE.md's target engine:
   - **glTF/GLB** (Three.js / Godot / UE5 Interchange): `bpy.ops.export_scene.gltf`
   - **FBX** (Unity / Unreal / DCC interchange): `bpy.ops.export_scene.fbx`
   - **USD SkelAnimation** (Omniverse / Houdini / USD pipeline): pxr Python API
   - Critical flags table + gotchas: **`references/skeletal-morph-export.md §3.2–3.4`**.

7. **Post-export optimization** (web/mobile delivery) — **hand off, don't hand-roll.**
   Compression of the exported GLB is **forge-optimize**'s domain. It selects **Meshopt** for
   animated/morph assets (never Draco — Draco cannot carry animation or morph buffers),
   sanity-checks the input→output size delta, and gates on spec validation — none of which the
   raw 3-line chain below does. For any web/mobile delivery:
   ```
   Skill("forge-optimize")   # pass the exported GLB path; it runs optimize.ps1 (Meshopt + validate)
   ```
   **Run = call the Skill tool with exact name `forge-optimize`. Writing it in prose runs nothing.**

   Fallback ONLY if forge-optimize is unavailable — first confirm the CLI exists, else skip and
   hand off the unoptimized GLB with a note:
   ```powershell
   if (Get-Command gltf-transform -ErrorAction SilentlyContinue) {
     gltf-transform resample input.glb step1.glb --tolerance 1e-4
     gltf-transform dedup    step1.glb step2.glb
     gltf-transform meshopt  step2.glb final.glb --level medium   # Meshopt, NEVER Draco, for animated GLBs
   } else {
     Write-Host "gltf-transform absent — skipping optimization; handing off the unoptimized GLB."
   }
   ```
   Full fallback pipeline: **`references/skeletal-morph-export.md §3.5`**.

8. **Validate**:
   - Run `gltf_validator.exe` on the GLB (see `references/skeletal-morph-export.md §6.1`).
   - Run programmatic animation inspection if morph channels are present (§6.2).
   - Invoke **forge-validate** (Run = call the Skill tool with exact name `forge-validate`).

9. **Render-verify** — render a **deterministic** mid-animation frame to PNG and read it back.
   Headless on Windows means **Cycles** (EEVEE Next is unsupported headless); pin the frame and
   sample count so the verify image is reproducible across runs:
   ```powershell
   & $blender -b "C:/project/scene.blend" `
     -E CYCLES `                              # Cycles — EEVEE Next has no headless GPU context on Win
     -o "C:/out/verify/frame_" -F PNG -f 15   # fixed frame 15; set cycles.samples (e.g. 64) in the .blend/script
   ```
   **Guard before Read** — a missing or <1 KB PNG is an error image, not a frame; do not Read it,
   fix the export and re-run from step 4:
   ```powershell
   $png = "C:/out/verify/frame_0015.png"
   if (-not (Test-Path $png) -or (Get-Item $png).Length -lt 1024) {
     Write-Host "verify render missing or <1KB — render failed; fix and re-run from step 4."; exit 1
   }
   ```
   Then `Read` the PNG to confirm: correct pose (not T-pose), no mesh explosion, morph expression
   visible. If wrong, amend the bpy script and re-run from step 4.
   Full render-verify pattern: **`references/skeletal-morph-export.md §6.3`**.

---

## Key reference files

| File | What it covers |
|---|---|
| `references/keyframes-fcurves.md` | keyframe_insert, bulk F-curve construction (4.4+/5.0+), easing/handle types, Cycles/Noise/Generator FModifiers, NLA multi-clip, bake operators + BakeOptions API, validation script |
| `references/skeletal-morph-export.md` | glTF spec internals, Blender→glTF/FBX/USD export scripts (copy-paste ready), per-engine gotcha table, gltf-transform pipeline, gltf_validator usage, Three.js AnimationMixer consumption, USD SkelAnimation validation |

Read only the file relevant to the current step — both are ≤400 lines with a ToC.

---

## Operating principles

- **Bake before export, always.** IK chains, constraints, and drivers are invisible to FBX/glTF
  exporters. Uncollapsed constraints produce snapping or T-pose on the first exported frame.
  `do_visual_keying=True` is non-negotiable; `do_constraint_clear=True` prevents double-evaluation.

- **Guard for Blender version.** The 4.4 slotted-Action API and 5.0 removal of `action.fcurves`
  are silent failures without guards. Every script must check `bpy.app.version` before accessing
  channelbags or the legacy path. If the version cannot be determined, default to the 4.4+ API.

- **`fcu.update()` is mandatory after bulk keyframe writes.** Skipping it leaves handles
  unsorted and Bezier tangents incorrect — the curve will render differently from what was authored.

- **Scripts only — no inline bpy.** SKILL.md code blocks are illustration only; a model reading
  SKILL.md may pre-evaluate `$(...)`. All real animation logic lives in `.py` files run via
  `blender -b -P script.py -- <args>`. Run = call the Skill tool; writing "invoke forge-export"
  in prose invokes nothing.

- **Validate and verify before handing off.** Every animation export exits through `forge-validate`
  (Skill tool call). Web-bound GLBs additionally go through `forge-optimize` then `atelier-webgl`.
  The render-verify PNG read is the suite's eyes — never skip it for skeletal or morph work.

- **Compression belongs to forge-optimize, not here.** This skill exports; `forge-optimize` compresses.
  Hand the exported GLB to `Skill("forge-optimize")` — it picks **Meshopt** (never Draco, which cannot
  carry animation or morph buffers), checks the size delta, and validates. Only hand-run `gltf-transform`
  as a guarded fallback when forge-optimize is unavailable.
