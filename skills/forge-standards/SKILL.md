---
name: forge-standards
version: 1.0.0
description: >
  Forge suite — the "3D design tokens" layer. Defines and enforces every project-wide 3D constant
  before any geometry or texture is authored: coordinate system and handedness per export target
  (Blender Z-up RH → glTF/Three.js Y-up RH vs. Unreal Z-up LH → FBX), unit scale (meters in
  Blender, cm in UE5, the 100× correction), axis-swap matrices, real-world scale references,
  naming conventions (SM_/SK_/T_/M_/MI_ prefixes, _BC/_N/_ORM texture suffixes), pivot/origin
  placement rules per object class, per-platform polycount budgets (PC/console/mobile/web), texel
  density targets (px/m), UV utilization floors, ORM channel-pack policy, LOD ratios, and
  FORGE_STANDARDS.json schema. Use whenever DEFINING the 3D standards for a project (after the
  brief writes FORGE.md), resolving a "sideways mesh" or "100× scale" bug, establishing naming
  rules, budgeting polys or texel density, deciding pivot placement for a prop type, or generating
  the machine-readable standards file that other Forge skills ingest. Bootstrapping a brand-new 3D
  project (writing FORGE.md, "set up a 3D project") is `forge-brief`'s job — it runs first, then
  calls this skill. HEADLESS-ONLY: driven from code, output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - forge standards
  - 3d design tokens
  - naming convention 3d
  - polycount budget
  - texel density budget
  - set texel density target
  - coordinate system blender
  - handedness fbx
  - pivot placement
  - ORM channel pack
  - LOD ratios
  - FORGE_STANDARDS.json
  - unit scale unreal
  - axis swap gltf
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# Forge Standards — 3D Design Tokens

The ground-truth layer. Every other Forge skill ingests these constants before writing a line of
code. Without them, two independently authored assets collide in the same scene — wrong scale,
mismatched texel density, broken LOD slots — and the render-verify step cannot produce a stable
comparison baseline.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the confirmed coordinate system, scale unit, poly budget, texel density, render engine, and
> output paths for this project. If `FORGE.md` is absent, this skill writes the standards
> sections of it. When `ATELIER.md` exists, check for a `## Forge 3D assets` block.

---

> **Suite map — key cross-references:**
> - **`forge`** (router) dispatches here after `forge-brief`; reads FORGE.md target engine.
> - **`forge-brief`** writes FORGE.md; calls this skill to populate budgets + coordinate system.
> - **`forge-model`** / **`forge-parametric`** / **`forge-procedural`** consume naming + pivot rules.
> - **`forge-uv`** consumes texel density targets, UV utilization floors, and channel-pack policy.
> - **`forge-texture`** consumes ORM packing policy and texture suffix table.
> - **`forge-topology`** / **`forge-export`** consume handedness rules, axis-swap matrices, and LOD ratios.
> - **`forge-validate`** is the enforcement gate — it runs checks against every rule defined here.
> - **`atelier-webgl`** receives GLB assets; its Three.js scenes use glTF Y-up RH, matching this skill's web profile.
> - **`atelier-perf-a11y`** is the web-runtime performance gate after forge-export/optimize.
>
> **Run = call the Skill tool with the exact name. Writing "now run forge-validate" in prose runs nothing.**

---

## Decide first: which target profile?

Before consulting any table below, confirm:

1. Read `FORGE.md` (if absent, invoke `Skill("forge-brief")` to write it first): extract `## Target`, `## Coordinate system`, `## Budgets`.
2. Pick the profile that governs this asset:

| Profile | Engine / delivery | Up-axis | Handedness | 1 unit = | Export format |
|---------|------------------|---------|------------|----------|---------------|
| `web` | Three.js / R3F / model-viewer | Y-up | RH | 1 m | GLB (Draco) |
| `unreal` | Unreal Engine 5 | Z-up | LH | 1 cm | FBX binary |
| `unity` | Unity | Y-up | LH | 1 m | FBX binary |
| `godot` | Godot 4 | Y-up | RH | 1 m | GLB (glTF) |
| `print` | STL / STEP | Z-up | RH | 1 mm or 1 mm | STL / STEP |
| `film` | USD / USDA | Y-up | RH | 1 m (scene-dependent) | USD |

Blender always authors in **Z-up, right-handed, meters**. Every axis-swap and unit correction is baked at export time, not during modeling. Full axis-swap matrices and conversion snippets: **`references/coordinate-systems.md`**.

---

## The flow

1. **Read FORGE.md** — load existing profile; if absent, invoke `Skill("forge-brief")` to create it first (do not just narrate the handoff).
2. **Confirm target profile** (table above) — this gates every budget and convention downstream.
3. **Generate `FORGE_STANDARDS.json`** at project root — the machine-readable token file.
   Schema and full example: **`references/forge-standards-schema.md`**.
4. **Apply naming convention** — use the prefix + suffix tables; verify with the regex in the schema.
   Full prefix/suffix tables: **`references/naming-conventions.md`**.
5. **Set pivot / origin** per object class — ground props go bottom-center; hinged objects go at the hinge.
   Pivot rules + bpy snippets: **`references/pivot-origins.md`**.
6. **Load polycount budgets** for the confirmed profile — PC/console, mobile, web, or Nanite-era.
   Budget tables + LOD ratios: **`references/polycount-budgets.md`**.
7. **Load texel density targets** — px/m tier per asset class, UV utilization floor, channel-pack policy.
   Density tables + calc snippet: **`references/texel-density-uv.md`**.
