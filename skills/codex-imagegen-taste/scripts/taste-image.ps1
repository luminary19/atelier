#requires -Version 5.1
<#
.SYNOPSIS
  Render ONE premium website SECTION comp by injecting the Atelier taste preamble
  plus the site's locked style spec into a single call of the /codex-imagegen helper.

.DESCRIPTION
  This is the TASTE wrapper over /codex-imagegen. It does NOT talk to Codex itself
  and does NOT reimplement `codex exec`. It only composes a taste-enriched prompt
  (taste preamble + locked style spec + this section's art direction) and hands that
  to the REAL helper, codex-image.ps1, which owns every bit of Codex orchestration,
  the built-in image_gen tool, and the before/after filesystem-diff file discovery.

  One section = one call. Loop this once per planned section, threading the SAME
  -StyleSpec through every call so the whole site reads as a single brand. Vary the
  -SectionPrompt (composition anchor + background mode + content) per section.

  All real logic lives here, not in the SKILL.md: a model reading a SKILL.md will not
  execute fenced PowerShell verbatim, so the orchestration cannot live in markdown.

.NOTES
  Native Windows / PowerShell. ASCII-only on purpose (the composed prompt is embedded
  into the Codex call; non-ASCII risks encoding breakage on PowerShell 5.1).
  Exit codes are passed through from codex-image.ps1: 0 = image created,
  2 = none found (surface the agent message), 1 = preflight/error.
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)] [string] $SectionPrompt,   # art-directed brief for THIS section
    [Parameter(Mandatory = $true)] [string] $OutDir,
    [string] $Section      = "",            # label only, e.g. "3 of 8: Features"
    [string] $StyleSpec    = "",            # the LOCKED shared style spec (palette+type+CTA+treatment+radius)
    [string] $Anchor       = "",            # OPTIONAL style-anchor image (e.g. chosen-reference.png): fixes palette/quality/scheme; never copied. Omit => text-only (unchanged behaviour)
    [string] $PreambleFile = "",            # defaults to this skill's references\taste-preamble.md
    [string] $Size         = "1536x1024",   # horizontal by default; comps are always landscape
    [string] $Model,
    [switch] $Transparent,
    [int]    $TimeoutSec   = 420,
    [switch] $DryRun
)

$ErrorActionPreference = "Stop"
function Fail($m) { Write-Error $m; exit 1 }

# ---- locate the taste preamble --------------------------------------------
if (-not $PreambleFile) {
    $PreambleFile = Join-Path $PSScriptRoot "..\references\taste-preamble.md"
}
if (-not (Test-Path -LiteralPath $PreambleFile)) { Fail "Taste preamble not found: $PreambleFile" }
$preamble = Get-Content -LiteralPath $PreambleFile -Raw

# ---- locate the HANDS: the real /codex-imagegen helper --------------------
# Absolute path on this machine. The portable mirror copy replaces the next line with
# an env-resolver (CLAUDE_CONFIG_DIR) per the atelier-portable-mirror conventions.
$skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
$helper = "$skills\codex-imagegen\scripts\codex-image.ps1"
if (-not (Test-Path -LiteralPath $helper)) {
    Fail "codex-imagegen helper not found: $helper (is the codex-imagegen skill installed?)"
}

# ---- compose the taste-enriched prompt ------------------------------------
$styleBlock = ""
if ($StyleSpec) {
    $styleBlock = "LOCKED STYLE SPEC (identical across every section of this site):`n$StyleSpec`n`n"
}
$secLabel = if ($Section) { "SECTION $Section" } else { "SECTION (one of a multi-section site)" }

# Optional style anchor: the attached reference fixes palette/quality/scheme for the whole
# site, but each section keeps its OWN composition (anchor != template). Omitted => text-only.
$anchorBlock = ""
if ($Anchor) {
    if (-not (Test-Path -LiteralPath $Anchor)) { Fail "Anchor image not found: $Anchor" }
    $anchorBlock = "`n`nAESTHETIC ANCHOR (attached reference image): it fixes the SHARED palette, colour scheme, material quality, lighting, and mood for the entire site - match those precisely so this section belongs to the same world. But this is a DISTINCT section with its OWN composition, layout, and content per the brief above: do NOT replicate the anchor's composition, subject, framing, or specific elements. It is a style/colour reference, never a template to copy."
}

$composed = @"
$preamble

$styleBlock$secLabel - render ONE horizontal website-section comp (not a full page):
$SectionPrompt$anchorBlock
"@

# ---- normalize for safe native-arg passing (ASCII; self-sufficient) -------
# The npm `codex` shim splits a native arg at each embedded double-quote, so a prompt
# with double-quotes or newlines can be mis-parsed. Normalize here so the wrapper is
# safe regardless of whether the helper also sanitizes: any double-quote (straight or
# smart) -> single quote, then flatten newlines/tabs/space-runs to single spaces (image
# prompts don't need line structure). The smart-quote set is built from code points with
# [char], so this script stays pure ASCII while still catching smart quotes a caller
# might pass in -StyleSpec / -SectionPrompt.
$dquotes = @('"') + @(0x201C, 0x201D, 0x201E, 0x201F, 0x2033, 0x2036 | ForEach-Object { [char]$_ })
foreach ($q in $dquotes) { $composed = $composed.Replace([string]$q, "'") }
$composed = $composed -replace '[\r\n\t]+', ' '
$composed = ($composed -replace '\s{2,}', ' ').Trim()

# ---- per-section subdir so multi-section outputs don't collide ------------
# The helper derives each filename from the prompt, which shares the leading preamble
# across sections; landing each section in its own subdir of -OutDir keeps them distinct.
$sectionSlug = ($Section -replace '[^a-zA-Z0-9]+', '-').Trim('-').ToLower()
if ($sectionSlug) { $OutDir = Join-Path $OutDir $sectionSlug }

# ---- hand off to the REAL helper (it owns Codex + file discovery) ---------
$fwd = @{
    Prompt     = $composed
    OutDir     = $OutDir
    Count      = 1
    Size       = $Size
    TimeoutSec = $TimeoutSec
}
if ($Model)       { $fwd.Model = $Model }
if ($Transparent) { $fwd.Transparent = $true }
if ($DryRun)      { $fwd.DryRun = $true }
if ($Anchor)      { $fwd.Anchor = $Anchor }   # forwarded as the helper's -Anchor (attached via -i, generate-not-copy)

& $helper @fwd
exit $LASTEXITCODE
