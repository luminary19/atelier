---
name: forge-parametric
version: 1.0.0
description: >
  Forge suite — Code CAD: produce engineering-grade solid geometry headlessly from code.
  Deliverables: STL, 3MF, STEP, GLB files with exact fillets/chamfers, ISO tolerances & fits,
  threads, draft angles, and ribs — verified by rendering a PNG and reading it back. Use whenever
  asked to: design a part, model a mechanical component, create a parametric CAD file, generate a
  bracket/enclosure/housing/fixture, export STEP or STL for 3D printing, design threads or screw
  fits, apply fillets or chamfers to a solid, specify ISO tolerances or engineering fits (H7/p6 etc.),
  batch-generate design variants with different dimensions, convert between CAD formats, or produce
  a solid model from a sketch/spec. Triggers on: "OpenSCAD", "CadQuery", "build123d", "FreeCAD",
  "STEP export", "STL export", "3MF", "fillet", "chamfer", "tolerance", "clearance fit", "press fit",
  "threaded rod", "nut", "bolt", "BOSL2", "parametric model", "print-ready part", "CAD script",
  "solid model". HEADLESS-ONLY: driven from code (.scad / .py), output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - openscad
  - cadquery
  - build123d
  - freecad headless
  - step export
  - stl export
  - fillet chamfer
  - iso tolerance
  - engineering fit
  - threaded rod
  - parametric cad
  - solid model
  - 3d print ready
  - bosl2
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# forge-parametric — Code CAD

The engineering-precision layer of Forge. Everything produced here is dimensionally exact,
reproducible from source, and verified via headless render-in-the-loop before being handed
downstream. No GUI. No hand-tweaked binaries.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the chosen tool, coordinate system, scale unit, output paths, and poly budget for this project.
> If **`ATELIER.md`** also exists, note the aesthetic world and signature moment; aesthetic intent
> may constrain part geometry (organic vs. industrial, rounded vs. sharp edges).

---

> **Suite map:**
> - **forge** — router; call it when you are unsure which skill to use
> - **forge-brief** — writes FORGE.md; run before this skill if FORGE.md is absent
> - **forge-standards** — units, handedness, naming, poly budgets, validation thresholds (canonical home of 3D math)
> - _forge-parametric_ ← **YOU ARE HERE** — Code CAD, exact solids, STEP/STL/3MF export
> - **forge-model** — polygonal/box modeling via bpy when mesh-not-CAD is right
> - **forge-topology** — retopo, boolean cleanup, decimation, LOD
> - **forge-validate** — manifold/watertight gate, printability, glTF-Validator
> - **forge-export** — final format matrix (GLB/USD/FBX/web handoff)
> - **forge-optimize** — Draco/Meshopt, KTX2, web budgets → **atelier-webgl** seam
> - **atelier-webgl** — receives `.glb` from forge-optimize for Three.js/R3F scenes
>
> Run = call the Skill tool with the exact name above. Writing "now run forge-validate" in prose
> runs nothing. Every cross-skill handoff is a `Skill(...)` call.

---

## Decide first: which tool for which job?

Before writing a single line of geometry code, resolve the tool and confirm it is available.
Run the preflight check below, then use the decision matrix.

```powershell
# Probe tool availability + project state (run this; do NOT inline-expand $(...) in the skill body):
python "$CLAUDE_CONFIG_DIR/skills/forge/scripts/probe.py" --json
```
`probe.py` reports `openscad` (via `openscad.com`) and `python` under `tools[]`, plus any existing
`.scad`/`.step`/`.stl` sources. Reason over its output to confirm the tool you picked is present —
there is no `--tools` filter. build123d/CadQuery/FreeCAD are pip/installer packages (not on PATH),
so confirm those by their venv import or `FreeCADCmd.exe --version`, not by `probe.py`.

**Decision matrix — pick one, commit:**

