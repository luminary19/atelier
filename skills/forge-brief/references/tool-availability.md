# Tool Availability — Forge Brief Reference

## Contents
- §1. Preflight probe (PowerShell + Python)
- §2. Blender path detection on Windows
- §3. OpenSCAD — use `.com` not `.exe`
- §4. CadQuery / build123d install check
- §5. FreeCAD headless check
- §6. Node.js / gltf-transform (for forge-optimize)
- §7. Python version and stdlib check
- §8. Quick decision matrix

---

## §1. Preflight probe (PowerShell + Python)

Before forge-brief locks the tool choice in FORGE.md, verify the chosen tool is actually
installed and accessible on PATH.

**PowerShell one-liner (quick check):**
```powershell
# Check all Forge tools at once
@("blender", "openscad.com", "python", "node", "npx") | ForEach-Object {
    $found = [bool](Get-Command $_ -ErrorAction SilentlyContinue)
    $status = if ($found) { "OK  " } else { "MISS" }
    Write-Host "[$status] $_"
}
```

**Python preflight script (more detail — pure stdlib):**
```python
# scripts/preflight_tools.py
# Usage: python preflight_tools.py [--tools blender,openscad,python] [--json]
import subprocess, sys, json, shutil, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

TOOL_CMDS = {
    "blender":   ["blender", "--version"],
    "openscad":  ["openscad.com", "--version"],
    "python":    ["python", "--version"],
    "node":      ["node", "--version"],
    "npx":       ["npx", "--version"],
    "freecad":   ["freecadcmd", "--version"],
}

def check(name: str, cmd: list) -> dict:
    found = bool(shutil.which(cmd[0]))
    version = ""
    if found:
        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            version = (r.stdout or r.stderr or "").strip().splitlines()[0]
        except Exception:
            pass
    return {"tool": name, "found": found, "version": version}

def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--tools", default="blender,openscad,python,node", help="comma-separated")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    names = [t.strip() for t in args.tools.split(",") if t.strip() in TOOL_CMDS]
    results = [check(n, TOOL_CMDS[n]) for n in names]
    missing = [r["tool"] for r in results if not r["found"]]
    if args.json:
        print(json.dumps({"results": results, "missing": missing}))
    else:
        for r in results:
            print(f"[{'OK  ' if r['found'] else 'MISS'}] {r['tool']:15s} {r['version']}")
        if missing:
            print(f"\nMISSING: {', '.join(missing)}")
            sys.exit(1)

if __name__ == "__main__":
    main()
```

---

## §2. Blender path detection on Windows

Blender may or may not be on PATH. Common install locations:

| Install method | Typical path |
|---|---|
| Official installer (default) | `C:\Program Files\Blender Foundation\Blender 4.4\blender.exe` |
| winget | Same path as official installer |
| Portable (extracted zip) | Wherever the user extracted it |
| Steam | `C:\Program Files (x86)\Steam\steamapps\common\Blender\blender.exe` |
| Scoop | `C:\Users\<user>\scoop\apps\blender\current\blender.exe` |

**PowerShell — find Blender wherever it is:**
```powershell
function Find-Blender {
    # 1. Try PATH first
    $onPath = Get-Command blender -ErrorAction SilentlyContinue
    if ($onPath) { return $onPath.Source }

    # 2. Try common install directories
    $candidates = @(
        "C:\Program Files\Blender Foundation",
        "C:\Program Files (x86)\Blender Foundation",
        "C:\Users\$env:USERNAME\AppData\Local\Blender Foundation"
    )
    foreach ($dir in $candidates) {
        $found = Get-ChildItem $dir -Recurse -Filter "blender.exe" -ErrorAction SilentlyContinue |
                 Sort-Object LastWriteTime -Descending | Select-Object -First 1
        if ($found) { return $found.FullName }
    }

    # 3. Registry lookup (installed via official installer)
    try {
        $reg = Get-ItemProperty "HKLM:\SOFTWARE\BlenderFoundation\Blender*" `
               -ErrorAction SilentlyContinue
        if ($reg.InstallDir) {
            return Join-Path $reg.InstallDir "blender.exe"
        }
    } catch {}

    return $null
}

$blender = Find-Blender
if ($blender) {
    Write-Host "Found Blender: $blender"
    & $blender --version
} else {
    Write-Error "Blender not found — install from https://www.blender.org/download/"
}
```

**Install Blender via winget (if missing):**
```powershell
winget install --id BlenderFoundation.Blender --silent
```

**Forge standard invocation (use a variable, never hardcode the path):**
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
# Always quote the path; always add --python-exit-code 1; always use -- separator
& $blender -b "C:\project\scene.blend" -P "C:\project\script.py" --python-exit-code 1 `
    -- --arg1 value1
```

---

## §3. OpenSCAD — use `.com` not `.exe`

**The issue:** `openscad.exe` on Windows can fail silently on DPI-aware systems or when
launched without a display context. `openscad.com` is the headless console launcher that
handles this correctly.

```powershell
# CORRECT
openscad.com -o out.stl model.scad -D "width=50" -D "height=30"

# WRONG (may fail silently on some Windows configurations)
openscad.exe -o out.stl model.scad
```

**Check availability:**
```powershell
Get-Command openscad.com -ErrorAction SilentlyContinue
```

**Install OpenSCAD:**
```powershell
winget install --id OpenSCAD.OpenSCAD --silent
# Or download from https://openscad.org/downloads.html
```

After install, the `.com` launcher is in the same directory as `.exe`. If PATH doesn't
include it, invoke with the full path:
```powershell
& "C:\Program Files\OpenSCAD\openscad.com" -o out.stl model.scad
```

**Common OpenSCAD headless flags:**
```powershell
openscad.com `
    -o "C:\project\export\part.stl" `        # output file (format by extension)
    "C:\project\model.scad" `                # source file
    -D "width=50" `                          # override a variable
    -D "height=30" `
    --hardwarnings `                         # treat warnings as errors
    --export-format manifold                 # use manifold kernel (faster, more reliable)
