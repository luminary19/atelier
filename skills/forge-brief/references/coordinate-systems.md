# Coordinate Systems — Forge Reference

## Contents
- §1. Per-engine coordinate system table
- §2. Blender → UE5 unit and axis correction
- §3. glTF standard (authoritative)
- §4. USD / OpenUSD conventions
- §5. Blender headless axis/scale export flags
- §6. Common gotchas and fixes

---

## §1. Per-engine coordinate system table

| Engine / Format | Up axis | Handedness | Scale unit | Forward axis | Notes |
|---|---|---|---|---|---|
| **glTF 2.0 / three.js / R3F** | Y-up | right-handed | meters | -Z | OpenGL convention; spec-mandated |
| **Unreal Engine 5** | Z-up | left-handed | centimeters (1 unit = 1 cm) | X | Right = Y; must flip Y→Z on import |
| **Unity** | Y-up | left-handed | meters | Z | Blender → Unity: flip Z axis |
| **Godot 4** | Y-up | right-handed | meters | -Z | Same as glTF; GLB importer native |
| **Blender (native)** | Z-up | right-handed | meters (scene-configurable) | -Y | Default; set via Scene Properties → Units |
| **OpenSCAD** | Z-up | right-handed | millimeters (default) | Y | Configure with `$fn`, not scene units |
| **CadQuery / build123d** | Z-up | right-handed | millimeters | Y | Python-native; `cq.Workplane("XY")` |
| **FreeCAD** | Z-up | right-handed | millimeters | Y | FEM/CAD standard |
| **USD / Omniverse / USDZ** | Y-up (default) | right-handed | meters (default; configurable) | -Z | `metersPerUnit` stage metadata |
| **iOS ARKit / USDZ** | Y-up | right-handed | meters | -Z | ARKit uses Y-up; Quick Look renders Y-up |
| **Android ARCore / GLB** | Y-up | right-handed | meters | -Z | Same as glTF |
| **Model Viewer (`<model-viewer>`)** | Y-up | right-handed | meters | -Z | Wraps Three.js/glTF; inherits Y-up |
| **Babylon.js** | Y-up | left-handed | meters | Z | Differs from Three.js; check Z-flip on import |
| **3D print (STL / 3MF)** | Z-up | right-handed | millimeters | Y | Slicer convention; no runtime engine |
| **Alembic (.abc)** | Y-up | right-handed | centimeters (Maya default) | -Z | Unit varies by DCC; check on export |
| **FBX** | Y-up (but stored in file) | configurable | cm (Maya/UE default) or m (Blender) | configurable | FBX encodes axis metadata; not always respected |

---

## §2. Blender → Unreal Engine 5

**The core problem:** Blender default is Z-up / right-handed / meters. UE5 is Z-up /
left-handed / centimeters, with forward axis X. The apparent Z-up match is misleading —
the handedness and scale differ.

### Axis correction

Blender uses `-Y` forward by default. UE5 expects `X` forward. Set in the FBX exporter:
```
axis_forward = '-Y'    # maps Blender -Y → UE5 X (correct facing)
axis_up      = 'Z'     # Z stays Z (both Z-up; no flip needed)
```
Net result: object faces correctly in UE5 without a 90° rotation.

### Unit correction (100× scale problem)

Blender: 1 unit = 1 m. UE5: 1 unit = 1 cm. A 1 m chair in Blender = 1 cm in UE5.

**Fix 1 — FBX exporter flags (recommended):**
```python
bpy.ops.export_scene.fbx(
    filepath="C:/project/export/SM_Chair_01.fbx",
    apply_scale_options='FBX_SCALE_ALL',  # scales everything to cm on export
    apply_unit_scale=True,
    axis_forward='-Y',
    axis_up='Z',
)
```

**Fix 2 — Scene unit scale (pre-export):**
```python
# Set scene unit scale to 0.01 so 1 Blender unit = 1 cm
bpy.context.scene.unit_settings.scale_length = 0.01
```
Then export without the scale_options override.

**Verify by render:** drop the exported asset next to UE5's mannequin (180 cm). Render a
screenshot. A correctly-scaled chair should sit at ~90 cm high.

### Normal map convention

Blender uses **OpenGL** normals (Y+ = up in UV space, green-up appearance).
UE5 uses **DirectX** normals (Y- = down in UV space, green-down appearance).

**Flip the green channel before delivering to UE5:**
```python
from PIL import Image
import numpy as np

def flip_normal_green(path_in, path_out):
    img = np.array(Image.open(path_in).convert('RGB'), dtype=float)
    img[:, :, 1] = 255 - img[:, :, 1]   # invert G channel
    Image.fromarray(img.astype('uint8')).save(path_out)
```

Or in Blender: in the material node graph, insert a `Separate Color` → invert Green →
`Combine Color` before the `Normal Map` node, then bake.

---

## §3. glTF 2.0 standard (authoritative)

From the Khronos spec (glTF 2.0 §3.3):
- **Right-handed coordinate system**
- **Y-up**
- **Positive X right, positive Y up, positive Z toward viewer**
- **Meters** — no explicit unit metadata; the spec assumes 1 unit = 1 meter

Blender's built-in glTF exporter automatically converts from Blender's Z-up to glTF's Y-up
by applying a -90° X rotation at the root level (baked into the file, not visible as a scene
rotation).

