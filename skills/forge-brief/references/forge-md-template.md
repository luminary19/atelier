# FORGE.md — Annotated Template & Per-Engine Examples

## Contents
- §1. Full annotated schema (incl. `## Determinism`)
- §2. Example: web hero (three.js / R3F)
- §3. Example: Unreal Engine 5 prop
- §4. Example: print / CAD part
- §5. Example: render-only (no engine export)
- §6. Minimal viable FORGE.md (quick-start)

> **Determinism is a first-class section.** FORGE_PLAN §A mandates "idempotent rebuilds; seeded
> randomness," and the forge-validate render-compare QA needs a stable baseline. Every FORGE.md —
> schema, every example below, and the quick-start — carries a `## Determinism` block so a rebuild
> in a later session reuses the same seed and sample counts and the render-compare cannot silently
> drift. The machine-readable mirror is the `"seed"` key in FORGE_STANDARDS.json
> (see `references/budgets-and-standards.md §6`), which `forge-validate` reads.

---

## §1. Full annotated schema

```markdown
# FORGE.md — project memory
# Written by forge-brief. Read by every Forge skill at the start of its flow.
# Edit via forge-brief; do NOT hand-edit fields that other skills derive from.

## Asset
<!-- One-line description of what is being built. -->
<asset description>

## Target
<!-- Delivery engine/format. One of:
     three.js/R3F | AR/USDZ | Unreal | Unity | Godot | print | USD | render-only -->
<engine/format>
<!-- Delivery format (GLB / FBX / STL / USDZ / render PNG). -->
<format>

## Coordinate system
<!-- Up axis: Y-up | Z-up -->
<up-axis>
<!-- Handedness: right-handed | left-handed -->
<handedness>
<!-- Scale unit: meters | centimeters | millimeters -->
<scale unit>
<!-- Forward axis in the DCC (Blender default: -Y, glTF: -Z, UE5: X). -->
<forward axis>

## Budgets
<!-- Triangles at each LOD level for the asset class. "web hero" example:
     LOD0 ≤ 50,000 tri; no LODs required for web
     Console hero example: LOD0 50K, LOD1 25K, LOD2 12.5K, LOD3 3K -->
<polycount budget>
<!-- Texel density target in px/m. Standard tiers:
     Hero FPS / face: 2048 px/m
     Standard PC/console prop: 1024 px/m
     Environment background: 512 px/m
     Web / mobile: 512–1024 px/m -->
<texel density px/m>
<!-- Maximum texture resolution per map. -->
<max texture resolution>
<!-- Draw-call ceiling (web): target < 100; never > 300. Omit for non-web. -->
<draw call ceiling (web)>
<!-- GLB file-size ceiling for web delivery. Omit for non-web.
     Hero asset: ≤ 5 MB (2 MB ideal); full scene: ≤ 12 MB. -->
<GLB size ceiling>

## Render
<!-- Blender render engine. ALWAYS Cycles for headless Windows renders.
     EEVEE Next is unsupported in headless mode on Windows. -->
Cycles (headless Windows — EEVEE Next unsupported headless)
<!-- Cycles samples for QA renders (fast) vs final poster renders. -->
Samples: <N> (QA) / <M> (final poster)
<!-- Color view transform. AgX is the Blender 4.x default and preferred for PBR. -->
Color view: AgX
<!-- Output resolution for the static poster / web handoff PNG. -->
Poster resolution: <WxH>

## Determinism
<!-- The idempotent-rebuild contract (FORGE_PLAN §A: "idempotent rebuilds; seeded randomness").
     Read by forge-model/procedural/sim (seed), forge-render (Cycles seed/samples), and
     forge-validate (render-compare baseline). Machine-readable mirror: "seed" in
     FORGE_STANDARDS.json. Never bump the seed silently — a changed seed invalidates the baseline. -->
<!-- Master random seed for ALL procedural / scatter / simulation / Cycles operations. -->
Random seed: 0
<!-- Cycles sampling seed + whether it advances per frame. Keep animated_seed OFF for
     a stable, comparable baseline (ON re-randomizes noise every frame → render-compare drifts). -->
Cycles seed: 0, use_animated_seed: off
<!-- Sample counts MUST match ## Render so a rebuild reproduces the same noise floor. -->
QA samples: <N>; Final samples: <M>
<!-- The contract every downstream skill upholds. -->
Rebuild contract: same FORGE.md + same source => byte-identical GLB and comparable PNG

## PBR workflow
<!-- Material model: metallic-roughness (glTF default) | specular-glossiness (legacy) -->
metallic-roughness (glTF)
<!-- Channel packing policy for ORM maps (standard: R=AO, G=Roughness, B=Metallic). -->
ORM channel pack: AO→R, Roughness→G, Metallic→B
<!-- Normal map convention: OpenGL (Y+, Blender/glTF default) | DirectX (Y-, UE5) -->
Normals: OpenGL (Y+)

## Output paths
<!-- Working directory for intermediate renders, QA frames, exports. -->
.forge-build/out/
<!-- Web handoff path (public-served). Naming: <slug>-hero.glb / <slug>-hero-poster.webp -->
public/forge/<slug>-hero.glb
public/forge/<slug>-hero-poster.webp
<!-- Project slug (used in filenames). -->
Slug: <slug>

## Atelier link
<!-- Omit this entire section if ATELIER.md is absent.
     Written by forge-brief after extracting from ATELIER.md.
     Consumed by forge-material (OKLCH hue), forge-light (aesthetic), forge-render (poster tone). -->
World: <production | award>
Aesthetic: <named aesthetic from ATELIER.md>
Signature moment: <one-line concept from Direction Doc>
Primary OKLCH hue: <H float, e.g. 220.4>
```

