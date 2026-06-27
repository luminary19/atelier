# USD Pipeline — Stage Authoring, Validation & USDZ
# forge-export | references/usd-pipeline.md

## Contents
- §1. USD install options (Windows)
- §2. usd-core Python API — stage lifecycle
- §3. Mesh authoring (UsdGeom.Mesh)
- §4. UsdPreviewSurface material + textures
- §5. Composition arcs (LIVRPS rules)
- §6. Asset directory layout (ASWF convention)
- §7. USDZ packaging for iOS AR
- §8. CLI tools reference
- §9. USD validation
- §10. Windows-specific gotchas

---

## §1. USD install options (Windows)

**Option A — pip (usd-core 26.05, Python 3.11):**
```powershell
pip install usd-core==26.05
# Includes: pxr.Usd, pxr.UsdGeom, pxr.UsdShade, pxr.UsdUtils
# Does NOT include: usdview, usdrecord (requires Qt), full usdz CLI
python -c "from pxr import Usd; print(Usd.GetVersion())"
```

**Option B — NVIDIA prebuilt (full, includes usdview + usdrecord):**
```powershell
# Download from: https://developer.nvidia.com/usd#libraries-and-tools
# Example: usd-24.11-windows-x86_64.zip
Expand-Archive usd-24.11-windows-x86_64.zip -DestinationPath C:\tools\usd
$env:PATH += ";C:\tools\usd\bin"
$env:PYTHONPATH += ";C:\tools\usd\lib\python"
$env:PXR_PLUGINPATH_NAME = "C:\tools\usd\plugin\usd"
usdcat --version    # verify
```

**Option C — Full source build (development / custom plugins):**
```powershell
git clone https://github.com/PixarAnimationStudios/OpenUSD
cd OpenUSD
python build_scripts\build_usd.py "C:\tools\usd-build" `
    --no-tests --no-examples --no-imaging `
    --python-major-version 3
```

---

## §2. usd-core Python API — stage lifecycle

```python
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')  # Windows UTF-8

from pxr import Usd, UsdGeom, UsdShade, Gf

# Create a new stage
stage = Usd.Stage.CreateNew("C:/forge-build/out/scene.usdc")

# Set required metadata FIRST
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)   # Y-up (glTF/Blender convention)
stage.SetMetadata("metersPerUnit", 0.01)            # 1 USD unit = 1 cm (matches Blender/Maya)

# Define the default prim (REQUIRED — without this, many tools fail)
xform = UsdGeom.Xform.Define(stage, "/World")
stage.SetDefaultPrim(xform.GetPrim())

# Open an existing stage
stage = Usd.Stage.Open("C:/forge-build/out/scene.usdc")

# Work in memory (no file I/O until Export)
stage = Usd.Stage.CreateInMemory()

# Save (same path) vs Export (different path / format)
stage.Save()                                        # overwrite in place
stage.Export("C:/forge-build/out/scene.usda")       # text debug output

# Convert binary ↔ text
# (requires full USD build — usdcat CLI)
# usdcat scene.usdc --out scene.usda
# usdcat scene.usda --out scene.usdc
```

---

## §3. Mesh authoring (UsdGeom.Mesh) — key calls

```python
from pxr import Usd, UsdGeom, Gf, Vt, Sdf

mesh = UsdGeom.Mesh.Define(stage, "/World/Chair")
mesh.CreatePointsAttr(Vt.Vec3fArray([...]))           # XYZ positions
mesh.CreateFaceVertexCountsAttr(Vt.IntArray([...]))   # faces (3=tri, 4=quad)
mesh.CreateFaceVertexIndicesAttr(Vt.IntArray([...]))  # per-face indices

# CRITICAL for hard-surface — default is catmullClark (subdivides your mesh!)
mesh.CreateSubdivisionSchemeAttr("none")

# Normals — faceVarying = per vertex-per-face (most common)
mesh.CreateNormalsAttr(Vt.Vec3fArray([...]))
mesh.SetNormalsInterpolation("faceVarying")

# UV primvar — convention is "st" (NOT "uv" or "UV0") — required by UsdPreviewSurface
st = mesh.CreatePrimvar("st", Sdf.ValueTypeNames.TexCoord2fArray)
st.SetInterpolation("faceVarying")
st.Set(Vt.Vec2fArray([...]))

# Extent — required for correct viewport bounding box
bounds = mesh.ComputeLocalBound(Usd.TimeCode.Default(), UsdGeom.Tokens.default_)
mesh.CreateExtentAttr(Vt.Vec3fArray([bounds.GetBox().GetMin(), bounds.GetBox().GetMax()]))

stage.Save()
```

