# glTF Validation, GLB Structure & KHR Extensions
# forge-export | references/gltf-validator.md

## Contents
- §1. glTF-Validator install and headless invocation
- §2. GLB binary layout (byte structure)
- §3. pbrMetallicRoughness material model
- §4. Channel encoding rules (sRGB vs linear)
- §5. KHR extensions reference table
- §6. Common validator errors and fixes
- §7. gltf-transform CLI (pre-flight inspection)

---

## §1. glTF-Validator install and headless invocation

**Install (npm — recommended for CI):**
```powershell
npm install -g gltf-validator
gltf-validator --version
```

**Install pre-built Windows exe (no Node needed):**
```powershell
# Download: https://github.com/KhronosGroup/glTF-Validator/releases/tag/2.0.0-dev.3.10
# File: gltf_validator-2.0.0-dev.3.10-windows.zip
Expand-Archive gltf_validator-2.0.0-dev.3.10-windows.zip -DestinationPath C:\tools\gltf-validator
$env:PATH += ";C:\tools\gltf-validator"
```

**Headless invocation (PowerShell):**
```powershell
# Validate single file — fail pipeline on any errors
gltf_validator.exe -o --all -r "C:\output\model.glb"
if ($LASTEXITCODE -ne 0) { Write-Error "glTF validation FAILED"; exit 1 }

# Parse JSON report programmatically
$report = gltf_validator.exe --stdout "C:\output\model.glb" | ConvertFrom-Json
$errors   = $report.issues.numErrors
$warnings = $report.issues.numWarnings
Write-Host "Errors: $errors  Warnings: $warnings"

# List all error messages
$report.issues.messages | Where-Object {$_.severity -eq 0} | ForEach-Object {
    Write-Warning "ERROR [$($_.code)] pointer=$($_.pointer) — $($_.message)"
}

# Batch validate a directory
gltf_validator.exe -r "C:\forge_output\" --threads 0
```

**Severity levels:**
| Integer | Name | Meaning | CI action |
|---|---|---|---|
| 0 | Error | Spec violation — will fail to load | BLOCK |
| 1 | Warning | Legal but likely wrong | WARN |
| 2 | Info | Performance/best-practice note | NOTE |
| 3 | Hint | Minor suggestion | IGNORE |

**CI policy:** fail pipeline on `numErrors > 0`. Allow warnings with documented justification.

---

## §2. GLB binary layout

```
Offset   Size  Field        Value
------------------------------------------
0        4     magic        0x46546C67  ("glTF" ASCII) ← verify this first
4        4     version      2           (uint32)
8        4     length       total file bytes (uint32)

--- Chunk 0 (JSON, REQUIRED) ---
12       4     chunkLength  byte count, padded to 4-byte boundary (uint32)
16       4     chunkType    0x4E4F534A  ("JSON" ASCII)
20       N     chunkData    UTF-8 JSON, padded with 0x20 (space)

--- Chunk 1 (BIN, usually present) ---
20+N     4     chunkLength  byte count, padded to 4-byte boundary (uint32)
24+N     4     chunkType    0x004E4942  ("BIN\0" ASCII)
28+N     M     chunkData    raw binary, padded with 0x00
```

**Rules:**
- Chunk lengths must be 4-byte aligned. JSON padded with spaces (0x20); BIN with nulls (0x00).
- BIN chunk may be up to 3 bytes larger than `buffer.byteLength` due to alignment.
- If BIN chunk present, `buffers[0]` MUST have no `uri` property.
- GLB hard limit: BIN chunk max 2^32-1 bytes (~4 GB).

**Python: parse and verify GLB magic:**
```python
import struct, sys

def parse_glb(path: str) -> dict:
    with open(path, "rb") as f:
        data = f.read()
    magic, version, total_len = struct.unpack_from("<4sII", data, 0)
    assert magic == b"glTF", f"Bad magic: {magic!r}"
    assert version == 2, f"Unsupported version: {version}"
    offset = 12
    chunks = []
    while offset < total_len:
        chunk_len, chunk_type = struct.unpack_from("<II", data, offset)
        chunks.append({"type": hex(chunk_type), "length": chunk_len})
        offset += 8 + chunk_len
    return {"version": version, "total_bytes": total_len, "chunks": chunks}

if __name__ == "__main__":
    import json
    print(json.dumps(parse_glb(sys.argv[1]), indent=2))
```

