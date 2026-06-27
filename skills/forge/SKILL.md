---
name: forge
version: 1.0.0
description: >
  Forge suite — the entry point, router & orchestrator for headless 3D production on native Windows 11.
  START HERE when you need to create, render, rig, animate, simulate, or export any 3D asset — including
  polygon mesh modeling, parametric CAD, procedural geometry, PBR look-dev, UV unwrapping, baked textures,
  skeletal rigs, cloth/fluid sims, and web-delivery GLB export. With no argument it probes the project,
  picks the pipeline the situation needs, and RUNS it end-to-end by invoking each forge-* skill explicitly
  with the Skill tool — never narrating, always executing.
  `/forge <verb> [target]` dispatches to a specific forge-* skill or agent;
  `/forge init` writes the project's FORGE.md memory;
  `/forge help` shows the full stage menu.
  Use when the user says "use Forge", "model this in Blender", "render this headlessly", "rig this mesh",
  "export a GLB for the web", "generate a parametric shape", "bake textures", "UV unwrap", "run a sim",
  "set up Forge", or invokes /forge directly. Also use when atelier-webgl needs authored 3D geometry —
  the Atelier → Forge seam. HEADLESS-ONLY: all rendering is non-interactive; output verified by reading
  a PNG. Part of the Forge suite.
triggers:
  # Broad / orchestration only — the hub wins the ambiguous case ("use forge", "what next").
  # Concrete single-task phrases (export glb, bake textures, uv unwrap, model in blender, …)
  # are intentionally LEFT to their leaf skills (forge-export / forge-texture / forge-uv / …)
  # to avoid hub-vs-leaf trigger collisions; the description + dispatch table still route them.
  - use forge
  - forge init
  - forge help
  - 3d production
  - full 3d pipeline
  - authored 3d geometry
user-invocable: true
argument-hint: "[init | brief | standards | model | parametric | procedural | topology | uv | material | texture | light | render | rig | animate | sim | export | optimize | intake | validate | help] [target]"
# No allowed-tools — router orchestrates the full pipeline and needs every tool downstream skills use.
---

# Forge — Entry Point, Router & Orchestrator

The front door to the Forge 3D production suite. The suite is **19 focused skills** (plus `forge-data`
reference library) and **5 agents**; this hub keeps you from choosing the wrong one. It does four things:
**orchestrate** — probe project state, decide which pipeline the situation needs, then **actually run
it end-to-end by invoking each skill via the Skill tool** — plus **dispatch** a verb to a specific
skill, **init** FORGE.md project memory, and show the **menu**.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries the
> render engine, coordinate system, scale unit, poly budgets, texel density, PBR workflow, output
> paths, and Atelier aesthetic link for this project. Schema + template: **`references/project-memory.md`**.

> **Suite map (what this routes to).**
> **Planning & spec:** **`forge-brief`** (define asset + write FORGE.md) · **`forge-standards`** (design
> tokens: units/scale/pivot/naming/budgets).
> **Modeling:** **`forge-model`** (bpy/bmesh polygon modeling) · **`forge-parametric`** (OpenSCAD/CadQuery/
> Build123d/FreeCAD) · **`forge-procedural`** (Geometry Nodes/SDF/generative) · **`forge-topology`**
> (retopo/decimation/LOD/boolean cleanup) · **`forge-uv`** (unwrap/seams/packing/UDIMs).
> **Look-dev:** **`forge-material`** (PBR/glTF/Principled→glTF) · **`forge-texture`** (baking/procedural)
> · **`forge-light`** (lighting rigs/HDRI/IBL/color management).
> **Output:** **`forge-render`** (headless Cycles render/turntable/contact-sheet QA) · **`forge-export`**
> (glTF/GLB/USD/FBX/engine conventions) · **`forge-optimize`** (DRACO/Meshopt/KTX2/web budgets + the
> **`atelier-webgl`** handoff seam).
> **Rigging & Sim:** **`forge-rig`** (armatures/IK/FK) · **`forge-animate`** (keyframes/F-curves/bake)
> · **`forge-sim`** (cloth/rigid/particles/hair/fluids).
> **Intake:** **`forge-intake`** (photogrammetry/Gaussian splat/AI text-to-3D + cleanup).
> **Quality gate:** **`forge-validate`** (manifold/normals/scale/polycount/UV overlap/glTF-Validator/
> printability/render-QA + adversarial escalation; runs after every major stage).
> **Reference library:** **`forge-data`** (BM25 lookup over render parameters, material presets, lighting
> rigs, format budgets; called by other skills — not user-facing).
> **Agents:** **`forge-director`** (Opus orchestrator) fans out to **`forge-modeler`** · **`forge-lookdev`**
> · **`forge-rigtech`** · **`forge-pipeline`** (Sonnet specialists).
> Full pipeline sequence: **`references/pipeline.md`**.