---

## §4. UsdPreviewSurface material + textures

```python
from pxr import Usd, UsdGeom, UsdShade, Sdf, Gf

def build_preview_surface_material(
    stage: Usd.Stage,
    prim_path: str,
    base_color: tuple = (0.8, 0.8, 0.8),
    metallic: float = 0.0,
    roughness: float = 0.5,
    base_color_tex: str = None,   # e.g. "textures/baseColor.png"
    orm_tex: str = None,
):
    material = UsdShade.Material.Define(stage, prim_path)
    shader   = UsdShade.Shader.Define(stage, f"{prim_path}/PreviewSurface")
    shader.CreateIdAttr("UsdPreviewSurface")

    # PBR parameters (factor-only mode)
    shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).Set(Gf.Vec3f(*base_color))
    shader.CreateInput("metallic",     Sdf.ValueTypeNames.Float).Set(metallic)
    shader.CreateInput("roughness",    Sdf.ValueTypeNames.Float).Set(roughness)
    shader.CreateInput("useSpecularWorkflow", Sdf.ValueTypeNames.Int).Set(0)  # metallic workflow

    # Wire outputs
    material.CreateSurfaceOutput().ConnectToSource(
        shader.ConnectableAPI(), "surface"
    )

    # Add texture if provided
    if base_color_tex:
        reader = UsdShade.Shader.Define(stage, f"{prim_path}/UVReader")
        reader.CreateIdAttr("UsdPrimvarReader_float2")
        reader.CreateInput("varname", Sdf.ValueTypeNames.Token).Set("st")

        tex = UsdShade.Shader.Define(stage, f"{prim_path}/BaseColorTex")
        tex.CreateIdAttr("UsdUVTexture")
        tex.CreateInput("file", Sdf.ValueTypeNames.Asset).Set(base_color_tex)
        tex.CreateInput("sourceColorSpace", Sdf.ValueTypeNames.Token).Set("sRGB")
        tex.CreateInput("st", Sdf.ValueTypeNames.Float2).ConnectToSource(
            reader.ConnectableAPI(), "result"
        )
        tex.CreateOutput("rgb", Sdf.ValueTypeNames.Float3)
        shader.CreateInput("diffuseColor", Sdf.ValueTypeNames.Color3f).ConnectToSource(
            tex.ConnectableAPI(), "rgb"
        )

    return material

# Bind material to mesh
def bind_material(mesh_prim: Usd.Prim, material: UsdShade.Material) -> None:
    binding_api = UsdShade.MaterialBindingAPI.Apply(mesh_prim)
    binding_api.Bind(material)
```

---

## §5. Composition arcs (LIVRPS rules)

**LIVRPS strength order (strongest → weakest):**
| Strength | Arc | Description |
|---|---|---|
| 1 (strongest) | **L**ocal | Opinions in the local layer |
| 2 | **I**nherits | Class hierarchy |
| 3 | **V**ariants | VariantSet selections |
| 4 | **R**eferences | `references.Add()` to other USD files |
| 5 | **P**ayloads | Deferred-load references |
| 6 (weakest) | **S**ublayers | Layer stack composition |

**KEY RULE:** Variants (V) are STRONGER than References (R). This means variant-authored overrides
win over referenced geometry/material values. For material variant systems, author variant opinions
INSIDE the variant — they will win over material defaults from the referenced model.

**KEY RULE:** In sublayers, `subLayerPaths[0]` (first in the list) is the STRONGEST sublayer.
This is counter-intuitive: position 0 = top of stack = overrides everything below.

