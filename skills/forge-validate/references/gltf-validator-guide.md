# Forge Validate — glTF-Validator Guide
# Contents
- §1. Install & invocation
- §2. Report JSON structure & severity levels
- §3. Common error codes and fixes
- §4. CI gate policy
- §5. glTF-Transform inspect

---

## §1. Install & Invocation

**Via npm (recommended — always current version):**
```powershell
npm install -g gltf-validator
# Verify:
gltf_validator.exe --version
```

**Prebuilt Windows exe (no Node needed):**
Download `gltf_validator-2.0.0-dev.3.10-windows.zip` from:
https://github.com/KhronosGroup/glTF-Validator/releases/tag/2.0.0-dev.3.10

```powershell
Expand-Archive gltf_validator-2.0.0-dev.3.10-windows.zip -DestinationPath C:\tools\gltf-validator
$env:PATH += ";C:\tools\gltf-validator"
```

**Single file validation:**
```powershell
# Machine-readable JSON report to stdout
$report = gltf_validator.exe --stdout "model.glb" | ConvertFrom-Json
$errors   = $report.issues.numErrors
$warnings = $report.issues.numWarnings
Write-Host "Errors: $errors  Warnings: $warnings"

# Gate: fail pipeline on any errors
if ($report.issues.numErrors -gt 0) {
    $report.issues.messages |
        Where-Object { $_.severity -eq 0 } |
        ForEach-Object { Write-Error "[$($_.code)] $($_.pointer) — $($_.message)" }
    exit 1
}
```

**File-based report (also generates .report.json alongside the GLB):**
```powershell
gltf_validator.exe -o --all -r "C:\output\model.glb"
# -o = output report file; --all = include info/hints; -r = report to .report.json
```

**Batch validation:**
```powershell
gltf_validator.exe -r "C:\forge_output\" --threads 0  # auto thread count
```

**Python subprocess wrapper:**
```python
import subprocess, json, pathlib

def run_gltf_validator(glb_path: str) -> dict:
    """Run gltf_validator CLI, return parsed report. Returns error dict if not installed."""
    try:
        result = subprocess.run(
            ["gltf_validator", "--stdout", glb_path],
            capture_output=True, text=True, timeout=30
        )
        return json.loads(result.stdout)
    except FileNotFoundError:
        return {"error": "gltf_validator not found — install with: npm install -g gltf-validator"}
    except Exception as e:
        return {"error": str(e)}
```

---

## §2. Report JSON Structure & Severity Levels

```json
{
  "uri": "model.glb",
  "mimeType": "model/gltf-binary",
  "validatorVersion": "2.0.0-dev.3.10",
  "issues": {
    "numErrors": 0,
    "numWarnings": 2,
    "numInfos": 1,
    "numHints": 0,
    "messages": [
      {
        "code": "IMAGE_NPOT_DIMENSIONS",
        "message": "Image has non-power-of-two dimensions: 960x540.",
        "severity": 1,
        "pointer": "/images/0"
      }
    ]
  },
  "info": {
    "version": "2.0",
    "generator": "Blender 5.1.0",
    "hasAnimations": false,
    "hasMorphTargets": false,
    "hasSkins": false,
    "hasTextures": true,
    "materialCount": 1,
    "meshCount": 1,
    "nodeCount": 3,
    "primitiveCount": 1,
    "vertexCount": 480
  }
}
```

**Severity levels:**

| Integer | Name | Meaning | Gate action |
|---------|------|---------|-------------|
| 0 | Error | Spec violation — invalid or will fail to load | BLOCK always |
| 1 | Warning | Legal but likely wrong — rendering issues | REVIEW vs brief |
| 2 | Info | Performance/best-practice note | NOTE |
| 3 | Hint | Minor suggestion | IGNORE |

---

## §3. Common Error Codes and Fixes

