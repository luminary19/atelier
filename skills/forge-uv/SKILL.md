---
name: forge-uv
version: 1.0.0
description: >
  Forge suite — UV unwrapping, seam placement, island packing, texel density normalization,
  UDIM tile layout, and distortion/checker verification for 3D assets. Produces a validated
  UV map (non-overlapping bake channel + layout PNG) that downstream baking, material, and
  export skills can consume without rework. (The project-wide texel-density BUDGET is set in
  forge-standards; this skill normalizes a mesh's UVs to hit it.)
  Use whenever UV unwrapping a mesh, placing seams, packing UV islands, normalizing texel density,
  setting up UDIMs, checking UV stretch or distortion, generating a UV layout PNG, validating
  UV overlaps, running a checker-map render, preparing UVs for texture baking, or correcting
  UV scale before export. Trigger phrases: "unwrap", "UV seams", "pack islands", "normalize
  texel density", "fix UV texel density", "texel density on a UV map", "UDIM", "UV checker",
  "UV layout", "UV distortion", "UV stretch", "UV overlap", "UV validation", "bake UVs",
  "lightmap UV", "UV scale". HEADLESS-ONLY: driven from code (pure `--background` via bpy +
  bmesh), output verified by reading a PNG. Part of the Forge suite.
triggers:
  - unwrap
  - UV seams
  - pack islands
  - normalize texel density
  - fix UV texel density
  - UDIM
  - UV checker
  - UV layout
  - UV distortion
  - UV overlap
  - UV validation
  - bake UVs
  - lightmap UV
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# Forge UV

UV maps are the contract between geometry and texture. Every bake, paint, and export operation
downstream depends on a valid, non-overlapping, correctly-scaled UV layout. This skill owns
that contract — from raw mesh to verified UV PNG — in pure `blender --background`: unwrap and
projection solvers run headless directly, and the post-process ops that normally need a UV
editor area (pack, overlap check, TD scale) run via operator-free **bmesh** implementations
(`references/seams-packing.md §7/§8`, `references/texel-density.md §4`). The one step that wants
a screen — the optional `export_layout` reference PNG — degrades to the checker-map render.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the texel density target, texture resolution budget, target engine, UV channel naming policy,
> and verified output paths for this project. If **`ATELIER.md`** exists, check the aesthetic
> and surface-fidelity notes, which drive texel density targets.

---

> **Suite map — where this skill fits:**
>
> Upstream (must complete first):
> - **forge-brief** — writes FORGE.md with texel density + poly budget targets
> - **forge-standards** — canonical units, scale, naming, and texel density budgets per asset class
> - **forge-model** — clean geometry; applied scale; hard edges set for seam automation
> - **forge-topology** — N-gon cleanup, retopo, decimation — topology must be final before UV
>
> This skill (UV):
> - Seams → unwrap → pack → TD normalize → validate → layout PNG
>
> Downstream (consumes this skill's output):
> - **forge-texture** — baking (normal/AO/curvature) requires non-overlapping bake channel
> - **forge-material** — UV maps drive all texture sampling; texel density governs tex resolution
> - **forge-export** — multi-UV-channel export (diffuse UV0, lightmap UV1); FBX/GLB UV naming
> - **forge-validate** — UV overlap gate is part of the full asset validation pass
> - **forge-render** — checker-map render for visual QA
>
> Web handoff: **forge-export** → **forge-optimize** → **atelier-webgl** (R3F / Three.js scene).
> UVs are upstream of texture and feed the web GLB, so a UV asset bound for the web rides this
> canonical chain after texturing/validation.
>
> **Run = call the Skill tool with the exact name. Writing "now run forge-texture" in prose runs nothing.**

---

## Decide first: pick the unwrap method

Before writing any bpy code, choose the method. Wrong choice = re-unwrap later.

| Method | Best for | Seams required? | Speed |
|--------|---------|----------------|-------|
| `ANGLE_BASED` | Organic meshes, characters, curved hard-surface | Yes | Medium |
| `CONFORMAL` | Quick iterations, background assets, simple shapes | Optional | Fast |
| `MINIMUM_STRETCH` | Hero assets, displacement maps, print | Yes | Slow |
| Smart UV Project | Architecture, hard-surface boxes, no-seam workflow | No | Medium* |
| Cube/Cylinder Project | Box/cylinder primitives, atlases | No | Fast |
| Lightmap Pack | Dedicated lightmap channel (UV1), engine baking | No | Medium |

\* Smart UV Project is ~100× slower via Python on meshes >100 k faces (pre-Blender 3.6 solver bug).
Use Blender 4.x. See **`references/unwrap-methods.md §Gotchas`** for the workaround.

**Verify Blender is available before executing:**

```powershell
# PowerShell — confirm blender is on PATH before proceeding
blender --version
# If missing: winget install BlenderFoundation.Blender
```

**If Blender is absent — degrade, don't dead-end.** For the common "no Blender on this box" case
there is a real pure-Python fallback for the **bake-channel** use case:

| Need | Primary (Blender) | Fallback (no Blender) |
|------|-------------------|-----------------------|
| Clean non-overlapping UVs for baking | `ANGLE_BASED` + pack | **xatlas** (`pip install xatlas`) → `xatlas.parametrize(verts, faces)` |
| Seam control / TD craft / UDIM / layout PNG | Blender (required) | not available — needs Blender |
| Checker-map visual QA | Cycles checker render | trimesh + PIL (forge-topology `references/mesh-libs.md §7`) |

xatlas produces guaranteed non-overlapping atlas UVs headlessly with zero Blender dependency, so
"just need clean UVs for baking" still ships. Seam placement, texel-density normalization, UDIM,
and the layout PNG still require Blender. Full fallback recipe + caveats:
**`references/xatlas-fallback.md`**.

If Blender is absent AND the task needs seam/TD/UDIM craft (not just a bake channel), stop and
report — xatlas cannot cover those. Document the fallback in a comment whenever you take it.

---

## The flow

1. **Read FORGE.md** — pull texel density target, texture resolution, UV channel naming, output paths.
   If absent, use defaults: TD = 1024 px/m, texture = 2048 px, bake channel = `"UVMap"`.

2. **Pre-flight the mesh** — confirm scale is applied; confirm the mesh exists and has faces.
   Scale not applied = stop and run **forge-topology** → apply transforms first.
   Full pre-flight: `references/preflight.md`.

3. **Choose the unwrap method** using the table above. For most game/web props: `ANGLE_BASED` with
   seams from sharp edges at 30°. Deep method options: `references/unwrap-methods.md`.

4. **Mark seams** — for `ANGLE_BASED` / `CONFORMAL` / `MINIMUM_STRETCH`:
   - Hard-surface: use `mark_seams_from_sharp(sharpness=radians(30))`.
   - Organic / characters: place seams manually along hidden/back-facing edges.
   - Back-propagate after unwrap with `seams_from_islands()` to lock the layout.
   Full seam rules: `references/seams-packing.md §Seam placement rules`.

5. **Unwrap** — run the chosen operator. Always pass `correct_aspect=True`.
   For `MINIMUM_STRETCH`, cap `iterations=500` headlessly (unlimited = hangs).
   Full API signatures: `references/unwrap-methods.md`.

6. **Pack islands** — after any unwrap, pack to fill UV space. In pure `--background` use
   `pack_islands_bmesh()` (operator-free); only use `bpy.ops.uv.pack_islands` if a screen exists.
   Compute margin from texture resolution: `margin = px_gap / texture_px` (4 px at 2048 = 0.002).
   `CONCAVE`/`CONVEX` density is operator-only; the bmesh packer is AABB shelf.
   Full packing options + bmesh packer: `references/seams-packing.md §3` (operator) / `§7` (bmesh).

7. **Normalize texel density** — compute TD per object, scale UVs to match the target from FORGE.md.
   In pure `--background` use `normalize_texel_density_bmesh()` (operator-free), then re-pack.
   Hero props: 1024–2048 px/m. Game environment: 512–1024. Background: 256–512.
   Full TD formulas + bmesh scaler: `references/texel-density.md §4`.

8. **UDIM layout** (if needed) — if `FORGE.md` specifies UDIM workflow or target is Film/VFX:
   distribute islands to integer tiles (1001, 1002…). Full UDIM setup: `references/udim.md`.

9. **Validate** — run the UV QA suite:
   - Overlap check → must return 0 faces for bake channel. In pure `--background` use
     `detect_overlaps_bmesh()` (operator-free); `bpy.ops.uv.select_overlap` only if a screen exists.
   - Out-of-bounds check (UVs outside 0–1 range, unless UDIM).
   - TD deviation < 20% from target.
   - Utilization > 75% (environment props) / > 85% (hero assets).
   Full QA checklist: `references/validation.md`.

10. **Checker-map render** — apply `UV_GRID` or `COLOR_GRID` checker material, render headlessly
    to PNG via Cycles CPU. Then call `Read` on the PNG to visually inspect:
    - Squares uniform in size (consistent TD) and square-shaped (no stretch).
    - No abrupt size jumps at polygon seams.
    - No unexpected overlap patterns.
    Render command + visual read-back: `references/validation.md §Checker-map render`.

11. **Export UV layout PNG** — for hand-painting or reference. Requires the `io_mesh_uv_layout`
    addon (not enabled by default headless) AND an EDIT-mode area, so this is the one step that
    needs a screen. In pure `--background` skip it and rely on the checker-map render (step 10).
    Full export snippet: `references/validation.md §UV layout export`.

12. **Write results** — report TD, utilization %, overlap count, and PNG path back to the
    caller (agent or pipeline). If overlaps > 0 for a bake channel: block and fix before handing
    off to **forge-texture**. For final gate, call `Skill("forge-validate")`.
    - If this asset ships to the web, the chain after texturing/validation is
      `Skill("forge-export")` → `Skill("forge-optimize")` → `Skill("atelier-webgl")`.

---

## Headless invocation pattern

All UV scripts run via:

```
blender --background <scene.blend> --python <uv_script.py> --python-exit-code 1 -- <args>
```

- The `--` separator is mandatory for passing script arguments.
- `--python-exit-code 1` makes Python exceptions fail the process (check `$LASTEXITCODE`).
- Use absolute forward-slash paths in `filepath` parameters — Blender's Python prefers POSIX paths
  even on Windows: `"C:/assets/prop.blend"` not `"C:\\assets\\prop.blend"`.
- `blender.exe` (full path if not on `$env:PATH`): `"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"`.

**Pure `--background` is the default — use bmesh, not operators, for post-process ops.** The
unwrap/projection solvers (`bpy.ops.uv.unwrap`, `smart_project`, cube/cylinder) run headless fine.
But the post-process operators `pack_islands` / `select_overlap` / `transform.resize` require a UV
editor area and fail in pure `--background` with `RuntimeError: poll() failed`. Forge runs them via
operator-free **bmesh** equivalents — no area, no `temp_override`:

```python
# Pure --background (no screen): the canonical Forge path.
pack_islands_bmesh(obj, margin=0.005)                 # seams-packing.md §7
assert detect_overlaps_bmesh(obj) == 0               # seams-packing.md §8 — bake channel gate
normalize_texel_density_bmesh(obj, target_td, texture_px)  # texel-density.md §4
```

Only if Blender was launched WITH a screen (GUI / offscreen window) may you instead use the
operator + `temp_override` path. The `export_layout` reference PNG is the one step that needs an
area — when there is no screen, skip it and rely on the checker-map render (validation.md §2).

| Step | Pure `--background` path |
|------|--------------------------|
| Pack islands | `pack_islands_bmesh()` (NOT `bpy.ops.uv.pack_islands`) |
| Overlap check | `detect_overlaps_bmesh()` (NOT `bpy.ops.uv.select_overlap`) |
| TD scale | `normalize_texel_density_bmesh()` (NOT `bpy.ops.transform.resize`) |
| Layout PNG | needs a screen → else use checker render |

Full implementations + the area-vs-background matrix: `references/unwrap-methods.md §3`,
`references/seams-packing.md §7/§8`, `references/texel-density.md §4`.

---

## Reference files (read on demand)

| File | Contents |
|------|---------|
| `references/unwrap-methods.md` | All unwrap API signatures, gotcha table, headless context override |
| `references/seams-packing.md` | Seam placement rules, island packing options, overlap rules table |
| `references/texel-density.md` | TD formula, TD budget table, batch normalization, per-LOD targets |
| `references/udim.md` | UDIM numbering formula, tile setup, island distribution, UDIM export |
| `references/validation.md` | Full QA suite, checker-map render, UV layout export, overlap detection, determinism checklist |
| `references/preflight.md` | Scale check, UV layer normalization, modifier-stack gotchas |
| `references/xatlas-fallback.md` | No-Blender fallback: xatlas non-overlapping bake-channel UVs + trimesh/PIL QA |

---

## Operating principles

- **Apply scale before anything.** Unapplied scale corrupts every TD calculation and every
  overlap check. If `obj.scale != (1, 1, 1)`, stop and call `transform_apply(scale=True)` first.
- **Bake channel must be zero overlaps — no exceptions.** Overlapping UVs cause light/shadow
  bleeding. Block the pipeline and report before handing off to **forge-texture**.
- **Checker render is the eyes.** After every pack, render the checker map and call `Read` on the
  PNG. Numbers alone cannot catch seam-direction errors or invisible stretching.
- **Enable `io_mesh_uv_layout` explicitly.** Blender does not auto-enable addons headless. Add
  `addon_utils.enable("io_mesh_uv_layout", default_set=True, persistent=True)` at script start.
- **Run = call the Skill tool.** Handing off to forge-texture, forge-validate, or forge-render
  means calling `Skill("forge-texture")` / `Skill("forge-validate")` / `Skill("forge-render")`.
  Writing "now run forge-texture" in prose runs nothing.
