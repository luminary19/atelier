#requires -Version 5.1
<#
.SYNOPSIS
  Crop one pane out of an N-pane moodboard grid (default 4x2 = 8 panes, row-major).

.DESCRIPTION
  Used by atelier-direction after the user picks one of the moodboard directions: cuts the chosen
  pane out of the single grid PNG so it can be passed back into codex-image.ps1 -Edit as an image
  reference for a clean, faithful regeneration. Native Windows System.Drawing — no install, no network.

  The grid is assumed evenly divided into $Cols x $Rows cells (the moodboard prompt requests thin
  gutters, so a fractional crop may include a hairline of gutter / the corner caption — harmless,
  since the crop is only an image reference for the regeneration that follows).

.EXAMPLE
  crop-pane.ps1 -Grid "...\.atelier\moodboards\board.png" -Pane 8 -Out "...\chosen-pane.png"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][string] $Grid,
    [Parameter(Mandatory)][int]    $Pane,    # 1-based, row-major (top row = 1..Cols)
    [int]    $Cols = 4,
    [int]    $Rows = 2,
    [string] $Out
)
$ErrorActionPreference = "Stop"
function Fail($m) { Write-Error $m; exit 1 }

if (-not (Test-Path -LiteralPath $Grid)) { Fail "Grid image not found: $Grid" }
$total = $Cols * $Rows
if ($Pane -lt 1 -or $Pane -gt $total) { Fail "Pane $Pane is out of range 1..$total" }

$gridPath = (Resolve-Path -LiteralPath $Grid).Path
if (-not $Out) { $Out = Join-Path (Split-Path -Parent $gridPath) ("chosen-pane-{0}.png" -f $Pane) }

Add-Type -AssemblyName System.Drawing
$img = [System.Drawing.Image]::FromFile($gridPath)
try {
    $W = $img.Width; $H = $img.Height
    $idx = $Pane - 1
    $col = $idx % $Cols
    $row = [math]::Floor($idx / $Cols)
    $cw = [int]($W / $Cols); $ch = [int]($H / $Rows)
    $x = [int]($col * $W / $Cols); $y = [int]($row * $H / $Rows)

    $crop = New-Object System.Drawing.Bitmap($cw, $ch)
    $g = [System.Drawing.Graphics]::FromImage($crop)
    $g.DrawImage($img, (New-Object System.Drawing.Rectangle(0, 0, $cw, $ch)), $x, $y, $cw, $ch, [System.Drawing.GraphicsUnit]::Pixel)
    $crop.Save($Out, [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose(); $crop.Dispose()
}
finally { $img.Dispose() }

Write-Host "CROPPED: $Out ($cw x $ch) [pane $Pane of $total -> col $col, row $row]"
