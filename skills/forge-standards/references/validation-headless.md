# Headless Validation Invocations — forge-standards reference

Covers the exact PowerShell/Bash commands to run standards validation headlessly on Windows 11.
For full per-check logic, see `forge-standards-schema.md §4` and the `forge-validate` skill.

---

## Single asset validation (PowerShell)

```powershell
$blender   = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$validator = "C:\project\tools\forge_validate_standards.py"
$asset     = "C:\project\source\props\SM_Chair_Wood\SM_Chair_Wood_v01.blend"

& $blender --factory-startup -b $asset `
    -P $validator `
    -- --profile console --root "C:\project"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Validation FAILED for $asset"
}
```

## Batch validation (all .blend files in a directory)

See `forge-standards-schema.md §5` for the full `validate_all_assets.ps1` script.

Quick one-liner (PowerShell, no script file):
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
Get-ChildItem "C:\project\source" -Recurse -Filter "*.blend" | ForEach-Object {
    Write-Host "Validating: $($_.Name)"
    & $blender --factory-startup -b $_.FullName `
        -P "C:\project\tools\forge_validate_standards.py" `
        -- --profile console --root "C:\project"
}
```

## Render-verify scale check (after export)

After exporting, confirm scale and visual correctness against the 1.8 m human reference.

**Pinned, reproducible defaults** (so two runs of the same asset produce the same PNG):

| Setting | Value | Why |
|---------|-------|-----|
| Engine / samples | **Cycles 16 samples, `cycles.seed=0`** (or Workbench for a flat matte) | Deterministic; Cycles not EEVEE-Next headless on Windows |
| Resolution | **512×512** | Small, fast, enough to read a silhouette ratio |
| Camera | **Fixed orthographic side camera** (baked into `render_rig.blend`) | Ortho removes perspective foreshortening so height ratios are exact |
| Reference | **1.8 m human silhouette at world origin** | The single fixed scale yardstick every asset is judged against |

```powershell
$blender  = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$rig      = "C:\project\tools\render_rig.blend"  # ortho side cam + 1.8 m silhouette + Cycles 16spp seed=0
$verifier = "C:\project\tools\render_verify.py"  # links asset, renders 512x512 to --out
$export   = "C:\project\export\SM_Chair_Wood_01.fbx"
$out      = "C:\project\qa\SM_Chair_Wood_01_verify.png"

& $blender --factory-startup -b $rig `
    -P $verifier `
    -- --asset $export --out $out -f 1

# Then Read the PNG visually in Claude:
# Read("C:\project\qa\SM_Chair_Wood_01_verify.png")
# Confirm: chair seat top at ~25% of 1.8 m silhouette height (~0.45 m)
```

**Scale/orientation failure → cause → fix:**

| What the PNG shows | Likely cause | Fix |
|--------------------|--------------|-----|
| Silhouette ~**half** the expected height (or asset ~2× too tall) | 0.01× / 2× unit mismatch | Set `unit_settings.scale_length` correctly, then `object.transform_apply(scale=True)`; re-export |
| Asset a **tiny speck** (~1% height) or **fills the frame** (~100×) | meters↔cm 100× error (the classic skeletal-mesh bug) | For SK: `scale_length=0.01` + `FBX_SCALE_UNITS`; for SM: `FBX_SCALE_ALL` + `apply_unit_scale=True` (see `coordinate-systems.md §3/§7`) |
| Asset **rotated 90°** (lying down / facing wrong way) | Z-up (Blender) vs Y-up (web/Unity) export mismatch | Re-export with the correct up axis — glTF: `export_yup=True`; FBX: `axis_up='Z', axis_forward='-Y'` |
| Asset **mirrored** | scale swizzle sign error on conversion | Scale swizzle is `(x, z, y)` — no sign flip (see `coordinate-systems.md §7`) |

Deeper render-QA (samples, passes, contact sheets): `forge-validate` `references/render-qa-guide.md`.

## Handoff to forge-validate

For the full production gate (manifold, watertight, normals, UV overlap, glTF-Validator):

```
Run = call Skill("forge-validate")
```

Do NOT write "run forge-validate" in prose — that runs nothing. Call the Skill tool.

## Windows batch-render hang fix (Blender 4.5+)

If multiple sequential Blender invocations hang after the first:

```powershell
# Use Start-Process -Wait instead of &; add --factory-startup
foreach ($blend in $blends) {
    $proc = Start-Process -FilePath $blender `
        -ArgumentList "--factory-startup -b `"$blend`" -P `"$validator`" -- --profile console" `
        -Wait -PassThru -NoNewWindow
    Write-Host "Exit: $($proc.ExitCode)"
}
```
