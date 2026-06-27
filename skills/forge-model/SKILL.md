---
name: forge-model
version: 1.0.0
description: >
  Forge suite — polygonal and box modeling via Blender bpy + bmesh + modifier stacks.
  Produces a clean, export-ready .blend/mesh datablock (quad base mesh + non-destructive
  modifier stack) plus a headless QA render PNG: primitives, extrude, inset, bevel, loop cuts,
  bridge loops, modifier stacks (Mirror, Array, Solidify, Bevel, Subsurf, Shrinkwrap,
  WeightedNormal, SmoothByAngle), depsgraph-evaluated geometry reads, and programmatic mesh
  validation. Use whenever asked to "model a polygonal mesh", "box-model a character/prop",
  "model a hard-surface/organic mesh", "make a hard-surface asset", "create a base mesh", "add
  bevel", "add subdivision", "add array modifier", "add mirror modifier", "extrude/inset faces",
  or "sculpt base". For a toleranced mechanical part use forge-parametric; for scatter/L-system/SDF
  use forge-procedural; for retopo/LOD/topology repair use forge-topology. Hands off to forge-uv
  (seams), forge-material (PBR shading), forge-topology (retopo/LOD), forge-render (headless QA
  render), and forge-validate (manifold/watertight gate). HEADLESS-ONLY: driven from code, output
  verified by reading a PNG. Part of the Forge suite.
triggers:
  - model a polygonal mesh
  - box model
  - base mesh
  - hard surface mesh
  - bevel modifier
  - subdivision modifier
  - mirror modifier
  - array modifier
  - bmesh
  - extrude faces
  - inset faces
  - polygonal modeling
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# forge-model — Polygonal & Box Modeling

The geometry foundation of the Forge pipeline. Every downstream skill — UVs, materials, rigs,
simulations, export — consumes meshes built here. The discipline: **clean quads from code,
non-destructive modifier stacks, visual QA by render-and-read before handing off.**

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the coordinate system (Y-up/Z-up), scale unit (m/cm), poly budget, target engine, and output
> paths that every modeling decision must respect. Created by **forge-brief**; validated by
> **forge-validate**. When `ATELIER.md` is also present, extract the aesthetic signature moment
> it describes — this is your brief for silhouette and detail level.

---

> **Suite map.** forge-model is the geometry source. Upstream: **forge-brief** (writes the brief
> + FORGE.md), **forge-standards** (units, naming, pivot rules, poly budgets). Peer craft:
> **forge-parametric** (CAD/OpenSCAD for precision solids), **forge-procedural** (Geometry Nodes
> + SDF for generative/scatter meshes), **forge-topology** (retopo, decimation, LOD, boolean
> cleanup). Downstream consumers: **forge-uv** (needs clean topology + sharp edge marks),
> **forge-material** (PBR setup), **forge-render** (headless Cycles QA loop), **forge-validate**
> (manifold/watertight gate before export), **forge-export** (FBX/glTF/USD). Web handoff:
> **forge-export** → **forge-optimize** → **atelier-webgl** (R3F/Three.js scene).
>
> **Run = call the Skill tool with the exact name. Writing "now run forge-render" in prose runs
> nothing.**

---

## Decide first: Blender availability + modeling approach

Before writing any mesh script, resolve two gates:

**Gate 1 — Blender available?**
Run the PowerShell discovery snippet from `references/headless-invocation.md §1` to locate
`blender.exe`. If Blender is absent, stop and instruct the user to install from blender.org
(MSI, not Microsoft Store — the Store sandbox breaks headless subprocess calls).

```powershell
# Locate blender.exe (PowerShell — Windows-native, no WSL)
$blender = Get-ChildItem -Path `
    "C:\Program Files\Blender Foundation\Blender*\blender.exe",`
    "C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe" `
    -ErrorAction SilentlyContinue |
    Sort-Object { $_.VersionInfo.FileVersionRaw } -Descending |
    Select-Object -First 1
if (-not $blender) { throw "blender.exe not found — install from blender.org (MSI)" }
$BLENDER_EXE = $blender.FullName
Write-Host "Blender: $BLENDER_EXE"
```

Smoke-test the found binary before writing any script:
```powershell
& $BLENDER_EXE --background --factory-startup --python-exit-code 1 `
    --python-expr "import bpy, sys; print('OK', bpy.app.version_string); sys.exit(0)"
```

**Gate 2 — Which modeling approach?**

| Situation | Approach |
|---|---|
| One-time static mesh (prop, hard-surface panel) | **bmesh.ops** — context-free, headless-safe |
| Modifier-driven iteration (mirror, bevel, subsurf) | **bpy modifier stack** via `obj.modifiers` |
| Precision solid (toleranced mechanical part) | Delegate → `Skill("forge-parametric")` |
| Generative / scatter / attribute-driven | Delegate → `Skill("forge-procedural")` |
| Retopology / LOD reduction of existing mesh | Delegate → `Skill("forge-topology")` |

**Rule: never use `bpy.ops.mesh.*` operators in headless scripts** — they require Edit Mode
context that is unreliable outside the GUI. Use `bmesh.ops` instead. The one safe exception:
`bpy.ops.object.modifier_apply`, `modifier_move_to_index`, `shade_smooth` — these work after
setting `bpy.context.view_layer.objects.active`. Full rationale: `references/gotchas.md §G1`.

---

## The flow

