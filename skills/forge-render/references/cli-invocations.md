# forge-render — CLI Invocations Reference

## Contents
- §1. Core headless invocation patterns (PowerShell)
- §2. Argument order rules (critical)
- §3. Finding blender.exe on Windows
- §4. Subprocess from Python
- §5. Common flag reference table
- §6. Timing and output validation patterns

---

## §1. Core headless invocation patterns (PowerShell)

All invocations use PowerShell. `$BLENDER` must be set before use (see §3).

```powershell
# Render single frame from a .blend file
& $BLENDER -b "C:/forge/scene.blend" -o "C:/forge/out/frame_####" -F PNG -f 1

# Render with Python script (most common Forge pattern)
& $BLENDER -b --factory-startup --python-exit-code 1 `
    -P "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts/render.py" `
    -- --out "C:/forge/out/beauty" --engine CYCLES --samples 128

# Render a scene built entirely from script (no .blend file)
& $BLENDER -b --factory-startup --python-exit-code 1 `
    -P "C:/forge/scripts/build_and_render.py" `
    -- --out "C:/forge/out/qa" --size 1024

# Turntable: N angles using render.py
& $BLENDER -b --factory-startup --python-exit-code 1 `
    -P "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts/render.py" `
    -- --out "C:/forge/out/turntable" --mode turntable --n-angles 12 --size 512

# Diagnostic contact sheet (Workbench wireframe + matcap + normals)
& $BLENDER -b --factory-startup --python-exit-code 1 `
    -P "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts/render.py" `
    -- --out "C:/forge/out/diag" --mode diagnostic --size 512

# Force Cycles GPU (OptiX — NVIDIA RTX required)
& $BLENDER -b "C:/forge/scene.blend" -f 1 -- --cycles-device OPTIX

# Force Cycles GPU + CPU combined
& $BLENDER -b "C:/forge/scene.blend" -f 1 -- --cycles-device OPTIX+CPU

# Render animation range (frames 1-24), PNG sequence
& $BLENDER -b "C:/forge/scene.blend" -o "C:/forge/out/frame_####" -F PNG -s 1 -e 24 -a

# Render with --cycles-print-stats for timing + memory profiling
& $BLENDER -b "C:/forge/scene.blend" -f 1 -- --cycles-device OPTIX --cycles-print-stats

# PowerShell subprocess with 120-second timeout
$job = Start-Process -FilePath $BLENDER `
    -ArgumentList "-b", "--factory-startup", "--python-exit-code", "1", "-P", $script, "--", $argStr `
    -NoNewWindow -Wait -PassThru -RedirectStandardOutput "C:/forge/out/blender.log"
if ($job.ExitCode -ne 0) { throw "[forge-render] Blender exited with code $($job.ExitCode)" }
```

---

## §2. Argument order rules (CRITICAL)

Blender processes arguments **left-to-right**. Arguments set before a .blend file load are
overwritten by the blend file's stored settings. The render trigger (`-f` or `-a`) must be
**last**.

```powershell
# WRONG: -o set after -f; output path ignored
& $BLENDER -b scene.blend -f 1 -o "C:/out/"

# CORRECT: all flags before render trigger
& $BLENDER -b scene.blend -o "C:/out/frame_####" -F PNG -f 1
```

```powershell
# WRONG: .blend file loaded before flags that should override it
& $BLENDER -b -o "C:/out/" scene.blend -f 1

# CORRECT: -b and the .blend file first, then -o, then -f
& $BLENDER -b "C:/forge/scene.blend" -o "C:/out/frame_####" -F PNG -f 1
```

The `--` separator is **mandatory** when passing custom arguments to a `-P` script:
```powershell
# Everything after -- is accessible as sys.argv in the Python script
& $BLENDER -b --python-exit-code 1 -P script.py -- --my-arg value
```

---

## §3. Finding blender.exe on Windows

Use `$env:BLENDER_EXE` if set (highest priority). Otherwise discover:

```powershell
function Get-BlenderExe {
    # Priority 1: environment variable
    if ($env:BLENDER_EXE -and (Test-Path $env:BLENDER_EXE)) {
        return $env:BLENDER_EXE
    }

    # Priority 2: FORGE.md cache (read by preflight.py)
    # (preflight.py writes discovered path to stdout JSON; see scripts/preflight.py)

    # Priority 3: glob Program Files (works for installer)
    $candidates = @(
        "C:\Program Files\Blender Foundation\Blender*\blender.exe",
        "C:\Program Files (x86)\Blender Foundation\Blender*\blender.exe",
        "C:\Tools\blender*\blender.exe"
    )
    foreach ($pattern in $candidates) {
        $found = Get-ChildItem -Path $pattern -ErrorAction SilentlyContinue |
            Sort-Object { $_.VersionInfo.FileVersionRaw } -Descending |
            Select-Object -First 1
        if ($found) { return $found.FullName }
    }

    # Priority 4: .blend file association in registry
    try {
        $assoc = cmd /c 'assoc .blend' 2>$null
        if ($assoc) {
            $ftype = cmd /c "ftype $($assoc -replace '.*=','')" 2>$null
            $exePath = $ftype -replace '^[^"]*"([^"]+)".*', '$1'
            if (Test-Path $exePath) { return $exePath }
        }
    } catch {}

    # Priority 5: PATH
    $fromPath = (Get-Command blender.exe -ErrorAction SilentlyContinue)?.Source
    if ($fromPath) { return $fromPath }

    throw "blender.exe not found. Install from https://www.blender.org/download/ " +
          "or set BLENDER_EXE environment variable."
}

$BLENDER = Get-BlenderExe
Write-Host "[forge-render] Using Blender: $BLENDER"
```

**Avoid the Microsoft Store version** — it runs in an AppContainer sandbox, and subprocess
calls from PowerShell may fail with permission errors or return a wrong path. Use the zip
(portable) or MSI installer distribution from blender.org.

---

## §4. Subprocess from Python

When Forge scripts need to call Blender from within a Python subprocess (e.g., from an
orchestration script):

```python
import subprocess
import sys
from pathlib import Path

BLENDER_EXE = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
RENDER_SCRIPT = Path(__file__).parent / "render.py"

def run_blender(args: list[str], timeout: int = 300) -> str:
    """
    Invoke Blender headlessly. Returns combined stdout+stderr.
    Raises RuntimeError on non-zero exit.
    """
    cmd = [
        BLENDER_EXE,
        "--background",
        "--factory-startup",
        "--python-exit-code", "1",
        "--python", str(RENDER_SCRIPT),
        "--",          # mandatory separator; everything after goes to sys.argv
    ] + args

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        encoding="utf-8",
        errors="replace",
    )
    combined = result.stdout + result.stderr
    if result.returncode != 0:
        raise RuntimeError(
            f"[forge-render] Blender exited {result.returncode}:\n{combined[-2000:]}"
        )
    return combined
```

---

## §5. Common flag reference table

| Flag | Long form | Effect |
|---|---|---|
| `-b` | `--background` | No GUI; required for headless |
| (omit) | `--factory-startup` | Skip user prefs / startup.blend; ensures determinism |
| (omit) | `--python-exit-code 1` | Exit code 1 if script raises uncaught exception |
| `-P <script>` | `--python <script>` | Run Python script after loading (if any) .blend file |
| (omit) | `--python-expr "<expr>"` | Run a one-line Python expression (debugging only) |
| `-y` | `--enable-autoexec` | Enable Python autoexec for .blend-embedded scripts |
| `-o <path>` | `--render-output <path>` | Output path; use `####` for zero-padded frame number |
| `-F <fmt>` | `--render-format <fmt>` | `PNG`, `OPEN_EXR`, `OPEN_EXR_MULTILAYER`, `JPEG`, etc. |
| `-f <n>` | `--render-frame <n>` | Render frame n; must be LAST Blender argument |
| `-a` | `--render-anim` | Render animation range; must be LAST Blender argument |
| `-s <n>` | `--frame-start <n>` | First frame of animation range |
| `-e <n>` | `--frame-end <n>` | Last frame of animation range |
| `--` | (separator) | All following args go to Python `sys.argv` |
| (after `--`) | `--cycles-device OPTIX` | Force OptiX GPU backend for Cycles |
| (after `--`) | `--cycles-device CUDA` | Force CUDA GPU backend for Cycles |
| (after `--`) | `--cycles-device OPTIX+CPU` | OptiX GPU + CPU combined |
| (after `--`) | `--cycles-print-stats` | Print render time + memory to console |
| (omit) | `--offline-mode` | Block add-on network access (Blender 4.2+) |
| (omit) | `--log-file C:/log.txt` | Redirect Blender log to file |