**Python: assemble a hand-built GLB (correct padding):**
```python
import struct

def pack_glb(json_bytes: bytes, bin_bytes: bytes) -> bytes:
    json_pad = (4 - len(json_bytes) % 4) % 4
    json_chunk_data = json_bytes + b' ' * json_pad
    bin_pad = (4 - len(bin_bytes) % 4) % 4
    bin_chunk_data = bin_bytes + b'\x00' * bin_pad
    json_chunk = struct.pack('<II', len(json_chunk_data), 0x4E4F534A) + json_chunk_data
    bin_chunk  = struct.pack('<II', len(bin_chunk_data),  0x004E4942) + bin_chunk_data
    header     = struct.pack('<4sII', b'glTF', 2, 12 + len(json_chunk) + len(bin_chunk))
    return header + json_chunk + bin_chunk
```

---

## §3. pbrMetallicRoughness material model

```json
{
  "materials": [{
    "name": "MyMaterial",
    "pbrMetallicRoughness": {
      "baseColorFactor": [1.0, 1.0, 1.0, 1.0],
      "baseColorTexture": { "index": 0, "texCoord": 0 },
      "metallicFactor": 1.0,
      "roughnessFactor": 1.0,
      "metallicRoughnessTexture": {
        "index": 1, "texCoord": 0
        // B channel = metallic, G channel = roughness, R channel unused by core spec
      }
    },
    "normalTexture": {
      "index": 2, "texCoord": 0,
      "scale": 1.0
      // OpenGL convention: +X=right, +Y=up, +Z=toward viewer
    },
    "occlusionTexture": {
      "index": 3, "texCoord": 0,
      "strength": 1.0
      // R channel only; 1.0=full light, 0.0=full shadow
    },
    "emissiveTexture": { "index": 4, "texCoord": 0 },
    "emissiveFactor": [0.0, 0.0, 0.0],
    "alphaMode": "OPAQUE",
    "alphaCutoff": 0.5,
    "doubleSided": false
  }]
}
```

**Alpha modes:**
| Mode | Behavior | Use case |
|---|---|---|
| OPAQUE | Alpha ignored | Metals, stone, most surfaces |
| MASK | Fully opaque if alpha ≥ alphaCutoff, else transparent | Leaves, hair cards, chain-link |
| BLEND | Porter-Duff "over" compositing | Glass, gauze — order-dependent! |

---

## §4. Channel encoding rules (sRGB vs linear) — CRITICAL

| Map | Color space | Notes |
|---|---|---|
| `baseColorTexture` | **sRGB** | GPU decodes gamma on sample |
| `emissiveTexture` | **sRGB** | Same |
| `metallicRoughnessTexture` | **LINEAR** | B=metallic, G=roughness — no gamma decode |
| `normalTexture` | **LINEAR** | Raw XYZ vector data |
| `occlusionTexture` | **LINEAR** | R channel scalar |

**In Blender:** Set all non-color textures (ORM, normal, roughness, metallic, AO, displacement)
to "Non-Color" in the Image Texture node. The glTF exporter respects this setting.
Forgetting this is the #1 cause of `IMAGE_COLORSPACE_MISMATCH` warnings.

**Normal map convention:** glTF uses OpenGL (+Y = up/green = bright for surfaces facing up).
DirectX normals (from Substance Painter "DirectX" preset) have the green channel inverted.

**Python fix for DirectX → OpenGL normal map:**
```python
from PIL import Image
import numpy as np
img = np.array(Image.open("normal_dx.png"))
img[:, :, 1] = 255 - img[:, :, 1]   # flip green channel
Image.fromarray(img).save("normal_gl.png")
```

---

## §5. KHR extensions reference table

