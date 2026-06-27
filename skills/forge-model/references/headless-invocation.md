# forge-model — Headless Invocation Reference

## Contents
- §1. Finding blender.exe on Windows
- §2. Canonical PowerShell invocation patterns
- §3. Key CLI flags
- §4. Argument order rules
- §5. subprocess invocation from Python
- §6. Gotchas specific to invocation

---

## §1. Finding blender.exe on Windows

**Do NOT use the Microsoft Store version** — it runs in a sandbox that blocks headless subprocess
calls and locks the `WindowsApps` path behind a package identity token. Install from blender.org
(MSI or portable zip).

**Preferred: glob Program Files (fastest for installer)**
```powershell
$blender = Get-ChildItem -Path `
    "C:\Program Files\Blender Foundation\Blender*\blender.exe",`
    "C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe" `
    -ErrorAction SilentlyContinue |
    Sort-Object { $_.VersionInfo.FileVersionRaw } -Descending |
    Select-Object -First 1

if (-not $blender) { throw "blender.exe not found — install from blender.org (MSI)" }
$BLENDER_EXE = $blender.FullName
Write-Host "Found: $BLENDER_EXE"
```

**Fallback: .blend file association**
```powershell
$assoc = cmd /c 'assoc .blend' 2>$null
$ftype = cmd /c "ftype $($assoc -replace '.*=','')" 2>$null
$BLENDER_EXE = ($ftype -replace '^[^"]*"([^"]+)".*','$1')
if (-not (Test-Path $BLENDER_EXE)) { throw "blender.exe not found via association" }
```

**Standard install paths (Blender 4.x):**
```
C:\Program Files\Blender Foundation\Blender 4.2\blender.exe   (4.2 LTS)
C:\Program Files\Blender Foundation\Blender 4.5\blender.exe   (4.5 LTS — Forge default)
```

**Bundled Python (inside Blender — not system Python):**
```
C:\Program Files\Blender Foundation\Blender 4.5\4.5\python\bin\python.exe
```
Forge scripts invoke `blender.exe` as a subprocess; they do not call this Python directly.

---

## §2. Canonical PowerShell Invocation Patterns

**Pattern A — script builds everything from scratch (Forge standard):**
```powershell
& $BLENDER_EXE `
    --background `
    --factory-startup `
    --python-exit-code 1 `
    --python "C:\absolute\path\build_mesh.py" `
    -- `
    --output "C:\absolute\path\out\qa_render.png" `
    --samples 32 `
    --width 1280 `
    --height 720
```

**Pattern B — load an existing .blend file, then run script:**
```powershell
& $BLENDER_EXE `
    --background `
    --factory-startup `
    --python-exit-code 1 `
    "C:\absolute\path\scene.blend" `
    --python "C:\absolute\path\modify_scene.py" `
    -- `
    --output "C:\absolute\path\out\result.png"
```

**Pattern C — render a .blend directly without Python:**
```powershell
& $BLENDER_EXE `
    --background `
    "C:\absolute\path\scene.blend" `
    --render-output "C:\absolute\path\out\frame_####" `
    --render-format PNG `
    --render-frame 1
```

**Pattern D — smoke-test that Blender runs:**
```powershell
& $BLENDER_EXE --background --factory-startup --python-exit-code 1 `
    --python-expr "import bpy, sys; print('FORGE_BLENDER_OK', bpy.app.version_string); sys.exit(0)"
if ($LASTEXITCODE -ne 0) { throw "Blender smoke test failed" }
```

**Verify render output after any invocation:**
```powershell
$out = "C:\absolute\path\out\qa_render.png"
if (-not (Test-Path $out)) { throw "Render failed — no output file at $out" }
$sz = (Get-Item $out).Length
if ($sz -lt 10000) { throw "Render suspiciously small ($sz bytes) — possible black frame" }
Write-Host "QA render OK: $out ($sz bytes)"
```

---

## §3. Key CLI Flags

| Flag | Effect | Notes |
|---|---|---|
| `--background` / `-b` | No GUI; exits when script finishes | **Required for headless** |
| `--factory-startup` | Ignores user prefs + startup.blend | **Required for reproducibility** |
| `--python-exit-code 1` | Script exception → exit code 1 | **Required** — Blender exits 0 by default even on crash |
| `--python <file>` / `-P <file>` | Run script after Blender initializes | Use absolute paths only |
| `--python-expr <expr>` | Inline Python expression | Debugging only |
| `--python-use-system-env` | Allow Blender's Python to import system packages | Rarely needed |
| `--` | End of Blender args; rest goes to `sys.argv` in script | **Mandatory** when passing custom args |
| `--log "render"` | Enable render log category | Useful for diagnosing GPU/EEVEE failures |
| `--log-file C:\log.txt` | Write logs to file | Redirect verbose output |
| `--offline-mode` | Block add-on network access (4.2+) | Recommended for CI |
| `--enable-autoexec` / `-y` | Allow embedded scripts in .blend files | Only if loading external .blend with scripts |
| `--render-output <path>` | Set output path before rendering | Must come BEFORE `--render-frame` |
| `--render-format PNG` | Output format | Also: JPEG, OPEN_EXR, etc. |
| `--render-frame 1` | Render frame 1 | Can be a range: `1..10` |

**Argument order matters:** Blender processes flags left-to-right. `--render-output` MUST precede
`--render-frame` or the output goes to the default location (Blender's install directory).

---

## §4. Argument Order Rules

```
CORRECT order:
  blender.exe --background [blend_file_optional] --factory-startup --python-exit-code 1
              --python script.py
              -- --custom-arg value

