---
name: forge-brief
version: 1.0.0
description: >
  Forge suite — define the 3D asset brief and write FORGE.md (the project-memory file every
  other Forge skill reads). Produces: a completed FORGE.md at the project root with target
  engine, coordinate system, poly/texel budgets, render settings, PBR workflow, the determinism
  contract (seed + sample counts for idempotent rebuilds), output paths,
  and (when ATELIER.md is present) the extracted world/aesthetic/signature-moment/OKLCH-hue
  that drives look-dev. Use this FIRST whenever starting any Forge 3D pipeline — including
  "define the asset", "set up a 3D project", "what are the budgets for this mesh",
  "create FORGE.md", "brief a 3D asset", "extract the aesthetic from ATELIER.md for Blender",
  "what engine is the target", "set poly budget", "set texel density", "configure render engine".
  (The bare "init Forge" / "forge init" phrase is owned by the `forge` router's `init` mode, which
  scaffolds FORGE.md inline and then calls this skill — this skill does not claim that trigger.)
  HEADLESS-ONLY: driven from code, output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - forge-brief
  - create FORGE.md
  - define 3d asset brief
  - brief a 3d asset
  - define 3d asset
  - set poly budget
  - asset brief
  - 3d project setup
  - extract atelier brief
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# Forge — Asset Brief & Project Memory

The foundation skill. Before any geometry, material, or render work starts, the pipeline needs a
single shared truth: what is being built, for what target, at what budget, in what style.
**forge-brief writes that truth into `FORGE.md`.** Every downstream Forge skill reads it first.

> **Project memory:** if **`FORGE.md`** already exists at the project root, **read it first** —
> honor its decisions and update only the fields the user explicitly changes.
> If **`ATELIER.md`** exists, also read it — it carries the web aesthetic that the 3D look-dev
> must harmonize with. See §3 below and `references/atelier-extraction.md` for the extraction logic.

---

> **Forge suite — skill map**
>
> | Role | Skill | When |
> |---|---|---|
> | **Brief (you are here)** | **`forge-brief`** | Define asset + write FORGE.md |
> | Standards | **`forge-standards`** | 3D design tokens: units/naming/pivots/budgets |
> | Router | **`forge`** | Probe + dispatch to all Forge skills |
> | Model | **`forge-model`** | bpy/bmesh polygonal modeling |
> | Parametric | **`forge-parametric`** | OpenSCAD / CadQuery / FreeCAD |
> | Procedural | **`forge-procedural`** | Geometry Nodes / SDF / L-systems |
> | Topology | **`forge-topology`** | Retopo / LOD / decimation / booleans |
> | UV | **`forge-uv`** | Unwrap / seams / packing / texel density |
> | Material | **`forge-material`** | PBR shading / glTF material model |
> | Texture | **`forge-texture`** | Baking / procedural textures |
> | Light | **`forge-light`** | Lighting rigs / HDRI / color management |
> | Render | **`forge-render`** | Headless Cycles render / turntable QA |
> | Rig | **`forge-rig`** | Armatures / IK-FK / skinning |
> | Animate | **`forge-animate`** | Keyframes / F-curves / skeletal export |
> | Sim | **`forge-sim`** | Cloth / rigid / fluid / hair |
> | Export | **`forge-export`** | Format matrix: GLB / FBX / USD / engine import |
> | Optimize | **`forge-optimize`** | gltf-transform / KTX2 / LOD / web budgets |
> | Intake | **`forge-intake`** | Photogrammetry / AI-to-3D / cleanup |
> | Validate | **`forge-validate`** | Manifold / normals / scale / UV / glTF-Validator |
> | Data | **`forge-data`** | BM25 reference library (tool cheatsheets / budgets) |
>
> Atelier seam: **`atelier-webgl`** ↔ **`forge-export`** / **`forge-optimize`** (GLB + poster handoff).
> Also connects to **`atelier-direction`** (Direction Doc → aesthetic brief) and
> **`atelier-perf-a11y`** (post-handoff CWV / a11y gate).

---

## Decide first: tool and target engine

Before writing FORGE.md, lock two decisions that gate everything downstream:

**1. Target engine / delivery format**