| Code | Severity | Cause | Fix |
|------|----------|-------|-----|
| `ACCESSOR_ELEMENT_OUT_OF_MAX_BOUND` | Error | Accessor min/max out of sync after geometry edit | Recompute: `accessor["min"] = positions.min(axis=0).tolist()` |
| `ACCESSOR_INDEX_TRIANGLE_DEGENERATE` | Info | Zero-area triangles from auto-triangulation | Manually triangulate in Blender (Ctrl+T) + Merge by Distance |
| `ACCESSOR_MISSING_BUFFER_VIEW` | Error | Draco + uncompressed accessor conflict | Use official Draco-aware exporter; don't mix |
| `BUFFER_BYTELENGTH_MISMATCH` | Error | Buffer byteLength doesn't match actual data | Rewrite GLB with correct byte counts |
| `EXTENSION_NOT_SUPPORTED` | Warning | Extension in extensionsRequired not in extensionsUsed | Add to extensionsUsed or remove from Required |
| `INCOMPATIBLE_EXTENSION` | Warning | Extension in Required without a non-extension fallback | Provide fallback mesh/texture or move to Used |
| `IMAGE_COLORSPACE_MISMATCH` | Warning | ORM/normal texture sampled as sRGB | Set non-color textures to "Non-Color" in Blender before export |
| `IMAGE_NPOT_DIMENSIONS` | Warning | Non-power-of-two texture (960×540) | Resize: `gltf-transform resize input.glb output.glb --width 1024 --height 1024` |
| `INVALID_URI` | Error | Backslash in texture URI: `textures\\base.png` | Use forward slashes: `textures/base.png` |
| `MESH_PRIMITIVE_ATTRIBUTES_ACCESSOR_INVALID_TYPE` | Error | Wrong accessor type for attribute (e.g., POSITION as SCALAR) | Fix accessor type in exporter |
| `MESH_PRIMITIVE_NO_POSITION` | Error | Primitive missing POSITION attribute | Ensure geometry is exported with vertex positions |
| `NODE_MATRIX_TRS` | Error | Node has both `matrix` and TRS properties | Remove one — use TRS for animated nodes |
| `UNUSED_OBJECT` | Info | Material/texture/mesh defined but not referenced | Clean up with `gltf-transform dedup` |

**extensionsRequired vs extensionsUsed rule (critical):**
An extension goes in `extensionsRequired` ONLY if a loader CANNOT render the asset without it:
- `KHR_draco_mesh_compression` with no uncompressed fallback → Required (geometry unavailable)
- `KHR_texture_basisu` with no PNG/JPEG fallback → Required (texture unavailable)
- `KHR_materials_clearcoat` → NEVER Required (core PBR is an acceptable fallback)

---

## §4. CI Gate Policy

**Forge standard:**
- `numErrors > 0` → BLOCK — fix before export/merge
- `numWarnings > 0` → REVIEW — document justification in FORGE.md if accepted
- Common acceptable warnings: `UNUSED_OBJECT` (debug material left in), `ACCESSOR_INDEX_TRIANGLE_DEGENERATE` (minor)

**PowerShell CI gate snippet:**
```powershell
param([string]$GlbPath)
$report = gltf_validator.exe --stdout $GlbPath | ConvertFrom-Json
if ($report.issues.numErrors -gt 0) {
    Write-Error "GLTF VALIDATION FAILED: $($report.issues.numErrors) errors"
    $report.issues.messages | Where-Object { $_.severity -eq 0 } |
        ForEach-Object { Write-Warning "  [$($_.code)] $($_.pointer): $($_.message)" }
    exit 1
}
Write-Host "[OK] glTF-Validator: 0 errors, $($report.issues.numWarnings) warnings"
```

---

## §5. glTF-Transform Inspect

```powershell
# Structural stats without validation
gltf-transform inspect input.glb

# Example output:
# MESH        Primitives  Vertices  Indices  Size
# MyMesh      1           2048      6144     24.0 KB
# TEXTURE     Format  Size (GPU)  Resolution
# base.png    PNG     5.3 MB      2048x2048

# Optimization pipeline (web delivery)
gltf-transform optimize input.glb output.glb --compress draco --texture-compress webp

# Weld duplicate vertices (10-30% typical size reduction)
gltf-transform weld input.glb output.glb

# Deduplicate identical meshes/textures
gltf-transform dedup input.glb output.glb

# Draco geometry compression
gltf-transform draco input.glb output.glb --method edgebreaker

# KTX2 for normal/ORM (quality-sensitive), then ETC1S for color
gltf-transform uastc input.glb step1.glb `
    --slots "{normalTexture,occlusionTexture,metallicRoughnessTexture}" `
    --level 4 --rdo --rdo-lambda 4 --zstd 18
gltf-transform etc1s step1.glb output.glb --quality 255
```

**glTF-Transform channel encoding rules (critical for correct PBR):**

| Texture role | Color space | Channel packing |
|-------------|-------------|----------------|
| baseColorTexture | sRGB | RGB = color, A = opacity |
| emissiveTexture | sRGB | RGB = glow color |
| metallicRoughnessTexture | LINEAR | B = metallic, G = roughness, R = unused |
| normalTexture | LINEAR | RGB = XYZ (OpenGL convention: +Y = up) |
| occlusionTexture | LINEAR | R = AO (G, B unused) |

**DirectX → OpenGL normal map fix (invert green channel):**
```python
from PIL import Image
import numpy as np
img = np.array(Image.open("normal_dx.png"))
img[:, :, 1] = 255 - img[:, :, 1]  # flip green channel
Image.fromarray(img).save("normal_gl.png")
```