1. **Read FORGE.md** — absorb coordinate system, scale unit, poly budget, output path. If it
   doesn't exist, ask the user for target engine + scale before proceeding.

2. **Locate Blender + smoke-test** (Gate 1 above). Store path as `$BLENDER_EXE` in PowerShell.

3. **Pick the modeling approach** (Gate 2 above). Delegate to a sibling Forge skill if the work
   belongs there.

4. **Write the modeling script** (`build_mesh.py` or a descriptive name). Follow the boilerplate
   in `references/bpy-patterns.md §1` — arg-parse after `--`, import `bpy` only after arg-parse,
   wrap `main()` in `try/except` with `sys.exit(1)` on failure, use `--python-exit-code 1`.
   Reference the appropriate section:
   - Primitives + bmesh construction → `references/bpy-patterns.md §2`
   - Extrude / inset / bevel / loopcut / bridge → `references/bmesh-ops.md`
   - Modifier stack (hard-surface or organic) → `references/modifier-stack.md`
   - Normals (SmoothByAngle 4.1+, WeightedNormal) → `references/modifier-stack.md §normals`

5. **Run the script headlessly**:
   ```powershell
   & $BLENDER_EXE --background --factory-startup --python-exit-code 1 `
       --python "C:\absolute\path\build_mesh.py" `
       -- --output "C:\absolute\path\qa_render.png" --samples 32
   ```
   The `--` separator is **mandatory** — everything after it goes to `sys.argv` inside the
   script. Use absolute forward-slash paths in `scene.render.filepath`; never `//`.

6. **Verify the output PNG exists and has plausible size**:
   ```powershell
   if (-not (Test-Path "C:\absolute\path\qa_render.png")) {
       throw "Render failed — no output file"
   }
   $sz = (Get-Item "C:\absolute\path\qa_render.png").Length
   if ($sz -lt 10000) { throw "Render suspiciously small ($sz bytes)" }
   Write-Host "QA render OK ($sz bytes)"
   ```
   Then use `Read` on the PNG to visually inspect geometry — correct silhouette, shading, no
   missing faces, no clipping. If the visual fails, fix the script and re-render. This is the
   headless verification loop. For any **closed/manifold export mesh**, a single 3/4 angle hides
   back-facing problems (inverted normals, missing rear faces) — render front-3/4 + back-3/4 + top
   with `render_qa_multiangle()` (`references/scene-render.md §2`) and Read all three. For a full
   turntable / wireframe / normals pass, invoke `Skill("forge-render")`.

7. **Programmatic mesh validation** (inside the script, after building geometry):
   Run `validate_mesh(obj)` from `references/bpy-patterns.md §4` before the render call.
   Check: non-manifold edges = 0 (if a boolean target or export mesh), isolated verts = 0,
   zero-area faces = 0, duplicate verts = 0, ngon count acceptable for the target pipeline.

8. **Hand off** to downstream skills as needed:
   - UV seams needed → `Skill("forge-uv")`
   - PBR material → `Skill("forge-material")`
   - Final validation gate → `Skill("forge-validate")`
   - Full render pass (turntable, wireframe, normals check) → `Skill("forge-render")`

---

## Reference index

Deep, copy-paste-ready content lives in references/ — read only the section you need:

| File | Contents |
|---|---|
| `references/headless-invocation.md` | Finding blender.exe on Windows, PowerShell invocation patterns, key CLI flags, argument-order rules, subprocess pitfalls |
| `references/bpy-patterns.md` | Script boilerplate (arg-parse, bm.free, try/except), scene setup from scratch, camera/light helpers, render-to-PNG, mesh validation functions |
| `references/bmesh-ops.md` | Extrude (region/discrete/edge), inset (individual/region), bevel, loop cut via subdivide_edges, bridge loops, triangulate, recalc normals |
| `references/modifier-stack.md` | Hard-surface stack order (Mirror→Array→Solidify→Bevel→WeightedNormal→SmoothByAngle), organic stack, each modifier's key params, SmoothByAngle 4.1+ loading pattern, depsgraph evaluated mesh |
| `references/gotchas.md` | All critical failure modes: use_auto_smooth removed (4.1+), SmoothByAngle must be last, bpy.ops.mesh headless RuntimeError, boolean non-manifold failure, lookup table staleness, to_mesh_clear leak, --python-exit-code, path gotchas |

---

## Operating principles

- **bmesh.ops over bpy.ops.mesh — always.** `bpy.ops.mesh.*` operators require Edit Mode context
  that doesn't reliably exist headless. `bmesh.ops` has zero context dependency. Use it for all
  geometry operations; reserve `bpy.ops.object.*` only for modifier apply / shade smooth.
- **Verify before reporting.** Every modeling run reads back the QA render PNG with `Read` before
  declaring success. A script that produced a black image or missing geometry is a failure, not
  a warning. Fix and re-render.
- **Non-destructive first.** Build the modifier stack; apply only when handing off to an exporter
  that requires it (FBX) or to forge-topology for retopo. Keep the parametric base mesh clean.
- **Modifier order is a correctness invariant.** Hard-surface: Mirror → Array → Solidify → Bevel
  → WeightedNormal → SmoothByAngle (last, always). Organic: Mirror → Subsurf → SmoothByAngle.
  WeightedNormal above SmoothByAngle produces broken shading — enforce with `modifier_move_to_index`.
- **Run = call the Skill tool.** Cross-skill handoffs (forge-uv, forge-render, forge-validate,
  forge-material) are Skill tool calls, not narrative instructions.
