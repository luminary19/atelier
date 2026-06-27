---
name: forge-export
version: 1.0.0
description: >
  Forge suite — format matrix, glTF/GLB/USD/FBX export, and engine import conventions.
  Produces a validated, engine-ready asset (GLB, USDC, FBX, or USDZ) from any Forge
  working file. Use whenever: exporting a Blender scene or procedural mesh to glTF/GLB;
  converting FBX, OBJ, or STL to GLB; building a USD stage for multi-DCC pipeline;
  packaging USDZ for iOS AR / Quick Look; importing a GLB into Unreal Engine (Interchange,
  Nanite, FBX naming), Unity (FBX/glTFast, ORM pack, axis bake), or Godot 4 (headless
  --import, sidecar .import, collision suffixes); fixing 100× FBX scale; choosing between
  glTF, USD, FBX, OBJ, Alembic, STEP for a given pipeline stage; or producing a web-ready GLB
  and handing it to forge-optimize for the atelier-webgl handoff (forge-optimize owns the final
  Skill(atelier-webgl) call). HEADLESS-ONLY: driven from code, output verified by reading a PNG.
  Part of the Forge suite.
triggers:
  - export glb
  - export gltf
  - export fbx
  - export usd
  - export usdz
  - convert to glb
  - unreal import
  - unity import
  - godot import
  - format matrix
  - forge export
  - ar quick look
  - engine ready
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge — Export & Engine Import

Export is the **egress boundary** of every Forge pipeline. A wrong format, flipped axis, or
silent 100× scale error renders wrong and fails visual QA. This skill owns the format decision,
the export command, the post-export validation, and the per-engine import recipe.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the target engine, coordinate system (Y-up/Z-up), scale unit, PBR workflow, and output paths
> that gate every decision below.
>
> **Windows headless truths:** EEVEE-Next is unsupported headless on Windows — use **Cycles** for
> any render-verify step. Blender CLI: `blender -b scene.blend -P script.py -- <args>` (the `--`
> separator is mandatory). Call `openscad.com` not `.exe`. Use `python` not `python3`. Absolute
> forward-slash paths in Blender `filepath` (never `//`). `--python-exit-code 1` so errors fail
> the process.

---

> **Forge suite — this skill's position:**
>
> | Upstream (produces source) | **forge-export** | Downstream (consumes output) |
> |---|---|---|
> | **forge-model**, **forge-parametric**, **forge-procedural** → geometry | → validates + exports | **forge-optimize** → web delivery |
> | **forge-material**, **forge-texture**, **forge-uv** → look-dev | → bundles materials | **atelier-webgl** → Three.js/R3F scene |
> | **forge-rig**, **forge-animate**, **forge-sim** → motion | → carries animation | Unreal / Unity / Godot runtime |
> | **forge-validate** (called here) | → gates every export | **forge-render** (verify PNG) |
>
> **Run = call the Skill tool.** Writing "next: forge-validate" in prose runs nothing.
> Every cross-skill handoff MUST be `Skill("forge-validate")`, `Skill("forge-optimize")`, etc.

---

## Decide first: pick the export format + tool

Before executing any export command, resolve three questions from FORGE.md (or ask explicitly):

1. **Target delivery** — web/Three.js, Unreal, Unity, Godot, AR/USDZ, print/STL, multi-DCC
   pipeline? See the format matrix below.
2. **Source type** — `.blend`, `.usdc`, `.fbx`, procedural bpy, OpenSCAD `.stl`?
3. **Tool availability** — verify Blender is on `PATH` before any Blender export. For USD tools
   verify `usdchecker`; for Assimp CLI verify `assimp version`.

**Format decision matrix (quick reference):**

| Target | Recommended format | Primary tool |
|---|---|---|
| Web / Three.js / R3F / atelier-webgl | **GLB** (binary glTF 2.0) | Blender bpy → forge-optimize |
| Unreal Engine 5.x | **FBX 2020** or **GLB** (Interchange) | Blender bpy |
| Unity 6 / URP / HDRP | **FBX** (AssetPostprocessor) or **GLB** (glTFast) | Blender bpy |
| Godot 4.3+ | **GLB** (headless `--import`) | Blender bpy |
| iOS AR / Quick Look | **USDZ** | `usdzip --arkitAsset` |
| Multi-DCC pipeline hub | **USDC** (binary crate) | `usd-core` pxr |
| Baked sim cache | **Alembic** (`.abc`) | Blender `wm.alembic_export` |
| 3D print | **STL** or **3MF** | Blender or assimp |
| CAD ingress | **STEP** → tessellate → GLB | FreeCAD CLI → assimp |
| Batch format conversion | assimp CLI (`glb2` format ID) | `assimp export` |

Full command-level detail: see **`references/format-matrix.md`** and **`references/blender-export.md`**.

---

