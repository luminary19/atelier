---
name: forge-material
version: 1.0.0
description: >
  Forge suite — PBR shading, glTF material model, and Blender Principled BSDF authoring (the
  lookdev layer). Produces verified Blender materials and glTF-export-ready (round-trip-checked)
  node graphs with correct metal/rough maps, ORM channel packing, normal maps, and glTF KHR
  extension wiring — the shipping GLB itself is emitted by forge-export — then
  renders to PNG for visual QA via Cycles headless. Use whenever authoring or debugging PBR
  materials, setting metallic/roughness/IOR/clearcoat/transmission/sheen/anisotropy, building
  Principled BSDF node graphs in Python (bpy), packing ORM textures, exporting glTF/GLB with
  correct material settings, wiring KHR_materials_clearcoat / KHR_materials_transmission /
  KHR_materials_volume / KHR_materials_emissive_strength / KHR_materials_anisotropy /
  KHR_materials_iridescence, converting DirectX to OpenGL normal maps, diagnosing sRGB/non-color
  space errors, validating glTF material output with gltf-validator, or understanding the
  Blender→glTF Principled BSDF mapping table. HEADLESS-ONLY: driven from code, output verified
  by reading a PNG. Part of the Forge suite.
triggers:
  - pbr material
  - metallic roughness
  - principled bsdf
  - blender material python
  - gltf material
  - orm texture
  - channel packing
  - normal map blender
  - clearcoat blender
  - transmission glass blender
  - khr_materials
  - iridescence gltf
  - anisotropy gltf
  - forge-material
  - lookdev blender
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge — PBR Materials & glTF Shading

The lookdev layer. A correctly authored PBR material graph is the prerequisite for every Forge
render-check and for clean glTF export. The discipline: **glTF metallic-roughness is the
interchange truth — every material authored in Blender's Principled BSDF must survive the
Blender→glTF export mapping without loss of intent.**

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the PBR workflow (metallic-roughness vs spec-gloss), ORM channel-packing policy, texel density
> budget, target engine, and verified output paths. When **`ATELIER.md`** also exists, extract the
> aesthetic direction and primary OKLCH hue before choosing material presets.

---

> **Suite map — where this skill fits:**
>
> Upstream: **forge-uv** (UV layout required before any map can be applied) · **forge-texture**
> (baked normal/AO/curvature/displacement maps arrive here as inputs)
>
> Downstream: **forge-render** (consumes the material-complete .blend for headless Cycles renders)
> · **forge-export** (Blender→glTF pipeline; material node topology must match the export
> whitelist) · **forge-validate** (material schema QA: gltf-validator, colorspace checks,
> anisotropy tangent verification)
>
> Sibling: **forge-light** (HDRI/IBL wiring needed to evaluate material quality) · **forge-data**
> (BM25 lookup for roughness presets, IOR values, F0 reference tables)
>
> Atelier seam: **atelier-webgl** (Three.js `MeshStandardMaterial` / `MeshPhysicalMaterial`
> implement the same metal/rough model; GLB produced here is consumed there via `GLTFLoader`)
> · **atelier-direction** (art-direction sets metallic vs dielectric, roughness register, coat
> presence — read it before choosing presets)
>
> **Run = call the Skill tool with the exact name. Narrating "now run forge-render" runs nothing.**

---

## Decide first: tool + availability

Before writing any material code, verify Blender is present:

```powershell
# PowerShell — check Blender availability (do NOT run headlessly if missing)
$blender = Get-Command blender -ErrorAction SilentlyContinue
if (-not $blender) {
    Write-Error "Blender not found in PATH. Install via: winget install BlenderFoundation.Blender"
    exit 1
}
blender --version
```

If Blender is absent, stop and report. Do not attempt a material workflow without it.

**Engine gate:** Headless rendering of materials uses **Cycles** (CPU fallback). EEVEE Next is
unsupported headless on Windows. EEVEE-based material checks run only inside the Blender GUI.
All scripts in this skill target Cycles; the EEVEE `surface_render_method` API is noted for
reference only.

**Workflow gate:** Always use **metallic-roughness** (glTF core). Avoid spec-gloss for new work
(KHR_materials_pbrSpecularGlossiness was archived 2021; deprecated in Three.js r147).

---

## The flow

1. **Read FORGE.md** → confirm PBR workflow, ORM policy, target engine, output paths.

2. **Decide material complexity** (choose one):
   - **Solid / constant** — no textures, scalar BSDF inputs only → skip to step 4.
   - **Textured / ORM** — albedo + ORM (AO/rough/metal packed) + normal → steps 3–5.
   - **Advanced** — clearcoat, transmission, volume, sheen, anisotropy, iridescence → step 6.

