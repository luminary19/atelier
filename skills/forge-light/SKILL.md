---
name: forge-light
version: 1.0.0
description: >
  Forge suite — lighting rigs, HDRI/IBL, and color management for headless 3D renders.
  Delivers studio-quality, physically-correct lighting setups (three-point area-light rigs,
  IBL/HDRI world environments, turntable/catalog rigs, shadow catchers, cycloramas, and
  light linking) plus truthful color management (AgX/ACES/OCIO, texture color-space tagging,
  false-color QA). Use whenever setting up lights for a Blender scene, choosing a view
  transform (AgX vs ACES vs Standard), wiring an HDRI environment texture, configuring
  color management for a render, fixing blown-out or washed-out renders, or verifying
  exposure with a false-color pass. Covers: "light the scene", "add a three-point rig",
  "studio lighting", "HDRI setup", "IBL", "PolyHaven HDRI", "shadow catcher",
  "rim light", "AgX tone mapping", "ACES pipeline", "OCIO config", "color space",
  "Non-Color texture", "exposure stops", "false color pass", "color management mismatch".
  HEADLESS-ONLY: driven from code, output verified by reading a PNG. Part of the Forge suite.
triggers:
  - lighting rig
  - three-point light
  - hdri setup
  - ibl
  - agx
  - aces pipeline
  - ocio
  - color management
  - shadow catcher
  - view transform
  - false color pass
  - texture color space
  - studio lighting blender
  - polyhaven hdri
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# forge-light — Lighting Rigs & Color Management

The rendering pipeline's truthfulness depends entirely on this skill: wrong lights produce
misleading material reads; wrong color management corrupts pixel values the QA loop uses
to pass or fail. Get both right before dispatching a single render.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the established render engine (`Cycles` headless default on Windows), color view transform
> (`AgX` default for 4.x), output paths, and any per-project lighting notes. When `ATELIER.md`
> is also present, its `world` / `aesthetic` field sets the lighting mood (warm/cool,
> hard/soft, high-key/low-key) that governs parameter choices here.

---

> **Forge suite map**
>
> This skill sits in the **lookdev** pipeline alongside **`forge-material`** (PBR shading,
> Principled→glTF mapping) and **`forge-texture`** (baking, procedural maps). It is called
> **before** **`forge-render`** (headless Cycles/Workbench dispatch, turntable frames, contact
> sheet QA) — lighting must be configured before render dispatch. Geometry input comes from
> **`forge-model`**, **`forge-parametric`**, or **`forge-procedural`**. The full validation
> gate is **`forge-validate`** (manifold, normals, UV, glTF-Validator, render-QA escalation).
> For web delivery, **`forge-optimize`** handles DRACO/Meshopt/KTX2 compression and the
> **`atelier-webgl`** handoff.
>
> Run any other Forge skill = call the Skill tool with its exact name. Writing "now run
> forge-render" in prose runs nothing — **Run = call `Skill("forge-render")`**.

---

## Decide first: rig type and color pipeline

Before touching bpy, resolve these two gates. Read FORGE.md; if absent, ask or infer from context.

**Gate A — Lighting rig**

| Intent | Rig to build |
|---|---|
| Hero / packshot / editorial | Three-point area-light rig (§2) |
| Material QA / catalog / turntable | HDRI-only + kicker (§3) |
| Clean transparent bg with contact shadow | Shadow catcher + area lights (§4) |
| Cyclorama / infinite white | Cyclorama + key/fill (§4) |
| Complex multi-object / render farm | Light linking (§5) |

**Gate B — Color pipeline**

| Need | Setting |
|---|---|
| Standard product / web QA (default) | AgX, sRGB display, exposure 0.0 |
| Wide-gamut / studio deliverable | ACES CG config via OCIO env var |
| Game-engine / no tone-map export | Standard (no view transform) |
| Exposure verification only | False Color pass |

**Verify Blender is available before any render attempt** (same preflight the other lookdev
skills use):
```
python "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts/preflight.py" --tools blender,python --json
```
If `all_found` is false (or `blender` is listed in `missing`), stop and instruct installation;
`blender_path` gives the resolved `blender.exe` for the invocation below. Reference:
`references/blender-invocation.md`.

---

## The flow

