# forge-data — PBR & Material Reference

PBR theory, ORM channel-pack recipe, Blender Principled→glTF mapping, color-space rules, and
texture suffix conventions. Decision authority: **forge-material**.

## Contents
- §1. PBR metallic-roughness model
- §2. ORM channel-pack recipe
- §3. Blender Principled BSDF → glTF mapping
- §4. Color-space rules
- §5. Material preset starting points
- §6. glTF material extensions

---

## §1. PBR metallic-roughness model

The glTF 2.0 / UE5 / Unity default. Two channels define a surface:

| Channel | Range | Meaning |
|---------|-------|---------|
| **Metallic** | 0–1 (binary in practice: 0 or 1) | 0 = dielectric (wood, stone, plastic); 1 = metallic (iron, gold, copper) |
| **Roughness** | 0–1 (continuous) | 0 = mirror-smooth; 1 = completely diffuse |

**Why binary metallic matters:** Real-world metals are either fully metallic or fully dielectric
at a micro level. Non-binary metallic values represent oxidized/dusty surfaces — use a mask
texture to blend, not a uniform mid-value.

**Principled BSDF quick-start (Blender):**
```python
mat = bpy.data.materials.new(name="M_Oak_Plank")
mat.use_nodes = True
nodes = mat.node_tree.nodes
principled = nodes.get("Principled BSDF")

principled.inputs["Metallic"].default_value = 0.0      # wood = dielectric
principled.inputs["Roughness"].default_value = 0.65    # slightly rough
principled.inputs["Specular IOR Level"].default_value = 0.5  # Blender 4.x
# Connect T_Oak_BC texture to Base Color
# Connect T_Oak_ORM to Principled via a Separate RGB node
```

---

## §2. ORM channel-pack recipe

**Layout:** R = AO, G = Roughness, B = Metallic.

**Rationale for Green = Roughness:** BC1/BC3 compression allocates 6 bits to Green vs 5 to Red/Blue.
Roughness has the most perceptually-critical gradients, so it goes in the highest-precision channel.

**Why ORM:** One texture replaces three maps. Saves ~4 MB per 2048² material at BC1 compression.
UE5's default PBR setup and Substance Painter's Unreal export preset both use this layout.

**Blender Principled BSDF node wiring for ORM:**
```python
# In a Blender material node tree:
# 1. Add Image Texture node, load T_Asset_ORM.png, set Color Space = Non-Color
# 2. Add Separate RGB node
# 3. ORM texture → Separate RGB input
# 4. Separate RGB R → Principled "Ambient Occlusion" (via MixRGB if needed)
#    Separate RGB G → Principled "Roughness"
#    Separate RGB B → Principled "Metallic"
import bpy

def wire_orm_to_principled(mat, orm_path):
    mat.use_nodes = True
    tree = mat.node_tree
    links = tree.links
    nodes = tree.nodes

    principled = nodes.get("Principled BSDF")

    tex_node = nodes.new("ShaderNodeTexImage")
    tex_node.image = bpy.data.images.load(orm_path)
    tex_node.image.colorspace_settings.name = 'Non-Color'

    sep_node = nodes.new("ShaderNodeSeparateColor")
    links.new(tex_node.outputs["Color"], sep_node.inputs["Color"])
    # R (AO) — optional; Principled has no direct AO input; use MixRGB on Base Color
    links.new(sep_node.outputs["Green"], principled.inputs["Roughness"])
    links.new(sep_node.outputs["Blue"],  principled.inputs["Metallic"])
```

---

## §3. Blender Principled BSDF → glTF material mapping

When exporting to GLB, Blender's glTF exporter maps Principled BSDF nodes to glTF properties.
Using the wrong Principled input names breaks the export.

| Principled BSDF input | glTF property | Notes |
|-----------------------|--------------|-------|
| `Base Color` (input) | `pbrMetallicRoughness.baseColorFactor` | Connect Base Color texture to this input |
| `Base Color` (texture) | `pbrMetallicRoughness.baseColorTexture` | Must be sRGB color space |
| `Metallic` | `pbrMetallicRoughness.metallicFactor` | Value or separate metallic texture B-channel |
| `Roughness` | `pbrMetallicRoughness.roughnessFactor` | Value or ORM texture G-channel |
| ORM texture (wired via Separate RGB) | `metallicRoughnessTexture` | Blender 4.x auto-detects ORM if wired correctly |
| `Normal` (via Normal Map node) | `normalTexture` | Strength via Normal Map node Scale |
| `Emission Color` | `emissiveFactor` | Set `Emission Strength` ≥ 1 for visible emissive |
| `Alpha` (via `Transmission`) | `alphaMode: BLEND` | Or use `Alpha` input directly for cutout |
| `Subsurface Weight` | Baked to Base Color | No direct glTF equivalent |
| `Coat Weight` | `KHR_materials_clearcoat` extension | Requires Blender 4.1+ glTF export |
| `Sheen Weight` | `KHR_materials_sheen` extension | |

