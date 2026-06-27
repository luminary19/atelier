# Forge Texture — Headless Invocation & Compression Reference

## Contents
- §1. Blender headless invocation patterns (Windows)
- §2. GPU device setup from Python
- §3. Complete PowerShell bake pipeline script
- §4. KTX2 compression (ktx CLI)
- §5. WebP conversion (Pillow)
- §6. POT resize guard (required for glTF KHR_texture_basisu)

---

## §1. Blender Headless Invocation Patterns (Windows)

### Basic form (PowerShell)

```powershell
# Canonical Forge invocation — all flags in this order, -- MANDATORY before script args
& "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe" `
    --background "C:/path/to/scene.blend" `
    --python     "C:/path/to/bake_script.py" `
    --python-exit-code 1 `
    -- `
    --lowpoly "Hero_LP" --highpoly "Hero_HP" --out "C:/out" --res 2048
```

### No-blend-file variant (build scene from scratch in Python)

```powershell
& blender --background --python "C:/forge/scripts/forge_bake_procedural.py" --python-exit-code 1
```

### Force Cycles device from CLI (avoid relying on user prefs)

```powershell
& blender --background scene.blend --python bake.py --python-exit-code 1 `
    -- --cycles-device OPTIX     # or CUDA, HIP, CPU
```

Then in the Python script, read it from `sys.argv` after `--`:
```python
import sys, argparse
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--cycles-device", default="CPU")
args = ap.parse_args(argv)
# Apply:
bpy.context.preferences.addons["cycles"].preferences.compute_device_type = args.cycles_device.upper()
```

### Key flags reference

| Flag | Short | Description |
|------|-------|-------------|
| `--background` | `-b` | No GUI. Required for headless. |
| `--python <file>` | `-P` | Run Python script after loading. |
| `--python-exit-code 1` | | Return exit code 1 if script raises an exception. Always include. |
| `--python-expr "<code>"` | `-E` | Run a single Python expression inline. |
| `--` | | Separator: everything after is passed to the Python script via `sys.argv`. MANDATORY when passing script args. |
| `--cycles-device <type>` | | Override GPU device: `OPTIX`, `CUDA`, `HIP`, `ONEAPI`, `CPU`. |
| `--enable-autoexec` | `-y` | Allow scripts embedded in .blend. Only needed for .blend-internal scripts. |

**CRITICAL:** The `--` separator is mandatory whenever you pass arguments to the Python script.
Omitting it causes Blender to try to interpret your args as its own flags, producing confusing errors.

### Finding the Blender executable on Windows

```powershell
# Check common install locations
$candidates = @(
    "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
)
$BLENDER = ($candidates | Where-Object { Test-Path $_ } | Select-Object -First 1)
if (-not $BLENDER) { $BLENDER = (Get-Command blender -ErrorAction SilentlyContinue)?.Source }
if (-not $BLENDER) { Write-Error "Blender not found"; exit 1 }
Write-Host "Using: $BLENDER"
```

---

## §2. GPU Device Setup from Python

**Always call `refresh_devices()` after setting `compute_device_type` — otherwise the device list
is empty and enabling GPUs has no effect.**

```python
def setup_gpu(prefer: str = "OPTIX") -> str:
    """
    Enable GPU in Cycles. Must be called before bpy.ops.object.bake().
    Returns activated device type string.
    prefer: 'OPTIX' (NVIDIA RTX+), 'CUDA' (NVIDIA Maxwell+), 'HIP' (AMD), 'CPU'
    """
    prefs = bpy.context.preferences.addons["cycles"].preferences
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"

    order = {
        "OPTIX": ["OPTIX", "CUDA", "HIP", "ONEAPI", "CPU"],
        "CUDA":  ["CUDA", "OPTIX", "HIP", "ONEAPI", "CPU"],
        "CPU":   ["CPU"],
    }.get(prefer.upper(), ["OPTIX", "CUDA", "HIP", "ONEAPI", "CPU"])

    for device_type in order:
        if device_type == "CPU":
            scene.cycles.device = "CPU"
            print("[forge] Using CPU")
            return "CPU"
        try:
            prefs.compute_device_type = device_type
            prefs.refresh_devices()        # <-- REQUIRED
            gpu_devs = [d for d in prefs.devices if d.type != "CPU"]
            if gpu_devs:
                for d in prefs.devices:
                    d.use = (d.type != "CPU")
                scene.cycles.device = "GPU"
                print(f"[forge] GPU: {device_type} ({len(gpu_devs)} device(s))")
                return device_type
        except (TypeError, AttributeError):
            continue

    scene.cycles.device = "CPU"
    return "CPU"
```

**Windows-specific:** OptiX may fail when the process has no interactive display driver context
(service accounts, certain CI environments). If OptiX fails, fall back to CUDA or CPU:
the `setup_gpu()` function above handles this automatically via the fallback order.

---

## §3. Complete PowerShell Bake Pipeline Script