When writing a Blender bpy glTF export script, always use:
```python
bpy.ops.export_scene.gltf(
    filepath="C:/project/export/hero.glb",
    export_format='GLB',
    export_apply=True,         # apply modifiers and transforms
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    # coordinate system baked automatically by the built-in exporter
)
```
Do NOT manually rotate the scene — the exporter handles Y-up conversion.

**Absolute forward-slash paths — critical on Windows:**
```python
# CORRECT
bpy.ops.export_scene.gltf(filepath="C:/project/public/forge/hero.glb")

# WRONG — Blender interprets // as "relative to the .blend file"
bpy.ops.export_scene.gltf(filepath="//hero.glb")

# WRONG — raw backslashes break on some Blender Python path handlers
bpy.ops.export_scene.gltf(filepath="C:\\project\\public\\forge\\hero.glb")
```

---

## §4. USD / OpenUSD conventions

USD stages can specify axis and units in stage metadata:

```python
from pxr import Usd, UsdGeom, UsdUtils
stage = Usd.Stage.CreateNew("scene.usdc")
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)          # Y-up (default; preferred)
UsdGeom.SetStageMetersPerUnit(stage, 1.0)                 # meters
stage.GetRootLayer().Save()
```

For Unreal Engine USD import (Y-up / right-handed / meters):
```python
UsdGeom.SetStageUpAxis(stage, UsdGeom.Tokens.y)
UsdGeom.SetStageMetersPerUnit(stage, 0.01)  # UE5 cm: 100 units per meter
```

USDZ (iOS ARKit) requires Y-up / meters and must be a single-file archive:
```powershell
# macOS: usdzip hero.usdz hero.usda textures/*.png
# Windows: usdzip equivalent — install OpenUSD Windows build or use Blender USDZ export
```

---

## §5. Blender headless axis/scale export flags (quick reference)

### FBX export for UE5

```python
bpy.ops.export_scene.fbx(
    filepath="C:/out/SM_Asset_01.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',  # cm correction
    apply_unit_scale=True,
    axis_forward='-Y',   # Blender -Y → UE5 X
    axis_up='Z',
    mesh_smooth_type='EDGE',
    use_mesh_modifiers=True,
    bake_anim=False,
    add_leaf_bones=False,
    use_armature_deform_only=True,
)
```

### FBX export for Unity

```python
bpy.ops.export_scene.fbx(
    filepath="C:/out/SM_Asset_01.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',
    apply_unit_scale=True,
    axis_forward='-Z',   # Blender -Z → Unity Z
    axis_up='Y',
    mesh_smooth_type='EDGE',
)
```

### GLB / glTF export (web / Godot / Android AR)

```python
bpy.ops.export_scene.gltf(
    filepath="C:/out/hero.glb",
    export_format='GLB',
    export_apply=True,
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
    export_texcoords=True,
    export_normals=True,
    export_materials='EXPORT',
    export_colors=True,
)
```

---

## §6. Common gotchas and fixes

### Gotcha: EEVEE Next is unsupported headless on Windows

**Symptom:** Headless render with `BLENDER_EEVEE_NEXT` produces a black image or Blender
crashes silently (exit code 1).

**Root cause:** EEVEE Next requires an OpenGL/Vulkan GPU context. Windows headless mode
(no display) cannot create one without additional setup.

**Fix:** Always use `CYCLES` for headless renders on Windows:
```python
bpy.context.scene.render.engine = 'CYCLES'
bpy.context.scene.cycles.device = 'CPU'  # GPU optional; CPU is the safe fallback
```

### Gotcha: `//` relative path in Blender filepath

**Symptom:** Render output writes to the `.blend` file's directory, not the intended path.

**Fix:** Pass an absolute forward-slash path:
```python
scene.render.filepath = "C:/project/.forge-build/out/render_"
```

### Gotcha: Blender -b exits 1 with no error message

**Causes:**
1. Missing `--` separator: `blender -b s.blend -P script.py --out foo` → `--out` is parsed
   as a Blender flag and fails.
2. Python error inside the script caught by Blender (not re-raised) → use `--python-exit-code 1`.
3. `.blend` file path is wrong (relative, wrong slashes).

**Fix pattern (PowerShell):**
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
& $blender `
    -b "C:\project\scene.blend" `
    -P "C:\project\scripts\render.py" `
    --python-exit-code 1 `
    -- --out "C:\project\.forge-build\out\render_" --frame 1 `
    2>&1 | Tee-Object -FilePath "C:\project\.forge-build\out\blender.log"
if ($LASTEXITCODE -ne 0) { Write-Error "Blender failed — see blender.log" }
```

### Gotcha: UE5 scale 100× too small

Blender 1 m → UE5 1 cm (100× mismatch). Use `FBX_SCALE_ALL` + `apply_unit_scale=True` on
export, or set scene `unit_settings.scale_length = 0.01` before export.

### Gotcha: Z-fighting on import to UE5

Unapplied scale in Blender causes UE5 to receive incorrect bounding boxes → Z-fighting between
near-coplanar faces. Fix: `Ctrl+A → Apply All Transforms` before export.

### Gotcha: Normal map appears inverted in UE5

Blender bakes OpenGL normals (green-up, Y+). UE5 expects DirectX normals (green-down, Y-).
Flip the G channel of the `_N` texture before delivering to UE5.

### Gotcha: OpenSCAD — use `openscad.com` not `openscad.exe`

On Windows, `openscad.exe` can silently fail to handle DPI scaling or PATH resolution.
`openscad.com` is the correct launcher for CLI/headless use:
```powershell
openscad.com -o out.stl model.scad -D "width=50"
```