| Extension | What it adds | In extensionsRequired? |
|---|---|---|
| `KHR_draco_mesh_compression` | ~10x lossy geometry compression | YES (no fallback mesh without it) |
| `KHR_texture_basisu` | KTX2 with ETC1S/UASTC supercompression | YES if no PNG/JPEG fallback |
| `KHR_mesh_quantization` | Vertex attributes from FLOAT32 → INT8/INT16 (~60% size reduction) | YES (no float fallback) |
| `KHR_meshopt_compression` | Lossless/configurable; better streaming than Draco | YES if no fallback |
| `KHR_lights_punctual` | Directional / point / spot lights | NO (core PBR is fine fallback) |
| `KHR_materials_variants` | Multiple named material variants on shared geometry | NO |
| `KHR_materials_clearcoat` | Automotive clear coat layer | NO |
| `KHR_materials_transmission` | Glass / thin translucency | NO |
| `KHR_materials_volume` | Volumetric absorption + scattering | NO |
| `KHR_materials_ior` | Index of refraction override | NO |
| `KHR_materials_sheen` | Fabric sheen | NO |
| `KHR_materials_specular` | Specular intensity/color for dielectrics | NO |
| `KHR_materials_emissive_strength` | emissiveFactor multiplier > 1.0 (for HDR bloom) | NO |
| `KHR_materials_anisotropy` | Brushed metal anisotropic reflections | NO |
| `KHR_materials_unlit` | Shadeless rendering | NO |
| `KHR_materials_iridescence` | Thin-film iridescence | NO |
| `KHR_texture_transform` | UV offset/scale/rotation per texture channel | NO |

**Rule on `extensionsRequired`:** An extension goes in `extensionsRequired` ONLY if a loader
CANNOT render the asset without it. Physical material extensions (clearcoat, transmission, etc.)
must NEVER be in `extensionsRequired` — the core PBR response is an acceptable fallback.

---

## §6. Common validator errors and fixes

| Error code | Meaning | Fix |
|---|---|---|
| `IMAGE_COLORSPACE_MISMATCH` | ORM/normal imported as sRGB | Set Image Texture nodes to Non-Color in Blender |
| `IMAGE_NPOT_DIMENSIONS` | Non-power-of-two texture | `gltf-transform resize input.glb output.glb --width 1024 --height 1024` |
| `ACCESSOR_INDEX_TRIANGLE_DEGENERATE` | Zero-area triangles | Manual Triangulate + Merge by Distance in Blender Edit Mode |
| `GLB_CHUNK_LENGTH_UNALIGNED` | Hand-assembled GLB missing padding | Use `pack_glb()` from §2 |
| `ACCESSOR_ELEMENT_OUT_OF_MAX_BOUND` | accessor min/max out of sync after geometry edit | Recompute `accessor["min/max"]` from vertex data |
| `INVALID_URI` | Windows backslash in URI | Forward slashes only: `"textures/base.png"` |
| `EXTENSION_NOT_SUPPORTED` | Extension in extensionsRequired but viewer can't handle it | Move to extensionsUsed or provide uncompressed fallback |
| `ACCESSOR_MISSING_BUFFER_VIEW` | Draco accessor still has bufferView | Use official Draco-aware exporters; never manually add bufferViews for Draco attrs |

---

## §7. gltf-transform CLI (inspection)

```powershell
# Install once globally
npm install -g @gltf-transform/cli

# Inspect asset structure (human-readable)
gltf-transform inspect input.glb

# Inspect as JSON
gltf-transform inspect input.glb --format json

# Deduplicate identical meshes/textures (before further processing)
gltf-transform dedup input.glb output.glb

# Weld duplicate vertices (10-30% size reduction)
gltf-transform weld input.glb output.glb

# Resize all textures to max 1024x1024
gltf-transform resize input.glb output.glb --width 1024 --height 1024

# Quick optimization: Draco + WebP
gltf-transform optimize input.glb output.glb --compress draco --texture-compress webp

# Meshopt (alternative to Draco — lossless, better streaming)
gltf-transform meshopt input.glb output.glb
```

Note: Deep optimization (KTX2, Draco, meshopt for web delivery) belongs in **forge-optimize**,
not here. Use gltf-transform here only for inspection and pre-validation fixes.
