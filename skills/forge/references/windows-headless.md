# Windows Headless 3D — Non-Negotiable Truths

> These rules apply to EVERY Forge skill and agent without exception. Violating any of them causes
> silent failures, wrong-path renders, or crashes. Read this before writing any Blender/OpenSCAD
> invocation. Platform: native Windows 11, no WSL, PowerShell-first.

---

# Contents
- §1. Blender headless invocation rules
- §2. EEVEE vs Cycles — the Windows headless constraint
- §3. OpenSCAD headless invocation
- §4. Python environment rules
- §5. Path handling — forward slashes, absolute paths, `//` trap
- §6. gltf-transform / Node.js dependencies
- §7. Gotcha → fix table

---

## §1. Blender headless invocation rules

### Canonical pattern

```powershell
# PowerShell — from any working directory
& blender --background "C:/project/scene.blend" `
          --python "C:/project/scripts/render.py" `
          --python-exit-code 1 `
          -- `
          --out "C:/project/.forge-build/out/hero.png" `
          --engine CYCLES `
          --samples 64
```

### Breakdown — each flag matters

| Flag | Required | Why |
|---|---|---|
| `--background` / `-b` | YES | Headless mode. Without it, Blender tries to open a window. |
| `scene.blend` (positional arg) | YES (if loading a file) | Load the blend file. Must be absolute path or resolve from CWD. |
| `--python script.py` / `-P script.py` | YES (for API scripts) | Execute a Python script inside Blender's embedded Python. |
| `--python-exit-code 1` | YES | Makes Python exceptions fail the process with exit code 1 so PowerShell can catch them. Without this, a Python error silently produces a zero exit code. |
| `--` | MANDATORY | Everything before `--` is parsed as Blender arguments. Everything after is passed to `sys.argv` in the Python script. FORGETTING `--` means your `--out` flag gets parsed as a Blender flag and causes a cryptic failure. |
| `--out`, `--engine`, etc. | After `--` | Your script's own arguments — passed via `sys.argv`. |

### Parsing args inside the script

```python
import sys

# Strip everything before '--'
argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

import argparse
parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--engine", default="CYCLES")
parser.add_argument("--samples", type=int, default=64)
args = parser.parse_args(argv)
```

### Capturing output and errors

```powershell
# Capture stdout + stderr together; write to log file for post-mortem
& blender -b scene.blend -P script.py --python-exit-code 1 -- --out out.png `
  2>&1 | Tee-Object -FilePath ".forge-build/blender.log"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Blender exited with code $LASTEXITCODE — check .forge-build/blender.log"
}
```

### Quitting Blender from inside a script

```python
import bpy, sys
# At the very end of any bpy script:
bpy.ops.wm.quit_blender()
# OR (if bpy.ops not available in context):
sys.exit(0)
```

If neither is called, Blender may hang in headless mode waiting for more commands.

---

## §2. EEVEE vs Cycles — the Windows headless constraint

**RULE: Always use Cycles for headless renders on Windows.**

EEVEE Next (Blender 4.x) requires an OpenGL/Vulkan context backed by a real display server or a
virtual framebuffer (VirtualGL, Xvfb, ANGLE). On native Windows without these:

- `blender -b ... -E BLENDER_EEVEE_NEXT` → crash or all-black PNG output.
- No error in stdout; `$LASTEXITCODE` may still be 0 (Blender returns 0 even on render failure in some versions).

### Correct Cycles setup in a bpy script

```python
import bpy

scene = bpy.context.scene
scene.render.engine = 'CYCLES'

# CPU-only — guaranteed to work anywhere on Windows
cycles_prefs = bpy.context.preferences.addons["cycles"].preferences
cycles_prefs.compute_device_type = 'NONE'  # CPU

# Optional: if you want to probe for GPU, but always fall back to CPU
# cycles_prefs.compute_device_type = 'CUDA'  # only if NVIDIA driver present
# for device in cycles_prefs.devices:
#     device.use = True

