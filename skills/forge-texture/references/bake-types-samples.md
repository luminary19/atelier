# Forge Texture — Bake Types, Samples, Color Spaces & File Formats

## Contents
- §1. Bake type reference table
- §2. Samples per map type
- §3. Color space per map type
- §4. File format per map type
- §5. Normal map convention per target engine
- §6. Bake settings reference (bpy fields)

---

## §1. Bake Type Reference Table

| Map | Blender bake type | Notes |
|-----|-------------------|-------|
| Normal (tangent) | `NORMAL` | Set `bake.normal_space = 'TANGENT'` |
| Normal (object) | `NORMAL` | Set `bake.normal_space = 'OBJECT'` |
| Ambient Occlusion | `AO` | Ignores all lights; uses World AO distance |
| Curvature | `EMIT` | No native type; bake Geometry > Pointiness via ColorRamp→Emission |
| Albedo / Base Color | `DIFFUSE` | Set `use_pass_direct=False, use_pass_indirect=False, use_pass_color=True` |
| Roughness | `EMIT` | Route Roughness socket → Emission node → bake EMIT (native ROUGHNESS unreliable in 4.x) |
| Metallic | `EMIT` | Same Emission trick as Roughness |
| Displacement / Height | `DISPLACEMENT` | Or: bake as `EMIT` with Displacement input socket |
| Position (world XYZ) | `POSITION` | Blender 4.1+; save as EXR (float32) |
| Combined (full lighting) | `COMBINED` | All passes; most expensive; denoiser works here only |
| Emission | `EMIT` | Direct emission value |
| Shadow | `SHADOW` | Baked shadow mask |
| Environment | `ENVIRONMENT` | Environment contribution at surface |

**`ROUGHNESS` and `METALLIC` are unreliable in Blender 4.x with Principled BSDF.**
Always use the Emission trick: connect the socket to `Emission → Surface`, bake as `EMIT`.

---

## §2. Samples Per Map Type

| Map type | Minimum samples | Recommended | Max useful | Notes |
|----------|-----------------|-------------|------------|-------|
| Normal | 1 | 16–32 | 64 | Mostly geometric; low stochastic noise |
| AO | 64 | 128–256 | 512 | Stochastic; denoiser does NOT apply |
| Curvature (EMIT) | 1 | 1–4 | 8 | Deterministic Emission evaluation |
| Albedo/Diffuse (color only) | 4 | 16 | 32 | Color-only pass (no lighting) |
| Roughness / Metallic (EMIT) | 1 | 4–16 | 32 | Deterministic |
| Displacement (EMIT) | 1 | 4 | 16 | Deterministic height evaluation |
| Combined (full lighting) | 128 | 256–512 | 1024 | Full path tracing; use sparingly |
| Position | 1 | 1 | 1 | Fully deterministic |

**Rule:** Use the lowest count that produces a noise-free result at 200% zoom.
Denoising only applies to the `COMBINED` bake type — increase samples for AO instead.

---

## §3. Color Space Per Map Type

| Map | bpy setting | Why |
|-----|-------------|-----|
| Albedo (Base Color) | `img.colorspace_settings.name = 'sRGB'` | Perceptual color; gamma-corrected for display |
| Normal | `'Non-Color'` | Coordinate values; gamma correction corrupts them |
| Roughness | `'Non-Color'` | Linear data |
| Metallic | `'Non-Color'` | Linear data |
| AO | `'Non-Color'` | Linear occlusion factor |
| Curvature | `'Non-Color'` | Linear surface curvature |
| Height / Displacement | `'Non-Color'` | Linear height value |
| Position | `'Non-Color'` | World-space coordinates |
| Emission (HDR) | `'Linear Rec.709'` or `'Linear'` | HDR; no gamma |
| Combined (SDR) | `'sRGB'` | Perceptual display |

**Critical:** Setting `'sRGB'` on a Normal map causes Blender to apply gamma de-correction to what
are vector coordinates. The map looks slightly different in Blender but shades catastrophically wrong
in game engines. Always double-check before saving.