**Build a component asset (ASWF convention):**
```python
from pxr import Usd, UsdGeom, Kind

def build_component_asset(stage, asset_name, geo_layer, mtl_layer):
    # Root prim with asset metadata
    root = UsdGeom.Xform.Define(stage, f"/{asset_name}")
    root.GetPrim().SetAssetInfoByKey("identifier", Sdf.AssetPath(f"./{asset_name}.usd"))
    root.GetPrim().SetAssetInfoByKey("name", asset_name)

    # Tag as component-kind model (leaf node, has renderable geometry)
    Usd.ModelAPI(root).SetKind(Kind.Tokens.component)

    stage.SetDefaultPrim(root.GetPrim())

    # Payload for geometry (deferred load)
    root.GetPrim().GetPayloads().AddPayload(geo_layer, f"/{asset_name}")

    # Reference for materials (always loaded)
    # Add sublayer for overrides
    stage.GetRootLayer().subLayerPaths.append(mtl_layer)

    return root
```

---

## §6. Asset directory layout (ASWF convention)

```
assets/
  propChair/
    propChair.usd          ← component stage (defaultPrim + kind=component)
    propChair.usda         ← text version for debugging
    payload/
      geo.usdc             ← geometry data (behind payload arc — deferred load)
      mtl.usdc             ← materials (referenced — always loaded)
    textures/
      T_Chair_BaseColor.png
      T_Chair_ORM.png
      T_Chair_Normal.png

shots/
  s00_opening/
    s00.usd                ← shot stage (kind=shot)
    sublayers/
      layout.usdc          ← camera, set dressing (weakest)
      animation.usdc       ← character poses / transforms
      fx.usdc              ← FX, crowd (strongest)
```

**Layer strength in a shot (strongest → weakest):**
```
fx.usdc > animation.usdc > layout.usdc > sequence.usdc > global.usdc
```

```python
# Build a shot (sublayer = correct for shots; NOT reference)
def assemble_shot(
    shot_path: str,
    layers: list[str],     # [fx.usdc, anim.usdc, layout.usdc] strongest-first
):
    stage = Usd.Stage.CreateNew(shot_path)
    # subLayerPaths[0] = strongest
    for layer in layers:
        stage.GetRootLayer().subLayerPaths.append(layer)
    stage.Save()
    return stage
```

---

## §7. USDZ packaging for iOS AR

**Requirements for ARKit-compliant USDZ:**
- All geometry must be triangulated (`subdivisionScheme=none`)
- Textures: PNG or JPEG only (no EXR, no TIFF, no WebP)
- No absolute file paths (all relative)
- No external referenced USD files (all geometry/materials in one USDZ)
- File size < 100 MB (practical limit for Quick Look)
- Must pass `usdchecker --arkit --strict`

**Package with usdzip CLI (from full USD build):**
```powershell
# Package a usda + textures → usdz
usdzip --arkitAsset "C:/out/chair.usda" "C:/out/chair.usdz"

# Verify the archive contents
usdzip --list "C:/out/chair.usdz"

# Inspect embedded data
usdzip --dump "C:/out/chair.usdz"

# Validate ARKit compliance (STRICT)
usdchecker --arkit --strict "C:/out/chair.usdz"
if ($LASTEXITCODE -ne 0) { Write-Error "USDZ ARKit validation FAILED"; exit 1 }
```

**Package with Python UsdUtils (usd-core):**
```python
from pxr import UsdUtils, Ar

def package_usdz(usda_path: str, out_usdz: str) -> bool:
    try:
        # UsdUtils.CreateNewARKitUsdzPackage is available in full USD builds (not usd-core pip)
        success = UsdUtils.CreateNewARKitUsdzPackage(
            Ar.ResolvedPath(usda_path), out_usdz
        )
        return success
    except AttributeError:
        # usd-core pip: use subprocess to call usdzip CLI instead
        import subprocess
        result = subprocess.run(
            ["usdzip", "--arkitAsset", usda_path, out_usdz],
            capture_output=True, text=True
        )
        return result.returncode == 0
```

**USDZ file size limit:** ZIP32 format — files > 4 GB produce corrupted archives (zip32 limit).
For large assets, split into multiple USDZ files per asset.

