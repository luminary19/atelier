# PBR Theory — forge-material reference

# Contents
- §1. Microfacet BRDF theory (Cook-Torrance)
- §2. IOR and F0 reference values
- §3. Normal map conventions (DX vs GL)
- §4. Color space rules
- §5. Common gotchas and fixes
- §6. White furnace test (programmatic)
- §7. Roughness real-world ranges
- §8. ORM channel layout per engine

---

## §1. Microfacet BRDF Theory (Cook-Torrance)

The Cook-Torrance specular BRDF used in Blender Cycles and all modern PBR engines:

```
f_r(ω_i, ω_o) = (D(h) · G(ω_i, ω_o, h) · F(ω_i, h)) / (4 · (n·ω_i) · (n·ω_o))
```

**Components:**

- **D(h)** — Normal Distribution Function (NDF): GGX/Trowbridge-Reitz is standard.
  Controls the statistical distribution of microfacet normals. `α = roughness²`.
  Blender 4.x Principled uses MULTI_GGX by default — adds energy compensation for multiple
  scattering (prevents rough metals appearing artificially dark). Always use MULTI_GGX in scripts:
  ```python
  bsdf.distribution = 'MULTI_GGX'
  ```

- **G(ω_i, ω_o)** — Masking-Shadowing: Smith geometry term. Prevents energy gain from microfacets
  hiding each other. Without it, rough metals appear artificially dark at grazing angles.

- **F(θ)** — Fresnel: fraction of light reflected vs refracted.
  Schlick approximation: `F(θ) = F0 + (1 − F0)(1 − cosθ)^5`
  where for dielectrics: `F0 = ((n−1)/(n+1))²`

**Energy conservation:** Diffuse lobe is scaled by `(1 − metallic) × (1 − specularTransmission) × (1 − F(θ))` so total outgoing energy ≤ incoming. Automatic in Principled BSDF.

---

## §2. IOR and F0 Reference Values

For dielectrics (non-metals), F0 at normal incidence:
```
F0 = ((IOR − 1) / (IOR + 1))²
```

**Dielectrics — IOR and F0:**

| Material              | IOR   | F0 linear | Notes                         |
|-----------------------|-------|-----------|-------------------------------|
| Vacuum / Air          | 1.0   | 0.00 (0%) | reference                     |
| Water                 | 1.333 | 0.020 (2%)| also glTF default for water  |
| Plastic (generic)     | 1.5   | 0.040 (4%)| most dielectrics cluster here |
| Glass (soda-lime)     | 1.52  | 0.043     |                               |
| Fused quartz          | 1.46  | 0.035     |                               |
| Ice                   | 1.31  | 0.017     |                               |
| Sapphire              | 1.77  | 0.073     |                               |
| Diamond               | 2.42  | 0.172 (17%)|                              |

Default Principled BSDF IOR = 1.5 (glass/plastic baseline). Do NOT leave IOR at 1.0 —
that produces F0 = 0% (no Fresnel, physically impossible for any material denser than vacuum).

**Metals (conductors) — F0 linear RGB (sRGB approx):**

| Metal       | F0 linear (R, G, B)         | sRGB approx |
|-------------|-----------------------------|-------------|
| Silver (Ag) | (0.987, 0.983, 0.967)       | (254,253,251)|
| Aluminum    | (0.916, 0.923, 0.924)       | (245,246,246)|
| Gold (Au)   | (1.000, 0.710, 0.315)       | (255,219,152)|
| Copper (Cu) | (1.000, 0.650, 0.527)       | (255,211,192)|
| Iron (Fe)   | (0.895, 0.876, 0.815)       | (243,241,233)|
| Chromium    | (0.550, 0.556, 0.553)       | (196,197,196)|
| Titanium    | (0.443, 0.399, 0.360)       | (178,169,162)|

Source: Adobe Substance ASM reference + physicallybased.info

For metals: albedo encodes the specular tint color (F0 value), NOT a diffuse color.
Metals have no diffuse lobe — their base color should be dark or near-black when metallic = 1.0.

---

## §3. Normal Map Conventions (DirectX vs OpenGL)

| Engine / Tool                    | Convention | Green channel (Y) |
|----------------------------------|------------|-------------------|
| Blender (Cycles / EEVEE)         | OpenGL     | +Y (right-hand)   |
| Unity (all pipelines)            | OpenGL     | +Y                |
| Unreal Engine 4 / 5              | DirectX    | −Y (inverted)     |
| 3ds Max                          | DirectX    | −Y                |
| ZBrush, Maya, C4D, Houdini       | OpenGL     | +Y                |
| Substance Painter                | Selectable | project setting   |

**Detect wrong convention:** DirectX map in OpenGL engine causes bumps to appear inverted —
raised details look recessed, grooves look raised. Lit on a sphere, the specular hotspot will be
on the opposite side from the light direction.

**Fix in Blender — flip G channel to convert DX → GL:**

