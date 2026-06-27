# Forge Texture — Advanced Bake Topics

## Contents
- §1. UDIM tile-shift workaround
- §2. Complete headless PowerShell pipeline script
- §3. sys.argv parsing pattern for bake scripts
- §4. Gotcha → Fix table (G1–G15)

---

## §1. UDIM Tile-Shift Workaround

Blender does not natively bake all UDIM tiles in one pass (5.2 LTS). Workaround: for each tile,
temporarily shift all UVs so that tile falls in [0,1], bake, then shift back.

```python
import bpy, os

def bake_udim_tiles(
    obj_name: str,
    uv_map_name: str,
    bake_type: str,
    out_dir: str,
    tile_count: int,     # tiles 1001, 1002, ...
    resolution: int = 2048,
    samples: int = 64,
) -> list[str]:
    """
    Tile 1001 = U offset 0, 1002 = U offset 1, 1003 = U offset 2, etc.
    Each tile is saved as {obj_name}_{tile_number}.png in out_dir.
    """
    from .bake_scripts import setup_cycles, make_bake_image, assign_bake_image_node, \
        remove_bake_image_nodes, save_image

    obj = bpy.data.objects[obj_name]
    setup_cycles(samples)
    os.makedirs(out_dir, exist_ok=True)
    saved = []

    for tile_index in range(tile_count):
        tile_number = 1001 + tile_index
        img_name = f"{obj_name}_{tile_number}"
        colorspace = "Non-Color" if bake_type == "NORMAL" else "sRGB"
        img = make_bake_image(img_name, resolution, colorspace)
        assign_bake_image_node(obj, img)

        # Shift UVs so this tile falls in [0,1]
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.transform.translate(value=(-tile_index, 0, 0), orient_type="GLOBAL")
        bpy.ops.object.mode_set(mode="OBJECT")

        bpy.ops.object.select_all(action="DESELECT")
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.object.bake(type=bake_type)

        # Shift back
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        bpy.ops.uv.select_all(action="SELECT")
        bpy.ops.transform.translate(value=(tile_index, 0, 0), orient_type="GLOBAL")
        bpy.ops.object.mode_set(mode="OBJECT")

        out_path = os.path.join(out_dir, f"{img_name}.png").replace("\\", "/")
        save_image(img, out_path)
        remove_bake_image_nodes(obj)
        saved.append(out_path)

    return saved
```

**Known limitation:** This workaround modifies UVs in place. If other passes are baked in the same
session, always confirm UV positions are back at their original tile offsets before the next bake.

---

## §2. Complete Headless PowerShell Pipeline Script

```powershell
# forge_bake_pipeline.ps1 — bake a full PBR set (normal + AO + curvature + albedo + roughness)
# Usage: .\forge_bake_pipeline.ps1 -Blend scene.blend -LowPoly Hero_LP -HighPoly Hero_HP -OutDir C:\out
param(
    [Parameter(Mandatory)][string]$Blend,
    [Parameter(Mandatory)][string]$LowPoly,
    [Parameter(Mandatory)][string]$HighPoly,
    [Parameter(Mandatory)][string]$OutDir,
    [string]$Resolution = "2048",
    [string]$Samples    = "64",
    [string]$Device     = "OPTIX",
    [string]$NormalG    = "POS_Y"   # POS_Y = OpenGL, NEG_Y = DirectX/Unreal
)

$BLENDER = "C:\Program Files\Blender Foundation\Blender 4.3\blender.exe"
$SCRIPT  = "$env:CLAUDE_CONFIG_DIR\skills\forge-texture\scripts\bake_pbr.py"

New-Item -ItemType Directory -Force -Path $OutDir | Out-Null

# Forward-slash paths for Blender filepath_raw
$BlendFwd  = $Blend  -replace "\\", "/"
$OutDirFwd = $OutDir -replace "\\", "/"

# The -- separator is MANDATORY before Python script arguments
& $BLENDER `
    --background $BlendFwd `
    --python     $SCRIPT `
    --python-exit-code 1 `
    -- `
    --lowpoly  $LowPoly `
    --highpoly $HighPoly `
    --out      $OutDirFwd `
    --res      $Resolution `
    --samples  $Samples `
    --device   $Device `
    --normal-g $NormalG