WRONG (output set after render fires):
  blender.exe --background scene.blend --render-frame 1 --render-output C:\out
```

Rules:
1. `--background` first.
2. If loading a `.blend` file, it goes BEFORE `--factory-startup` (or after, depending on version;
   to be safe, put it immediately after `--background`).
3. `--factory-startup` before `--python`.
4. `--python-exit-code 1` before `--python`.
5. `--python script.py` before `--`.
6. Everything after `--` is passed to `sys.argv` in the script.

---

## §5. subprocess Invocation from Python

When Forge needs to invoke Blender from another Python process (e.g., a wrapper orchestrator):

```python
import subprocess
import sys
from pathlib import Path

def run_blender_script(
    blender_exe: str,
    script_path: str,
    output_path: str,
    samples: int = 32,
    timeout: int = 300,
) -> None:
    """
    Run a Blender headless script and verify output.
    Each flag must be a separate list element — never combine into a string.
    """
    cmd = [
        blender_exe,
        "--background",
        "--factory-startup",
        "--python-exit-code", "1",
        "--python", str(Path(script_path).resolve()),
        "--",                                      # mandatory separator
        "--output", str(Path(output_path).resolve()),
        "--samples", str(samples),
    ]
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"Blender script failed (exit {result.returncode}):\n"
            f"STDOUT:\n{result.stdout[-3000:]}\n"
            f"STDERR:\n{result.stderr[-3000:]}"
        )
    # Structural check
    p = Path(output_path)
    if not p.exists():
        raise RuntimeError(f"Blender exited 0 but output missing: {output_path}")
    if p.stat().st_size < 10_000:
        raise RuntimeError(f"Output suspiciously small ({p.stat().st_size} bytes): {output_path}")
```

**Critical subprocess pitfall — each flag is a separate list element:**
```python
# WRONG: Blender receives '--python script.py' as one unknown argument
subprocess.run([blender_exe, "--python script.py"])

# CORRECT: separate elements
subprocess.run([blender_exe, "--python", r"C:\script.py"])
```

---

## §6. Invocation-Specific Gotchas

**G-INV-1: blender.exe not on PATH**
Blender's Windows installer does NOT add it to PATH. Always resolve the full path via the
PowerShell glob in §1. Do not rely on `blender` being resolvable from PowerShell without `&`.

**G-INV-2: `--` separator omitted**
Custom args after `--python script.py` are silently eaten by Blender if `--` is missing.
The script sees an empty `sys.argv[after --]` slice and may use defaults or crash on
`required=True` argparse arguments. Always include `--` even if passing no custom args.

**G-INV-3: Relative paths in `scene.render.filepath`**
Blender's `//` prefix resolves relative to the open `.blend` file. In scripts without a
saved `.blend`, `//` resolves to Blender's install directory or is undefined. Always use
`os.path.abspath()` or `Path(...).resolve()`.

**G-INV-4: EEVEE Next headless on Windows**
EEVEE Next (Blender 4.2+) uses Vulkan/OpenGL and requires a display adapter. On Windows
machines without a GPU or when running in a headless shell without a display context, EEVEE
may produce black images. **Forge default: always use Cycles CPU for headless renders.**
```python
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'   # explicit — --factory-startup defaults to CPU but be explicit
```

**G-INV-5: Exit code 0 on Python exception**
Without `--python-exit-code 1`, Blender exits 0 even when the script raises an unhandled
exception. CI pipelines see "green" while the geometry is wrong or missing. Always include
the flag, and also add `sys.exit(1)` in `except` blocks for belt-and-suspenders:
```python
try:
    main()
except Exception:
    import traceback
    traceback.print_exc()
    sys.exit(1)
```

**G-INV-6: Microsoft Store Blender sandbox**
The Store version runs in a `WindowsApps` directory that requires a package identity token.
Subprocess calls from within the Blender process fail. Add-ons can't write to their own
directory. Use the MSI or zip install from blender.org.