## The flow

**1. Read FORGE.md** — load target engine, coordinate system, poly budget, output paths.
If absent, prompt for target engine and scale unit before continuing.

**2. Decide format + verify tool** (the gate — do not skip):
   - `blender --version` must succeed before any Blender export.
   - `python -c "from pxr import Usd"` before any USD authoring.
   - `assimp version` before any assimp batch conversion.
   - If a required tool is missing, surface the install path and halt. Per-tool install blocks:
     assimp → **`references/format-matrix.md`** §4; glTF-Validator + gltf-transform →
     **`references/gltf-validator.md`** §1/§7; USD (`usd-core` / NVIDIA prebuilt) →
     **`references/usd-pipeline.md`** §1; web-optimizer tools (KTX/gltfpack) live downstream in
     `forge-optimize`'s `references/install-windows.md`. Blender: install Blender 4.2 LTS to
     `C:\Program Files\Blender Foundation\Blender 4.2\` and add it to `PATH` (see
     `references/blender-export.md` §1 for the canonical binary path).

**3. Pre-export prep** (do only what the format needs):
   - glTF/GLB: confirm all materials are PBR metallic-roughness, not Principled BSDF with
     unsupported nodes. Non-color textures (ORM, normal) must be in Linear color space in Blender.
   - FBX → Unreal: confirm `axis_forward='-Z'`, `axis_up='Y'`; `apply_unit_scale=True`.
   - USD: set `defaultPrim`, `upAxis=Y`, `metersPerUnit`. Confirm all meshes have
     `subdivisionScheme=none` for hard-surface.
   - USDZ: geometry must be triangulated; textures PNG or JPEG only; no absolute file paths.

**4. Export** — choose the right bpy operator or CLI tool:
   - Blender GLB: `bpy.ops.export_scene.gltf(filepath=…, export_format='GLB', export_yup=True, export_apply=False)`
     Full parameter tables: **`references/blender-export.md`**.
   - Blender FBX: `bpy.ops.export_scene.fbx(filepath=…, axis_forward='-Z', axis_up='Y', apply_unit_scale=True)`
   - USD: `bpy.ops.wm.usd_export(filepath=…, generate_preview_surface=True, rename_uvmaps=True)`
   - Assimp batch: `assimp export "in.fbx" "out.glb" -fglb2 -tri -jiv -gsn -cts -fuv -icl`
   - USDZ: `usdzip --arkitAsset scene.usda out.usdz` then `usdchecker --arkit --strict out.usdz`
   - All scripts go in `.forge-build/out/` working dir; web handoff to `public/forge/<slug>-hero.glb`.

**5. Validate** — non-negotiable gate:
   - GLB: `gltf_validator.exe --stdout out.glb` — zero errors required before proceeding.
   - USDZ: `usdchecker --arkit --strict out.usdz`.
   - **Degrade, never skip:** if `gltf_validator`/`usdchecker` is absent, fall back to
     `gltf-transform validate out.glb` (Khronos spec; install per `references/gltf-validator.md`
     §7) and note the substitution in FORGE.md. Validation is never silently skipped.
   - Invoke `Skill("forge-validate")` for the full manifold/normals/poly-budget/render gate.

**6. Verify by render** — load the export into a FRESH scene and render one deterministic Cycles
   frame (EEVEE-Next is unsupported headless on Windows). Full copy-paste script + invocation:
   **`references/render-verify.md`** (mirrors forge-sim/export-cache.md §8).
   ```
   blender -b --python-exit-code 1 -P render_verify.py -- --in out.glb --out verify.png
   ```
   The script forces `render.engine='CYCLES'`, `cycles.device='CPU'`, a single fixed frame,
   `samples=32`, `seed=0` so re-verifies reproduce. **Guard before Read:** confirm `verify.png`
   exists and is **> 1 KB** (the script exits non-zero otherwise). Then `Read("verify.png")` to
   inspect visually. A missing / < 1 KB / all-black PNG = silent export failure (no geometry,
   dead material, or 100x scale) — fix the export and re-verify, not the verify script.

**7. Hand off** (if web delivery):
   - Run `Skill("forge-optimize")` → Draco+Meshopt+KTX2 → `public/forge/<slug>-hero.glb`.
     forge-optimize owns the final `Skill("atelier-webgl")` call that wires the asset into the
     Three.js/R3F scene — export produces and validates the GLB, then hands it down the chain.
   - Naming contract: `public/forge/<slug>-hero.glb` + `<slug>-hero-poster.webp`.
   - Poster (reduced-motion fallback) must be rendered BEFORE the GLB handoff.
   - **Boundary:** Forge's asset gate is **`forge-validate`**; the WEB-runtime gate
     (CWV/LCP/CLS/INP, DOM a11y / alt text) is **`atelier-perf-a11y`**'s job, run downstream after
     `Skill("atelier-webgl")` — do not duplicate or skip it here.

---

## Engine import recipes

### Unreal Engine 5.x
Full detail: **`references/engine-unreal.md`**

- **1 UU = 1 cm.** Always set `convert_scene_unit=True` at import or export at cm scale from Blender
  (`apply_unit_scale=True`).
- **Z-up left-handed.** Enable `convert_scene=True` at import (handles Blender's Z-up/RH).
- **Interchange API** (UE 5.4+) is preferred for GLB; legacy `FbxImportUI` still works for FBX.
- **Nanite**: enable at import for meshes > 10k tris, Opaque/Masked only — NOT translucent,
  NOT morph targets, NOT mobile targets.
- **FBX naming**: collision hulls `UCX_MeshName_00`, LOD suffixes `_LOD0`…`_LOD3` in the same FBX.
- **Headless import**: `UnrealEditor-Cmd.exe project.uproject -run=pythonscript -script=import.py -unattended -nullrhi`
- **sRGB flags**: BaseColor/Emissive ON; Normal/ORM/Roughness/Metallic/AO OFF — the #1 cause of
  wrong materials on import.

### Unity 6 (URP / HDRP)
Full detail: **`references/engine-unity.md`**

- **1 unit = 1 meter.** Enable `useFileUnits=true` + `bakeAxisConversion=true` in `ModelImporter`.
  `bakeAxisConversion` bakes the axis fix into vertex data (not a root Transform rotation), which
  avoids breaking physics raycasts and NavMesh.
- **ORM channel layout differs per pipeline:**
  - URP Metallic Map: R=Metallic, G=AO, B=unused, **A=Smoothness** (1−Roughness).
  - HDRP Mask Map: R=Metallic, G=AO, B=DetailMask, **A=Smoothness**.
  - glTF spec: R=AO, G=Roughness, B=Metallic. Interchange auto-remaps; FBX does not.
- **glTFast** (`com.unity.cloud.gltfast` 6.17) is the recommended runtime/editor glTF importer.
- Headless import: `Unity.exe -projectPath … -batchmode -quit -executeMethod MyClass.Method`
- **AssetPostprocessor** `GetVersion()` must be incremented on every logic change or reimport won't fire.

### Godot 4.3+
Full detail: **`references/engine-godot.md`**

- **Prefer GLB** (single file, no sidecar). Commit `.import` files; gitignore `.godot/imported/`.
- **Headless import**: `godot.exe --headless --import --path C:\Project` (4.3+ flag; blocks until done).
- **Known bug (4.4.x)**: `ERROR: Parameter "t" is null` during headless glTF import — non-fatal,
  import still completes. Fixed in 4.6 / 4.5.x (PR #109116).
- **ORM**: glTF spec layout (R=AO, G=Roughness, B=Metallic). ORM textures must import as linear
  (`flags/srgb=false` in the `.import` file).
- **Collision suffixes** on mesh node names: `-col` (trimesh+visible), `-colonly` (trimesh+invisible),
  `-convcol` (convex+visible), `-convcolonly` (convex+invisible). Note: suffix applies to the *node*
  name, not the mesh data name (open bug #115869 as of 2026).
- **LOD**: set `meshes/generate_lods=true` in `.import` (uses meshoptimizer, zero runtime cost).
- **Normal maps**: Godot uses OpenGL convention (Y+ = up). Substance Painter default is OpenGL.
  DirectX normals (Y+ = down) must have the green channel inverted before import.

---

## Operating principles

- **Format before execution.** Pick the right format for the target — then choose the right tool.
  GLB is the runtime hub; USDC is the pipeline hub; FBX is the DCC-to-engine legacy path.
  Never default to FBX when the target accepts GLB.
- **Gate at validation, not at guesswork.** Run `gltf_validator` (zero errors) and
  `Skill("forge-validate")` before declaring an export done. A file that passes the validator
  but renders blank has a material or lighting problem — verify by render.
- **Coordinate system is a first-class concern.** glTF = Y-up right-handed meters. Unreal = Z-up
  left-handed cm. Unity = Y-up left-handed meters. Godot = Y-up right-handed meters. Every
  export command must address the axis and unit explicitly — never rely on defaults.
- **Scripts, not inline code.** The `blender -b -P script.py -- args` invocation pattern lives in
  a file; do not paste multi-line Python into `--python-expr` for anything beyond trivial one-liners
  (the model pre-evaluates `$()` in SKILL.md code blocks — real logic belongs in scripts).
- **Run = call the Skill tool.** Saying "now run forge-optimize" in prose runs nothing.
  This skill's direct handoffs are `Skill("forge-validate")` (the gate) and `Skill("forge-optimize")`
  (web delivery); forge-optimize makes the final `Skill("atelier-webgl")` call — do not call it here.