---

## §2. Example: web hero (three.js / R3F)

```markdown
# FORGE.md — project memory

## Asset
Floating glass orb with animated caustic light for the landing-page hero

## Target
three.js/R3F — web browser delivery
GLB (binary glTF 2.0)

## Coordinate system
Y-up
right-handed
meters
Forward: -Z (glTF convention)

## Budgets
LOD0 ≤ 30,000 tri (single asset, no LOD chain required for web)
Texel density: 1024 px/m (hero-class web asset)
Max texture resolution: 2048×2048
Draw calls: < 30 (single orb scene)
GLB size: ≤ 2 MB (DRACO + Meshopt compressed, KTX2 textures)

## Render
Cycles (headless Windows — EEVEE Next unsupported headless)
Samples: 128 (QA turntable) / 512 (final poster)
Color view: AgX
Poster resolution: 1920×1080

## Determinism
Random seed: 0
Cycles seed: 0, use_animated_seed: off
QA samples: 128; Final samples: 512
Rebuild contract: same FORGE.md + same source => byte-identical GLB and comparable PNG

## PBR workflow
metallic-roughness (glTF)
ORM channel pack: AO→R, Roughness→G, Metallic→B
Normals: OpenGL (Y+)
Transmission: KHR_materials_transmission (glass/caustic)

## Output paths
.forge-build/out/
public/forge/orb-hero.glb
public/forge/orb-hero-poster.webp
Slug: orb

## Atelier link
World: award
Aesthetic: glass/liquid-glass
Signature moment: rotating glass orb with refracted caustic light, hero center-stage
Primary OKLCH hue: 220.4
```

---

## §3. Example: Unreal Engine 5 prop

```markdown
# FORGE.md — project memory

## Asset
SM_Barrel_Oak_01 — oak barrel, hero interactive prop, AA console game

## Target
Unreal Engine 5
FBX (binary)

## Coordinate system
Z-up
left-handed (UE5 default)
centimeters (1 unit = 1 cm; apply FBX_SCALE_ALL on export)
Forward: X (UE5 default)

## Budgets
LOD0: 15,000 tri | LOD1: 7,500 | LOD2: 3,000 | LOD3: 500 (imposter)
Texel density: 1024 px/m (hero interactive prop)
Max texture resolution: 2048×2048
Collision mesh: UCX_SM_Barrel_Oak_01 (convex hull, single body)

## Render
Cycles (headless Windows — EEVEE Next unsupported headless)
Samples: 64 (QA) / 256 (asset sheet)
Color view: AgX
Poster resolution: 1024×1024 (asset thumbnail)

## Determinism
Random seed: 0
Cycles seed: 0, use_animated_seed: off
QA samples: 64; Final samples: 256
Rebuild contract: same FORGE.md + same source => byte-identical FBX and comparable PNG

## PBR workflow
metallic-roughness (glTF / UE5 compatible)
ORM channel pack: AO→R, Roughness→G, Metallic→B
Normals: DirectX (Y- / UE5 default — FLIP green channel from Blender's OpenGL Y+)

## Output paths
.forge-build/out/
export/SM_Barrel_Oak_01.fbx
textures/T_Barrel_Oak_BC_01.png
textures/T_Barrel_Oak_N_01.png
textures/T_Barrel_Oak_ORM_01.png
Slug: barrel_oak_01
```