| Need | Tool | Why |
|---|---|---|
| Mesh output (STL/3MF), FDM/resin print, algorithmic geometry, fast batch | **OpenSCAD + BOSL2** | Natively headless, `-D` param injection, Manifold backend 8–30x CGAL, zero-install libs |
| Exact fillets on computed topology, STEP for CAM/CNC, assembly constraints, B-rep round-trip | **build123d** (Python, OCP kernel) | `export_step()` is lossless; `fillet()` acts on exact OCCT topology, not mesh |
| Vendor STEP import with colors/metadata, existing FCStd files, TechDraw, FEM, Assembly workbench | **FreeCAD** (`FreeCADCmd.exe`) | Only tool with full OCAF framework headlessly; do NOT mix with system Python |
| Quick STL → STEP conversion, mesh-to-solid sewing | **FreeCAD** | `makeShapeFromMesh` + `sewShape` + `Import.export()` |

**Forge default:** Start with **OpenSCAD** for any mesh-output task; escalate to **build123d**
when exact fillets on computed topology or STEP is required. FreeCAD only for vendor STEP
import, FCStd round-trips, or FEM.

Full CLI flags, API calls, and gotcha→fix tables are in **`references/`** (read on demand):
- `references/openscad-cli.md` — headless invocations, BOSL2, tolerances/threads
- `references/build123d-cadquery.md` — Python B-rep API, export formats, validation
- `references/freecad-headless.md` — FreeCADCmd, STEP I/O, PartDesign scripting
- `references/tolerances-fits.md` — ISO 286-1 tables, FDM clearances, GD&T, design rules

---

## The flow

1. **Read FORGE.md** → load target engine, coordinate system, output paths, poly budget.
   If FORGE.md is absent, invoke `Skill("forge-brief")` to create it before continuing.

2. **Decide-first gate** → run preflight, pick tool (matrix above), confirm it is installed.
   If neither OpenSCAD nor build123d is found, surface the gap and stop — do not hallucinate CLI.

3. **Write the source file** (`.scad` or `.py`) following these invariants:
   - CONFIG block first (all user params with units in comments), then CALC, then GEOMETRY.
   - No magic numbers in geometry code. Derive everything from the config block.
   - For OpenSCAD: declare every `-D`-overridable param with a default. Read `references/openscad-cli.md §3.2–3.7`.
   - For build123d: parametric models are plain Python functions returning `Part`. Apply fillets
     and chamfers **last**, after all booleans. Read `references/build123d-cadquery.md §3b–3e`.
   - For FreeCAD: run via `FreeCADCmd.exe`; never import `*Gui` modules; always absolute paths;
     call `doc.recompute()` after every structural change. Read `references/freecad-headless.md §3`.

4. **Export geometry** (first pass — STL/3MF for quick check or STEP for B-rep):
   - OpenSCAD: `openscad.com -o out.stl --backend=Manifold model.scad` (nightly) or omit `--backend` for stable.
   - build123d: `export_step(part, "out.step")` + `export_stl(part, "out.stl", tolerance=1e-3, angular_tolerance=0.1)`.
   - FreeCAD: `Import.export([body], "out.step")` (preserves assembly structure and names).

5. **Render verification PNG** — headless render-in-the-loop:
   - **OpenSCAD (preferred for OpenSCAD models):**
     ```
     openscad.com -o verify.png --imgsize=1920,1080 --autocenter --viewall
                  --camera=0,0,0,55,0,25,200 --colorscheme=Cornfield model.scad
     ```
     Add `--render` for final sign-off only (slower — uses Manifold/CGAL). Omit for quick geometry check.
   - **For build123d / CadQuery — native render via agentcad** (the natural choice; gate on the
     §9 asserts first): `agentcad run model.py --output iso --render iso,front,top,right`, then
     size-check + `Read` + diagnose per `references/build123d-cadquery.md §8b`.
   - **For build123d / FreeCAD models — or import STL into OpenSCAD for preview:**
     Write a temp `.scad` with `import("out.stl");` and render it as above. This avoids a Blender
     dependency for quick checks. Reserve `Skill("forge-render")` for photorealistic verification.
   - **Confirm the PNG is non-trivial:** file must exist and be > 10 KB. A < 10 KB PNG means blank render.