if ($LASTEXITCODE -ne 0) {
    Write-Error "[forge] Bake failed: exit $LASTEXITCODE"
    exit 1
}
Write-Host "[forge] Bake complete -> $OutDir"
```

---

## §3. sys.argv Parsing Pattern

Inside the bake Python script, parse arguments passed after `--`:

```python
import sys, argparse, io

# Windows UTF-8 stdout fix (always include at top of headless scripts)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Extract Forge-specific argv (after the mandatory -- separator)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

ap = argparse.ArgumentParser()
ap.add_argument("--lowpoly",   required=True)
ap.add_argument("--highpoly",  required=True)
ap.add_argument("--out",       required=True)
ap.add_argument("--res",       type=int, default=2048)
ap.add_argument("--samples",   type=int, default=64)
ap.add_argument("--device",    default="OPTIX")
ap.add_argument("--normal-g",  default="POS_Y",  dest="normal_g",
                choices=["POS_Y", "NEG_Y"])
args = ap.parse_args(argv)

# Use args.lowpoly, args.highpoly, args.out, args.res, args.samples,
#     args.device, args.normal_g throughout the bake script
```

---

## §4. Gotcha → Fix Table (G1–G15)

| # | Gotcha | Symptom | Fix |
|---|--------|---------|-----|
| G1 | No active image | `Error: No active image found, add a material or bake to an external file` | `tex_node.select = True` AND `nodes.active = tex_node` — both required |
| G2 | Black bake output | Output image all black | Check: `obj.hide_render = False`; UV map exists on low-poly; selection order (hi=selected, lo=active) |
| G3 | Green/mustard splotches | Large wrong-colour patches at concavities | Reduce `cage_extrusion`; start at 0.001 and double until detail is captured; or use explicit cage object |
| G4 | Seams at UV island edges | Visible colour/normal discontinuity at island borders, especially at distance | Increase `bake.margin` to 16 px (2K) or 32 px (4K); switch `margin_type='ADJACENT_FACES'` |
| G5 | Inverted normals | Bumps look like dents in target engine | Set `bake.normal_g = 'NEG_Y'` for Unreal/DX targets before baking; or flip G channel post-bake |
| G6 | Image not saved to disk | Pink/missing texture on disk after session close | Always call `img.save()` explicitly — Blender does NOT auto-save baked images on .blend save |
| G7 | GPU not activated | Bake runs slowly; no GPU device messages in console | Call `prefs.refresh_devices()` AFTER setting `compute_device_type`; then set `d.use = True` per device |
| G8 | UDIM only bakes tile 1001 | All other tiles remain grey/black | Use tile-shift workaround (§1 above) |
| G9 | Unapplied transforms break extrusion | Extrusion value correct visually but produces artifacts after model is resized | Run `bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)` before baking |
| G10 | Denoiser does not clean AO | AO bake still noisy despite denoiser enabled | Cycles denoiser only applies to `COMBINED` bake type; increase AO sample count to 128–256 instead |
| G11 | Edge Split modifier causes tangent seams | Sharp cut-lines in normal map at edges where Edge Split is applied | Remove/un-apply Edge Split modifier before baking; use custom normals (`use_auto_smooth`) instead |
| G12 | Windows backslash paths in filepath_raw | `img.save()` fails or writes to wrong location | Use forward slashes: `img.filepath_raw = "C:/out/normal.png"`. Never raw `r"C:\path"` with filepath_raw |
| G13 | Native ROUGHNESS/METALLIC bake black | `ROUGHNESS` or `METALLIC` bake type produces all-black images | Route socket through Emission node, bake as `EMIT` (§6 in bake-scripts.md) |
| G14 | Musgrave node removed in Blender 4.0 | `ShaderNodeTexMusgrave` AttributeError on every 4.x / 5.x build the suite targets (the node was merged into Noise and removed in 4.0, **not** 5.x) | Use `ShaderNodeTexNoise` with `noise_type='FBM'` (or `MULTIFRACTAL` / `RIDGED_MULTIFRACTAL`) and `Detail >= 8`. If a version guard is needed, gate any legacy Musgrave path on `bpy.app.version < (4, 0, 0)`. Matches procedural-nodes.md §1. |
| G15 | GPU preferences not saved headless | GPU falls back to CPU in `-b` mode even after prior GUI setup | GPU preferences saved to `userpref.blend` not loaded in `-b` mode; always set `compute_device_type` + `refresh_devices()` + `d.use=True` in the Python script itself |
