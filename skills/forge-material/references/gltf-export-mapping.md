# glTF Export Mapping — forge-material reference

# Contents
- §1. Principled BSDF → glTF: what survives (direct export)
- §2. What is dropped or approximate
- §3. Blender export script with correct flags
- §4. ORM channel packing JSON schema (incl. texture sampler defaults — wrapS/wrapT/minFilter)
- §5. KHR_texture_transform (UV tiling / offset / rotation)
- §6. Validation: gltf-validator + gltf-transform + pygltflib
- §7. Gotchas specific to the export pipeline

---

## §1. Principled BSDF → glTF: What Survives

This is the canonical source-of-truth table for Blender 4.2→glTF 2.0 material export.
Only Principled BSDF node topology is recognized. Any other BSDF node is silently dropped.

| Principled BSDF Socket    | glTF Target                                    | Notes                                |
|---------------------------|------------------------------------------------|--------------------------------------|
| Base Color (factor)       | `pbrMetallicRoughness.baseColorFactor`         | Linear RGBA                          |
| Base Color (texture)      | `pbrMetallicRoughness.baseColorTexture`        | sRGB encoded                         |
| Metallic (factor)         | `pbrMetallicRoughness.metallicFactor`          |                                      |
| Metallic (texture B)      | `metallicRoughnessTexture.B`                   | Packed with Roughness; Non-Color     |
| Roughness (factor)        | `pbrMetallicRoughness.roughnessFactor`         |                                      |
| Roughness (texture G)     | `metallicRoughnessTexture.G`                   | Packed with Metallic; Non-Color      |
| Alpha                     | `baseColorFactor.A` + `alphaMode`              | Depends on material alphaMode setting|
| Normal Map node           | `normalTexture` + `normalScale`                | Requires Image→NormalMap→BSDF.Normal |
| Emission Color + Strength | `emissiveFactor` + `KHR_materials_emissive_strength` | Strength>1 activates extension |
| Transmission Weight       | `KHR_materials_transmission.transmissionFactor`|                                      |
| IOR                       | `KHR_materials_ior.ior`                        | With transmission or specular        |
| Coat Weight               | `KHR_materials_clearcoat.clearcoatFactor`      |                                      |
| Coat Roughness            | `KHR_materials_clearcoat.clearcoatRoughnessFactor`|                                   |
| Coat Normal               | `KHR_materials_clearcoat.clearcoatNormalTexture`|                                    |
| Sheen Weight              | `KHR_materials_sheen.sheenRoughnessFactor`     | Blender 4.x+                         |
| Sheen Tint                | `KHR_materials_sheen.sheenColorFactor`         |                                      |
| Anisotropic               | `KHR_materials_anisotropy.anisotropyStrength`  | Blender 4.2+; requires TANGENT attr  |
| Anisotropic Rotation      | `KHR_materials_anisotropy.anisotropyRotation`  |                                      |
| AO (glTF Material Output) | `occlusionTexture`                             | NOT a BSDF socket; use custom node   |

**Occlusion note:** AO is NOT routed through Principled BSDF. It must be wired to the
`glTF Material Output` custom node group (created by the glTF IO add-on) via its `Occlusion` socket.
Wire the R channel of the ORM texture to this node group to trigger glTF occlusionTexture export.

---

## §2. What Is Dropped or Approximate