**1. Read FORGE.md** (or gather scene constraints: bounding sphere, target engine, output path).

**2. Decide rig + color pipeline** (Gate A + B above). If ATELIER.md is present, map its aesthetic to
   lighting parameters using `references/lighting-presets.md §1`.

**3. Build the bpy lighting script.**
   - Compute bounding sphere first — all rig distances are multiples of radius.
     Full helpers + three-point builder: `references/three-point-rig.md`.
   - For HDRI/IBL: wire the world node graph with rotation control and optional packshot mode.
     Full HDRI node setup + PolyHaven download: `references/hdri-ibl.md`.
   - For shadow catcher / cyclorama: `references/shadow-catcher.md`.
   - For light linking (Cycles 4.0+): `references/light-linking.md`.
   - For turntable catalog rig: `references/turntable-catalog.md`.

**4. Configure color management** in the same script.
   - Always set `view_transform`, `display_device`, `exposure`, and `gamma` explicitly.
   - Always set `gamma = 1.0` — loaded `.blend` files may have non-default gamma.
   - Tag texture color spaces on load (`Non-Color` for data maps; `sRGB` for albedo/emissive).
   - Use `image.save_render()`, not `image.save()`, for display-ready PNG output.
   - Full bpy color management API + OCIO details: `references/color-management.md`.

**5. Write and invoke the Blender script headlessly (Windows PowerShell):**

```powershell
# Mandatory: -b BEFORE -P; user args AFTER the -- separator
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b --factory-startup `
    -P "C:\forge\scripts\light_and_render.py" `
    -- "C:\assets\widget.glb" "C:\renders\widget_hero.png"
```

   Gotcha: `--factory-startup` strips GPU device preferences. Re-apply GPU in script.
   Always use forward-slash paths in `bpy.data.images.load()` — use `Path(...).as_posix()`.
   Full invocation reference + GPU device flags: `references/blender-invocation.md`.

**6. Verify render output.**
   After render: confirm file exists and size > 1 KB, then `Read` the PNG to visually inspect:
   - Product centred and fully in frame
   - No pure-black areas outside the product (lights hitting the object)
   - Shadow visible beneath product if shadow catcher is in use
   - No fireflies (white single-pixel spikes → insufficient samples)

**7. Optional: False Color QA pass.**
   For exposure verification, run a False Color render before the production render.
   Middle gray (scene-linear 0.18) should appear as the "Gray" band (~RGB 128,128,128
   in the false color output). See `references/color-management.md §4` (False Color QA pass)
   and `references/color-management-qa.md` for the programmatic pixel checks.

**8. Hand off to render dispatch.**
   When lighting and color management are confirmed correct, invoke `Skill("forge-render")`
   for full turntable / contact-sheet production. Pass the configured scene path and output dir.

---

## Key parameters at a glance

### Three-point ratios (proven for product)

```
Key : Fill : Rim  =  1.0 : 0.35 : 0.60
```

- Key: 45° azimuth, 30° elevation — primary shadow definition
- Fill: opposite azimuth, 20° elevation — prevents shadow side going > 2 EV darker
- Rim: directly behind product (180° from camera), 60° elevation — edge separation

All distances are `radius × 3.0`; all sizes are `radius × multiplier`. Full Python builder
with Kelvin→linear conversion: `references/three-point-rig.md`.

### Light units (bpy)

| Light Type | `light.energy` unit | Typical range (30 cm product) |
|---|---|---|
| `AreaLight` | Watts (W) — total radiant power | 200–2000 W |
| `SunLight` | W/m² (irradiance) | 5–20 W/m² |
| `PointLight` | Watts (W) | 100–1000 W |
| `SpotLight` | Watts (W) | 200–1500 W |
| World Background | Dimensionless multiplier on HDRI | 0.5–2.0 |

`AreaLight.normalize = True` (default in 4.5): resizing keeps total Watts constant;
bigger panel = softer shadows, same energy. To add both softness AND brightness,
increase `energy_w` proportionally.

### HDRI resolution guide

| Use case | Resolution |
|---|---|
| Quick QA / batch | 1K |
| Standard product | 2K |
| Hero / marketing | 4K |
| Jewellery / gem (tight specular) | 4K–8K |

### Color management quick-reference

