#requires -Version 5.1
<#
.SYNOPSIS
  Generate or edit raster images by driving the local OpenAI Codex CLI's built-in
  `image_gen` tool, using Codex's existing ChatGPT (Plus/Pro) login. No OPENAI_API_KEY.

.DESCRIPTION
  Wraps `codex exec` non-interactively. Sends a prompt that forces Codex to call its
  FIRST-PARTY built-in `image_gen` tool (not the python image_gen.py fallback, which
  would need an API key), saves images into -OutDir, then discovers the produced files
  via a before/after filesystem diff combined with `IMAGE: <path>` lines printed by the
  agent. All parsing lives here on purpose: a model reading a SKILL.md will not execute
  fenced bash verbatim, so the orchestration cannot live in markdown.

.NOTES
  Native Windows / PowerShell. Codex on Windows has no OS sandbox, so the default
  -Sandbox 'bypass' is safe: the agent only writes into -OutDir.
#>

[CmdletBinding()]
param(
    [string]   $Prompt,
    [string]   $OutDir       = ".\codex-images",
    [int]      $Count        = 1,
    [string]   $Size         = "1024x1024",
    [switch]   $Transparent,
    [string]   $Model,
    [string]   $Edit,                                  # path to source image => edit mode (MODIFIES the image)
    [string]   $Anchor,                                # path to a STYLE-ANCHOR image => attach as -i reference for a NEW generation (palette/quality/scheme only, never copied)
    [ValidateSet("bypass","workspace-write","danger-full-access")]
    [string]   $Sandbox      = "bypass",
    [int]      $TimeoutSec   = 420,
    [switch]   $DryRun
)

$ErrorActionPreference = "Stop"
function Fail($m) { Write-Error $m; exit 1 }

# ---- preflight -------------------------------------------------------------
$codex = Get-Command codex -ErrorAction SilentlyContinue
if (-not $codex) { Fail "codex CLI not found on PATH. Install with: npm i -g @openai/codex, then 'codex login'." }

$ch = $env:CODEX_HOME
if (-not $ch) { $ch = Join-Path $env:USERPROFILE ".codex" }
$authPath = Join-Path $ch "auth.json"
if (-not (Test-Path $authPath)) { Fail "No auth.json at $ch. Run 'codex login' (ChatGPT) first." }
try {
    $auth = Get-Content $authPath -Raw | ConvertFrom-Json
    if (-not $auth.tokens -and -not $auth.OPENAI_API_KEY) { Fail "auth.json has no ChatGPT tokens and no key. Run 'codex login'." }
} catch { Fail "Could not parse $authPath : $_" }

if ($Edit -and $Anchor) {
    Fail "Use -Edit OR -Anchor, not both: -Edit MODIFIES the source image; -Anchor attaches it as a style reference for a NEW generation."
}
if ($Edit) {
    if (-not (Test-Path $Edit)) { Fail "Edit source image not found: $Edit" }
    $Edit = (Resolve-Path $Edit).Path
} else {
    if (-not $Prompt) { Fail "Provide -Prompt (generate), -Edit <image> + -Prompt (edit), or -Anchor <image> + -Prompt (style-anchored generate)." }
    if ($Anchor) {
        if (-not (Test-Path $Anchor)) { Fail "Anchor image not found: $Anchor" }
        $Anchor = (Resolve-Path $Anchor).Path
    }
}

# ---- sanitize prompt for safe native-arg passing ---------------------------
# PowerShell 5.1 + the npm `codex` shim mangle native arguments that contain
# embedded double-quotes: the arg gets split at each `"`, so `codex exec` sees the
# tail of the prompt as stray positional args and aborts ("unexpected argument ...").
# Image prompts never *need* raw double-quotes, so normalize straight + smart double
# quotes to single quotes and flatten newlines/tabs/runs-of-spaces into single spaces.
if ($Prompt) {
    $Prompt = $Prompt -replace '[“”„‟″‶"]', "'"
    $Prompt = $Prompt -replace '[\r\n\t]+', ' '
    $Prompt = ($Prompt -replace '\s{2,}', ' ').Trim()
}

# ---- output dir + snapshot -------------------------------------------------
# The built-in image_gen tool writes to $CODEX_HOME\generated_images\<session>\ig_*.png
# (no path argument exists). The agent's own "copy to OutDir" step is unreliable, so THIS
# script copies the produced files out. We snapshot both locations before the run.
if (-not (Test-Path $OutDir)) { New-Item -ItemType Directory -Path $OutDir -Force | Out-Null }
$OutDir = (Resolve-Path $OutDir).Path
$genDir = Join-Path $ch "generated_images"
$imgExt = @("*.png","*.jpg","*.jpeg","*.webp")
function Get-Images([string]$root) {
    if (Test-Path $root) { Get-ChildItem -Path $root -Recurse -File -Include $imgExt -ErrorAction SilentlyContinue } else { @() }
}
$before = @{}
foreach ($f in @(Get-Images $OutDir) + @(Get-Images $genDir)) { $before[$f.FullName] = $true }

# ---- build the forcing prompt ---------------------------------------------
$bgClause = if ($Transparent) { " Use a transparent background (PNG with alpha)." } else { "" }
if ($Edit) {
    $task = "Edit the attached image with the built-in image_gen tool. $Prompt"
} else {
    $task = @"
Generate $Count image(s) at size $Size with the built-in image_gen tool.$bgClause
Prompt: $Prompt
"@
}
# NOTE: the built-in tool has no path argument and saves under `$CODEX_HOME`. This script
# locates and copies the result, so we do NOT ask the agent to move files (it does that
# unreliably and then claims success). We only ask it to generate and stop.
$anchorRule = ""
if ($Anchor) {
    $anchorRule = "`n- The attached image is a STYLE ANCHOR ONLY: match its colour palette, colour scheme, material quality, lighting, and finish so the result clearly belongs to the same world - but do NOT copy its composition, subject, framing, layout, or specific elements. Generate a NEW image from the Prompt above; the anchor is a palette/quality reference, never a template to reproduce."
}
$fullPrompt = @"
You are running headless. $task