| Principled BSDF Feature     | glTF Status  | Workaround                                            |
|-----------------------------|--------------|-------------------------------------------------------|
| Subsurface Scattering        | DROPPED      | Bake to baseColor texture                            |
| Specular (old 3.x socket)   | APPROXIMATE  | Converted to `KHR_materials_specular`; use `export_original_specular=False` |
| Subsurface Color            | DROPPED      | Bake to texture                                      |
| Specular Tint               | DROPPED      | Use `KHR_materials_specular.specularColorFactor`     |
| Volume Absorption           | DROPPED      | Manually configure `KHR_materials_volume`            |
| Volume Scatter              | DROPPED      | glTF volume has no scattering term                   |
| Hair BSDF                   | DROPPED      | Use Principled BSDF + geometry-based hair            |
| Glass BSDF                  | DROPPED      | Use Principled BSDF with Transmission=1 + IOR        |
| Diffuse BSDF                | DROPPED      | Switch to Principled BSDF                            |
| Velvet BSDF                 | DROPPED      | Use Principled BSDF + Sheen                          |
| True displacement           | NOT EXPORTED | Bake to tangent-space normal map before export       |
| Bump node                   | NOT EXPORTED | Bake to tangent-space normal map                     |
| Noise/Voronoi/Wave texture  | NOT EXPORTED | Bake to image texture first                          |
| ColorRamp / Math chains     | PARTIAL      | Only recognized patterns are exported; bake the rest |
| UV Warp modifier            | PARTIAL      | Only Mapping node (POINT type) → `KHR_texture_transform` |
| UDIM tiles                  | AUTO-SPLIT   | Increases file size; consider atlasing instead       |
| MixShader / AddShader       | PARTIAL      | Emission + BSDF combos only                          |
| Cycles-only nodes (AO node, Light Path) | DROPPED | Bake before export                        |
| Multi-material node groups  | PARTIAL      | May not resolve correctly; flatten before export     |

---

## §3. Blender Export Script with Correct Flags

```python
# export_gltf.py — headless Blender glTF export
# Invocation:
#   blender --background "C:/path/scene.blend" --python export_gltf.py --python-exit-code 1
#   -- "C:/path/scene.blend" "C:/out/scene.glb"

import bpy, sys, os, argparse

argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
p = argparse.ArgumentParser()
p.add_argument("blend",  help="Input .blend file path")
p.add_argument("output", help="Output .glb file path")
p.add_argument("--apply-mods", action="store_true",
               help="Apply modifiers before export (destroys instancing)")
p.add_argument("--animations", action="store_true",
               help="Include animations in export")
args = p.parse_args(argv)

# Forward slashes required for Blender bpy paths on Windows
blend_path = args.blend.replace("\\", "/")
out_path   = args.output.replace("\\", "/")
os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)

bpy.ops.wm.open_mainfile(filepath=blend_path)

bpy.ops.export_scene.gltf(
    filepath=out_path,
    export_format='GLB',            # single binary; GLTF_SEPARATE for debug (human-readable JSON)
    export_apply=args.apply_mods,   # False = keep modifiers (preserves instancing/arrays)
    export_materials='EXPORT',      # 'NONE' = strip, 'PLACEHOLDER' = geometry only
    export_normals=True,
    export_image_format='AUTO',     # 'PNG' lossless; 'JPEG' for albedo only; 'WEBP' for web
    export_jpeg_quality=75,
    export_texture_dir='',          # empty = embed in GLB
    export_original_specular=False, # False = convert to KHR_materials_specular (recommended)
    export_animations=args.animations,
    export_yup=True,                # glTF is Y-up; Blender is Z-up; exporter handles this
    export_texcoords=True,
    export_colors=True,             # vertex colors
)

size_mb = os.path.getsize(args.output) / 1_048_576
print(f"[forge-material] GLB exported: {args.output} ({size_mb:.2f} MB)")
```

**Note on `export_apply`:** `export_apply=False` (default) is correct for most cases. Array /
Mirror / Subdivision modifiers remain non-destructive. Use `True` only if the engine can't handle
modifier data, or when you explicitly want to bake the modifier results. Using `True` on an Array
modifier with 100 instances makes the GLB 100× larger.

---

## §4. ORM Channel Packing JSON Schema

The complete glTF `pbrMetallicRoughness` block with ORM wiring:

```json
{
  "materials": [{
    "name": "MyMaterial",
    "pbrMetallicRoughness": {
      "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
      "baseColorTexture": { "index": 0, "texCoord": 0 },
      "metallicFactor": 1.0,
      "roughnessFactor": 1.0,
      "metallicRoughnessTexture": { "index": 1, "texCoord": 0 }
    },
    "normalTexture": {
      "index": 2,
      "texCoord": 0,
      "scale": 1.0
    },
    "occlusionTexture": {
      "index": 1,
      "texCoord": 0,
      "strength": 1.0
    }
  }]
}
```

**Key facts:**
- `metallicRoughnessTexture` and `occlusionTexture` can reference the same texture index (the ORM).
- `metallicRoughnessTexture.R` is unused by spec; `G = roughness`, `B = metallic`.
- `occlusionTexture` reads only the `R` channel; G and B are ignored.
- All these textures must be **LINEAR** (Non-Color). The spec assumes linear data.
- `baseColorTexture` and `emissiveTexture` are **sRGB** — the spec mandates sRGB decode.

**Texture wrap/filter defaults (trilinear, repeat — standard):**
```json
{
  "samplers": [{
    "wrapS": 10497,
    "wrapT": 10497,
    "magFilter": 9729,
    "minFilter": 9987
  }]
}
```
`wrapS/wrapT`: 10497 = REPEAT, 33071 = CLAMP_TO_EDGE, 33648 = MIRRORED_REPEAT.
`minFilter 9987` = LINEAR_MIPMAP_LINEAR (trilinear — best quality for mipmapped assets).

---

## §5. KHR_texture_transform (UV Tiling / Offset / Rotation)

```json
{
  "pbrMetallicRoughness": {
    "baseColorTexture": {
      "index": 0,
      "extensions": {
        "KHR_texture_transform": {
          "offset": [0.0, 0.5],
          "rotation": 0.392699,
          "scale": [4.0, 4.0],
          "texCoord": 0
        }
      }
    }
  }
}
```

In Blender Python — use `ShaderNodeMapping` with `vector_type = 'POINT'`:
```python
mapping.inputs['Location'].default_value = (offset_x, offset_y, 0.0)
mapping.inputs['Rotation'].default_value = (0.0, 0.0, rotation_z)  # Z = UV rotation
mapping.inputs['Scale'].default_value    = (scale_x, scale_y, 1.0)
```

**Gotcha:** UV origin (0,0) = UPPER LEFT in glTF. Three.js UV (0,0) = LOWER LEFT.
`GLTFLoader` flips V automatically — do not manually correct for this.

**Gotcha:** `KHR_texture_transform` only produces sane results with `wrapS/wrapT = REPEAT` (10497).
Using CLAMP_TO_EDGE with scale > 1 clips UV to [0,1] — tile effect disappears.

---

## §6. Validation: gltf-validator + gltf-transform + pygltflib

### Khronos glTF-Validator (authoritative — run this always)

```powershell
# Install once
npm install -g gltf-validator

# Validate and write JSON report
gltf-validator "C:\forge\out\scene.glb" --out "C:\forge\out\report.json"

# Quick PowerShell parse — show errors and warnings
$r = Get-Content "C:\forge\out\report.json" | ConvertFrom-Json
$r.issues.messages | Where-Object { $_.severity -le 1 } |
    Select-Object severity, code, message | Format-Table
# severity: 0=error, 1=warning, 2=info, 3=hint
```

Exit code 0 = valid. Exit code 1 = errors present. Warnings for missing TANGENT attributes
on anisotropy materials will appear here.

### gltf-transform quick audit

```powershell
# Inspect materials, extensions, texture dimensions
npx gltf-transform inspect "C:\forge\out\scene.glb"

# Pre-bake KHR_texture_transform into UV data (for engines that don't support the extension)
npx gltf-transform uv-transform "C:\forge\out\scene.glb" "C:\forge\out\scene_baked.glb"
```

### pygltflib programmatic inspection