```python
# In shader graph: Separate RGB → invert G → Combine RGB → Normal Map node
# Use ShaderNodeSeparateColor (4.2+) not ShaderNodeSeparateRGB (deprecated)

sep = nodes.new('ShaderNodeSeparateColor')
sep.mode = 'RGB'
links.new(nm_tex.outputs['Color'], sep.inputs['Color'])

invert_g = nodes.new('ShaderNodeMath')
invert_g.operation = 'SUBTRACT'
invert_g.inputs[0].default_value = 1.0
links.new(sep.outputs['Green'], invert_g.inputs[1])

comb = nodes.new('ShaderNodeCombineColor')
comb.mode = 'RGB'
links.new(sep.outputs['Red'],    comb.inputs['Red'])
links.new(invert_g.outputs[0],   comb.inputs['Green'])   # flipped G
links.new(sep.outputs['Blue'],   comb.inputs['Blue'])

links.new(comb.outputs['Color'], nm_node.inputs['Color'])
```

Note: Blender's Normal Map node `space` and orientation settings do NOT flip G.
You must invert G explicitly in the texture or in the node graph above.

---

## §4. Color Space Rules (Critical)

Wrong color space is the single most destructive and hardest-to-diagnose error in PBR workflows.
Set explicitly on every `bpy.data.images` load — never rely on auto-detection.

| Map type         | Color Space   | Python API                                       |
|------------------|---------------|--------------------------------------------------|
| baseColor/albedo | `sRGB`        | `img.colorspace_settings.name = 'sRGB'`          |
| emission texture | `sRGB`        | `img.colorspace_settings.name = 'sRGB'`          |
| metallic         | `Non-Color`   | `img.colorspace_settings.name = 'Non-Color'`     |
| roughness        | `Non-Color`   | same                                             |
| ORM (packed)     | `Non-Color`   | same                                             |
| normal map       | `Non-Color`   | same                                             |
| AO               | `Non-Color`   | same                                             |
| height/disp.     | `Non-Color`   | same                                             |
| HDR environment  | `Linear Rec.709` / `ACEScg` | depends on OCIO config          |

**Why it matters:**  sRGB decode applies a gamma curve (~2.2) to the sampled value. On a roughness
map, a 0.5 value becomes 0.73 after sRGB decode — every surface appears dramatically smoother
than authored. On a metallic map, the 0/1 binary threshold shifts, producing physically implausible
blend states.

**Programmatic check (inside Blender script):**
```python
for img in bpy.data.images:
    print(img.name, "->", img.colorspace_settings.name)
# Expected: albedo/emission = 'sRGB'; everything else = 'Non-Color'
```

---

## §5. Common Gotchas and Fixes

**G1 — Wrong color space on data maps**
- Symptom: roughness looks washed out (everything too shiny); normal map has no effect.
- Detect: check `img.colorspace_settings.name` after load.
- Fix: `img.colorspace_settings.name = 'Non-Color'` for metallic, roughness, normal, AO, height.

**G2 — Baked lighting in albedo**
- Symptom: asset looks fine in one lighting setup, has a permanent shadow under other lights.
- Detect: desaturate the albedo texture — if grey values vary across flat geometry, lighting is baked.
- Fix: re-author the albedo from the source, or use Substance's "Remove Baked Lighting" / InstaMAT.

**G3 — Normal map direction flipped (DX vs GL mismatch)**
- Symptom: bumps appear as dents; surface detail is inverted.
- Detect: render a sphere with a point light. If specular is on the opposite side from the light, Y is wrong.
- Fix: flip G channel (see §3 script above).

**G4 — Metallic map has gray values (not 0 or 1)**
- Symptom: surface appears as a physically impossible blend of metal and plastic.
- Detect: histogram the metallic map. If values cluster 0.3–0.7, it was painted with soft brushes.
- Fix: threshold the map (values < 0.5 → 0.0, >= 0.5 → 1.0):
  ```python
  # System Python with Pillow (pip install pillow)
  from PIL import Image
  import numpy as np
  img = Image.open("metallic.png").convert("L")
  arr = np.array(img, dtype=np.float32) / 255.0
  arr = (arr >= 0.5).astype(np.float32)
  Image.fromarray((arr * 255).astype(np.uint8)).save("metallic_fixed.png")
  ```

**G5 — Blender 4.x Principled BSDF input name changes**
- Symptom: `bsdf.inputs['Specular']` raises KeyError in Blender 4.0+ scripts.
- Cause: Blender 4.0 renamed all inputs to align with OpenPBR.
- Fix: use the current 4.x names:
  ```python
  bsdf.inputs['Specular IOR Level'].default_value = 0.5  # was 'Specular' in 3.x
  bsdf.inputs['Emission Color'].default_value = (0, 0, 0, 1)  # was 'Emission'
  bsdf.inputs['Transmission Weight'].default_value = 0.0  # was 'Transmission'
  bsdf.inputs['Coat Weight'].default_value = 0.0  # was 'Clearcoat'
  bsdf.inputs['Coat Roughness'].default_value = 0.0  # was 'Clearcoat Roughness'
  ```

