---
name: forge-render
version: 1.0.0
description: >
  Forge suite — headless rendering engine and QA eyes. Drives Blender (Cycles/Workbench)
  to produce render outputs without a GUI: beauty stills, render passes/AOVs (normals,
  depth, AO, wireframe, UV checker), turntable sequences, 6-view orthographic sheets, and
  assembled contact-sheet PNGs that the model reads back to verify geometry, shading, and
  UV quality. Use whenever rendering a 3D asset to PNG, generating a QA contact sheet,
  setting up Cycles passes, enabling AOVs, doing a turntable render, checking normals or
  wireframe headlessly, verifying materials or UV unwraps visually, or running any render →
  Read → critique → fix loop. Triggers: "render the model", "turntable", "contact sheet",
  "wireframe render", "normal pass", "AO pass", "render passes", "headless render",
  "Cycles render", "QA render", "render and check", "AOV", "render to PNG". HEADLESS-ONLY:
  driven from code, output verified by reading a PNG. Part of the Forge suite.
triggers:
  - render to png
  - headless render
  - turntable render
  - contact sheet
  - wireframe render
  - normal pass
  - ao pass
  - render passes
  - cycles render
  - qa render
  - render and check
  - aov
  - render the model
  - matcap render
  - uv checker render
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# forge-render — Headless Render + QA Eyes

The render-in-the-loop layer. Every Forge build cycle ends here: emit a render, read the
PNG, critique vs brief, fix or advance. This skill drives that loop from code with no GUI.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it
> carries the render engine, sample counts, output paths, and coordinate system for this
> project. Honor those settings; do not override them without a reason.

---

> **Suite map**
>
> **forge** (router) → dispatches here via forge-lookdev agent. This skill is called by:
> - **`forge-material`** — after shader authoring, for material QA preview
> - **`forge-texture`** — baked maps verified by rendering with the texture applied
> - **`forge-light`** — lighting rig validation (beauty render comparison)
> - **`forge-uv`** — UV checker pass is the primary unwrap QA output
> - **`forge-validate`** — invokes this skill's contact-sheet mode as the visual gate
>
> When the model hands off to another skill, **Run = call the Skill tool with its exact
> name. Writing "now run forge-validate" in prose runs nothing.**
>
> Atelier connection: rendered hero stills feed **`atelier-webgl`** as poster fallbacks
> (`public/forge/<slug>-hero-poster.webp`). The web-runtime/a11y gate is
> **`atelier-perf-a11y`**'s job — invoked downstream via `Skill("atelier-perf-a11y")` after
> **`forge-optimize`** packages the GLB + poster (forge-render does not own that call). For
> art-direction moodboards from rendered output, see **`atelier-direction`**.

---

## Decide first: engine + availability

Before any render attempt:

1. **Check FORGE.md** for `## Render` section (engine, samples, output path).
2. **Verify Blender exists** — run `scripts/preflight.py --json` to confirm `blender` is found
   and capture `blender_path`. (forge-render ships its own `scripts/preflight.py` — a focused
   Blender + Pillow check that returns `blender_path`; the router's `forge/scripts/probe.py` is
   the broader project-state probe. This skill only needs preflight.)
3. **Pick the render mode:**

| Goal | Engine | Rationale |
|---|---|---|
| Iterative QA (geometry, normals, wireframe) | `BLENDER_WORKBENCH` | Headless-safe on Windows, ~1 s/frame, no GPU needed |
| UV checker pass | `CYCLES` CPU 16 samples | Workbench ignores shader nodes; Cycles respects UV mapping |
| Normal pass (world-space) | `CYCLES` CPU 1 sample + compositor | Accurate per-pixel world normals |
| Beauty / material hero render | `CYCLES` GPU (OptiX) or CPU fallback | Physically correct; AgX color management |
| Full contact-sheet QA | Workbench + selective Cycles | Combine both above |

**EEVEE Next is UNSUPPORTED headless on Windows.** Never use `BLENDER_EEVEE_NEXT` or
`BLENDER_EEVEE` as the engine for any headless render. Use Cycles (CPU or GPU) for all
passes requiring node-material evaluation, and Workbench for fast geometry diagnostics.

**GPU activation (Cycles):** GPU devices are NOT auto-activated in headless mode. Always
call `prefs.refresh_devices()` (Blender 4.x) before setting `cycles.device = 'GPU'`.
See `references/cycles-gpu-passes.md §GPU` for the exact pattern.

---

## The flow

1. **Read FORGE.md** (if present) — extract engine, samples, output path, slug.

2. **Preflight** — run `scripts/preflight.py --json`. Confirm Blender is found; determine
   the Blender path for all subsequent subprocess calls. If missing, surface the install
   URL and stop.

3. **Write the render script** — compose `render.py` or a targeted diagnostic script from
   the patterns in `references/cycles-gpu-passes.md` and `references/workbench-diagnostic.md`.
   Key non-negotiables every script must follow:
   - UTF-8 stdout wrapper at the top
   - `--factory-startup` for determinism
   - `--python-exit-code 1` so Python errors fail the Blender process
   - Absolute forward-slash paths in `scene.render.filepath` (never `//` relative)
   - `-f 1` (or `-a`) as the **last** Blender argument
   - `pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)` before render
   - `bpy.ops.render.render(write_still=True)` — without `write_still`, no file is saved