```python
# pip install pygltflib (v1.16.5+)
from pygltflib import GLTF2
from pygltflib.validator import validate, summary

def audit_gltf_materials(glb_path: str) -> None:
    gltf = GLTF2().load(glb_path)
    validate(gltf)    # raises on schema violations (partial — always also run gltf-validator)
    summary(gltf)

    print(f"Extensions used:     {gltf.extensionsUsed}")
    print(f"Extensions required: {gltf.extensionsRequired}")

    for i, mat in enumerate(gltf.materials):
        pbr = mat.pbrMetallicRoughness
        print(f"\n--- Material {i}: {mat.name} ---")
        print(f"  alphaMode: {mat.alphaMode}, doubleSided: {mat.doubleSided}")
        if pbr:
            print(f"  baseColorFactor: {pbr.baseColorFactor}")
            print(f"  metallicFactor:  {pbr.metallicFactor}")
            print(f"  roughnessFactor: {pbr.roughnessFactor}")
        if mat.extensions:
            for ext_name, ext_data in mat.extensions.items():
                print(f"  [{ext_name}]: {ext_data}")
        # Flag anisotropy without normalTexture (missing tangent space)
        if mat.extensions and 'KHR_materials_anisotropy' in mat.extensions:
            print(f"  ANISOTROPY: normalTexture present = {mat.normalTexture is not None}")
            if not mat.normalTexture:
                print("  WARNING: anisotropy without normalTexture may lack tangent vectors")
```

Note: `pygltflib.validator` is partial — it only checks a subset of rules. Always run the
Khronos CLI `gltf-validator` for full spec compliance.

---

## §7. Export Pipeline Gotchas

**G1 — Diffuse BSDF / other BSDF nodes silently dropped**
- Detect: exported GLB has default gray material.
- Fix: switch all materials to Principled BSDF. Only Principled BSDF is fully supported.

**G2 — `export_apply=True` destroys instancing**
- Detect: Array modifier with 100 copies produces 100× larger GLB.
- Fix: leave `export_apply=False`. Apply modifiers in Blender manually only when required.

**G3 — Windows path backslashes in bpy export call**
- Symptom: `FileNotFoundError` or empty export.
- Fix: `filepath = os.path.abspath(out).replace("\\", "/")` before passing to `export_scene.gltf`.

**G4 — Clearcoat IOR is always 1.5 in glTF**
- `KHR_materials_clearcoat` uses fixed IOR=1.5 for the coat layer.
- `KHR_materials_ior` does NOT affect clearcoat. Spec limitation as of 2025.
- Artistic workaround: adjust `clearcoatFactor` to compensate.

**G5 — Transmission + alphaMode BLEND conflict**
- Glass with `transmission > 0` AND `alphaMode = BLEND` = undefined behavior in engines.
- Fix: glass uses `alphaMode = OPAQUE` + transmission. Transparency comes from the BTDF.

**G6 — Three.js transmission requires environment map**
- Detect: transmission material appears black or solid in Three.js.
- Fix: provide a scene environment (IBL) for the refracted light to sample from:
  ```javascript
  scene.environment = new THREE.RGBELoader().load('envmap.hdr');
  ```

**G7 — ORM imported as sRGB in engine**
- Detect: roughness/metallic behave incorrectly in Unreal or Unity.
- Fix: In UE5: Compression Settings → Masks (no sRGB). In Unity: uncheck sRGB in Inspector.

**G8 — Anisotropy texture normalization**
- Detect: anisotropy appears as noise or has dark patches.
- Fix: normalize ONLY the RG channels as a 2D vector. Do NOT include B (B = strength scalar).

**G9 — Non-manifold mesh with volume**
- `gltf-validator` does not check manifold; broken refraction at runtime.
- Fix: Blender Edit Mode → Select All → Mesh → Select → Non-Manifold; fill holes before export.

**G10 — KHR_texture_transform ignored by some engines**
- Detect: UV tiling looks wrong in target engine (tiles 1× instead of authored 4×).
- Fix: either add to `extensionsRequired`, or pre-bake with `gltf-transform uv-transform`.