8. **Validate existing assets** — run `forge-validate` (call via Skill tool) against the written standards.
   Headless validation invocation: **`references/validation-headless.md`**.
9. **Render-verify scale** — after export, render against a **1.8 m human silhouette at world origin**
   with fixed, reproducible settings: **Cycles 16 samples, seed=0** (or Workbench), **512×512**, fixed
   **orthographic side camera**. `Read` the PNG and compare silhouette height. Detect→fix:
   silhouette ≈ half (or 100×) expected height → unit mismatch → set `unit_settings.scale_length` +
   `transform_apply(scale=True)`; asset rotated 90° → Z-up vs Y-up export → re-export with `export_yup=True`.
   Settings + table: **`references/validation-headless.md`** (deeper render-QA: `forge-validate` render-qa-guide).

---

## Coordinate systems & axis-swap in brief

Model in Blender **Z-up RH, meters** always. Export corrections per target:

| From → To | Location swizzle | Scale swizzle | Unit | Quat reorder |
|-----------|-----------------|--------------|------|-------------|
| Blender → glTF/web | `(x, z, -y)` | `(x, z, y)` | 1:1 | w,x,y,z → x,z,-y,w |
| Blender → Unreal | `(x*100, -y*100, z*100)` | uniform ×100 | ×100 | negate qy, qw |
| Blender → Unity | `(-x, y, z)` or FBX auto | `(x, y, z)` | 1:1 | negate qx, qw |

The Blender glTF exporter and FBX exporter handle these automatically when given correct axis settings.
**For skeletal meshes to UE5:** set `bpy.context.scene.unit_settings.scale_length = 0.01` before export
to avoid the 100× skeleton bug (static mesh imports fine, skeleton comes in at 1% scale).
Full matrices, Python conversion functions, and gotchas: **`references/coordinate-systems.md`**.

---

## Naming — quick reference

Pattern: `[TypePrefix]_[AssetName]_[Descriptor]_[VariantNumber]`
— no spaces, no Unicode, PascalCase asset name, zero-padded number (`_01`).

Key prefixes: `SM_` static mesh · `SK_` skeletal/skinned · `T_` texture · `M_` material · `MI_` material instance.
Texture suffixes: `_BC` base color (sRGB) · `_N` normal (Linear) · `_ORM` packed AO/Rough/Metal (Linear).
Collision (UE5 auto-detect): `UCX_SM_Barrel_Oak_01` (convex hull) · `UBX_` (box) · `USP_` (sphere).
LOD slots: `SM_Barrel_Oak_LOD0` → `SM_Barrel_Oak_LOD3`.

Full prefix table, texture suffix table, Blender Studio in-file prefixes, and regex patterns:
**`references/naming-conventions.md`**.

---

## Polycount & LOD — quick reference

All counts in **triangles** (GPU draw unit). Quads ≈ half the tri count.

| Profile | Small prop LOD0 | Hero char LOD0 | Web single asset | Scene budget |
|---------|----------------|---------------|-----------------|--------------|
| PC/Console | 500–3 k | 50–100 k | — | scene-dependent |
| Mobile | 100–500 | 3–8 k | — | 50–150 k total |
| Web/AR | ≤ 3 k | ≤ 50 k | ≤ 50 k / 4 MB GLB | ≤ 150 k |

Default LOD ratios: `[1.0, 0.5, 0.2, 0.05]` (LOD0 → LOD3). Always decimate from LOD0, not
cascading from the previous LOD. Full per-class tables and Nanite notes:
**`references/polycount-budgets.md`**.

---

## Texel density — quick reference

Formula: `TD (px/m) = texture_resolution_px / object_dimension_m`

| Tier | px/m | Use case |
|------|------|---------|
| Hero (FPS weapon, face) | 2048 | Closeup, screen-filling |
| Standard foreground prop | 1024 | PC/console default |
| Mid-range environment | 512 | Background props, environment |
| Web / AR | 512–1024 | Keep GLB ≤ 4 MB total |
| Mobile foreground | 512 | Mid-range Android |

**ORM channel-pack:** R = AO, G = Roughness (most bit precision under BC compression), B = Metallic.
One ORM replaces three maps, saving ~4 MB per 2048² material at BC1.
All tiers, UV utilization floors (≥ 85% hero, ≥ 75% env), lightmap UV rules, and bpy snippets:
**`references/texel-density-uv.md`**.

---

## Operating principles

- **One profile, one truth.** Every project has exactly one `FORGE_STANDARDS.json` at root. All Forge skills
  read it; none hardcode budgets or names. If the file is absent, this skill writes it first.
- **Model in meters, convert at export.** Blender stays Z-up RH meters throughout. Axis swaps and unit
  corrections happen in the exporter, never during modeling — so the source .blend is always portable.
- **Apply transforms before any export. Every time.** Unapplied scale is the #1 pipeline killer: it
  corrupts physics, normals, and skeletal animation. Automate `apply_transforms()` in the pre-export script.
- **Naming is a contract.** `SM_`, `SK_`, `T_` prefixes and `_BC`, `_N`, `_ORM` suffixes are not style
  — they drive engine auto-import, LOD slot detection, lightmap UV assignment, and `forge-validate` regex.
  A single misnamed asset silently breaks the import pipeline.
- **Validate before handing off.** Run `Skill("forge-validate")` against every asset before `forge-export`.
  The standards file is machine-readable precisely so that the validation gate can run without human review.