| Intent | Target | Notes |
|---|---|---|
| Web hero (three.js / R3F) | `three.js/R3F` | GLB + DRACO + Meshopt; < 5 MB; Y-up |
| iOS / Android AR | `AR/USDZ` | GLB for Android; USDZ for ARKit |
| Unreal Engine 5 | `Unreal` | FBX + UE5 naming; Z-up; 1 unit = 1 cm |
| Unity / Godot 4 | `Unity` / `Godot` | FBX or GLB; 1 unit = 1 m; Y-up |
| 3D print | `print` | STL / 3MF; manifold; real-world mm |
| Archive / interchange | `USD` | USDA/USDC; Y-up; meters |
| Blender/film render | `render-only` | Stays in Blender; no engine export needed |

**2. Modeling tool**

Run `python "$env:CLAUDE_CONFIG_DIR\skills\forge\scripts\probe.py" --json`
(the **`forge`** router's preflight probe — calls it via Skill if available) to confirm tool
availability before committing. Deep invocation reference: `references/tool-availability.md`.

| Use | Tool | Headless invocation |
|---|---|---|
| Polygonal / organic / subdivision | **Blender** `bpy` | `blender -b scene.blend -P s.py -- <args>` |
| Parametric / precision / CAD | **OpenSCAD** | `openscad.com -o out.stl model.scad` |
| Parametric (Python) | **CadQuery** / **build123d** | `python script.py` |
| STEP / IGES exchange | **FreeCAD** | `freecadcmd script.py` |

**WINDOWS HEADLESS TRUTHS — apply everywhere:**
- Cycles only (not EEVEE Next) for headless renders on Windows.
- `blender -b scene -P s.py -- <args>` — the `--` separator is **mandatory**.
- `openscad.com` not `openscad.exe` (the `.com` wrapper handles DPI/HiDPI correctly).
- `python` not `python3`.
- Absolute forward-slash paths in Blender `filepath` — never `//relative`.
- `--python-exit-code 1` so Python errors fail the Blender process.

---

## The flow

**1. Read existing state**
- If `FORGE.md` exists → read it; note what is already decided.
- If `ATELIER.md` exists → read it; extract fields using the regex patterns in
  `references/atelier-extraction.md`. Particularly: `Interactivity`, `World`, `Aesthetic`,
  `Concept/signature moment`, and the OKLCH primary hue from `## Tokens`.

**2. Gather missing decisions (AskUserQuestion if needed)**

The minimum set for FORGE.md:
- **Asset description** — what is the object/scene (one sentence)
- **Target engine/delivery** — pick from the table above
- **Asset class** — hero prop / character / environment / web hero / CAD / print
- **Poly budget** — derive from class table in `references/budgets-and-standards.md`
  or ask if unusual
- **Texel density** — derive from target tier; see `references/budgets-and-standards.md §texel`

Use `AskUserQuestion` only when the target cannot be inferred. Note: the picker caps at 4
options — for engine choices, list all options in the message body and use the picker only
for the binary "confirm / let me pick differently".

**3. Determine coordinate system and scale unit**

Full table in `references/coordinate-systems.md`. Quick lookup:

| Target | Up axis | Scale unit | Forward axis |
|---|---|---|---|
| glTF / three.js / R3F | Y-up | meters | -Z |
| Unreal Engine 5 | Z-up | cm (1 unit = 1 cm) | X |
| Unity | Y-up | meters | Z |
| Godot 4 | Y-up | meters | -Z |
| OpenSCAD default | Z-up | mm | Y |
| Blender default | Z-up | meters | -Y |
| USD / Omniverse | Y-up | meters (configurable) | -Z |

**4. Write FORGE.md**

Use the schema from FORGE_PLAN.md §G. Full annotated template in
`references/forge-md-template.md`. Minimum viable content:

```
## Target            <engine> + <delivery format>
## Coordinate system <up-axis>, <handedness>, <scale unit>, <forward axis>
## Budgets           <poly-class>: <lod0-tris> tri LOD0; texel density <px/m> px/m; tex max <res>
## Render            Cycles (headless Windows default); <qa-samples> QA / <final-samples> final; color view AgX
## Determinism       Seed: 0 (all procedural/sim/Cycles ops); Cycles use_animated_seed: off;
##                   rebuild contract: same FORGE.md + same source => byte-identical GLB, comparable PNG
## PBR workflow      metallic-roughness (glTF default); ORM channel-pack (AO→R, Rough→G, Metal→B)
## Output paths      .forge-build/out/ working; public/forge/<slug>-* for web handoff
## Atelier link      (omit if no ATELIER.md) world: <world>; aesthetic: <aesthetic>;
##                   signature: <moment>; primary OKLCH hue: <H>
```

Write with `Write` tool to `<project-root>/FORGE.md`. If FORGE.md already exists, use `Edit`
to update only changed fields.

**5. Confirm and summarize**

- Read back the written FORGE.md to confirm correctness.
- Print a brief summary: target engine, coordinate system, poly budget, render engine, and
  whether ATELIER.md was found and its aesthetic extracted.
- Name the next Forge skill the user should invoke: typically **`forge-standards`** (for
  the full 3D design-token ruleset) or directly to **`forge-model`** / **`forge-parametric`**
  for a simple asset.

**Run = call the Skill tool with the exact skill name. Writing "next: run forge-model"
in prose runs nothing — invoke `Skill("forge-model")` or `Skill("forge-standards")`.**

---

## §3 — ATELIER.md extraction

When `ATELIER.md` is present at the project root, forge-brief is also the **aesthetic bridge**:
it reads the Atelier Direction Doc and writes the extracted context into FORGE.md's
`## Atelier link` section so every downstream Forge skill (forge-material, forge-light,
forge-render) can harmonize look-dev with the web design system without re-reading ATELIER.md.

Full extraction logic (regex patterns + Python pseudocode):
**`references/atelier-extraction.md`** — read it before attempting extraction.

Fields to extract:

| ATELIER.md field | Where it lives | Maps to FORGE.md |
|---|---|---|
| `Interactivity` | `## Interactivity` section | Sanity check: must be Award-grade to justify authored 3D |
| `World` | `**World:**` bold inline | `## Atelier link → world` |
| `Aesthetic` | `**Aesthetic:**` bold inline | `## Atelier link → aesthetic` |
| Signature moment | `**Concept.*signature moment.*:**` | `## Atelier link → signature` |
| Primary OKLCH hue | First `oklch(... ... <H>)` in `## Tokens` | `## Atelier link → primary OKLCH hue` |

If ATELIER.md is absent, omit the `## Atelier link` section from FORGE.md entirely.
If Interactivity is not Award-grade and the user has requested authored 3D, **pause** and
suggest running **`Skill(atelier-direction)`** first to sanction the 3D moment — do NOT
proceed to build geometry that will violate the project's budget.

---

## References

Deep material lives here — read the relevant file before each step:

- **`references/forge-md-template.md`** — fully-annotated FORGE.md template with per-field
  guidance, examples for each target engine, and the complete schema.
- **`references/budgets-and-standards.md`** — polycount tables (mobile / console / web / print),
  texel density tiers, LOD ratios, UV utilization targets, draw-call ceiling, Git LFS rules.
- **`references/coordinate-systems.md`** — up-axis, handedness, scale, forward-axis per target;
  Blender → UE5 unit correction; glTF standard; USD conventions.
- **`references/atelier-extraction.md`** — Python regex patterns to extract world/aesthetic/
  OKLCH hue from ATELIER.md; AskUserQuestion option-cap note (max 4 picker items);
  aesthetic → look-dev direction table; sanction-check logic.
- **`references/tool-availability.md`** — preflight probe patterns (PowerShell + Python),
  Blender path lookup on Windows, OpenSCAD `.com` gotcha, CadQuery install check.

---

## Operating principles

- **Write FORGE.md first, always.** No Forge skill should execute without a project-memory file.
  forge-brief is the mandatory step 0. If it already exists, update it; never silently skip it.
- **Honor ATELIER.md when present.** An ATELIER.md aesthetic is not a suggestion — it is the
  design contract. Poly budgets, texel density, and render engine are your decisions; aesthetic
  and OKLCH harmony are the project's decisions.
- **Derive, don't ask.** Poly budgets, texel density, coordinate system, and output paths can
  all be derived from the target engine and asset class. Only ask when something is genuinely
  ambiguous (e.g. a custom constraint the dossier does not cover).
- **Sanction 3D before building it.** If ATELIER.md exists and Interactivity is not Award-grade,
  do not build geometry. Run `Skill(atelier-direction)` first. An unsanctioned 3D moment is a
  performance and accessibility liability the project did not budget for.
- **Fail loudly at the gate.** A target engine the probe cannot verify, a missing tool, or a
  contradictory constraint (e.g. Z-up asset for a Y-up web target) must surface here as a clear
  error — before any geometry is written. Downstream skills depend on FORGE.md being correct.