3. **Verify / prepare maps** (textured path):
   - All maps must be authored before material wiring. Check they exist on disk.
   - Confirm color-space assignment: albedo/emission → sRGB; ORM/normal/height → Non-Color.
   - Verify ORM channel layout (R=AO, G=Roughness, B=Metallic — glTF convention).
   - Full color-space table and DX→GL normal flip: **`references/pbr-theory.md`** §§3–4.

4. **Build the Principled BSDF node graph via Python (bpy)**:
   - Use socket names, never numeric indices (names changed in Blender 4.0 OpenPBR rewrite).
   - Set `bsdf.distribution = 'MULTI_GGX'` (energy-conserving; prevents dark rough metals).
   - Wire ORM via `ShaderNodeSeparateColor` (4.2+) G→Roughness, B→Metallic.
   - Normal map requires: `Image Texture → ShaderNodeNormalMap (space='TANGENT') → BSDF.Normal`.
   - Wire AO to `glTF Material Output.Occlusion` node group (not to BSDF directly).
   - Full commented build script: **`references/bpy-material-scripts.md`** §1.

5. **Verify glTF export compatibility** (a *round-trip QA check*, not the production export —
   **forge-export owns the egress**; see step 8b):
   - Only Principled BSDF node topology is exported; all other BSDF nodes are silently dropped.
   - Procedural nodes (Noise, Voronoi, ColorRamp chains) are dropped — bake to image first.
   - UV mapping: use `ShaderNodeMapping` with `vector_type = 'POINT'` for `KHR_texture_transform`.
   - The inline `export_scene.gltf` here exists only to confirm the material survives the export
     whitelist — keep it scoped to QA; the canonical production GLB is produced by `forge-export`.
   - Full export support/drop table: **`references/gltf-export-mapping.md`** §§1–2.

6. **Wire advanced extensions** (when FORGE.md or brief specifies):
   - Clearcoat / car paint → `Coat Weight` + `Coat Roughness` + `Coat Normal` input sockets.
   - Transmission (thin glass) → `Transmission Weight` (>=0) → `KHR_materials_transmission`.
   - Volume (thick glass, amber) → combine with `KHR_materials_volume`; mesh must be manifold.
   - Sheen (cloth, velvet) → `Sheen Weight` + `Sheen Roughness` + `Sheen Tint` sockets.
   - Anisotropy (brushed metal) → `Anisotropic` + `Anisotropic Rotation`; requires TANGENT attribute.
   - Iridescence (soap bubble, oil slick) → `KHR_materials_iridescence` JSON params.
   - Emissive HDR bloom → `Emission Strength > 1.0` → `KHR_materials_emissive_strength`.
   - Extension JSON schemas and Three.js mappings: **`references/gltf-extensions.md`**.

7. **Headless Cycles render for visual QA**:
   - Invoke `forge-render` for the full headless render loop.
   - For a quick material-only check (sphere preview): use the script in
     **`references/bpy-material-scripts.md`** §2 (pbr_material_setup.py pattern).
   - Invocation pattern: `blender --background --python script.py -- <args>` (the `--` is mandatory).
   - After render: `Read` the PNG. For the numeric gate, don't hand-compute a mean — run the
     battle-tested Pillow checks `check_luminance_range` + `check_no_clipping` from
     **`Skill("forge-light")` references/color-management-qa.md §2** on the preview PNG:
     mean <0.02 = failed material/lighting, >0.98 = overexposed, near-zero variance = uniform
     (material not active). The local `verify()` in `references/bpy-material-scripts.md` §2 is a
     standalone fallback when forge-light is not loaded.
   - Run = call `Skill("forge-render")` for full turntable + contact-sheet QA.

8. **Validate the round-trip GLB** (material-survival check, not the shipping artifact):
   - Run `gltf-validator` (Khronos CLI) on the QA .glb to confirm the material round-trips.
   - Run `npx gltf-transform inspect` for quick material/extension audit.
   - For anisotropy: verify TANGENT attribute present (`gltf-validator` flags missing tangents).
   - For volume: verify mesh is manifold (open-mesh + volume = undefined behavior in engines).
   - Run = call `Skill("forge-validate")` for the full gate.