---

## §4. File Format Per Map Type

| Map | Format | Bit depth | Reason |
|-----|--------|-----------|--------|
| Albedo | PNG | 8-bit | Display-ready; sRGB |
| Normal | PNG | 8-bit sufficient | 16-bit EXR only for subdiv-heavy sculpts |
| Roughness | PNG | 8-bit | Linear; 8-bit adequate for PBR |
| Metallic | PNG | 8-bit | Binary in practice; 8-bit fine |
| AO | PNG | 8-bit | Linear shadow factor |
| Curvature | PNG | 8-bit | Edge detection |
| Height / Displacement | **EXR** | 32-bit float | Sub-pixel precision; PNG truncates |
| Position | **EXR** | 32-bit float | World-space XYZ; float required |
| Combined (SDR) | PNG | 8-bit | Display render |

For Displacement/Height: save as EXR for the source, then optionally derive an 8-bit PNG for
engine import (16-bit PNG also acceptable for Unity/Unreal displacement input).

---

## §5. Normal Map Convention Per Target Engine

| Engine | Convention | G channel | bpy setting |
|--------|-----------|-----------|-------------|
| Blender (internal) | OpenGL | +Y (green up) | `bake.normal_g = 'POS_Y'` |
| Unity HDRP | OpenGL | +Y | `bake.normal_g = 'POS_Y'` |
| Unity Standard pipeline | OpenGL | +Y | `bake.normal_g = 'POS_Y'` |
| Unreal Engine 5 | DirectX | −Y (green down) | `bake.normal_g = 'NEG_Y'` |
| DirectX (general) | DirectX | −Y | `bake.normal_g = 'NEG_Y'` |
| Marmoset Toolbag | OpenGL (default) | +Y | `bake.normal_g = 'POS_Y'` |
| Three.js / glTF | OpenGL | +Y | `bake.normal_g = 'POS_Y'` |

**Read from FORGE.md `## Target` before baking.** Default is OpenGL (`POS_Y`) unless FORGE.md
specifies Unreal or DirectX.

**Post-process flip (if you already baked OpenGL and need DirectX):**
```python
import cv2
n = cv2.imread("normal_gl.png")   # BGR
n[:,:,1] = 255 - n[:,:,1]         # index 1 = G channel in BGR
cv2.imwrite("normal_dx.png", n)
```

---

## §6. Bake Settings Reference (bpy fields)

All accessed via `bpy.context.scene.render.bake` (a `BakeSettings` object):

| Field | Type | Notes |
|-------|------|-------|
| `use_selected_to_active` | bool | True = high→low; False = self-bake |
| `cage_extrusion` | float | World-space; start at 1–2% of bounding box longest axis |
| `max_ray_distance` | float | 0.0 = unlimited (use extrusion only); set to 1.5–2x extrusion for thin parts |
| `use_cage` | bool | True to use an explicit cage object |
| `cage_object` | Object | Must be inflated copy of low-poly, same topology |
| `use_multires` | bool | True to bake from Multires modifier levels |
| `margin` | int | Pixel padding around UV islands; 16px at 2K, 32px at 4K |
| `margin_type` | str | `'EXTEND'` (fast) or `'ADJACENT_FACES'` (quality seams) |
| `use_clear` | bool | True = fill image with black before baking |
| `normal_space` | str | `'TANGENT'` or `'OBJECT'` |
| `normal_r` | str | `'POS_X'` (default) |
| `normal_g` | str | `'POS_Y'` (OpenGL) or `'NEG_Y'` (DirectX) |
| `normal_b` | str | `'POS_Z'` (default) |
| `use_pass_direct` | bool | For DIFFUSE bake: include direct lighting |
| `use_pass_indirect` | bool | For DIFFUSE bake: include indirect lighting |
| `use_pass_color` | bool | For DIFFUSE bake: include base color (set True for albedo) |

**For albedo (base color only, no lighting):**
```python
bake.use_pass_direct   = False
bake.use_pass_indirect = False
bake.use_pass_color    = True
```