scene.cycles.device = 'CPU'
scene.cycles.samples = 64          # QA: 16-32; final beauty: 128-256
scene.cycles.use_denoising = True   # Intel OpenImageDenoise — CPU-based, works everywhere
```

### When to use Workbench

Blender Workbench (`BLENDER_WORKBENCH`) is a solid-color/matcap renderer that DOES work headless on
Windows. Use it for:
- Fast wireframe renders (no texture sampling required).
- Normals/UV-checker visualization passes.
- Build validation where material fidelity is not required.

```python
scene.render.engine = 'BLENDER_WORKBENCH'
scene.display.shading.type = 'WIREFRAME'   # or 'MATERIAL', 'SOLID'
```

---

## §3. OpenSCAD headless invocation

### CRITICAL: Use `openscad.com`, not `openscad.exe`

On Windows, OpenSCAD ships two executables:
- `openscad.exe` — launches the GUI application (allocates a console window, does not run headlessly).
- `openscad.com` — the true headless/console version; required for scripted use.

```powershell
# CORRECT — headless
& openscad.com -o "C:/project/out/part.stl" "C:/project/model.scad" -D "param=10"

# WRONG — opens GUI
& openscad.exe -o "..." "..."  # may hang or fail headlessly
```

### Parameter override syntax

```powershell
# Multiple -D flags for multiple parameters:
& openscad.com -o out.stl model.scad `
    -D "wall_thickness=2.5" `
    -D "height=50" `
    -D "$fn=64"        # special variable: facets per circle
```

### Common output formats

```powershell
openscad.com -o out.stl   model.scad   # STL for printing
openscad.com -o out.png   model.scad --render --imgsize=1920,1080  # PNG render
openscad.com -o out.svg   model.scad   # 2D SVG (for 2D models)
openscad.com -o out.amf   model.scad   # AMF (multi-material)
openscad.com -o out.3mf   model.scad   # 3MF (preferred for printing)
```

### Version check

```powershell
openscad.com --version   # should print OpenSCAD version string
```

---

## §4. Python environment rules

### Always `python`, never `python3`

Windows installs `python.exe`, not `python3.exe`. Using `python3` causes:
```
python3 : The term 'python3' is not recognized as a name of a cmdlet...
```

All Forge scripts and all documentation must use `python`.

### Blender's embedded Python vs system Python

Blender ships its own embedded Python (~3.11 in Blender 4.x). This Python:
- Can only be used from inside a `--python` script (via `bpy`).
- Cannot install packages via `pip` from outside.
- Has access to: `bpy`, `bmesh`, `mathutils`, `bpy_extras`, and the stdlib.
- Does NOT have `numpy`, `scipy`, `PIL`, or other third-party packages unless Blender bundles them.

System Python (the `python` in PATH):
- Used for all non-Blender Forge scripts (probe.py, search.py, validate.py, etc.).
- Pure stdlib only in utility scripts.
- Can `import numpy` if installed, but do not depend on it in probes.

### UTF-8 stdout fix (required in all scripts)

```python
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
```

Add this at the top of every Forge Python script. Windows cp1252 default stdout encoding causes crashes
on degree symbols (°), arrows (→), and Unicode characters in Blender output.

### CSV reading — BOM-safe

```python
import csv
with open("data.csv", "r", encoding="utf-8-sig") as f:
    rows = list(csv.DictReader(f))
```

`utf-8-sig` strips the UTF-8 BOM (byte-order mark) that Excel-saved CSVs include. Without it, the
first column header has a garbage prefix that breaks dictionary lookups.

---

## §5. Path handling — forward slashes, absolute paths, `//` trap

### Rule: always forward slashes in Blender `filepath`

```python
# CORRECT
scene.render.filepath = "C:/project/public/forge/hero-poster.png"

# CORRECT (raw string, backslashes OK in Python but not preferred)
scene.render.filepath = r"C:\project\public\forge\hero-poster.png"

# WRONG — Blender interprets // as "relative to .blend file location"
scene.render.filepath = "//hero-poster.png"   # outputs to .blend directory, not project
scene.render.filepath = "//public/forge/hero-poster.png"  # ALSO wrong
```

