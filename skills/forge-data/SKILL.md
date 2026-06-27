---
name: forge-data
version: 1.0.0
user-invocable: false  # a library the other forge-* skills query via scripts/search.py, not a menu skill
description: On-demand reference DATA for the Forge 3D suite — a local, searchable (BM25) library of
  tool cheatsheets (Blender headless invocations, OpenSCAD, assimp CLI, gltf-transform), polycount
  budgets by asset class and platform, texel-density standards, a format interchange matrix
  (glTF/FBX/USD/OBJ/STL/Alembic/STEP), PBR material presets, web delivery budgets, and a gotcha→fix
  table covering Windows-headless production pitfalls. It is the data layer of the Forge suite; the
  other forge-* skills remain the authorities that make the actual 3D decisions. Do not use it as a
  code generator or as an auditor of existing files. Part of the Forge suite. HEADLESS-ONLY: all
  rendering is non-interactive; output verified by reading a PNG.
---

# forge-data — searchable 3D reference

A curated, **local** dataset + a tiny BM25 search engine. It answers "give me a vetted *starting
point* / cross-check" fast — polycount budgets, texel densities, format decisions, headless CLI
flags, PBR presets — without spending model context on the entire corpus. It is the **data** layer
of the Forge suite; the other `forge-*` skills remain the authorities that make the actual craft
decisions.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries the
> confirmed tool choices, poly budget, texel density, render engine, PBR workflow, and output paths
> for this project. forge-data answers "what is the standard starting point?"; FORGE.md answers
> "what did we already decide for this project?"

---

> **Forge suite map**
>
> - **forge** — router / orchestrator (entry point for all 3D work)
> - **forge-brief** — writes FORGE.md; extracts ATELIER.md brief
> - **forge-standards** — authoritative 3D design-token rules (units, naming, pivots, budgets)
> - **forge-model** — bpy / bmesh polygonal modelling
> - **forge-parametric** — OpenSCAD / CadQuery / FreeCAD code-CAD
> - **forge-procedural** — Geometry Nodes, SDF, L-systems, scatter
> - **forge-topology** — retopo, decimation, LOD chains, boolean cleanup
> - **forge-uv** — UV unwrap, seams, packing, texel density, UDIMs
> - **forge-material** — PBR shading, Principled→glTF mapping
> - **forge-texture** — baking (normal / AO / curvature / displacement) + procedural
> - **forge-light** — lighting rigs, HDRI / IBL, color management (AgX / ACES)
> - **forge-render** — headless Cycles renders, turntable + contact-sheet QA
> - **forge-rig** — armatures, IK / FK, skinning / weights, blend shapes
> - **forge-animate** — keyframes, F-curves, baking, skeletal + morph export
> - **forge-sim** — cloth, rigid / soft / particles, hair / fur, fluids
> - **forge-export** — format matrix, glTF / GLB / USD / FBX export, engine conventions
> - **forge-optimize** — gltf-transform, Draco / Meshopt / KTX2, web delivery, atelier-webgl handoff
> - **forge-intake** — photogrammetry, Gaussian splat / NeRF, AI text-to-3D cleanup
> - **forge-validate** — manifold, normals, scale, polycount, UV overlap, glTF-Validator, render QA
> - **forge-data** ← you are here (BM25 reference library)
>
> Atelier seam: **forge-export → forge-optimize → Skill(atelier-webgl)**

---

## When to query (and when not)

**Use for:** fast budget lookup (polycount / texel density for a given platform and asset class);
format selection (should this be FBX, GLB, or USD?); headless CLI flags for Blender / assimp /
gltf-transform; PBR channel-pack conventions (ORM layout, color-space rules); Windows gotcha
cross-checks before running a conversion.

**Do not use for:** making the final craft decision (use the responsible forge-* skill); reading
or auditing existing files (use Read tool or forge-validate); real-time rendering parameters
already locked in FORGE.md (read FORGE.md directly).