---

## §4. Example: print / CAD part

```markdown
# FORGE.md — project memory

## Asset
Phone stand — desk accessory, FDM printable, PLA material

## Target
3D print (FDM — FFF)
STL + 3MF

## Coordinate system
Z-up
right-handed
millimeters
Forward: Y

## Budgets
Triangle count: not restricted (print — all tris rendered on slicer, not GPU)
Wall thickness minimum: 1.5 mm (PLA structural minimum for non-load-bearing)
Manifold: required (watertight — no open edges, no internal faces)
Overhang limit: ≤ 45° from vertical without supports

## Render
Cycles (headless Windows — EEVEE Next unsupported headless)
Samples: 64 (QA)
Color view: AgX
Poster resolution: 800×600

## Determinism
Random seed: 0 (any randomized pattern/fillet ops; OpenSCAD/CadQuery are otherwise deterministic)
Cycles seed: 0, use_animated_seed: off (QA preview only)
QA samples: 64
Rebuild contract: same FORGE.md + same .scad/source => byte-identical manifold STL/3MF

## PBR workflow
N/A — print, not rendered material

## Output paths
.forge-build/out/
export/phone_stand_v01.stl
export/phone_stand_v01.3mf
Slug: phone_stand
```

---

## §5. Example: render-only (Blender film/motion)

```markdown
# FORGE.md — project memory

## Asset
Abstract kinetic sculpture, 10-second looping animation, motion-graphics deliverable

## Target
render-only (Blender .blend — no engine export)
PNG frame sequence → MP4 via FFmpeg

## Coordinate system
Z-up (Blender native)
right-handed
meters
Forward: -Y (Blender default)

## Budgets
No poly budget (render-only — unlimited for final beauty)
Subdivision: apply before render, adaptive subdivision enabled

## Render
Cycles (headless Windows)
Samples: 512 (final beauty frames)
Color view: AgX
Output: 2560×1440 PNG sequence → .forge-build/out/frames/frame_####.png

## Determinism
Random seed: 0 (all procedural/sim ops)
Cycles seed: 0, use_animated_seed: on (animation — advance the noise seed per frame to avoid
  a frozen firefly pattern; the master seed still makes the whole sequence reproducible)
Final samples: 512
Rebuild contract: same FORGE.md + same .blend => identical frame sequence (same seed per frame)

## PBR workflow
metallic-roughness (Blender Principled BSDF)
ORM channel pack: N/A (render-only)
Normals: OpenGL (Y+)

## Output paths
.forge-build/out/frames/
.forge-build/out/render_01.mp4
Slug: kinetic_sculpture
```

---

## §6. Minimal viable FORGE.md (quick-start)

The absolute minimum forge-brief should write when the user gives a brief description and
nothing more. Derive engine, budgets, and coordinate system from the class; confirm with the
user before a full build starts.

```markdown
# FORGE.md — project memory

## Asset
<one-line asset description>

## Target
<engine/format>

## Coordinate system
<up-axis>, <handedness>, <scale unit>

## Budgets
LOD0 ≤ <N> tri; texel density <TD> px/m; max texture <res>

## Render
Cycles (headless Windows); <N> samples; AgX

## Determinism
Seed: 0 (all procedural/sim/Cycles ops); Cycles use_animated_seed: off; QA <N> / Final <M> samples;
rebuild contract: same FORGE.md + same source => byte-identical GLB and comparable PNG

## PBR workflow
metallic-roughness; ORM (AO→R, Rough→G, Metal→B); Normals OpenGL Y+

## Output paths
.forge-build/out/
public/forge/<slug>-hero.glb
Slug: <slug>
```