4. **Invoke Blender** (PowerShell):
   ```
   $BLENDER = $env:BLENDER_EXE  # set by preflight or FORGE.md
   & $BLENDER -b --factory-startup --python-exit-code 1 -P "scripts/render.py" -- <args>
   ```
   Full invocation reference: `references/cli-invocations.md`.

5. **Verify output** — check the PNG exists and is >1 KB. A <1 KB PNG is almost certainly
   an error image (Blender writes a minimal stub when it fails silently).

6. **Read the PNG** — call `Read` on the output path. Visually inspect:
   - Turntable: silhouette consistency, no floating geometry, scale vs brief
   - Wireframe: edge density, no poles >6, no N-gons on SDS surfaces
   - Normals (RGB): smooth color gradients; abrupt reversals = flipped normals
   - UV checker: uniform checker scale = even texel density; distorted squares = stretching
   - Matcap: smooth shading flow; black patches = inverted normals
   - Beauty: no fireflies, correct color transform (AgX), transparent background if RGBA

7. **Assemble contact sheet** (multi-pass QA) — if running a full QA suite, after all
   individual renders complete, run `scripts/contact_sheet.py` to tile them (PowerShell
   backtick continuation):
   ```powershell
   python "skills/forge-render/scripts/contact_sheet.py" `
       --input-dir C:/forge/out/qa --output C:/forge/out/qa_sheet.png --cols 4
   ```
   The cap is **enforced**: >36 tiles auto-splits into numbered sheets
   (`qa_sheet_01.png`, `qa_sheet_02.png`, …) — `Read` each one. Override with
   `--max-per-sheet N`. Then `Read` the contact sheet PNG(s).

8. **Decide: iterate or advance** — if defects found, amend the geometry/material script
   (via the responsible skill) and loop back to step 3. If clean, advance to the next
   pipeline stage. For hard validation, call `Skill("forge-validate")`.

---

## Render modes in detail

### Quick geometry QA (Workbench, <5 s total)

Turntable + wireframe + matcap in one Blender invocation. The fastest read of asset health.
Full pattern: `references/workbench-diagnostic.md §turntable`.

### Passes + AOVs (Cycles compositor)

Enable per-pass toggles on `bpy.context.view_layer` **before** the render call. Passes not
enabled at render time cannot be recovered. Route each pass to a separate File Output node.
Critical: keep `scene.render.filepath` on a **different stem** from compositor `fo.base_path`
or they overwrite each other.
Full pattern + gotcha table: `references/cycles-gpu-passes.md §passes`.

### Normal pass (world-space → PNG)

Use Cycles CPU, 1 sample, compositor: Normal pass → multiply 0.5 → add 0.5 → File Output.
Do not use CompositorNodeNormalize — it acts on pixel min/max, not on the [-1,1] theoretical
range. Full remap pattern: `references/cycles-gpu-passes.md §normals`.

### Contact-sheet assembly

`scripts/contact_sheet.py` tiles all PNGs in a directory into a single labelled sheet.
Degrades gracefully when Pillow is absent (emits a plain text manifest instead). Two
enforced ceilings keep the result `Read`-friendly: cell cap 512×512 px, and **36 tiles per
sheet** (`--max-per-sheet`, default 36) — beyond that it auto-splits into numbered sheets.
Full usage + layout spec: `references/contact-sheet.md`.

---

## Operating principles

- **Verify, don't assume.** Every render attempt must be followed by a file-existence check
  and a `Read` of the output PNG before reporting success. A zero-KB file is a silent failure.
- **Workbench first, Cycles only when needed.** Workbench is headless-safe on Windows and
  ~60× faster than Cycles for geometry QA. Use Cycles only for node-material passes (UV
  checker, normals) and final beauty renders.
- **Absolute forward-slash paths everywhere.** `scene.render.filepath` and `fo.base_path`
  must use forward slashes (e.g. `C:/forge/out/frame_####`). Backslashes in Blender Python
  strings are escape sequences; they silently produce wrong paths.
- **Scripts, not inline code.** All render logic lives in `scripts/`; SKILL.md code blocks
  are illustration only — the model pre-evaluates `$()` expressions it sees in Markdown,
  so never rely on them for real execution.
- **One earned read per loop.** Each iteration renders, reads the PNG, critiques against
  the brief, and makes a single clear fix decision. Do not accumulate multiple unread renders
  before inspecting.
- **Deterministic rebuilds.** The Cycles seed is pinned to 0 by default (`--seed N` to change)
  and `--clean` (on by default) clears this skill's prior output stems first, so two builds of
  the same scene produce byte-comparable renders and stale frames never leak into a contact
  sheet. `render.py --json` carries a `health` field (per-file exists / size / blank-frame
  check) — let the loop iterate-or-advance on that signal, not on prose.