8b. **Hand the production GLB to forge-export** (the egress boundary):
   - forge-material verifies only that the material *survives* the glTF export whitelist; it does
     not own the shipping export. For the canonical GLB, `Skill("forge-export")` — it owns the
     format matrix, axis/unit handling, Draco/Meshopt flags, and per-engine import recipes
     (Unreal/Unity/Godot/Three.js). Pass it the material-complete .blend and the verified node
     topology; forge-export emits the egress artifact (and on a web handoff, the
     `public/forge/<slug>-hero.glb` consumed by atelier-webgl).
   - Run = call `Skill("forge-export")`.

9. **Fix → re-render loop** until visual check passes:
   - Wrong color space → fix `img.colorspace_settings.name`; re-render.
   - Bumps inverted (DX normal on GL engine) → flip G channel (script in `references/pbr-theory.md` §3.9).
   - Anisotropy noise → normalize only RG channels as 2D vector (B = strength, not direction).
   - Metallic gray values (not 0/1) → threshold map (script in `references/pbr-theory.md` §5).
   - Full gotcha→fix table: **`references/pbr-theory.md`** §5, **`references/gltf-export-mapping.md`** §3.

---

## Quick-reference: Principled BSDF 4.x socket names

Socket names changed in Blender 4.0 (OpenPBR rewrite). Use these names; never numeric indices.

| Old (3.x) name    | New (4.x) name          | Range / Default |
|-------------------|-------------------------|-----------------|
| `Specular`        | `Specular IOR Level`    | 0–1, default 0.5 |
| `Clearcoat`       | `Coat Weight`           | 0–1 |
| `Clearcoat Roughness` | `Coat Roughness`    | 0–1 |
| `Transmission`    | `Transmission Weight`   | 0–1 |
| `Subsurface`      | `Subsurface Weight`     | 0–1 |
| `Emission`        | `Emission Color`        | RGBA |

Full socket index table (0–27): **`references/bpy-material-scripts.md`** §3.

---

## Key material rules (memorize these)

- **Base color — never bake lighting in.** Albedo should be flat, shadow-free. Clamp non-metals
  to sRGB [30, 240]; metal albedo encodes the specular tint (F0 color), not diffuse.
- **Metallic — binary 0 or 1 only.** Intermediate values (0.1–0.9) are physically implausible;
  allow at most a 2–3 px transition zone at metal/non-metal boundaries.
- **Roughness ranges.** Polished metal: 0.05–0.2; brushed metal: 0.3–0.5; plastic: 0.3–0.5;
  concrete/rubber: 0.85–0.95. Never author pure 0.0 or 1.0 for real materials.
- **ORM must be PNG, not JPEG.** JPEG chroma subsampling corrupts the metallic and roughness
  channels. Use lossless PNG for ORM; JPEG only for albedo when filesize is critical.
- **Transmission + alphaMode.** Glass: `alphaMode = OPAQUE` + `transmission > 0`. Do NOT use
  `BLEND` + transmission — undefined behavior in most engines.

IOR and F0 reference tables (metals + dielectrics): **`references/pbr-theory.md`** §2.

---

## Operating principles

- **glTF is the interchange truth.** Design every Principled BSDF graph to survive the export
  mapping. Bake anything the glTF exporter cannot understand (procedurals, displacement, SSS)
  before claiming the material is done.
- **Color space is load-bearing.** Set it explicitly on every image node immediately after load;
  never rely on Blender's auto-detection. Wrong color space on a roughness map silently corrupts
  every render and every export.
- **MULTI_GGX always.** Set `bsdf.distribution = 'MULTI_GGX'` in every scripted material.
  Plain GGX loses energy at high roughness, making rough metals artificially dark — a common,
  subtle, and hard-to-diagnose error.
- **Verify by rendering.** No material is done until a Cycles render has been read back as a PNG
  and visually inspected. The minimum gate is the reusable Pillow checks (`check_luminance_range`
  / `check_no_clipping`) in `Skill("forge-light")` references/color-management-qa.md §2 — run them
  rather than eyeballing or hand-computing a mean; `forge-render` turntable is the full gate.
- **forge-export owns the egress.** forge-material's own `export_scene.gltf` is a *round-trip QA
  check* — it proves the material survives the glTF whitelist, nothing more. The shipping GLB
  (format matrix, axis/unit handling, Draco/Meshopt, per-engine recipes) is produced by
  `Skill("forge-export")`. Never treat this skill's QA export as the canonical egress artifact.
- **Run = call the Skill tool.** Invoking `forge-render`, `forge-validate`, or `forge-export`
  means calling `Skill("forge-render")` / `Skill("forge-validate")` / `Skill("forge-export")`
  with the Skill tool. Writing the name in prose runs nothing — this is the exact failure mode
  documented in the Forge suite.