**Alpha mode rules:**
- `OPAQUE`: no alpha — best performance (use `export_materials='EXPORT'` default)
- `MASK`: binary cutout (foliage, hair cards) — set `Blend Mode = Alpha Clip` in material settings
- `BLEND`: smooth transparency — use sparingly; sorts per-draw-call in WebGL

---

## §4. Color-space rules

| Texture type | Blender color space | UE5 sRGB checkbox | Notes |
|-------------|---------------------|-------------------|-------|
| `_BC` / `_D` Base Color | sRGB | ON | Perceived colors must be gamma-corrected |
| `_E` / `_EM` Emissive | sRGB | ON | Same as Base Color |
| `_N` Normal | **Non-Color** (Linear) | OFF | Normals are vectors, not colors |
| `_ORM` AO/Rough/Metal | **Non-Color** (Linear) | OFF | Linear data, not perceptual |
| `_R` Roughness | **Non-Color** | OFF | |
| `_M` / `_MT` Metallic | **Non-Color** | OFF | |
| `_AO` Ambient Occlusion | **Non-Color** | OFF | |
| `_H` Height / Displacement | **Non-Color** | OFF | |
| `_O` Opacity / Alpha | **Non-Color** | OFF | |

**Common mistake:** Importing a Normal map as sRGB causes subtle shading errors — normals appear
slightly wrong in light direction. Hard to detect at low resolution but visible at close range.

---

## §5. Material preset starting points

These are BM25-queryable starting points. **forge-material is the authority for final values.**

| Material | Metallic | Roughness | Base Color hint | Notes |
|----------|---------|-----------|----------------|-------|
| Polished steel | 1.0 | 0.1–0.2 | 0.7, 0.7, 0.7 | Mirror-like; add micro-scratches via roughness map |
| Brushed steel | 1.0 | 0.4–0.6 | 0.65, 0.65, 0.65 | Anisotropic roughness if DCC supports |
| Raw / rusted iron | 1.0 → 0.0 blend | 0.7–0.9 | Dark gray → orange-brown | Use metallic mask with rust texture |
| Gold | 1.0 | 0.1–0.3 | 1.0, 0.77, 0.33 (sRGB) | Colored reflections via metallic base color |
| Copper | 1.0 | 0.2–0.5 | 0.96, 0.63, 0.5 | Patina via roughness + color mask |
| Plastic (glossy) | 0.0 | 0.1–0.3 | Any | IOR Level ~0.5 (Blender 4.x) |
| Plastic (matte) | 0.0 | 0.6–0.9 | Any | |
| Rubber | 0.0 | 0.8–1.0 | Dark gray or black | Very rough, no specular |
| Dry wood (raw oak) | 0.0 | 0.65–0.8 | Warm brown | Grain via normal map |
| Lacquered wood | 0.0 | 0.05–0.2 | Warm brown | Coat extension for clear-coat |
| Concrete (rough) | 0.0 | 0.8–0.95 | Gray | Cavity AO in ORM |
| Painted metal | 0.0 | 0.3–0.6 | Any solid color | Chips = metallic mask; scratches = normal |
| Glass (transparent) | 0.0 | 0.0–0.1 | 1,1,1 (white) | Transmission = 1.0; IOR = 1.45 |
| Emissive LED panel | 0.0 | 0.5 | Emission color | Emission Strength 5–20; HDR render |
| Skin (human) | 0.0 | 0.3–0.5 | Peach / dark brown | Subsurface (baked to base color for glTF) |

---

## §6. glTF material extensions

| Extension | Purpose | Blender 4.x support |
|-----------|---------|---------------------|
| `KHR_materials_clearcoat` | Clear-coat layer (lacquered wood, car paint) | Yes (Coat Weight node input) |
| `KHR_materials_sheen` | Fabric sheen (velvet, microfiber) | Yes (Sheen Weight) |
| `KHR_materials_transmission` | Glass / transparent | Yes (Transmission) |
| `KHR_materials_volume` | Subsurface / volumetric absorption | Yes (limited) |
| `KHR_materials_emissive_strength` | HDR emissive (>1.0) | Yes (Emission Strength) |
| `KHR_materials_ior` | Index of refraction | Yes (IOR input) |
| `KHR_materials_unlit` | No lighting (skybox, UI quads) | Yes (`Shadeless` toggle) |
| `KHR_texture_basisu` | KTX2 / Basis Universal textures | Via gltf-transform post-process |
| `KHR_draco_mesh_compression` | Draco geometry compression | Via Blender export or gltf-transform |
| `EXT_meshopt_compression` | Meshopt compression + animation | Via gltf-transform meshopt |