---

## Setup — read project state first

Run the signal probe once (pure-Python stdlib, no network, reads only):

```
python "$CLAUDE_CONFIG_DIR/skills/forge/scripts/probe.py"
```

It reports: which 3D tools are on PATH (Blender/OpenSCAD/Python/Node/gltf_validator/toktx), existing
`.blend`/`.scad`/`.glb`/`.usd` files, prior renders, and whether `FORGE.md` / `ATELIER.md` are present.
It recommends nothing — you reason over the facts. Add `--json` for machine-parseable output; pass
`--root <dir>` for a specific project. If Python is unavailable, skip it and reason from what you can
see; never block on the probe.

## Decide-first gate

Before routing, do the suite's mandatory opening move (FORGE_PLAN §A; mirrors forge-brief's *Decide
first* section): from the probe output, **confirm the tool the chosen pipeline needs is present.**
- Modeling/render/rig/anim/sim → **Blender**; parametric/print → **OpenSCAD** (`openscad.com`) or
  **CadQuery** (`python`); web compression → **Node + gltf-transform** (+ `toktx` for KTX2).
- If the *required* tool is MISS → stop with the one-line install hint, don't dead-end into a failed
  render. If only an *advisory* tool is MISS (gltf_validator, toktx) → degrade (see the table below),
  don't block.

## Routing rules

1. **No argument (often with a build prompt)** → the user wants the suite to move the project forward.
   Read probe output + FORGE.md (if present), decide the **pipeline the situation needs**, and **run it
   via the orchestration loop by invoking each skill with the Skill tool** — don't hand back a list, and
   don't name skills in prose. For a new build, run `init` inline then **`Skill(forge-brief)`**. Scale
   it: a single UV fix is a single-skill run, not the whole pipeline.
2. **First word is a verb in the dispatch table** → invoke that skill via the **Skill tool** by its exact
   `forge-*` name (pass anything after the verb as its target), and let it run — don't just narrate it.
3. **First word is `init`** → run the memory-setup flow below.
4. **First word is `help`** → print the stage menu.
5. **Verb maps to an agent** (e.g. "orchestrate full pipeline", "run the full 3D pipeline") → invoke the
   **Agent tool** with `subagent_type: "forge-director"` — not a skill call.
6. **Verb doesn't match but intent maps to one skill** → invoke that skill via the Skill tool by its exact
   name. If two fit, ask once which.

### Dispatch table (verb → forge-* skill or forge-* agent)