| Texture type | Color space tag |
|---|---|
| Albedo, emissive, AO (color) | `sRGB` |
| Normal, roughness, metallic, displacement | `Non-Color` |
| HDRI / EXR environment | `Linear` (or `Linear Rec.709`) |
| Data bake output | `Non-Color` |

View transform defaults: `AgX` (Blender 4.0+); `Standard` for game-engine exports; EXRs
store raw scene-linear (no view transform applied on save).

### Cycles sample budget

| Scenario | Samples | Denoiser |
|---|---|---|
| QA / iteration | 64–128 | OPENIMAGEDENOISE |
| Final product | 256 | OPENIMAGEDENOISE |
| Glass / caustics | 512–1024 | OPENIMAGEDENOISE |
| Hero shot | 1024 | OPENIMAGEDENOISE + Albedo pass |

---

## Critical gotchas (quick reference)

| # | Symptom | Fix |
|---|---|---|
| L-G1 | Blown-out or flat render → HDRI wrong colorspace | `n_env.image.colorspace_settings.name = 'Linear Rec.709'` (try `'Linear'` if it raises ValueError; see `enumerate_colorspaces()` in `references/hdri-ibl.md`) |
| L-G2 | Light linking poll error | Set `bpy.context.view_layer.objects.active = emitter_obj` first |
| L-G3 | `bpy.context` unavailable in batch | Use `bpy.data.scenes[0]` instead of `bpy.context.scene` |
| L-G4 | GPU not used after `--factory-startup` | Re-apply `prefs.compute_device_type = 'OPTIX'` in script |
| L-G5 | Bigger softbox makes scene darker | Set `light_data.normalize = False` or increase `energy_w` |
| L-G6 | Shadow catcher adds colour cast | Set `plane.visible_diffuse = False` on catcher plane |
| L-G7 | Backslash path in `bpy.data.images.load()` | Use `Path(...).as_posix()` or forward slashes |
| L-G8 | Transparent PNG renders black | `film_transparent = True` REQUIRES `color_mode = 'RGBA'` |
| L-G9 | Light linking 10× slower | `scene.cycles.use_light_tree = True` (verify; default True 4.x) |
| C-G1 | Normal map → faceted/triangulated surface | Tag `Non-Color`, not `sRGB` |
| C-G2 | Double AgX: re-imported PNG looks washed | Tag re-imported render PNGs as `Non-Color` |
| C-G3 | `bpy.ops.image.save_as` fails headless | Use `image.save_render(filepath=..., scene=scene)` |
| C-G4 | OCIO env var ignored by Blender | Set `$env:OCIO` in the SAME PowerShell session before launch |
| C-G5 | Filmic still active in old `.blend` | Always set `view_transform = "AgX"` explicitly in script |

Full reproduce/fix snippets live in the per-topic references: lighting gotchas in
**`references/shadow-catcher.md §4`** (transparent-PNG black, colour cast, light-tree,
`is_shadow_catcher` flag, factory-startup GPU) and **`references/light-linking.md §4`**
(poll error, slow convergence, EEVEE-ignored); colour gotchas in
**`references/color-management.md §7`** (+ Three.js/QA in `references/color-management-qa.md`).

---

## Operating principles

- **Compute the bounding sphere first.** Every rig parameter (distance, size, energy) is a
  multiple of object radius. Never hard-code light positions in absolute world units.
- **HDRI colorspace must be scene-linear, not `sRGB`.** Use `'Linear Rec.709'` (the canonical
  name in Blender 4.x's default OCIO config; fall back to `'Linear'` if it raises ValueError, or
  call `enumerate_colorspaces()` from `references/hdri-ibl.md`). An HDRI loaded as `sRGB` is the
  single most common cause of blown-out or flat renders. Verify it on every HDRI load call.
- **Set all color management properties explicitly in every script.** Never rely on `.blend`
  file defaults for `view_transform`, `gamma`, or `exposure` — a saved file from an old
  Blender version will carry wrong values.
- **Use `save_render()`, not `save()`.** Only `save_render()` bakes the view transform into
  a PNG. `save()` writes raw scene-linear data and will look wrong in any image viewer.
- **Verify with a read, not just a file-size check.** After rendering, `Read` the PNG to
  visually confirm exposure, shadow presence, and absence of fireflies before reporting success.
