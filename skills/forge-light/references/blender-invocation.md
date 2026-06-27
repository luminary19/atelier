# forge-light — Blender Headless Invocation
# Windows-correct CLI patterns, GPU device flags, and path handling

## Canonical headless invocation (Windows PowerShell)

```powershell
# Mandatory argument order:
#   -b          = background (no GUI), MUST come first
#   --factory-startup = clean state (strips user prefs / addons); recommended for batch
#   -P <script> = Python script to execute
#   --          = separator (REQUIRED); everything after goes to sys.argv in script
#   <args>      = passed to the Python script

& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b `
    --factory-startup `
    -P "C:\forge\scripts\light_and_render.py" `
    -- `
    "C:\assets\widget.glb" `
    "C:\renders\widget_hero.png"
```

If you also have an existing `.blend` scene to load, put it before `-P`:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b "C:\projects\studio.blend" `
    -P "C:\forge\scripts\add_lighting.py" `
    -- --output "C:\renders\hero.png"
```

Add `--python-exit-code 1` to make Python errors fail the process (recommended for CI):
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b --factory-startup --python-exit-code 1 `
    -P "C:\forge\scripts\light_and_render.py" `
    -- "C:\assets\widget.glb" "C:\renders\out.png"
if ($LASTEXITCODE -ne 0) { throw "Blender script failed (exit $LASTEXITCODE)" }
```

## GPU device selection (Cycles headless)

```powershell
# OPTIX (NVIDIA RT cores — fastest on modern NVIDIA)
$env:CYCLES_CUDA_DEVELOPER_FLAGS = ""
& blender.exe -b --factory-startup -P render.py -- --cycles-device OPTIX

# CUDA (NVIDIA without RT)
& blender.exe -b --factory-startup -P render.py -- --cycles-device CUDA

# HIP (AMD GPUs)
& blender.exe -b --factory-startup -P render.py -- --cycles-device HIP

# CPU (always works headlessly; fallback for any environment)
& blender.exe -b --factory-startup -P render.py -- --cycles-device CPU
```

**Critical:** `--factory-startup` strips GPU device preferences from the session.
You must re-apply them inside the Python script:

```python
# In your .py script, after --factory-startup:
import bpy

def reset_gpu(compute_type: str = 'OPTIX'):
    """Re-apply GPU prefs stripped by --factory-startup."""
    try:
        prefs = bpy.context.preferences.addons['cycles'].preferences
        prefs.compute_device_type = compute_type   # 'OPTIX' | 'CUDA' | 'HIP'
        # refresh_devices() is the Blender 4.x API; get_devices() is the 3.x fallback
        try:
            prefs.refresh_devices()
        except AttributeError:
            prefs.get_devices()
        for d in prefs.devices:
            d.use = True
        bpy.data.scenes[0].cycles.device = 'GPU'
        print(f"[forge] GPU ({compute_type}) configured.")
    except Exception as e:
        print(f"[forge] GPU setup failed: {e}. Falling back to CPU.")
        bpy.data.scenes[0].cycles.device = 'CPU'
```

EEVEE Next on headless Windows: requires a real GPU context. For CI/batch production,
**Cycles is the correct default**. EEVEE Next headlessly on Windows is unsupported.

## Path handling in bpy (Windows)

**Always use forward slashes or `Path.as_posix()` in Blender API calls.**
Backslashes cause `RuntimeError` in `bpy.data.images.load()` and `scene.render.filepath`.

```python
from pathlib import Path

# WRONG — may raise RuntimeError on Windows
bpy.data.images.load(r"C:\forge\hdri_cache\studio_2k.hdr")

# CORRECT — forward slashes work on Windows in Blender
bpy.data.images.load("C:/forge/hdri_cache/studio_2k.hdr")

# SAFEST — Path.as_posix() normalizes regardless of input format
bpy.data.images.load(Path(r"C:\forge\hdri_cache\studio_2k.hdr").as_posix())

# Output paths follow the same rule
scene.render.filepath = Path(r"C:\renders\out\frame_####").as_posix()
```

## sys.argv parsing (args after --)

```python
import sys
import argparse

def parse_forge_args():
    """Parse arguments passed after the -- separator."""
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    else:
        argv = []

    p = argparse.ArgumentParser(description="Forge lighting script")
    p.add_argument("glb_path",  nargs='?', help="Path to .glb asset")
    p.add_argument("out_path",  nargs='?', default="C:/renders/out.png",
                   help="Output PNG path")
    p.add_argument("--samples", type=int, default=256)
    p.add_argument("--hdri",    help="Path to HDRI file (optional)")
    p.add_argument("--rig",     choices=["three-point", "ibl", "catalog"],
                   default="three-point")
    return p.parse_args(argv)
```

## stdout encoding fix (required for Windows cp1252 sessions)

```python
import sys, io

# Top of every Forge script that may output non-ASCII
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

## bpy.context vs bpy.data in headless mode

In `blender -b` mode with `--factory-startup`, `bpy.context` attributes are available
during operator execution but may be `None` in module-level code or timer callbacks.

**Safe headless pattern — use data-level access:**
```python
# WRONG in headless/timer context
scene = bpy.context.scene   # may be None

# CORRECT — always works headlessly
scene = bpy.data.scenes[0]
world = bpy.data.worlds[0] if bpy.data.worlds else bpy.data.worlds.new("ForgeWorld")
```

Exception: `bpy.context.view_layer.objects.active = obj` for operators that require
an active object (e.g., light linking). These are fine in the main script body.

## Blender version detection

```python
import bpy

major, minor, patch = bpy.app.version
print(f"Blender {major}.{minor}.{patch}")

# Feature availability
if major >= 4 and minor >= 0:
    print("AgX view transform available")
if major >= 4 and minor >= 0:
    print("Light linking available (Cycles)")
if major >= 5 and minor >= 0:
    print("ACEScg working space available")
```

## Headless invocation minimum checklist

Before dispatching a render script, verify:
- [ ] `-b` flag present (no GUI)
- [ ] `-P script.py` with absolute path
- [ ] `--` separator before any script arguments
- [ ] Script uses `bpy.data.scenes[0]`, not `bpy.context.scene`
- [ ] All image/HDRI paths use forward slashes
- [ ] `view_transform`, `gamma`, `exposure` set explicitly
- [ ] `film_transparent` + `color_mode = 'RGBA'` if transparent background
- [ ] `use_light_tree = True` if using light linking
- [ ] GPU prefs re-applied if `--factory-startup` is used with GPU render
