#requires -Version 5.1
<#
.SYNOPSIS
    forge-optimize wrapper — compress a GLB for web delivery using gltf-transform.

.DESCRIPTION
    Runs gltf-transform optimize over a GLB file with configurable geometry and texture
    compression. Reports before/after file size in KB. Exits non-zero on validation failure.

    Defaults: Meshopt geometry compression + WebP texture compression.
    With -KTX2 flag: switches texture compression to KTX2 (requires toktx on PATH).
    With -Draco flag: switches geometry compression to Draco (static meshes only — do NOT
    use for animated/rigged/morph-target meshes). When -Draco is set on a GLB that contains
    animations or morph targets, the script auto-falls-back to Meshopt with a warning
    (Draco silently corrupts animated/rigged meshes — see references/install-windows.md Gotcha 4).

    PS 5.1-compatible — no ?. / ?? / ternary (?:) operators. This script targets Windows
    PowerShell 5.1 (the Forge suite's primary shell); 7+-only syntax is a hard parse error there.

.PARAMETER InputPath
    Path to the input GLB file (unoptimized source). This file is never modified.
    Alias: -Input (preserved for backward compatibility with documented call sites).

.PARAMETER Output
    Path for the optimized output GLB. Parent directory is created if needed.
    Refuses to run if Output resolves to the same file as InputPath (the source is sacred).

.PARAMETER TextureSize
    Maximum texture resolution (width and height). Default: 1024.
    Common values: 512, 1024, 2048.

.PARAMETER Draco
    Switch: use Draco geometry compression instead of Meshopt.
    WARNING: Draco cannot compress animations or morph targets. Use only for static meshes.
    If animations/morph targets are detected, the script falls back to Meshopt automatically.

.PARAMETER KTX2
    Switch: use KTX2 texture compression (UASTC for normal/ORM, ETC1S for base color).
    Requires toktx in PATH (KTX-Software https://github.com/KhronosGroup/KTX-Software/releases).

.PARAMETER Poster
    Optional path to a rendered poster image (PNG/WebP) produced for this asset. When given,
    the script enforces the >= 10 KB poster-size gate (references/budgets-and-runtime.md §4)
    so the build carries a visual artifact the model can Read back. Validate passing does NOT
    mean the asset renders — always Read the poster to confirm it is not blank/black.

.PARAMETER Force
    Switch: overwrite an existing Output file without warning. Without it, an existing Output
    is overwritten with a warning (re-runs stay explicit). Output == Input is always refused.

.PARAMETER NoValidate
    Switch: skip the gltf-transform validate step (faster, but no spec-conformance check).

.PARAMETER Json
    Switch: emit a JSON summary instead of human-readable output.

.EXAMPLE
    # Safe defaults (Meshopt + WebP, 1024px textures)
    .\optimize.ps1 -InputPath .\raw\hero.glb -Output .\public\forge\hero-hero.glb

.EXAMPLE
    # KTX2 textures (requires toktx)
    .\optimize.ps1 -InputPath .\raw\hero.glb -Output .\public\forge\hero-hero.glb -KTX2

.EXAMPLE
    # Draco + larger textures + poster gate
    .\optimize.ps1 -InputPath .\raw\hero.glb -Output .\public\forge\hero-hero.glb -Draco -TextureSize 2048 -Poster .\public\forge\hero-hero-poster.webp

.NOTES
    Part of the Forge suite — forge-optimize skill.
    Windows-native: no WSL required. Targets Windows PowerShell 5.1 + Node.js LTS + @gltf-transform/cli (4.4.0+).
    Install: npm install --global @gltf-transform/cli
    toktx install: https://github.com/KhronosGroup/KTX-Software/releases
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [Alias('Input')]
    [string]$InputPath,

    [Parameter(Mandatory = $true)]
    [string]$Output,

    [ValidateSet(512, 1024, 2048, 4096)]
    [int]$TextureSize = 1024,

    [switch]$Draco,

    [switch]$KTX2,

    [string]$Poster,

    [switch]$Force,

    [switch]$NoValidate,

    [switch]$Json
)

# ── Encode stdout as UTF-8 (Windows default is cp1252) ─────────────────────
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8

# ── Helpers ─────────────────────────────────────────────────────────────────
function Write-Status([string]$msg) {
    if (-not $Json) { Write-Host "[forge-optimize] $msg" }
}

function Exit-Fail([string]$msg, [hashtable]$result = @{}) {
    if ($Json) {
        $result['ok'] = $false
        $result['error'] = $msg
        Write-Host ($result | ConvertTo-Json -Compress)
    } else {
        Write-Error "[forge-optimize] ERROR: $msg"
    }
    exit 1
}

# ── Resolve paths (PS 5.1-safe — no null-conditional operator) ────────────────
# NB: use a distinct working-var name. PowerShell variable names are case-INSENSITIVE,
# so a lowercase `$inputPath` would be the SAME variable as the `$InputPath` param and
# would clobber it (wiping the path before error messages print).
$resolvedInput     = Resolve-Path -LiteralPath $InputPath -ErrorAction SilentlyContinue
$resolvedInputPath = if ($resolvedInput) { $resolvedInput.Path } else { $null }
if (-not $resolvedInputPath) {
    Exit-Fail "Input file not found: $InputPath"
}

$outputPath = $Output

# ── Source is sacred: never let Output clobber the input GLB ──────────────────
# Resolve Output if it already exists; compare against the resolved input path.
$resolvedOutput = Resolve-Path -LiteralPath $outputPath -ErrorAction SilentlyContinue
if ($resolvedOutput -and ($resolvedOutput.Path -eq $resolvedInputPath)) {
    Exit-Fail "Output path equals input — refusing to overwrite the source GLB. The uncompressed source is sacred; write the optimized GLB elsewhere."
}

$outputDir = Split-Path -Parent $outputPath
if ($outputDir -and -not (Test-Path $outputDir)) {
    New-Item -ItemType Directory -Force -Path $outputDir | Out-Null
    Write-Status "Created output directory: $outputDir"
}

# ── Idempotent re-run: existing Output is overwritten, explicitly ─────────────
if ((Test-Path -LiteralPath $outputPath) -and -not $Force) {
    Write-Warning "[forge-optimize] Output already exists and will be overwritten: $outputPath  (pass -Force to silence). Re-running optimize on the same input is safe; the source GLB is never touched."
}

# ── Check gltf-transform ─────────────────────────────────────────────────────
$gltfTransform = (Get-Command "gltf-transform" -ErrorAction SilentlyContinue)
if (-not $gltfTransform) {
    Exit-Fail "gltf-transform not found. Install: npm install --global @gltf-transform/cli"
}

# ── Check toktx if KTX2 requested ───────────────────────────────────────────
if ($KTX2) {
    $toktx = (Get-Command "toktx" -ErrorAction SilentlyContinue)
    if (-not $toktx) {
        Exit-Fail "toktx not found in PATH. Required for -KTX2. Install KTX-Software: https://github.com/KhronosGroup/KTX-Software/releases"
    }
    Write-Status "toktx found: $($toktx.Source)"
}

# ── Record input size ────────────────────────────────────────────────────────
$inputBytes = (Get-Item $resolvedInputPath).Length
$inputKB    = [math]::Round($inputBytes / 1KB, 1)
Write-Status "Input:  $inputKB KB  ($resolvedInputPath)"

# ── Inspect first ────────────────────────────────────────────────────────────
# Use forward-slash paths (gltf-transform CLI is Node.js and can mishandle backslashes)
$inputFwd  = $resolvedInputPath -replace '\\', '/'
$outputFwd = $outputPath -replace '\\', '/'

Write-Status "Inspecting..."
$inspectText = (& gltf-transform inspect $inputFwd 2>&1) | Out-String
$inspectExit = $LASTEXITCODE
if (-not $Json) {
    $inspectText -split "`r?`n" | ForEach-Object { if ($_ -ne "") { Write-Host "  $_" } }
}
# A corrupt input that fails inspect must NOT be reported as a successful inspect.
if ($inspectExit -ne 0) {
    Exit-Fail "gltf-transform inspect failed (exit $inspectExit) — input may be corrupt: $resolvedInputPath"
}

# ── Build gltf-transform arguments ──────────────────────────────────────────
$compress        = if ($Draco) { "draco" } else { "meshopt" }
$textureCompress = if ($KTX2)  { "ktx2"  } else { "webp"   }

# ── Graceful degradation: Draco silently corrupts animated/morph GLBs ─────────
# (references/install-windows.md Gotcha 4). If Draco was requested but the inspect
# report mentions animations or morph targets, fall back to Meshopt automatically.
# Fail-safe by design: a false positive only costs slightly less compression
# (Meshopt vs Draco) — never the silent T-pose/lost-animation corruption Draco causes.
# `gltf-transform inspect` lists an "Animations" table (with name/duration rows) only
# when animations exist, and "morphTargets" in the meshes table when morphs exist.
if ($Draco) {
    $hasAnimation = $inspectText -match '(?im)\banimation'
    $hasMorph     = $inspectText -match '(?im)\bmorph'
    if ($hasAnimation -or $hasMorph) {
        $reason = if ($hasAnimation -and $hasMorph) { "animations + morph targets" }
                  elseif ($hasAnimation)            { "animations" }
                  else                              { "morph targets" }
        Write-Warning "[forge-optimize] Draco cannot compress $reason — Draco corrupts animated/rigged/morph meshes. Falling back to Meshopt for geometry compression."
        $compress = "meshopt"
    }
}

Write-Status "Compressing: geometry=$compress textures=$textureCompress maxTex=${TextureSize}px"

# ── Run optimize ─────────────────────────────────────────────────────────────
# Paths are already forward-slashed above ($inputFwd / $outputFwd).
# Texture resize flag: gltf-transform 4.4.0's `optimize` accepts `--texture-size <number>`
# as the MAX texture dimension (single scalar, NOT a WxH pair — that paired form is the
# standalone `resize --width/--height` command, see references/cli-invocations.md §2/§5).
# Passing TextureSize as one integer matches the optimize-command contract for v4.4.0+.
$optimizeArgs = @(
    "optimize",
    $inputFwd,
    $outputFwd,
    "--compress",        $compress,
    "--texture-compress", $textureCompress,
    "--texture-size",    $TextureSize
)

& gltf-transform @optimizeArgs
$exitCode = $LASTEXITCODE

if ($exitCode -ne 0) {
    Exit-Fail "gltf-transform optimize failed (exit $exitCode). Check input file and codec flags."
}

# ── Report output size ───────────────────────────────────────────────────────
if (-not (Test-Path $outputPath)) {
    Exit-Fail "Output file was not created: $outputPath"
}

$outputBytes  = (Get-Item $outputPath).Length
$outputKB     = [math]::Round($outputBytes / 1KB, 1)
$reductionPct = [math]::Round((1 - $outputBytes / $inputBytes) * 100, 1)

Write-Status "Output: $outputKB KB  ($outputPath)"
Write-Status "Reduction: ${reductionPct}%"

# ── Sanity checks ────────────────────────────────────────────────────────────
if ($reductionPct -lt 5) {
    Write-Warning "[forge-optimize] Low reduction (${reductionPct}%) — pipeline may not have applied. Check input file."
}
if ($reductionPct -gt 99) {
    Write-Warning "[forge-optimize] Suspiciously high reduction (${reductionPct}%) — verify output is not corrupted."
}

# ── Validate ─────────────────────────────────────────────────────────────────
$validationPassed = $true
if (-not $NoValidate) {
    Write-Status "Validating..."
    & gltf-transform validate $outputFwd
    if ($LASTEXITCODE -ne 0) {
        $validationPassed = $false
        Exit-Fail "gltf-transform validate failed for $outputPath"
    }
    Write-Status "Validation: PASSED"
}

# ── Poster gate ──────────────────────────────────────────────────────────────
# validate passing != renders correctly. A GLB can pass spec validation while
# rendering blank/black/wrong-color. If a poster was supplied, enforce the
# >= 10 KB gate (references/budgets-and-runtime.md §4) so the build carries a
# visual artifact the model can Read back to confirm the asset is not blank.
$posterChecked = $false
if ($Poster) {
    $resolvedPoster = Resolve-Path -LiteralPath $Poster -ErrorAction SilentlyContinue
    if (-not $resolvedPoster) {
        Exit-Fail "Poster not found: $Poster  (generate it first — see references/budgets-and-runtime.md §4)"
    }
    $posterBytes = (Get-Item $resolvedPoster.Path).Length
    if ($posterBytes -lt 10KB) {
        Exit-Fail "Poster suspiciously small ($posterBytes B, < 10 KB) — generation likely failed or rendered blank. Read it before handing off."
    }
    $posterChecked = $true
    Write-Status "Poster OK: $([math]::Round($posterBytes / 1KB)) KB  ($($resolvedPoster.Path))"
}

# ── JSON output ──────────────────────────────────────────────────────────────
if ($Json) {
    $result = [ordered]@{
        ok              = $true
        input           = $resolvedInputPath
        output          = $outputPath
        inputKB         = $inputKB
        outputKB        = $outputKB
        reductionPct    = $reductionPct
        compress        = $compress
        textureCompress = $textureCompress
        textureSize     = $TextureSize
        validated       = (-not $NoValidate -and $validationPassed)
        posterChecked   = $posterChecked
    }
    Write-Host ($result | ConvertTo-Json -Compress)
} else {
    Write-Host ""
    Write-Host "[forge-optimize] Done."
    Write-Host "  $inputKB KB -> $outputKB KB  (-${reductionPct}%)"
    Write-Host "  geometry: $compress | textures: $textureCompress | maxTex: ${TextureSize}px"
    if (-not $NoValidate) { Write-Host "  validation: PASSED" }
    if ($posterChecked)   { Write-Host "  poster: PASSED (>= 10 KB)" }
    Write-Host ""
    Write-Host "  Read the poster PNG/WebP with the Read tool to confirm the asset is not blank —"
    Write-Host "  validate passing does NOT mean the GLB renders correctly."
    Write-Host ""
    Write-Host "  Next: run Skill('forge-validate') for full Forge gate,"
    Write-Host "  then Skill('atelier-webgl') with the GLB + poster paths."
}

exit 0
