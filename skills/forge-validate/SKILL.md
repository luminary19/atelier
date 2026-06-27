---
name: forge-validate
version: 1.0.0
description: >
  Forge suite — the quality gate every asset must pass before it is considered done.
  Runs manifold/watertight checks, normal consistency, scale/units, polycount budgets,
  UV checks (presence, range, texel-density), glTF-Validator spec compliance,
  printability (wall thickness, overhang, drain holes via `--print`), render-QA
  (Workbench contact sheet + verified Read pass), and adversarial escalation via
  independent sub-reviewers. Use whenever finishing a 3D
  asset, before export or handoff, running a mesh audit, checking if a GLB is spec-
  valid, confirming a model is print-ready, or reviewing render output for defects.
  This is the canonical gate other Forge skills reference for validation rules.
  HEADLESS-ONLY: all rendering is non-interactive, output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - validate mesh
  - mesh audit
  - check manifold
  - watertight check
  - gltf validator
  - print ready
  - normals check
  - polycount check
  - UV overlap
  - render QA
  - asset gate
  - pre-export check
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Task   # Tier 3 spawns parallel adversarial sub-reviewers
---

# Forge — Validate

The line between a finished Forge asset and a broken one. **An asset is not done until
it passes this gate.** This skill is both a *gate* (run it before export) and the
*reference* every other Forge skill cites for validation rules — when those skills say
"check manifold" or "run the render QA pass", the full how lives here.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it
> carries the coordinate system, scale unit, poly budget, target engine, and render
> engine for this project. Honour every constraint it specifies before running checks.
>
> **Suite position:**
> - Upstream craft skills: **`forge-model`**, **`forge-parametric`**, **`forge-procedural`**, **`forge-topology`**, **`forge-uv`**, **`forge-material`**, **`forge-texture`**, **`forge-light`**, **`forge-render`**
> - Downstream pipeline: **`forge-export`** → **`forge-optimize`** → `Skill(atelier-webgl)`
> - Called by ALL Forge agents: **`forge-director`**, **`forge-modeler`**, **`forge-lookdev`**, **`forge-rigtech`**, **`forge-pipeline`**
> - Perf/a11y analogue (web): **`atelier-perf-a11y`** (handles CWV, WCAG; defer web-runtime gate there) — this is the analogue for Tiers 0–2 (the deterministic self-checklist)
> - Adversarial analogue (web): **`atelier-review`** — Forge-validate Tier 3 mirrors the `atelier-perf-a11y → atelier-review` escalation; this is the 3D-asset counterpart of that fan-out, run on substantial/print/web-delivery assets (analogy, not a handoff — no Skill() call)
> - Standards reference: **`forge-standards`** (units, budgets, naming — read it for threshold values)
>
> **Run = call the Skill tool with the exact name. Writing "run forge-validate" in prose
> runs nothing.**

---

## How to use this skill

Two modes:

1. **Inline gate** — other skills call `Skill("forge-validate")` after a construction
   step; this skill runs the appropriate ladder tier and reports pass/fail.
2. **Full audit** — invoked directly on a finished asset; runs all four tiers in order,
   escalates to adversarial reviewers on substantial/print/web-delivery assets.

---

## The quality ladder

Four tiers, escalating rigor. Each tier builds on the last — do not skip.

**Tier 0 — Deterministic pre-pass (always, seconds)**
Run `scripts/detect.py` over the target directory or file. Advisory regex + structural
checks: missing poster, oversized GLB, EEVEE headless flag, `//` Blender paths, missing
`--` separator. Exit 0 always. Fix every `[BLOCK]`; weigh `[WARN]` against FORGE.md intent.

