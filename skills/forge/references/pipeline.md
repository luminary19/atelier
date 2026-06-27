# Forge Pipeline — Full Sequence Reference

> This file documents the ordered pipeline for every major Forge workflow. The `forge` router reasons
> over these to decide the shortest pipeline that moves a project forward.

---

# Contents
- §1. New asset — full production pipeline
- §2. Web delivery — 3D hero for Atelier/R3F
- §3. Geometry-only pipeline
- §4. Look-dev pipeline
- §5. Rig + animation pipeline
- §6. Photogrammetry / AI intake pipeline
- §7. Print pipeline
- §8. Forge ↔ Atelier integration seam

---

## §1. New asset — full production pipeline

Invoke for: "build a [thing] for [engine]", "I need a 3D hero for this website", orchestration by `forge-director`.

```
/forge init          → writes FORGE.md (target engine, coord system, budgets, render settings)
  ↓
Skill(forge-brief)   → defines asset spec in FORGE.md; extracts ATELIER.md aesthetic if present
  ↓
Skill(forge-standards) → writes budget thresholds; confirms scale/pivot/naming
  ↓
[MODELING — pick one path]
  Organic / hard-surface:  Skill(forge-model)
  Toleranced / print:      Skill(forge-parametric)
  Generative / scatter:    Skill(forge-procedural)
  ↓ (all paths converge here)
Skill(forge-topology)    → retopo if needed; LOD generation; boolean cleanup
Skill(forge-uv)          → unwrap, pack, set texel density
  ↓
[LOOK-DEV]
Skill(forge-material)    → PBR material graph, Principled BSDF, glTF extension wiring
Skill(forge-texture)     → bake normal/AO/curvature/displacement maps
Skill(forge-light)       → lighting rig + HDRI/IBL + color management (AgX)
Skill(forge-render)      → headless Cycles render → Read PNG → critique → fix loop
  ↓
[RIG / ANIM — if animated]
Skill(forge-rig)         → armature, IK/FK, weights, blend shapes
Skill(forge-animate)     → keyframes, F-curves, NLA bake
Skill(forge-sim)         → cloth/rigid/particles if needed → bake → export
  ↓
Skill(forge-validate)    → manifold, normals, scale, polycount, UV overlap, glTF-Validator, render QA
  ↓
[EXPORT]
Skill(forge-export)      → GLB/USD/FBX/USDZ + engine import conventions
Skill(forge-optimize)    → DRACO+Meshopt+quantize; KTX2 textures if web
  ↓
[WEB DELIVERY — if target is three.js/R3F]
Skill(atelier-webgl)     → R3F ForgeScene + HeroPoster wiring, reduced-motion fallback, perf-a11y gate
```

---

## §2. Web delivery — 3D hero for Atelier/R3F

Invoke for: `/forge handoff`, `/forge to-web`, or any Atelier Award-grade signature moment.

**Prerequisites:** ATELIER.md present; FORGE.md written; asset validated.

```
# Build the fallback FIRST (poster rule)
Skill(forge-render)
  → engine: CYCLES, samples: 64, resolution: 1920×1080
  → output: public/forge/<slug>-hero-poster.png
  → Read PNG → confirm composition matches Direction Doc signature moment

# Convert poster for web delivery (ImageMagick)
magick convert public/forge/<slug>-hero-poster.png -quality 85 public/forge/<slug>-hero-poster.webp

# Export GLB with DRACO
Skill(forge-export)
  → bpy.ops.export_scene.gltf(filepath=..., export_draco_mesh_compression_enable=True, ...)
  → output: .forge-build/out/<slug>-hero-raw.glb

# Compress further with gltf-transform (Meshopt + quantize)
Skill(forge-optimize)
  → npx gltf-transform optimize <slug>-hero-raw.glb public/forge/<slug>-hero.glb --meshopt --quantize
  → [if texture-heavy] add: --texture-compress ktx2  (requires toktx in PATH)

# Write FORGE.md §Forge 3D assets block
# (file paths, sizes, scene description, DRACO decoder path)

# Hand to Atelier
Skill(atelier-webgl)
  → receives: GLB path + poster WebP path + scene description string
  → wires: ForgeScene + HeroPoster, lazy-load, reduced-motion, DRACO /draco/ decoder
  → runs: atelier-perf-a11y gate (LCP/CLS/INP + a11y)
```

**Asset naming contract:**
```
public/forge/<slug>-hero.glb           ← DRACO+Meshopt compressed GLB
public/forge/<slug>-hero-poster.png    ← full-res render
public/forge/<slug>-hero-poster.webp   ← compressed poster (web delivery + fallback)
```