**Engine strings for `scene.render.engine`:**

| String | Engine | Notes |
|---|---|---|
| `CYCLES` | Cycles path tracer | Headless-safe on Windows; GPU optional |
| `BLENDER_EEVEE_NEXT` | EEVEE Next | NOT headless-safe on Windows; do not use |
| `BLENDER_WORKBENCH` | Workbench | Headless-safe; fast; no shader nodes |
| `BLENDER_EEVEE` | Old EEVEE | Removed in Blender 4.2; use BLENDER_EEVEE_NEXT |

---

## §6. Timing and output validation patterns

### Existence + size check (PowerShell)
```powershell
function Test-RenderOutput {
    param([string]$Path, [int]$MinKB = 1)
    if (-not (Test-Path $Path)) {
        Write-Error "[forge-render] FAIL: output not found: $Path"
        return $false
    }
    $sizeKB = [math]::Round((Get-Item $Path).Length / 1KB, 1)
    if ($sizeKB -lt $MinKB) {
        Write-Warning "[forge-render] WARN: output suspiciously small: ${sizeKB}KB at $Path"
        return $false
    }
    Write-Host "[forge-render] OK: $Path  (${sizeKB}KB)"
    return $true
}

# Usage after render
$ok = Test-RenderOutput -Path "C:/forge/out/beauty0001.png" -MinKB 2
if (-not $ok) { throw "Render output validation failed" }
```

### Validate all expected outputs in a batch
```powershell
$expected = @(
    "C:\forge\out\turntable\turntable_000_000deg.png",
    "C:\forge\out\turntable\turntable_001_030deg.png",
    "C:\forge\out\diag\wireframe_030deg.png",
    "C:\forge\out\diag\matcap_030deg.png",
    "C:\forge\out\qa_contact_sheet.png"
)
$allOk = $true
foreach ($f in $expected) {
    if (Test-Path $f) {
        $kb = [math]::Round((Get-Item $f).Length / 1KB, 1)
        if ($kb -lt 1) { Write-Warning "[WARN] Tiny: $f (${kb}KB)"; $allOk = $false }
        else            { Write-Host   "[OK]  $f (${kb}KB)" }
    } else {
        Write-Error "[FAIL] Missing: $f"; $allOk = $false
    }
}
if (-not $allOk) { exit 1 }
Write-Host "[forge-render] All outputs validated."
```

### Capture Blender console output for crash diagnosis
```powershell
# Redirect stdout+stderr to a log file so crash tracebacks are preserved
& $BLENDER -b --factory-startup --python-exit-code 1 -P $script -- @rest `
    2>&1 | Tee-Object -FilePath "C:/forge/out/blender_run.log"
if ($LASTEXITCODE -ne 0) {
    Write-Error "[forge-render] Blender crashed (exit $LASTEXITCODE). See: C:/forge/out/blender_run.log"
    exit 1
}
```

### Suppress the Windows console window pop-up
```powershell
$psi = [System.Diagnostics.ProcessStartInfo]::new($BLENDER)
$psi.Arguments   = "-b --factory-startup --python-exit-code 1 -P `"$script`" -- $argStr"
$psi.WindowStyle = [System.Diagnostics.ProcessWindowStyle]::Hidden
$psi.UseShellExecute = $false
$proc = [System.Diagnostics.Process]::Start($psi)
$proc.WaitForExit(120000)  # 120 second timeout
if ($proc.ExitCode -ne 0) { throw "Blender exited $($proc.ExitCode)" }
```