```powershell
# forge_bake_pipeline.ps1
# Bakes a full PBR set: normal, AO, curvature, roughness, albedo.
# Usage: .\forge_bake_pipeline.ps1 -Blend scene.blend -LowPoly Hero_LP -HighPoly Hero_HP -OutDir C:\out

param(
    [Parameter(Mandatory)][string]$Blend,
    [Parameter(Mandatory)][string]$LowPoly,
    [Parameter(Mandatory)][string]$HighPoly,
    [Parameter(Mandatory)][string]$OutDir,
    [string]$Resolution = "2048",
    [string]$Samples    = "64",
    [string]$Device     = "OPTIX",
    [string]$NormalG    = "POS_Y"   # POS_Y=OpenGL, NEG_Y=DirectX/Unreal
)

$BLENDER = "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
$SCRIPT  = "$env:CLAUDE_CONFIG_DIR\skills\forge-texture\scripts\bake_pbr.py"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Normalize paths to forward slashes for Blender filepath_raw
$BlendFwd  = $Blend   -replace "\\", "/"
$OutDirFwd = $OutDir  -replace "\\", "/"

& $BLENDER `
    --background $BlendFwd `
    --python     $SCRIPT `
    --python-exit-code 1 `
    -- `
    --lowpoly  $LowPoly `
    --highpoly $HighPoly `
    --out      $OutDirFwd `
    --res      $Resolution `
    --samples  $Samples `
    --device   $Device `
    --normal-g $NormalG

if ($LASTEXITCODE -ne 0) {
    Write-Error "[forge] Bake failed (exit $LASTEXITCODE)"
    exit 1
}
Write-Host "[forge] Bake complete -> $OutDir"
```

---

## §4. KTX2 Compression (ktx CLI)

Install: `KTX-Software-4.3.2-Windows-x64.exe` from GitHub Releases → KhronosGroup/KTX-Software.
Add install dir to PATH. The CLI command is `ktx` (not `toktx`, which is deprecated in v4.3+).

```powershell
# Albedo / diffuse — ETC1S (smaller, ~10:1 compression, universally transcodeable)
ktx create `
    --encode etc1s `
    --format R8G8B8_SRGB `
    --assign-tf srgb `
    --clevel 1 `
    --qlevel 192 `
    input_albedo.png `
    output_albedo.ktx2

# Normal map — UASTC (higher quality, critical for lighting accuracy)
ktx create `
    --encode uastc-ldr-4x4 `
    --format R8G8B8_UNORM `
    --uastc-quality 2 `
    input_normal_gl.png `
    output_normal.ktx2

# Roughness / Metallic — ETC1S single channel
ktx create `
    --encode etc1s `
    --format R8_UNORM `
    --clevel 1 --qlevel 128 `
    input_roughness.png `
    output_roughness.ktx2

# AO — ETC1S single channel
ktx create `
    --encode etc1s `
    --format R8_UNORM `
    --clevel 1 --qlevel 128 `
    input_ao.png `
    output_ao.ktx2

# Validate for glTF + WebGL compatibility
ktx validate --gltf-basisu output_albedo.ktx2
```

### Encode quality guide

| Map | Encode | Format | Notes |
|-----|--------|--------|-------|
| Albedo (sRGB) | `etc1s` | `R8G8B8_SRGB` | Small file, good color fidelity |
| Normal | `uastc-ldr-4x4` | `R8G8B8_UNORM` | Higher quality needed for normals |
| Roughness | `etc1s` | `R8_UNORM` | Single channel; ETC1S fine |
| Metallic | `etc1s` | `R8_UNORM` | Single channel |
| AO | `etc1s` | `R8_UNORM` | Single channel |
| Height (HDR) | Not KTX2 | Use EXR | KTX2 is for GPU-transcoded 8-bit textures |

---

## §5. WebP Conversion (Pillow)

```python
from PIL import Image

# Lossy WebP — good for albedo/diffuse (quality 85-92)
img = Image.open(r"C:\tmp\albedo.png")
img.save(r"C:\tmp\albedo.webp", quality=88, method=6, lossless=False)

# Lossless WebP — for normal maps / data textures
img = Image.open(r"C:\tmp\normal_gl.png")
img.save(r"C:\tmp\normal_gl.webp", lossless=True)
```

**Note:** Lossless WebP is larger than PNG for normal maps. Use KTX2 (UASTC) for web delivery of
normal maps; WebP is mainly useful for albedo poster images and fallback previews.

---

## §6. POT Resize Guard (Required for glTF KHR_texture_basisu)

The glTF `KHR_texture_basisu` extension requires power-of-two (POT) dimensions for WebGL 1.0
compatibility. `ktx validate --gltf-basisu` will fail on non-POT inputs.

```python
from PIL import Image

def ensure_pot(img_path: str, out_path: str = None) -> str:
    """
    Resize image to next power-of-two dimensions if not already POT.
    Returns the output path (modified in-place if out_path is None).
    """
    out_path = out_path or img_path
    img = Image.open(img_path)
    w, h = img.size
    pw = 2 ** (w - 1).bit_length()
    ph = 2 ** (h - 1).bit_length()
    if (w, h) == (pw, ph):
        print(f"[forge] Already POT: {w}x{h}")
        return out_path
    img_resized = img.resize((pw, ph), Image.LANCZOS)
    img_resized.save(out_path)
    print(f"[forge] Resized {w}x{h} -> {pw}x{ph}: {out_path}")
    return out_path

# Example: ensure_pot(r"C:\tmp\albedo.png", r"C:\tmp\albedo_pot.png")
```

**Rule:** Always run `ensure_pot` before `ktx create` for web delivery targets. Bake maps at POT
resolutions (512, 1024, 2048, 4096) from the start to avoid resizing losses.