**G6 — Windows path separators in bpy image loading**
- Symptom: `bpy.data.images.load()` raises FileNotFoundError despite the file existing.
- Cause: Windows backslashes sometimes fail in Blender's Python context.
- Fix:
  ```python
  import os
  path = os.path.normpath(r"C:\Maps\roughness.png").replace("\\", "/")
  img = bpy.data.images.load(path, check_existing=True)
  ```

**G7 — True displacement does nothing (Eevee / missing subdivision)**
- Symptom: Displacement node wired, `mat.cycles.displacement_method = 'DISPLACEMENT'`, but flat.
- Cause 1: Using Eevee — true displacement is Cycles-only.
- Cause 2: No Subdivision Surface modifier.
- Fix: assert engine == CYCLES, add SubSurf modifier, set `scene.cycles.feature_set = 'EXPERIMENTAL'`.

**G8 — Blender headless GPU init fails silently on Windows**
- Symptom: render uses CPU at full speed despite NVIDIA card available.
- Detect: `print(bpy.context.scene.cycles.device)` — if it prints 'CPU', GPU init failed.
- Fix: call the canonical `setup_gpu()` helper — set `compute_device_type`, then
  `prefs.refresh_devices()`, then enable each non-CPU device (`d.use = True`) before
  `scene.cycles.device = 'GPU'` (see bpy-material-scripts.md §1).

**G9 — ORM imported as sRGB in Unreal / Unity**
- Symptom: roughness and metallic behave erratically in engine; ORM values look wrong.
- Fix: In UE5: Compression Settings → Masks (no sRGB). In Unity: uncheck sRGB in Inspector.

---

## §6. White Furnace Test (Programmatic Energy Conservation Check)

Render a material against a uniform white environment. A correctly energy-conserving material
should dissolve into the background at metallic=1.0, baseColor=(1,1,1), any roughness.

```python
# Add to a pbr_setup.py script (inside Blender bpy context)
def setup_white_furnace(scene, mat, roughness=0.5):
    """Configure scene for white furnace energy conservation test."""
    world = bpy.data.worlds['World']
    world.use_nodes = True
    bg = world.node_tree.nodes.get('Background')
    bg.inputs['Color'].default_value    = (1.0, 1.0, 1.0, 1.0)
    bg.inputs['Strength'].default_value = 1.0
    # Remove all scene lights
    for obj in list(bpy.data.objects):
        if obj.type == 'LIGHT':
            bpy.data.objects.remove(obj, do_unlink=True)
    # White metal material
    bsdf = mat.node_tree.nodes.get('Principled BSDF')
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
        bsdf.inputs['Metallic'].default_value   = 1.0
        bsdf.inputs['Roughness'].default_value  = roughness
```

---

## §7. Roughness Real-World Ranges

| Material            | Roughness range | Notes                               |
|---------------------|-----------------|-------------------------------------|
| Polished metal      | 0.05 – 0.20     | phone screens ~0.10–0.15 (micro-scratches) |
| Brushed metal       | 0.30 – 0.50     | anisotropic if directional grain    |
| Plastic (glossy)    | 0.20 – 0.35     |                                     |
| Plastic (matte)     | 0.50 – 0.70     |                                     |
| Wood (lacquered)    | 0.25 – 0.45     |                                     |
| Wood (raw)          | 0.60 – 0.80     |                                     |
| Glass (clear)       | 0.02 – 0.05     | nearly mirror; frosted = 0.30–0.60 |
| Rubber              | 0.80 – 0.95     |                                     |
| Concrete            | 0.85 – 0.95     |                                     |
| Chalk / snow        | 0.90 – 1.00     | near-Lambertian                     |

Real-world materials never reach pure 0.0 (theoretical perfect mirror) or pure 1.0 (perfectly
diffuse). Author within these ranges; use extremes only for intentional stylistic effect.

---

## §8. ORM Channel Layout Per Engine

The **glTF standard** and **Unreal Engine 5 (ORM)** use the same layout. Unity HDRP differs:

| Channel | glTF / UE5 ORM  | Unity HDRP Mask Map | Unity URP |
|---------|-----------------|---------------------|-----------|
| R       | Occlusion (AO)  | Metallic            | Metallic  |
| G       | Roughness       | Ambient Occlusion   | AO        |
| B       | Metallic        | Detail Mask         | —         |
| A       | (unused)        | Smoothness (1−rough)| Smoothness|

**Critical Unity HDRP note:** HDRP uses Smoothness = 1 − Roughness in the alpha channel.
Must invert the roughness map before packing for HDRP. In Blender compositor, add a Math node
(Subtract, 1.0 − roughness_value) before plugging into the alpha channel.

For glTF/UE5: use PNG (lossless). JPEG chroma subsampling corrupts the metallic and roughness
channels — never use JPEG for ORM.