---

## §8. CLI tools reference

| Tool | Description | Available in usd-core pip? |
|---|---|---|
| `usdcat` | Convert between .usda/.usdc/.usdz; print contents | YES |
| `usdchecker` | Validate spec compliance + ARKit rules | YES |
| `usdzip` | Package/unpackage .usdz archives | Partial (no --arkitAsset) |
| `usdedit` | Open usda in default text editor | YES |
| `usdtree` | Print prim hierarchy | YES |
| `usdview` | Interactive viewer | NO (needs Qt) |
| `usdrecord` | Headless render to PNG | NO (needs Qt + GL) |

**usdrecord headless render (full USD build only):**
```powershell
# Render frame 0 via Embree (no GPU needed)
usdrecord `
    --renderer Embree `
    --frames 0:0 `
    --imageWidth 512 `
    "C:/out/scene.usdc" `
    "C:/out/preview.png"

# On Windows without Qt — usdrecord needs DISPLAY env workaround:
# If usdrecord fails with "No displays found" even with Embree renderer,
# install a minimal Qt and set QT_QPA_PLATFORM=offscreen:
$env:QT_QPA_PLATFORM = "offscreen"
```

---

## §9. USD validation

```python
# validate_usd.py — run usdchecker via subprocess
import subprocess, sys, json, pathlib

USD_CHECKER = r"C:\tools\usd\bin\usdchecker.exe"

def validate_usd(path: str, arkit: bool = False) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {"ok": False, "error": "file_not_found"}
    cmd = [USD_CHECKER]
    if arkit:
        cmd += ["--arkit", "--strict"]
    cmd.append(str(p))
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout + result.stderr
    errors   = [l for l in output.splitlines() if "ERROR" in l.upper()]
    warnings = [l for l in output.splitlines() if "WARN"  in l.upper()]
    return {
        "ok": result.returncode == 0,
        "path": str(p),
        "errors": errors,
        "warnings": warnings,
        "size_mb": round(p.stat().st_size / (1024*1024), 2),
    }

if __name__ == "__main__":
    arkit = "--arkit" in sys.argv
    path  = [a for a in sys.argv[1:] if not a.startswith("--")][0]
    result = validate_usd(path, arkit)
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)
```

---

## §10. Windows-specific gotchas

| Gotcha | Symptom | Fix |
|---|---|---|
| **DLL load failures (conda)** | `ImportError: DLL load failed` on `from pxr import Usd` | Use non-conda Python; set `os.add_dll_directory()` for USD DLL paths |
| **PXR_PLUGINPATH_NAME not set** | USD plugins (e.g. glTF file format) not found | Set `$env:PXR_PLUGINPATH_NAME = "C:\tools\usd\plugin\usd"` |
| **usdrecord fails without Qt** | "Could not find or load platform plugin" | Set `$env:QT_QPA_PLATFORM="offscreen"` or use usd-core + Embree |
| **Wrong subdivisionScheme** | Mesh over-subdivided on import | Always set `subdivisionScheme=none` for hard-surface meshes |
| **Missing defaultPrim** | "No default prim" error in AR/Quick Look | `stage.SetDefaultPrim(root_prim)` BEFORE saving |
| **USDZ > 4 GB** | Corrupted archive (zip32 limit) | Split into per-asset USDZ packages |
| **Variant selection in wrong layer** | Variant override ignored | Variants must be authored in the LOCAL layer — not in a sublayer weaker than local |
| **usd-core missing UsdUtils** | `AttributeError: module 'pxr.UsdUtils' has no attribute 'CreateNewARKitUsdzPackage'` | Use subprocess call to `usdzip` CLI (see §7); full USD build required for CreateNewARKitUsdzPackage |
| **Backslash paths** | Asset paths with backslash corrupt on non-Windows | Always use forward slashes in USD asset paths: `"./textures/base.png"` not `".\\textures\\base.png"` |
| **usd-core no usdview/usdrecord** | ImportError or "command not found" | These tools require Qt GUI — use full USD prebuilt or NVIDIA prebuilt |