Hard rules:$anchorRule
- Use the built-in image_gen tool ONLY. Do NOT run the python image_gen.py fallback CLI.
- Do NOT ask for, set, or use an OPENAI_API_KEY. Your existing session auth is sufficient.
- Do not ask questions and do not wait for approval; just generate the image(s) now.
- Do NOT attempt to move, copy, or rename the output; leave it where the tool saves it.
- When the image(s) exist, end your final message with exactly: DONE
"@

# ---- assemble argv ---------------------------------------------------------
$lastMsg = Join-Path $OutDir (".codex-lastmsg.txt")
$cxArgs = @("exec","--skip-git-repo-check","-C",$OutDir,"-o",$lastMsg)
switch ($Sandbox) {
    "bypass"          { $cxArgs += "--dangerously-bypass-approvals-and-sandbox" }
    "workspace-write" { $cxArgs += @("-s","workspace-write","-c","sandbox_workspace_write.network_access=true") }
    "danger-full-access" { $cxArgs += @("-s","danger-full-access") }
}
if ($Model) { $cxArgs += @("-m",$Model) }
# Positional prompt MUST precede -i: `-i/--image <FILE>...` is variadic and would
# otherwise greedily consume the prompt, leaving codex to read an (empty) stdin.
$cxArgs += $fullPrompt
if ($Edit)       { $cxArgs += @("-i",$Edit) }
elseif ($Anchor) { $cxArgs += @("-i",$Anchor) }

if ($DryRun) {
    "DRY RUN - would execute:"
    "codex " + (($cxArgs | ForEach-Object { if ($_ -match '\s') { '"' + $_ + '"' } else { $_ } }) -join " ")
    exit 0
}

# ---- run -------------------------------------------------------------------
Write-Host "==> codex exec (image_gen, auth=chatgpt-login, sandbox=$Sandbox) ..." -ForegroundColor Cyan
$start = Get-Date
$job = Start-Job -ScriptBlock {
    param($a)
    & codex @a 2>&1 | Out-String
} -ArgumentList (,$cxArgs)

if (-not (Wait-Job $job -Timeout $TimeoutSec)) {
    Stop-Job $job -ErrorAction SilentlyContinue
    Remove-Job $job -Force -ErrorAction SilentlyContinue
    Fail "codex exec timed out after ${TimeoutSec}s. Try a simpler prompt or raise -TimeoutSec."
}
$stdout = Receive-Job $job
Remove-Job $job -Force -ErrorAction SilentlyContinue

$finalMsg = if (Test-Path $lastMsg) { Get-Content $lastMsg -Raw } else { "" }

# ---- discover produced files ----------------------------------------------
# Truth = new image files in generated_images (and any the agent happened to drop in OutDir),
# created after this run started and not present in the pre-run snapshot.
$startUtc = $start.ToUniversalTime()
$new = @()
foreach ($f in @(Get-Images $genDir) + @(Get-Images $OutDir)) {
    if (-not $before.ContainsKey($f.FullName) -and $f.LastWriteTimeUtc -ge $startUtc.AddSeconds(-2)) { $new += $f }
}
$new = $new | Sort-Object LastWriteTimeUtc

# ---- copy results into OutDir with friendly names --------------------------
$slug = ($Prompt -replace '[^a-zA-Z0-9]+','-').Trim('-').ToLower()
if (-not $slug) { $slug = "image" }
if ($slug.Length -gt 40) { $slug = $slug.Substring(0,40).Trim('-') }
$found = @()
$i = 0
foreach ($f in $new) {
    # if it's already inside OutDir, keep it; otherwise copy it out
    if ($f.FullName.StartsWith($OutDir, [StringComparison]::OrdinalIgnoreCase)) {
        $found += $f.FullName; continue
    }
    $i++
    $suffix = if ($new.Count -gt 1) { "-$i" } else { "" }
    $dest = Join-Path $OutDir ("{0}{1}{2}" -f $slug, $suffix, $f.Extension)
    $n = 2
    while (Test-Path -LiteralPath $dest) { $dest = Join-Path $OutDir ("{0}{1}-v{2}{3}" -f $slug,$suffix,$n,$f.Extension); $n++ }
    Copy-Item -LiteralPath $f.FullName -Destination $dest -Force
    $found += (Resolve-Path -LiteralPath $dest).Path
}

# ---- report ----------------------------------------------------------------
Remove-Item $lastMsg -ErrorAction SilentlyContinue
""
if ($found.Count -gt 0) {
    Write-Host "SUCCESS - $($found.Count) image(s) (copied into OutDir):" -ForegroundColor Green
    foreach ($p in $found) { "CREATED: $p" }
    exit 0
} else {
    Write-Host "NO IMAGES FOUND - agent finished without producing a file." -ForegroundColor Yellow
    "---- agent final message ----"
    if ($finalMsg) { $finalMsg } else { ($stdout | Select-Object -Last 40) }
    "-----------------------------"
    "Hints: re-run; if it asks for an API key it used the fallback (force built-in image_gen)."
    "       if auth errors, run 'codex login'. Try -Model gpt-5.1-codex if the tool seems disabled."
    exit 2
}