6. **Read the PNG** — call `Read("verify.png")` (or the resolved absolute path). Inspect visually:
   - Is the geometry present and correctly shaped?
   - Are fillets/chamfers visible where expected?
   - Is scale plausible (bounding box consistent with spec)?
   - If blank or wrong: diagnose against the visual-failure table for your tool
     (`references/openscad-cli.md §10` for OpenSCAD, `references/build123d-cadquery.md §8b` for
     build123d/CadQuery), fix the source, and re-render. Do not report success until the PNG passes.

7. **Validate programmatically:**
   - OpenSCAD: `openscad.com -o out.stl --summary all --summary-file summary.json model.scad`
     → parse `summary.json` for volume and bounding box; fail if volume is zero.
   - build123d: `assert part.is_valid`, `assert part.volume > 0`.
   - FreeCAD: run `validate_shape()` (see `references/freecad-headless.md §6.1`).
   - For printability gate: invoke `Skill("forge-validate")` — it runs the full manifold/watertight
     check, printability analysis, and adversarial escalation.

8. **Export final deliverable** — format per FORGE.md target:
   - FDM/resin print → `binstl` or `3mf` (3MF preferred: preserves units, color, metadata).
   - CAM / CNC → STEP (B-rep only; STL is not accepted by most CAM tools).
   - Web / Three.js → GLB from build123d (`export_gltf(part, "out.glb", binary=True)`), then
     invoke `Skill("forge-export")` → `Skill("forge-optimize")` → `Skill("atelier-webgl")`.
   - Batch design family → PowerShell loop over `-D` flags (OpenSCAD) or Python function calls (build123d).

9. **Handoff** — record the verified output path in FORGE.md. If the downstream skill is
   forge-render (photorealistic shot), forge-topology (cleanup), or forge-validate (gate),
   invoke `Skill("forge-render")`, `Skill("forge-topology")`, or `Skill("forge-validate")`
   as appropriate. Run = call the Skill tool. Nothing else.

---

## Key invocation patterns (read-ready — no expansion needed)

**OpenSCAD batch family (PowerShell):**
```
openscad.com -o "bracket_w{w}.stl" -D "width={w}" --backend=Manifold model.scad
```
Loop `$w in @(60, 80, 100)` — each generates a separate STL without touching the `.scad`.

**build123d venv setup (Python 3.12, Windows):**
```
python -m venv .venv && .venv\Scripts\Activate.ps1
python -m pip install --upgrade pip && pip install build123d
```

**FreeCADCmd invocation pattern:**
```
FreeCADCmd.exe "C:\absolute\path\to\forge_part.py"
```
Script names must NOT shadow stdlib modules (`test.py`, `math.py` → rename to `forge_test.py`).

**BOSL2 install (OpenSCAD user library path):**
```
git clone https://github.com/BelfrySCAD/BOSL2.git "$env:USERPROFILE\Documents\OpenSCAD\libraries\BOSL2"
```

---

## Operating principles

- **Decide before executing.** Run the preflight, pick the tool, read the decision matrix. Never
  start writing geometry code before the tool choice is confirmed and verified as installed.
- **Config → Calc → Geometry — always.** All user dimensions live in the config block at the top.
  No magic numbers in modules. Derived values are computed once in a calc block, consumed everywhere.
- **Verify with eyes, not assumptions.** Every geometry pass ends with a PNG render read by `Read`.
  Do not report the part correct until the image passes visual inspection. Blank PNG = broken render,
  not success.
- **Fillets and chamfers are last.** In build123d and FreeCAD, apply fillets after all boolean ops.
  In OpenSCAD, use BOSL2 `cuboid(rounding=R)` or `edge_profile()` — never `minkowski(sphere)` on
  complex geometry (O(V²) cost; use Manifold backend if unavoidable).
- **Run = call the Skill tool.** When the flow says "invoke forge-validate", that is a `Skill()`
  call, not a narrated instruction. Writing "next, run forge-validate" in prose runs nothing.