| Verb(s) | Routes to | For |
|---|---|---|
| `brief`, `spec`, `define`, `plan` | **`forge-brief`** | Define asset brief + write/update FORGE.md |
| `standards`, `units`, `scale`, `naming`, `budget` | **`forge-standards`** | Design tokens: units/pivot/poly & texel budgets |
| `model`, `mesh`, `box-model`, `bpy`, `blender` | **`forge-model`** | Polygon/box modeling via bpy + bmesh + modifiers |
| `parametric`, `openscad`, `cadquery`, `cad`, `scad`, `print` | **`forge-parametric`** | Code CAD: OpenSCAD/CadQuery/Build123d/FreeCAD |
| `procedural`, `geonodes`, `sdf`, `lsystem`, `scatter`, `generative` | **`forge-procedural`** | Geometry Nodes, SDF/implicit, L-systems, scatter |
| `topology`, `retopo`, `decimate`, `lod`, `boolean`, `cleanup`, `repair` | **`forge-topology`** | Retopo, decimation, LOD, boolean cleanup, transforms |
| `uv`, `unwrap`, `seams`, `udim`, `pack`, `texel` | **`forge-uv`** | UV unwrap, seams, packing, UDIMs, distortion |
| `material`, `shader`, `pbr`, `principled`, `gltf-mat` | **`forge-material`** | PBR shading, glTF material model, Principled→glTF |
| `texture`, `bake`, `normal-map`, `ao`, `curvature` | **`forge-texture`** | Texture baking (normal/AO/curvature) + procedural |
| `light`, `hdri`, `ibl`, `lighting`, `ocio`, `agx` | **`forge-light`** | Lighting rigs, HDRI/IBL, color management (AgX) |
| `render`, `turntable`, `contact-sheet`, `qa-render` | **`forge-render`** | Headless Cycles render, turntable, contact-sheet QA |
| `rig`, `armature`, `ik`, `fk`, `bone`, `skin`, `weight` | **`forge-rig`** | Armatures, IK/FK, skinning/weight painting |
| `animate`, `keyframe`, `fcurve`, `bake-anim`, `export-anim` | **`forge-animate`** | Keyframes, F-curves, baking, skeletal+morph export |
| `sim`, `cloth`, `rigid`, `particles`, `hair`, `fluid` | **`forge-sim`** | Cloth/rigid/particles/hair/fluids — bake & export |
| `intake`, `photogrammetry`, `splat`, `nerf`, `ai-3d`, `text-to-3d` | **`forge-intake`** | Photogrammetry/Gaussian-splat/AI text/image-to-3D |
| `validate`, `check`, `manifold`, `watertight`, `gltf-validate` | **`forge-validate`** | Full quality gate: mesh + UV + glTF + render QA |
| `export`, `glb`, `usd`, `fbx`, `unreal`, `unity`, `godot` | **`forge-export`** | Format export: glTF/GLB/USD/FBX + engine conventions |
| `optimize`, `draco`, `meshopt`, `ktx2`, `compress`, `web-budget` | **`forge-optimize`** | gltf-transform compression, KTX2, LODs, web budgets |
| `handoff`, `to-web`, `atelier-webgl`, `web-delivery` | **`forge-export`** → **`forge-optimize`** → **`Skill(atelier-webgl)`** | Full web-delivery chain; see §Atelier handoff below |
| `director`, `orchestrate`, `full-pipeline` | Agent: **`forge-director`** | Full orchestration via the director subagent (Opus) |
| `data`, `lookup`, `preset`, `cheatsheet` | **`forge-data`** | BM25 search over parameter/material/budget tables |

### Atelier handoff — the Forge → atelier-webgl seam (§F.4 of FORGE_PLAN)

When the task is web delivery:
1. Run **`Skill(forge-export)`** — produce `public/forge/<slug>-hero.glb` (DRACO enabled).
2. Run **`Skill(forge-optimize)`** — gltf-transform Meshopt + quantize (+ KTX2 if texture-heavy).
3. Write the handoff note to `FORGE.md` (`## Forge 3D assets` block — template in `references/project-memory.md`).
4. Run **`Skill(atelier-webgl)`** — it wires the R3F ForgeScene + HeroPoster pattern, reduced-motion fallback, and perf-a11y gate.

Run = call the Skill tool with its exact name. Nothing else counts.