**Size targets:**
- GLB < 5 MB (ideally < 2 MB with DRACO+Meshopt)
- Poster WebP < 300 KB at 1920 px wide

---

## §3. Geometry-only pipeline

Invoke for: "just model this mesh", "retopologize this", "unwrap UV only".

```
Skill(forge-model | forge-parametric | forge-procedural)  ← pick one
  ↓
[optional] Skill(forge-topology)    ← if retopo or LOD needed
[optional] Skill(forge-uv)          ← if UVs required
  ↓
Skill(forge-validate)               ← manifold, normals, polycount gate
  ↓
Skill(forge-export)                 ← GLB/OBJ/STL as appropriate
```

---

## §4. Look-dev pipeline

Invoke for: "shade this model", "add PBR materials", "bake textures", "set up lighting".

```
Skill(forge-material)   ← PBR material graph; Principled BSDF; glTF extensions
  ↓
Skill(forge-texture)    ← bake: normal / AO / curvature / displacement / albedo
  ↓
Skill(forge-light)      ← lighting rig + HDRI/IBL + AgX color management
  ↓
Skill(forge-render)     ← Cycles headless beauty render → Read PNG → critique → fix
  ↓
Skill(forge-validate)   ← texture color space, glTF material check, render QA
```

---

## §5. Rig + animation pipeline

Invoke for: "rig this character", "add keyframe animation", "sim cloth and bake", "export animated GLB".

```
Skill(forge-rig)       ← armature hierarchy, IK/FK, weight paint, blend shapes
  ↓
Skill(forge-animate)   ← keyframes, F-curves, NLA clips, loop (Cycles modifier)
  [optional]
Skill(forge-sim)       ← cloth/fluid/particles — bake — bake to keyframes for export
  ↓
Skill(forge-validate)  ← rig deformation check, weight normalization, blend shape sanity
  ↓
Skill(forge-export)    ← animated GLB / FBX / USD SkelAnimation
```

---

## §6. Photogrammetry / AI intake pipeline

Invoke for: "clean up this photogrammetry scan", "import a NeRF", "use AI to generate a mesh".

```
Skill(forge-intake)    ← photogrammetry (RealityCapture/Meshroom) / Gaussian splat / AI text-to-3D
  → produces raw mesh (.ply / .obj / .glb)
  ↓
Skill(forge-topology)  ← decimate, retopo, boolean cleanup
Skill(forge-uv)        ← unwrap for bake
Skill(forge-texture)   ← bake from raw to retopo target
  ↓
Skill(forge-validate)  ← production-ready gate
  ↓
Skill(forge-export)    ← final format
```

---

## §7. Print pipeline

Invoke for: "design a part for 3D printing", "export STL", "watertight mesh for FDM".

```
Skill(forge-parametric)   ← OpenSCAD / CadQuery / Build123d solid model
  [or]
Skill(forge-model)        ← bpy modeling → ensure manifold/watertight
  ↓
Skill(forge-topology)     ← wall thickness check, boolean union for watertight
Skill(forge-validate)     ← manifold, watertight, printability checks (min wall, overhangs)
  ↓
Skill(forge-export)       ← STL or 3MF export
  → openscad.com -o model.stl  (use openscad.com not openscad.exe — com variant is headless-safe)
```

---

## §8. Forge ↔ Atelier integration seam

### When Atelier routes to Forge

`atelier` router dispatch table includes:
```
forge | blender | model | mesh | geometry | render | glb | look-dev | hdri → Skill(forge)
```

`atelier-webgl` escalates to Forge when:
- ATELIER.md Interactivity = Award-grade AND signature moment requires authored geometry.
- The model cannot be procedurally generated in GLSL/TSL.

### When Forge routes back to Atelier

After `forge-optimize` delivers the compressed GLB + poster:
```
Skill(atelier-webgl)   ← wires R3F ForgeScene, lazy-load, fallback, DRACO decoder
  ↓
atelier-perf-a11y      ← LCP/CLS/INP/a11y gate (web-runtime gate; NOT Forge's gate)
```

### Data flow at the seam

```
ATELIER.md (Forge reads):
  Interactivity: Award-grade     → sanctioned to build authored 3D
  Aesthetic: dark-tech           → forge-material uses matte/brushed metal + dark env
  Signature moment: "hero orb"  → forge-brief sets asset spec
  OKLCH primary H: 264.5         → forge-material harmonizes base color hue

FORGE.md § Forge 3D assets (Atelier reads):
  GLB: public/forge/hero-hero.glb
  Poster: public/forge/hero-hero-poster.webp
  Scene description: "brushed titanium orb suspended in dark space"
  DRACO decoder path: /draco/
```