### Rule: always absolute paths

```python
from pathlib import Path
import os

# CORRECT
out = Path("C:/project/.forge-build/out/hero.png").resolve()
scene.render.filepath = out.as_posix()  # Windows → forward slashes

# CORRECT in PowerShell
$out = [System.IO.Path]::GetFullPath(".\public\forge\hero.glb")
```

Never use relative paths in Blender script arguments — Blender's CWD inside `-b` mode is not
predictable and may not match PowerShell's CWD.

### In Git Bash (Bash tool)

Git Bash accepts POSIX paths: `/c/Users/you/...` maps to `C:\Users\you\...`. Either form works:
```bash
blender -b "/c/project/scene.blend" -P "/c/project/script.py" -- --out "/c/project/out.png"
```

### In PowerShell

Use the call operator `&` to run executables with spaces in path:
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" -b ...
```

---

## §6. gltf-transform / Node.js dependencies

### Dependency check before running

```powershell
node --version          # confirm Node.js installed; LTS recommended
npm --version
npx gltf-transform --version   # confirm @gltf-transform/cli installed globally
toktx --version         # confirm KTX-Software installed (for --texture-compress ktx2)
```

### Installation (one-time)

```powershell
# Install gltf-transform CLI globally
npm install -g @gltf-transform/cli

# Install KTX-Software for KTX2 texture compression (optional but recommended for web)
# Download Windows installer from: https://github.com/KhronosGroup/KTX-Software/releases
# After install, toktx.exe is in PATH
```

### Standard optimize command

```powershell
npx gltf-transform optimize in.glb out.glb --meshopt --quantize
```

### With KTX2 texture compression

```powershell
npx gltf-transform optimize in.glb out-ktx2.glb --meshopt --quantize --texture-compress ktx2
```

### Fallback when toktx is missing

```powershell
npx gltf-transform optimize in.glb out.glb --meshopt --quantize --texture-compress webp
# WebP is ImageMagick-based; reduces texture size without GPU-native compression
```

---

## §7. Gotcha → fix table

| Symptom | Root cause | Fix |
|---|---|---|
| Render produces all-black PNG | EEVEE Next in headless mode on Windows | Set `scene.render.engine = 'CYCLES'` |
| `blender` exits 0 but no PNG written | Missing `bpy.ops.wm.quit_blender()` or `--python-exit-code 1` not set | Add exit call at end of script; add `--python-exit-code 1` |
| `--out` flag causes "unknown option" Blender error | Missing `--` separator | Add `--` between Blender flags and script args |
| `python3: not recognized` | Windows uses `python.exe` | Use `python` everywhere |
| Script output has garbled characters | Default cp1252 stdout | Add UTF-8 stdout wrapper at top of script |
| CSV first column has garbage prefix | Excel BOM in CSV | Open with `encoding='utf-8-sig'` |
| `openscad.exe` hangs or opens GUI | Wrong executable | Use `openscad.com` not `.exe` |
| `//hero.png` renders to .blend directory | `//` = blend-relative in Blender | Use absolute forward-slash path |
| `gltf-transform: command not found` | Node.js or CLI not installed | `npm install -g @gltf-transform/cli` |
| `toktx not found` | KTX-Software not installed | Install from KhronosGroup/KTX-Software releases |
| DRACO compression has no effect | Blender < 4.2 built-in glTF addon | Use `npx gltf-transform optimize --draco` post-export instead |
| Agent doesn't know coordinate system / budgets | Context isolation — subagent didn't read FORGE.md | Always instruct subagent: "Read FORGE.md first" in delegation prompt |
| Script fails with `import bpy` in system Python | bpy only available in Blender's embedded Python | Run script via `blender -b -P script.py` not `python script.py` |