### Orchestration logic — which skills the situation needs

- **`FORGE.md` absent + new asset brief** → `init` inline → **`Skill(forge-brief)`** → **`Skill(forge-standards)`**, then the modeling stack.
- **`ATELIER.md` present + Award-grade interactivity** → read the aesthetic + signature moment → **`Skill(forge-brief)`** (extract Atelier link), then modeling + look-dev + render → web-delivery chain.
- **Request is geometry-only** → pick one of `forge-model` / `forge-parametric` / `forge-procedural` based on the asset type (organic/hard-surface → `forge-model`; toleranced/print → `forge-parametric`; L-system/scatter/SDF → `forge-procedural`) → **`Skill(forge-validate)`** after.
- **Request is look-dev** → `forge-material` → `forge-texture` → `forge-light` → `forge-render` (verify visually) → `forge-validate`.
- **Full production run** → spawn **`Agent(forge-director)`**; it orchestrates specialists in parallel.
- **Web delivery only (existing GLB)** → `forge-export` → `forge-optimize` → `Skill(atelier-webgl)`.

Pick the **shortest pipeline** that actually moves this project forward.

### Degrade, don't dead-end (partial toolchain)

When the decide-first gate shows a tool MISS, route around it instead of stopping — only a *required*
tool blocks. Common partial-toolchain cases:

| Tool MISS | Effect | Route |
|---|---|---|
| **Blender** | Cannot model/render/rig/anim/sim | BLOCK — surface install hint; no headless 3D path exists |
| **OpenSCAD** / **CadQuery** | Cannot do parametric/print | BLOCK for that path; try the other CAD tool, or `forge-model` (bpy) if the asset allows |
| **Node** / **gltf-transform** | Cannot Draco/Meshopt/quantize | Export raw GLB via `forge-export`, **skip** `forge-optimize`, WARN that the GLB is uncompressed |
| **toktx** (KTX2) | Cannot GPU-native texture-compress | Fall back to `--texture-compress webp` (`forge/references/windows-headless.md` §6); WARN |
| **gltf_validator** | forge-validate Tier 2 unavailable | Run Tier 1 mesh/UV checks; note glTF spec validation was skipped |
| **magick** / **ffmpeg** | No poster WebP / anim preview | Keep the PNG; WARN that web poster / preview bake was skipped |

Always report what was degraded so a later run (with the tool installed) can complete it.

### The orchestration loop (how it actually runs)

You have full tool access — including the **Skill tool** and the **Agent tool** (for subagents).

> **Running a skill = calling the Skill tool with its exact name. Nothing else counts.**
> Writing "next: forge-render" or "now apply forge-material" in prose runs NOTHING — that narration
> is the exact bug this loop exists to kill. Every stage is an explicit `Skill(forge-<name>)` call
> by full name. `init` is the one exception: it is a mode of THIS skill, so run its flow inline.

Run the pipeline as one continuous flow:

1. **Invoke → carry forward.** Call each stage with the Skill tool; let it execute its full flow.
   Its output (FORGE.md edits, .blend files, rendered PNGs, GLBs) feeds the next stage.
2. **FORGE.md is the shared, living brief.** `init` writes it; `forge-brief` writes the asset spec;
   `forge-standards` writes budgets. Each stage reads it first.
3. **Let forge-validate run after every major stage.** Never skip the quality gate.
4. **Parallel fan-out for independent stages** — delegate to `forge-director` when geometry,
   look-dev, and rigging can run simultaneously, each with unique output paths under `.forge-build/out/`.
5. **Stop conditions.** Stop when the pipeline completes, a real blocker occurs (missing tool, failed
   render), or the user steers. Report what ran and what remains.

---

## `init` — write the project's 3D memory

`/forge init` creates **`FORGE.md`** at the project root — the persistent brief every Forge skill reads.
Full schema and template: **`references/project-memory.md`** — load it first, then:

1. **Probe + read.** Run `probe.py`; if `FORGE.md` already exists, read it and offer to *update*. If
   `ATELIER.md` is present, read it for aesthetic/world/signature moment/OKLCH hue — populate the
   `## Atelier link` section of FORGE.md from it.
2. **Interview (scaled).** Use `AskUserQuestion` for load-bearing choices: **target engine** (three.js/
   R3F | Unreal | Unity | Godot | print | AR/USDZ), **coordinate system** (Y-up for web/Unity/USD;
   Z-up for Blender/Godot — confirm handedness), **scale unit** (meters standard for glTF/Unreal;
   centimeters for print), **poly budget class** (hero prop / env set piece / background), and **render
   intent** (web delivery → Cycles headless; previz only; print). Infer the rest from the probe and
   brief; don't interrogate.
3. **Write `FORGE.md`** from the template (all 7 sections). Set `## Render: engine = Cycles` — this is
   the Windows-headless default (EEVEE Next has no headless support on Windows without a virtual display).
4. **Continue — invoke the next skill.** After writing FORGE.md, call **`Skill(forge-brief)`** to fill
   the asset spec. `init` is the first move; everything downstream reads what it writes.

## `help` — the stage menu

```
SPEC      /forge brief  ·  /forge standards
MODEL     /forge model  ·  /forge parametric  ·  /forge procedural
MESH QA   /forge topology  ·  /forge uv
LOOK-DEV  /forge material  ·  /forge texture  ·  /forge light  ·  /forge render
RIG/ANIM  /forge rig  ·  /forge animate  ·  /forge sim
PIPELINE  /forge export  ·  /forge optimize  ·  /forge validate
INTAKE    /forge intake     (photogrammetry / splat / AI text-to-3D)
WEB HAND  /forge handoff    (export → optimize → Skill(atelier-webgl))
AGENTS    /forge director   (Opus orchestrator — full autonomous pipeline)
DATA      /forge data       (BM25 lookup; not user-facing)
SETUP     /forge init       (writes FORGE.md — do this first on a new project)
```

---

## Operating principles

- **Decide and run — don't just recommend.** Probe state, choose the skills the situation needs, then
  execute the pipeline end-to-end. There is no "proceed?" gate between stages; the only pauses are for
  a skill's own required input (asset spec, engine target, poly budget class).
- **Run = call the Skill tool.** Naming a skill in prose ("next: forge-render") runs nothing. Every stage
  is an explicit `Skill(forge-<name>)` or `Agent(forge-director)` call — zero ambiguity, no narration in
  its place.
- **Render-in-the-loop is the eyes.** Every produced asset is verified by headless render to PNG + `Read`
  of that PNG for visual inspection. Never report a model as complete without a render check.
- **FORGE.md first on substantial work.** A persisted FORGE.md keeps every later skill on-brief across
  sessions — render engine, coordinate system, budgets, and Atelier aesthetic link all live there.
- **Deterministic, idempotent rebuilds.** Pin seeds (FORGE.md §Determinism / `forge-procedural` & `forge-sim`),
  write to fixed output paths, overwrite in place — re-running a stage on unchanged input reproduces the
  same asset. Emit reproducible source (`.py`/`.scad`/`.json`), never hand-tweaked binaries.
- **Degrade, don't dead-end.** Only a *required* tool blocks. If an advisory tool is absent (Node/
  gltf-transform, toktx, gltf_validator, magick), route around it (export raw GLB, WebP fallback,
  Tier-1-only validate) and WARN — see the §Degrade table. Never stop a pipeline a partial toolchain can still advance.
- **Windows headless truths are non-negotiable.** Cycles (not EEVEE Next) for all headless renders;
  `blender -b scene -P s.py -- <args>` with mandatory `--`; `openscad.com` not `.exe`; `python` not
  `python3`; absolute forward-slash paths in Blender `filepath`. Full details: **`references/windows-headless.md`**.
