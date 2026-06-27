# FORGE_STANDARDS.json Schema & Validation — forge-standards reference

## Contents
- §1. Schema overview
- §2. Full annotated example
- §3. Reading the schema in bpy (headless)
- §4. Headless validation script
- §5. PowerShell batch validation

---

## §1. Schema overview

`FORGE_STANDARDS.json` is the **machine-readable token file** for a 3D project. Every Forge skill
reads it to get project-specific budgets, naming patterns, and conventions. It lives at the project
root (same level as `FORGE.md`). `forge-brief` creates a starter version; `forge-standards` fills in
all sections.

Required top-level fields:

| Field | Type | Purpose |
|-------|------|---------|
| `version` | string | Schema version (currently `"1.0"`) |
| `project` | string | Project identifier (used in logs) |
| `engine` | string | Target: `"unreal5"`, `"unity"`, `"godot4"`, `"web"`, `"print"`, `"film"` |
| `coordinate_system` | object | Confirmed up-axis, handedness, scale unit |
| `profiles` | object | One or more named budget profiles (e.g. `"console"`, `"mobile"`, `"web"`) |

---

## §2. Full annotated example

```json
{
  "version": "1.0",
  "project": "MyGame",
  "engine": "unreal5",
  "coordinate_system": {
    "blender_up": "Z",
    "blender_handedness": "RH",
    "blender_unit": "meters",
    "target_up": "Z",
    "target_handedness": "LH",
    "target_unit": "centimeters",
    "fbx_axis_forward": "-Y",
    "fbx_axis_up": "Z",
    "fbx_apply_scalings": "FBX_SCALE_ALL",
    "notes": "Use FBX_SCALE_UNITS (with scene unit_settings.scale_length=0.01) for skeletal meshes to avoid the 100x bone bug"
  },
  "profiles": {
    "console": {
      "max_tris_lod0":          50000,
      "max_tris_lod1":          25000,
      "max_tris_lod2":          12500,
      "max_tris_lod3":           3000,
      "required_lod_count":         3,
      "lod_ratios":          [1.0, 0.5, 0.2, 0.05],
      "texel_density_px_m":      1024,
      "texel_density_hero_px_m": 2048,
      "min_uv_utilization":      0.80,
      "lm_uv_margin":            0.02,
      "max_texture_res":         4096,
      "draw_call_ceiling":        200,
      "allowed_name_pattern":
        "^(SM|SK|T|M|MI|MF|MPC|BP|ABP|SKEL|AM|AS|NS|HDR|DT|PHYS)_[A-Z][A-Za-z0-9]+(_[A-Za-z0-9]+)*(_LOD\\d)?$",
      "texture_suffixes": {
        "base_color":  ["_BC", "_D"],
        "normal":      ["_N"],
        "orm":         ["_ORM"],
        "roughness":   ["_R"],
        "metallic":    ["_M", "_MT"],
        "ao":          ["_AO"],
        "emissive":    ["_E", "_EM"],
        "height":      ["_H"]
      },
      "orm_channel_pack": {
        "R": "AO",
        "G": "Roughness",
        "B": "Metallic",
        "color_space": "Non-Color"
      },
      "collision_prefix": "UCX_",
      "pivot_rule": "bottom_center_for_props_hinge_for_doors",
      "pivot_tolerance_m": 0.005,
      "scale_unit": "meters_applied_fbx_scale_all",
      "git_lfs_extensions": [".blend", ".fbx", ".glb", ".png", ".tga", ".exr", ".psd"]
    },
    "mobile": {
      "max_tris_lod0":           8000,
      "max_tris_lod1":           4000,
      "max_tris_lod2":           1500,
      "required_lod_count":         2,
      "lod_ratios":          [1.0, 0.5, 0.2],
      "texel_density_px_m":       512,
      "texel_density_hero_px_m": 1024,
      "min_uv_utilization":      0.80,
      "lm_uv_margin":            0.04,
      "max_texture_res":         1024,
      "draw_call_ceiling":        100,
      "scene_tri_budget":       150000,
      "allowed_name_pattern":
        "^(SM|SK|T|M|MI)_[A-Z][A-Za-z0-9]+(_[A-Za-z0-9]+)*(_LOD\\d)?$"
    },
    "web": {
      "max_tris_lod0":          50000,
      "required_lod_count":         0,
      "lod_ratios":          [1.0],
      "texel_density_px_m":       512,
      "min_uv_utilization":      0.75,
      "max_texture_res":         2048,
      "max_glb_file_mb":            4,
      "scene_tri_budget":       150000,
      "draw_call_ceiling":         50,
      "draco_compression_level":    6,
      "allowed_name_pattern":
        "^(SM|T|M|MI)_[A-Z][A-Za-z0-9]+(_[A-Za-z0-9]+)*$"
    }
  }
}
```

---

## §3. Reading the schema in bpy (headless)

```python
# forge_load_standards.py — load FORGE_STANDARDS.json and extract active profile
import json, sys
from pathlib import Path

def load_standards(project_root=None):
    """Load FORGE_STANDARDS.json from project root. Returns (standards_dict, profile_dict)."""
    root = Path(project_root) if project_root else Path.cwd()
    path = root / "FORGE_STANDARDS.json"
    if not path.exists():
        raise FileNotFoundError(f"FORGE_STANDARDS.json not found at {path}")
    with open(path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    return data

def get_profile(standards, profile_name=None):
    """Get a named profile, or the first profile if name is None."""
    profiles = standards.get("profiles", {})
    if not profiles:
        raise ValueError("FORGE_STANDARDS.json has no profiles defined")
    if profile_name:
        if profile_name not in profiles:
            raise KeyError(f"Profile '{profile_name}' not in FORGE_STANDARDS.json")
        return profiles[profile_name]
    # Default: first profile
    return next(iter(profiles.values()))

# Usage in a headless Blender script:
# import bpy
# standards = load_standards(project_root="C:/project")
# profile   = get_profile(standards, "console")
# max_tris  = profile["max_tris_lod0"]   # → 50000
# pattern   = profile["allowed_name_pattern"]
```

