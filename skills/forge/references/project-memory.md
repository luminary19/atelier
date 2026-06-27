# FORGE.md — Project Memory Schema & Template

> This file is the authoritative template for `FORGE.md`. The `forge` router's `init` mode writes it;
> every other Forge skill reads it before executing. Update it whenever a project decision changes.
> Mirrors ATELIER.md's role in the Atelier suite.

---

## Template (copy to project root as `FORGE.md`, fill all sections)

```markdown
# FORGE.md — 3D Project Memory

## Target
engine: three.js/R3F | Unreal 5 | Unity 2024 | Godot 4 | print/STL | AR/USDZ
delivery format: GLB | USD | FBX | STL | USDZ
slug: <project-slug>   <!-- used in asset naming: public/forge/<slug>-hero.glb -->

## Coordinate system
handedness: Y-up (three.js/R3F/Unity/USD) | Z-up (Blender/Godot — flip on export)
scale unit: meters (glTF/Unreal/three.js standard) | centimeters (print) | millimeters (precision print)
forward axis: -Z forward (Blender default; glTF export auto-corrects to +Z)

## Budgets
<!-- Hero prop = hero asset (< 100K tris); env-piece = environment set piece (< 500K); bg = background -->
polycount class: hero-prop | env-piece | bg-asset
triangle target: <N>K tris (before LOD)
texel density: <N> px/m (e.g. 1024 px/m for hero props; 512 for bg)
texture max resolution: <N>x<N> (e.g. 2048×2048 per material)
draw call ceiling: <N> (web heroes: < 100; print: N/A)
LOD levels: <N> (e.g. LOD0 100K / LOD1 40K / LOD2 10K)

## Render
engine: Cycles   <!-- ALWAYS Cycles for headless on Windows; EEVEE Next not supported headless -->
device: CPU      <!-- CPU fallback; GPU only if confirmed available + CUDA/HIP driver present -->
samples: 64      <!-- QA renders: 16; final beauty: 128-256 -->
color view transform: AgX  <!-- AgX default; ACES for film/VFX pipelines -->
output resolution: 1920x1080  <!-- poster/QA; 640x480 for quick turntable checks -->
output dir: .forge-build/out/

## PBR workflow
material model: metallic-roughness (glTF default)
channel packing: ORM (Occlusion R / Roughness G / Metallic B) — Unreal convention
normal map: OpenGL (Y-up, glTF standard); flip G if using DirectX source maps
texture color spaces:
  - BaseColor/Albedo: sRGB
  - ORM/Roughness/Metallic/Normal: Non-Color (linear)
  - Emission: sRGB

## Output paths
working:     .forge-build/out/         <!-- temp renders, WIP exports -->
web handoff: public/forge/             <!-- final GLB + poster for atelier-webgl -->
naming convention: <slug>-<stage>.<ext>
  examples:
    .forge-build/out/geo_base.blend
    .forge-build/out/qa_turntable.png
    public/forge/<slug>-hero.glb         <!-- DRACO+Meshopt compressed -->
    public/forge/<slug>-hero-poster.png  <!-- full-res render (forge-render output) -->
    public/forge/<slug>-hero-poster.webp <!-- compressed for web delivery (ImageMagick) -->

## Atelier link
<!-- Fill from ATELIER.md when present; leave N/A if no Atelier project -->
world: production | award
aesthetic: <named aesthetic from ATELIER.md §Creative direction>
signature moment: <one-line description of the 3D moment>
primary OKLCH hue: <H value from --primary token, e.g. 264.5>
DRACO decoder path: /draco/  <!-- local copy of three/examples/jsm/libs/draco/ in public/ -->
pipeline log: .forge-build/export/<slug>-log.txt

## Forge 3D assets
<!-- forge-director or forge-optimize writes this block once assets are built -->
- GLB: public/forge/<slug>-hero.glb  (<size>KB; DRACO+Meshopt)
- Poster PNG: public/forge/<slug>-hero-poster.png  (full-res; forge-render output)
- Poster WebP: public/forge/<slug>-hero-poster.webp  (<size>KB; reduced-motion + no-WebGL fallback)
- Scene description: <one-line for canvas alt text>
- Forge pipeline log: .forge-build/export/<slug>-log.txt
```

---

## Field explanations

### Target engine — coordinate system implications

| Engine | Y/Z-up | Scale | glTF export adjustment needed |
|---|---|---|---|
| three.js / R3F | Y-up | meters | None — glTF is Y-up meters natively |
| Unity | Y-up | meters | None for glTF; FBX: flip Z on import |
| Unreal 5 | Z-up | centimeters | glTF import plugin handles; FBX: check scale × 100 |
| Godot 4 | Y-up | meters | glTF direct; Godot's glTF importer is first-class |
| Blender | Z-up | meters | glTF exporter auto-converts to Y-up — correct by default |
| Print / STL | Z-up (typically) | millimeters | No glTF; OpenSCAD/CadQuery → STL → slicer |
| AR / USDZ | Y-up | meters | USD file → convert with `xcrun usdz_converter` on macOS |

### Poly budget guidance (by class)

| Class | Triangle budget | Texture | Use case |
|---|---|---|---|
| Hero prop | ≤ 100K tris | 2048×2048 | Main hero asset in a web scene |
| Env set piece | ≤ 500K tris | 2048×2048 per mat | Large environment, non-hero |
| Background asset | ≤ 10K tris | 512×512 | Distant, non-interactive |
| Print-ready | Watertight required | N/A | FDM/SLA — check wall thickness |

For web heroes: draw calls < 100 (total scene), GLB < 5 MB after DRACO+Meshopt.

### Render engine — Windows headless rules

**CYCLES is the only supported headless engine on Windows.**

- EEVEE Next requires a display server (real GPU, Wayland/X11, or virtual display). On Windows without a
  virtual display driver, `-b` (background mode) + EEVEE Next causes a crash or black output.
- Cycles CPU mode always works headless: add `bpy.context.scene.render.engine = 'CYCLES'` and
  `bpy.context.preferences.addons["cycles"].preferences.compute_device_type = 'NONE'` (CPU).
- Cycles GPU (CUDA/HIP/Metal) works headless only if the GPU driver is installed and Claude Code has
  access to it — verify with `blender -b --python-expr "import bpy; print(bpy.context.preferences.addons['cycles'].preferences.compute_device_type)"`.

### Atelier link — when to populate

Populate the `## Atelier link` block when:
- `ATELIER.md` is present at the project root (read it with the Read tool).
- The user's prompt references a web project with an Atelier pipeline active.
- `forge-brief` extracts the aesthetic/world/signature/OKLCH from ATELIER.md.

The OKLCH primary hue (H channel) is used by `forge-material` to harmonize material base colors with
the web brand — do not hardcode; read it from the token file.