---

## How to query (Windows: use `python`, not `python3`)

```
cd $CLAUDE_CONFIG_DIR/skills/forge-data/scripts
python search.py "<query>" --domain <domain> [-n 3]
python search.py "<query>"              # auto-detect domain
python search.py "<query>" --json       # machine-parseable output
```

Keep `-n` small (≤ 5). The `--json` flag bypasses per-field 300-char truncation — use only when
the caller needs structured data. Python is stdlib-only; **no network calls**.

---

## Datasets → which Forge skill owns the decision

| Domain / file | Gives you | Decision owner |
|---|---|---|
| `--domain tools` → `tool-cheatsheet.csv` | Headless invocation patterns, when-to-use, gotcha per tool | **forge-model**, **forge-parametric**, **forge-render** |
| `--domain polycount` → `polycount-budgets.csv` | LOD0–LOD3 triangle limits by asset class + platform | **forge-topology**, **forge-standards** |
| `--domain texel` → `texel-density.csv` | px/m targets by platform tier + asset tier | **forge-uv**, **forge-standards** |
| `--domain format` → `format-matrix.csv` | Format capabilities (geo/UV/PBR/rig/anim/morph), up-axis, unit, assimp support | **forge-export** |
| `--domain material` → `material-presets.csv` | PBR preset values, ORM channel-pack layout, color-space rules | **forge-material** |
| `--domain gotchas` → `gotchas.csv` | Topic → symptom → fix for Windows headless pitfalls | ALL skills |

---

## The flow

1. **Receive query from a sibling skill** (e.g. forge-standards asks for mobile hero polycount,
   forge-export asks for FBX vs GLB for a Unity target).
2. **Run `scripts/search.py`** with the relevant `--domain` and the query string. Keep `-n ≤ 5`.
3. **Read the structured output** — check the Decision owner column; the result is a *starting
   point*, not a binding rule.
4. **Cross-check FORGE.md** — if the project has already locked a budget or format, that takes
   precedence over the dataset default.
5. **Hand back the answer to the requesting skill.** forge-data never makes the final decision
   itself.

Run = call the Skill tool with the exact skill name. Writing "now run forge-export" in prose runs
nothing.

---

## Deep references (load on demand)

Full copy-paste-ready detail lives in `references/` — the SKILL.md body only carries pointers.
Load a reference file with `Read` when the summary row from a CSV search is not enough.

| File | Contents |
|---|---|
| `references/tool-invocations.md` | Blender headless flags, OpenSCAD/FreeCAD/assimp CLI patterns, PowerShell wrappers, Windows gotchas |
| `references/budgets-and-standards.md` | Full polycount and texel-density tables, naming conventions, pivot rules, scale discipline, LOD ratios |
| `references/format-matrix.md` | Full format-capability table, conversion recipes, FBX unit scale fix, Blender↔glTF axis mapping |
| `references/pbr-and-material.md` | PBR theory, ORM channel-pack recipe, Principled→glTF mapping, color-space rules, texture suffixes |
| `references/web-delivery.md` | gltf-transform / gltfpack / toktx pipelines, KTX2 selection rules, web budget tiers, CWV alignment |

---

## Operating principles

- **Data layer, not decision layer.** forge-data surfaces starting points; forge-standards,
  forge-export, forge-material, and the other craft skills make binding decisions.
- **FORGE.md wins.** Any value already locked in the project memory file overrides a dataset
  default. Always check FORGE.md before citing a search result as the answer.
- **Stdlib only, no network.** Every script is pure Python stdlib. Never make a network call
  from a search or probe script.
- **Keep tokens small.** Keep `-n ≤ 5` and avoid `--json` unless the caller needs structured
  data — search results enter the model's context and large payloads waste budget.
- **2-char tokens match.** The BM25 tokenizer keeps `len(w) >= 2`, so queries like "uv", "3d",
  "ao", "gi", "lm" all resolve correctly.