---

## §4. Headless validation script

This is an abbreviated version; the full validator lives in `forge-validate`. This lightweight
version runs checks directly from `FORGE_STANDARDS.json` — useful for a quick pre-commit check.

```python
# forge_validate_standards.py — run via: blender -b asset.blend -P forge_validate_standards.py -- --profile console --root C:/project
import bpy, sys, re, json, io
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--profile", default="console")
ap.add_argument("--root", default=".")
ap.add_argument("--json", action="store_true")
args = ap.parse_args(argv)

# Load standards
standards_path = Path(args.root) / "FORGE_STANDARDS.json"
if standards_path.exists():
    with open(standards_path, 'r', encoding='utf-8-sig') as f:
        data = json.load(f)
    profile = data.get("profiles", {}).get(args.profile, {})
else:
    # Fallback built-in defaults
    profile = {
        "max_tris_lod0": 50000,
        "required_lod_count": 3,
        "texel_density_px_m": 1024,
        "max_texture_res": 4096,
        "allowed_name_pattern": r"^(SM|SK|T|M|MI)_[A-Z][A-Za-z0-9]+(_[A-Za-z0-9]+)*$",
    }

errors   = []
warnings = []

pattern  = profile.get("allowed_name_pattern", "")
max_tris = profile.get("max_tris_lod0", 0)

for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    name = obj.name

    # Naming check
    if pattern and not re.match(pattern, name):
        errors.append(f"NAMING: '{name}' does not match pattern")

    # Triangle count
    if max_tris:
        obj.data.calc_loop_triangles()
        count = len(obj.data.loop_triangles)
        if count > max_tris:
            errors.append(f"POLYCOUNT: '{name}' has {count:,} tris > limit {max_tris:,}")

    # N-gons
    ngon_count = sum(1 for p in obj.data.polygons if p.loop_total > 4)
    if ngon_count:
        warnings.append(f"NGONS: '{name}' has {ngon_count} n-gons — triangulate before export")

    # Unapplied scale
    sx, sy, sz = obj.scale
    if abs(sx-1)>0.001 or abs(sy-1)>0.001 or abs(sz-1)>0.001:
        errors.append(f"SCALE: '{name}' has unapplied scale {obj.scale[:]} — apply before export")

    # Negative scale
    if any(v < 0 for v in obj.scale):
        errors.append(f"NEG_SCALE: '{name}' has negative scale — apply then recalculate normals")

    # UV channels
    if not obj.data.uv_layers:
        errors.append(f"UV: '{name}' has no UV maps")
    else:
        lm_names = {'LightmapUV', 'UVMap_1', 'uv2', 'UV2', 'Lightmap'}
        has_lm = any(ul.name in lm_names or i==1 for i, ul in enumerate(obj.data.uv_layers))
        if not has_lm and profile.get("required_lod_count", 0) > 0:
            warnings.append(f"LIGHTMAP_UV: '{name}' has no dedicated lightmap UV channel")

    # Material assignment
    if not obj.data.materials:
        errors.append(f"MATERIAL: '{name}' has no material assigned")
    else:
        for mat in obj.data.materials:
            if mat is None:
                errors.append(f"MATERIAL: '{name}' has empty material slot")
            elif mat.name and ' ' in mat.name:
                errors.append(f"MATERIAL: '{mat.name}' has space in name")

result = {
    "profile": args.profile,
    "errors": errors,
    "warnings": warnings,
    "passed": len(errors) == 0,
}

if args.json:
    print(json.dumps(result, indent=2))
else:
    print(f"\n=== FORGE VALIDATE — profile: {args.profile} ===")
    if errors:
        print(f"ERRORS ({len(errors)}):")
        for e in errors: print(f"  [ERR]  {e}")
    if warnings:
        print(f"WARNINGS ({len(warnings)}):")
        for w in warnings: print(f"  [WARN] {w}")
    if not errors and not warnings:
        print("  ALL CHECKS PASSED")
    print(f"Result: {'FAIL' if errors else 'PASS'}\n")

sys.exit(1 if errors else 0)
```

---

## §5. PowerShell batch validation

```powershell
# validate_all_assets.ps1 — run forge_validate_standards.py against all .blend in source/
$blender   = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$validator = "C:\project\tools\forge_validate_standards.py"
$root      = "C:\project"
$profile   = "console"
$failed    = @()

$assets = Get-ChildItem "$root\source" -Recurse -Filter "*.blend"
Write-Host "Validating $($assets.Count) assets against profile: $profile"

foreach ($asset in $assets) {
    Write-Host "  $($asset.Name) ..."
    & $blender --factory-startup -b $asset.FullName `
        -P $validator `
        -- --profile $profile --root $root
    if ($LASTEXITCODE -ne 0) {
        $failed += $asset.Name
        Write-Host "    FAILED: $($asset.Name)" -ForegroundColor Red
    } else {
        Write-Host "    OK" -ForegroundColor Green
    }
}

if ($failed.Count -gt 0) {
    Write-Host "`nFAILED assets ($($failed.Count)):" -ForegroundColor Red
    $failed | ForEach-Object { Write-Host "  - $_" }
    exit 1
} else {
    Write-Host "`nAll assets passed validation." -ForegroundColor Green
    exit 0
}
```