```

---

## §4. CadQuery / build123d install check

CadQuery and build123d are Python packages. They must be installed in the same Python
environment the script runs in.

**Check:**
```python
# Pure stdlib check — no import needed
import subprocess, sys

def check_cadquery() -> dict:
    r = subprocess.run(
        [sys.executable, "-c", "import cadquery; print(cadquery.__version__)"],
        capture_output=True, text=True
    )
    if r.returncode == 0:
        return {"found": True, "version": r.stdout.strip(), "package": "cadquery"}
    # Try build123d
    r2 = subprocess.run(
        [sys.executable, "-c", "import build123d; print(build123d.__version__)"],
        capture_output=True, text=True
    )
    if r2.returncode == 0:
        return {"found": True, "version": r2.stdout.strip(), "package": "build123d"}
    return {"found": False, "version": "", "package": "none"}

result = check_cadquery()
print(result)
```

**Install (if missing):**
```powershell
# CadQuery (stable)
pip install cadquery

# build123d (more active development, preferred for new projects)
pip install build123d

# Note: CadQuery requires OCCT (Open CASCADE Technology) — pip handles this via
# cadquery-ocp wheel. Install may take 2–5 minutes.
```

**CadQuery headless invocation:**
```powershell
# python not python3 on Windows
python "C:\project\scripts\part.py" --out "C:\project\export\part.step"
```

---

## §5. FreeCAD headless check

FreeCAD ships its own Python interpreter (`freecadcmd` or `FreeCADCmd`).

**Check availability:**
```powershell
Get-Command FreeCADCmd -ErrorAction SilentlyContinue
```

**Common install path (Windows):**
```
C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe
```

**Headless invocation:**
```powershell
& "C:\Program Files\FreeCAD 1.0\bin\FreeCADCmd.exe" "C:\project\script.py"
```

FreeCAD headless is supported but less commonly used in Forge — default to OpenSCAD or
CadQuery for parametric CAD. See `forge-parametric` for full FreeCAD guidance.

---

## §6. Node.js / gltf-transform (for forge-optimize)

forge-optimize uses `gltf-transform` (npm CLI). It requires Node.js on PATH.

**Check:**
```powershell
node --version   # e.g. v22.x.x
npm --version    # e.g. 10.x.x
npx gltf-transform --version
```

**Install:**
```powershell
# Install Node.js LTS from nodejs.org (Windows installer)
# After install:
npm install -g @gltf-transform/cli
```

**Verify gltf-transform:**
```powershell
npx gltf-transform --version
# Should print something like "4.x.x"
```

**KTX2 texture compression also requires `toktx`:**
```powershell
toktx --version
# If missing: install from https://github.com/KhronosGroup/KTX-Software/releases
# Windows installer adds toktx.exe to PATH
```

forge-brief does not invoke gltf-transform directly — but it should note in FORGE.md's
`## Output paths` section whether Node.js/gltf-transform is available, because
forge-optimize will need it.

---

## §7. Python version and stdlib check

Forge scripts require `python` (not `python3`) and Python 3.10+ for:
- `match` statements (used optionally in forge scripts)
- `pathlib.Path` (3.4+)
- `subprocess.run(capture_output=True)` (3.7+)

**Check:**
```powershell
python --version   # should be 3.10+ for full Forge compatibility
```

**Verify stdlib modules used by Forge scripts:**
```powershell
python -c "import json, csv, re, pathlib, subprocess, argparse, shutil, math; print('OK')"
```

**UTF-8 stdout fix (required at top of every Forge script):**
```python
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
```
Without this, non-ASCII output (degree symbols, special chars from Blender stdout) may
crash or produce garbage on Windows (default cp1252 encoding).

---

## §8. Quick decision matrix

Use this when deciding which tool to recommend in FORGE.md based on the task:

| Task | Recommended tool | Availability check |
|---|---|---|
| Polygonal/organic mesh, animation, look-dev | **Blender** | `blender --version` |
| Parametric CAD, STEP export, engineering fits | **OpenSCAD** (simple) / **CadQuery** / **build123d** (complex) | `openscad.com --version` / `python -c "import cadquery"` |
| Multi-body CAD, FEM analysis | **FreeCAD** | `FreeCADCmd --version` |
| USD pipeline, Omniverse interop | **Blender** (USD export built-in 4.x) | `blender --version` |
| 3D print (FDM) | **OpenSCAD** or **CadQuery** → STL/3MF | Either |
| Web GLB (hero, product viewer) | **Blender** → GLB + gltf-transform | `blender --version` + `npx gltf-transform` |
| Procedural / generative geometry | **Blender** Geometry Nodes via bpy | `blender --version` |
| SDF / implicit surfaces | **Blender** (marching cubes) or **fogleman/sdf** Python | `blender --version` or `python -c "import sdf"` |
| Photogrammetry / NeRF cleanup | **Blender** (import + cleanup scripts) | `blender --version` |

**If Blender is missing and the task requires it:** do NOT fall back to a different tool
silently. Write a clear error in the forge-brief output and include the install command:
```powershell
winget install --id BlenderFoundation.Blender --silent
```