**Tier 1 — Mesh & spec self-checklist (every build)**
Run `scripts/validate.py` with the target file. Checks: GLB magic + size, **raw**
manifold / watertight / winding (measured on the UNTOUCHED mesh — the gate reports the
asset's real state, it does not silently repair before grading), volume > 0, broken
faces, face count vs budget, UV presence + range + texel-density CV, scale/units. If
trimesh is installed, full mesh checks; otherwise degrades to GLB structural checks
only. Two scoped-out items that need Blender, not trimesh: (a) **bmesh-level topology**
fields (non-manifold edge count, flipped faces, degenerate count, high-valence poles,
n-gon %) come from the §6 audit run as `blender -b <file> -P topology_audit.py`, not
from validate.py; (b) **full UV-island overlap** (intersection) is not computed — the
range check is a tiling/UDIM signal only. Full checklist: **`references/mesh-checklist.md`**.

**Tier 2 — glTF-Validator + render-QA contact sheet (pre-export)**
Run Khronos glTF-Validator (CLI or npm) — zero errors policy, warnings reviewed.
Fire Blender headless (BLENDER_WORKBENCH only on Windows — never EEVEE headless) to
produce turntable + 6-view + diagnostic overlays, assemble contact sheet, call `Read`
on the PNG. Visual inspection guide: **`references/render-qa-guide.md`**.

**Tier 3 — Adversarial escalation (substantial / print / web-delivery assets)**
Spawn independent sub-agent reviewers, one per dimension, in parallel using the Task
tool. Each reviewer gets the validate.py JSON + the contact-sheet path; the topology
reviewer additionally gets the §6 `topology_audit.py` JSON (non-manifold edges, flipped
faces, poles) and the printability reviewer gets the `--print` block — those fields do
NOT come from the base validate.py run. Dimensions: topology integrity, material/PBR
spec compliance, printability, render fidelity.
Escalation protocol: **`references/adversarial-escalation.md`**.

---

## The flow

**0. Read project memory**
   If FORGE.md exists, read it. Extract: coordinate system, scale unit, poly budget,
   target engine, render engine. These override any defaults below.

**1. Run the deterministic pre-pass**
   ```
   python "$CLAUDE_CONFIG_DIR/skills/forge-validate/scripts/detect.py" \
     --target <path> [--json]
   ```
   Fix every [BLOCK]. Note [WARN] items. Exit if [BLOCK] found and asset is not in
   repair mode.

**2. Run the mesh + spec validator**
   ```
   python "$CLAUDE_CONFIG_DIR/skills/forge-validate/scripts/validate.py" \
     --input <file.glb|.stl|.obj> [--budget-faces N] [--units mm|m] [--json]
   ```
   Parse the JSON. Any `"status": "FAIL"` item in the results is a hard gate — fix
   before proceeding. Repair guide: **`references/mesh-repair.md`**.

**3. Run glTF-Validator (GLB/GLTF assets only)**
   ```powershell
   # PowerShell — via npm-installed CLI
   gltf_validator.exe --stdout "model.glb" | ConvertFrom-Json | Select-Object -ExpandProperty issues
   ```
   Gate: `numErrors == 0`. Warnings reviewed against FORGE.md intent.
   **Graceful degradation:** if `gltf_validator` is not on PATH and neither
   `npx @gltf-transform/cli validate` nor a global `gltf-validator` is available, do NOT
   stall — emit `WARN: "glTF spec validation skipped (validator not installed; see
   references/gltf-validator-guide.md for install)"` and fall back to validate.py's
   stdlib GLB header/chunk + size checks as the floor.
   Full severity table and common error codes: **`references/gltf-validator-guide.md`**.

**4. Render QA contact sheet**
   Use BLENDER_WORKBENCH (not EEVEE) for all QA renders on Windows. Invoke via
   PowerShell using the absolute Blender path. Produce turntable (12 angles) + 6-view
   ortho + diagnostic variants (matcap, wireframe, normal, UV-checker). **Pin the seed**
   so two QA renders of an unchanged asset are byte-comparable (see
   render-qa-guide.md §1.5). Assemble contact sheet.

   **4a. Verify the PNG before reading it.** A failed Cycles/Workbench render on Windows
   commonly writes a 0-byte or tiny black PNG while Blender still exits 0. Confirm the
   file exists and is `>= 1024` bytes before trusting it:
   ```
   python "$CLAUDE_CONFIG_DIR/skills/forge-validate/scripts/validate.py" \
     --verify-png <contact_sheet.png> [--json]
   ```
   If missing/tiny, the render failed silently (EEVEE-on-Windows or missing
   `write_still=True`) → inspect `.forge-build/blender.log`, switch to CYCLES/Workbench,
   re-render. **Never `Read` a 0-byte PNG and report PASS.**

   **4b.** Then call `Read` on the verified PNG path — visually inspect for:
   - Black patches (inverted normals)
   - Silhouette discontinuities (floating geo, scale error)
   - Elongated checker squares (UV stretch > 2:1)
   - Non-uniform wireframe density (poles, ngons)
   Visual inspection guide: **`references/render-qa-guide.md`**.

**5. Printability gate (print-target assets only)**
   If FORGE.md specifies `Target: print` or `process: fdm|sla|sls|dmls`, run the
   printability sub-pass of validate.py — it emits the `printability` block the Tier-3
   reviewer reads (`volume_mm3`, `thin_sample_frac`, `overhang_face_count`,
   `drain_hole_count`, `body_count`):
   ```
   python "$CLAUDE_CONFIG_DIR/skills/forge-validate/scripts/validate.py" \
     --input <file.stl> --print --process fdm|sla|sls|dmls --units mm [--json]
   ```
   Wall thickness (inward ray-cast sampling) and overhang need trimesh; absence degrades
   to WARN, same as the structural trimesh pass. Thresholds, drain-hole rules and repair
   patterns: **`references/printability.md`**.

**6. Adversarial escalation (substantial builds)**
   If the asset is a hero asset, a print deliverable, or a web-delivery GLB, spawn
   parallel sub-agent reviewers via the Task tool. See
   **`references/adversarial-escalation.md`** for the exact delegation prompt template
   and required JSON output contract.

**7. Report and gate decision**
   Summarise all tier results in a structured report. Gate:
   - BLOCK: any Tier 0 [BLOCK] or Tier 1 FAIL or glTF numErrors > 0 → fix before merge
   - WARN: glTF warnings or Tier 3 advisory findings → review vs FORGE.md intent
   - PASS: all tiers green

---

## Operating principles

- **Gates block, advisories inform.** A BLOCK finding stops the pipeline. A WARN is
  evidence to weigh against the project brief, not a mandatory fix.
- **Workbench only for headless QA renders.** EEVEE Next is unsupported headless on
  Windows. Use `BLENDER_WORKBENCH`; switch to `CYCLES` (CPU) only for the UV-checker
  and normal-pass variants which require shader nodes.
- **Absolute forward-slash paths in Blender Python.** Never `//` relative paths in
  `bpy` `filepath` fields; never backslash literals in Python path strings — use
  `pathlib.Path` or forward slashes.
- **Scripts, not inline code.** `validate.py` and `detect.py` carry the real logic.
  Code blocks in this skill body are illustrations only — the model does NOT run `$()`
  expressions from SKILL.md.
- **Run = call the Skill tool.** When handing off to another Forge skill (e.g.,
  `forge-topology` for repair), use `Skill("forge-topology")`. Narrating the handoff
  in prose does nothing.
