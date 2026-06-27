# Forge Texture — Procedural Shader Nodes & Baked Procedural Textures

## Contents
- §1. Node type reference (bpy type strings + key properties)
- §2. Complete bake-procedural script (Noise + Voronoi → albedo, roughness, normal)
- §3. Common node recipes
- §4. Tileable bake strategies
- §5. AI texture generation via codex-imagegen
- §6. Free PBR asset download (PolyHaven, ambientCG)
- §7. Substance-style layering concept (Blender approximation)

---

## §1. Node Type Reference (Blender 4.4/5.x)

### Texture nodes

| Node | bpy type | Key inputs/properties | Outputs |
|------|----------|-----------------------|---------|
| Noise | `ShaderNodeTexNoise` | `noise_dimensions` ('2D'/'3D'), `noise_type` ('FBM'/'RIDGED_MULTIFRACTAL'/'MULTIFRACTAL'), `normalize` (bool) | Factor, Color |
| Voronoi | `ShaderNodeTexVoronoi` | `voronoi_dimensions` ('2D'/'3D'/'4D'), `feature` ('F1'/'F2'/'SMOOTH_F1'/'DISTANCE_TO_EDGE'/'N_SPHERE_RADIUS'), `distance` metric | Distance, Color, Position |
| Wave | `ShaderNodeTexWave` | `wave_type` ('BANDS'/'RINGS'), `wave_profile` ('SIN'/'SAW'/'TRI'), `rings_direction` | Color, Factor |
| Gradient | `ShaderNodeTexGradient` | `gradient_type` ('LINEAR'/'QUADRATIC'/'EASING'/'DIAGONAL'/'SPHERICAL'/'QUADRATIC_SPHERE'/'RADIAL') | Color, Factor |
| Musgrave | **removed in Blender 4.0** | Use `ShaderNodeTexNoise` with `noise_type='FBM'`, `Detail>=8` | — |
| Magic | `ShaderNodeTexMagic` | `turbulence_depth` | Color, Factor |
| Checker | `ShaderNodeTexChecker` | Scale | Color, Fac |
| Brick | `ShaderNodeTexBrick` | `offset`, `offset_frequency`, `squash`, `squash_frequency` | Color, Fac |

### Utility nodes

| Node | bpy type | Purpose |
|------|----------|---------|
| ColorRamp | `ShaderNodeValToRGB` | Remap factor/color to range; add elements via `.color_ramp.elements.new(pos)` |
| Mapping | `ShaderNodeMapping` | Scale/rotate/translate UV/Object/Normal coordinates |
| Texture Coordinate | `ShaderNodeTexCoord` | Outputs: Generated, UV, Object, Camera, Window, Reflection, Normal |
| Math | `ShaderNodeMath` | All math ops; set via `.operation` ('ADD','MULTIPLY','POWER','ABSOLUTE', etc.) |
| Vector Math | `ShaderNodeVectorMath` | Vector ops: 'ADD','SUBTRACT','NORMALIZE','DOT_PRODUCT','CROSS_PRODUCT' |
| Mix | `ShaderNodeMix` | Mix two values/colors/vectors; `.data_type` ('FLOAT','RGBA','VECTOR') |
| Emission | `ShaderNodeEmission` | Used as bake-target surface for EMIT bakes |
| Geometry | `ShaderNodeNewGeometry` | Outputs: Position, Normal, Tangent, True Normal, Incoming, Parametric, **Pointiness**, Random Per Island |

### Noise node socket defaults (Blender 4.4 source)

```
Scale        default=5.0   range [-1000, 1000]
Detail       default=2.0   range [0, 15]       -- octave count
Roughness    default=0.5   range [0, 1]        -- per-octave amplitude
Lacunarity   default=2.0   range [0, 1000]     -- frequency multiplier per octave
Distortion   default=0.0
Offset       (RIDGED only)
Gain         (RIDGED only)
```

**Detail rule for baking:** `Detail ≈ log2(resolution) - 3`  
— 1K → Detail ≤ 7, 2K → Detail ≤ 8, 4K → Detail ≤ 11. High Detail at low resolution = aliased bake.

---

## §2. Complete Bake-Procedural Script

Bakes a Noise + Voronoi shader network to albedo, roughness, and tangent-space normal PNGs.

```python
# forge_bake_procedural.py
# Usage: blender.exe -b -P forge_bake_procedural.py
# No .blend file needed; builds everything in an empty scene.
# Outputs: albedo.png, roughness.png, normal_gl.png in OUTPUT_DIR.

import bpy, os, sys, io

# Windows UTF-8 stdout fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

OUTPUT_DIR = r"C:\tmp\forge_bake_out"
RESOLUTION = 2048
SAMPLES    = 16

os.makedirs(OUTPUT_DIR, exist_ok=True)

# 1. Empty scene
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.context.scene.render.engine = "CYCLES"
bpy.context.scene.cycles.samples = SAMPLES
bpy.context.scene.cycles.device  = "GPU"   # auto-falls back to CPU if no GPU

# 2. Unit plane with UV
bpy.ops.mesh.primitive_plane_add(size=2, location=(0, 0, 0))
plane = bpy.context.object
bpy.ops.object.editmode_toggle()
bpy.ops.uv.unwrap(method="ANGLE_BASED", margin=0.001)
bpy.ops.object.editmode_toggle()

# 3. Build procedural material
mat = bpy.data.materials.new("ForgeProcedural")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

output   = nodes.new("ShaderNodeOutputMaterial"); output.location   = (900, 0)
pbsdf    = nodes.new("ShaderNodeBsdfPrincipled"); pbsdf.location    = (600, 0)
texcoord = nodes.new("ShaderNodeTexCoord");       texcoord.location = (-800, 0)
mapping  = nodes.new("ShaderNodeMapping");        mapping.location  = (-600, 0)

# Noise — fBM, drives Roughness
noise = nodes.new("ShaderNodeTexNoise")
noise.location                          = (-300, 150)
noise.noise_dimensions                  = "3D"
noise.noise_type                        = "FBM"
noise.normalize                         = True
noise.inputs["Scale"].default_value     = 6.0
noise.inputs["Detail"].default_value    = 8.0
noise.inputs["Roughness"].default_value = 0.6
noise.inputs["Lacunarity"].default_value = 2.0
noise.inputs["Distortion"].default_value = 0.2

# Voronoi — cell distance, drives Base Color
voronoi = nodes.new("ShaderNodeTexVoronoi")
voronoi.location                           = (-300, -150)
voronoi.voronoi_dimensions                 = "3D"
voronoi.feature                            = "DISTANCE_TO_EDGE"
voronoi.inputs["Scale"].default_value      = 4.0
voronoi.inputs["Randomness"].default_value = 0.8

# ColorRamp: remap noise → roughness 0.2–0.8
ramp_rough = nodes.new("ShaderNodeValToRGB")
ramp_rough.location                          = (0, 150)
ramp_rough.color_ramp.elements[0].position   = 0.0
ramp_rough.color_ramp.elements[0].color      = (0.2, 0.2, 0.2, 1.0)
ramp_rough.color_ramp.elements[1].position   = 1.0
ramp_rough.color_ramp.elements[1].color      = (0.8, 0.8, 0.8, 1.0)

# ColorRamp: remap voronoi → color
ramp_color = nodes.new("ShaderNodeValToRGB")
ramp_color.location                          = (0, -150)
ramp_color.color_ramp.interpolation          = "B_SPLINE"
ramp_color.color_ramp.elements[0].position   = 0.0
ramp_color.color_ramp.elements[0].color      = (0.02, 0.02, 0.02, 1.0)
ramp_color.color_ramp.elements[1].position   = 0.6
ramp_color.color_ramp.elements[1].color      = (0.55, 0.52, 0.48, 1.0)

links.new(texcoord.outputs["Object"], mapping.inputs["Vector"])
links.new(mapping.outputs["Vector"],  noise.inputs["Vector"])
links.new(mapping.outputs["Vector"],  voronoi.inputs["Vector"])
links.new(noise.outputs["Fac"],       ramp_rough.inputs["Fac"])
links.new(voronoi.outputs["Distance"],ramp_color.inputs["Fac"])
links.new(ramp_rough.outputs["Color"],pbsdf.inputs["Roughness"])
links.new(ramp_color.outputs["Color"],pbsdf.inputs["Base Color"])
links.new(pbsdf.outputs["BSDF"],      output.inputs["Surface"])
plane.data.materials.append(mat)

# 4. Bake helper
def bake_map(bake_type, filename, emit_socket=None):
    colorspace = "sRGB" if bake_type == "DIFFUSE" else "Non-Color"
    img = bpy.data.images.new(filename, RESOLUTION, RESOLUTION, alpha=False, float_buffer=True)
    img.colorspace_settings.name = colorspace

    img_node = nodes.new("ShaderNodeTexImage")
    img_node["forge_bake_node"] = True
    img_node.image  = img
    img_node.select = True
    mat.node_tree.nodes.active = img_node

    # Route scalar channels through Emission
    tmp = []
    if emit_socket:
        emit = nodes.new("ShaderNodeEmission")
        emit["forge_bake_node"] = True
        src = pbsdf.inputs[emit_socket].links[0].from_socket \
              if pbsdf.inputs[emit_socket].links else None
        if src:
            tmp.append(links.new(emit.inputs["Color"], src))
        # Disconnect original BSDF from output, connect Emission
        if output.inputs["Surface"].links:
            links.remove(output.inputs["Surface"].links[0])
        tmp.append(links.new(output.inputs["Surface"], emit.outputs["Emission"]))
        actual_type = "EMIT"
    else:
        actual_type = bake_type

    bpy.context.view_layer.objects.active = plane
    plane.select_set(True)
    bpy.ops.object.bake(type=actual_type, use_clear=True, save_mode="EXTERNAL")

    # Cleanup temp nodes/links
    for n in [n for n in nodes if n.get("forge_bake_node")]:
        nodes.remove(n)
    if emit_socket:
        links.new(pbsdf.outputs["BSDF"], output.inputs["Surface"])

    fp = os.path.join(OUTPUT_DIR, filename + ".png").replace("\\", "/")
    img.file_format  = "PNG"
    img.filepath_raw = fp
    img.save()
    print(f"[forge] Saved: {fp}")
    bpy.data.images.remove(img)

# 5. Run bakes
bake_map("DIFFUSE", "albedo")
bake_map("EMIT",    "roughness", "Roughness")
bake_map("NORMAL",  "normal_gl")
print("[forge] All procedural bakes complete.")
```

---

## §3. Common Node Recipes

### Brushed metal (Wave → directional roughness)

```python
wave = nodes.new("ShaderNodeTexWave")
wave.wave_type                            = "BANDS"
wave.wave_profile                         = "SIN"
wave.inputs["Scale"].default_value        = 80.0
wave.inputs["Distortion"].default_value   = 3.0
wave.inputs["Detail"].default_value       = 12.0
wave.inputs["Detail Scale"].default_value = 2.0
wave.inputs["Detail Roughness"].default_value = 0.7
# Link wave output → Roughness input of Principled BSDF
links.new(wave.outputs["Color"], pbsdf.inputs["Roughness"])
```

### Spherical matcap gradient (Gradient → ColorRamp)

```python
grad = nodes.new("ShaderNodeTexGradient")
grad.gradient_type = "SPHERICAL"

ramp = nodes.new("ShaderNodeValToRGB")
ramp.color_ramp.interpolation = "B_SPLINE"
e0 = ramp.color_ramp.elements[0]; e0.position = 0.0; e0.color = (0.05, 0.05, 0.1, 1.0)
e1 = ramp.color_ramp.elements.new(position=0.5);  e1.color = (0.4, 0.6, 0.9, 1.0)
e2 = ramp.color_ramp.elements.new(position=1.0);  e2.color = (1.0, 1.0, 1.0, 1.0)
links.new(grad.outputs["Color"], ramp.inputs["Fac"])
links.new(ramp.outputs["Color"], pbsdf.inputs["Base Color"])
```

### Distorted Voronoi (warp-by-noise)

```python
# Feed Noise output into Voronoi's Vector input for a warped cell pattern
noise_warp = nodes.new("ShaderNodeTexNoise")
noise_warp.inputs["Scale"].default_value = 3.0
noise_warp.inputs["Detail"].default_value = 4.0

voronoi = nodes.new("ShaderNodeTexVoronoi")
voronoi.voronoi_dimensions = "3D"
voronoi.feature = "F1"

links.new(noise_warp.outputs["Color"], voronoi.inputs["Vector"])
```

### Musgrave equivalent (Blender 4.x+)

```python
# Musgrave node was merged into Noise in Blender 4.0
noise.noise_type        = "FBM"          # or MULTIFRACTAL / RIDGED_MULTIFRACTAL
noise.noise_dimensions  = "3D"
noise.inputs["Detail"].default_value     = 15.0
noise.inputs["Roughness"].default_value  = 0.7
noise.inputs["Lacunarity"].default_value = 2.0
# ShaderNodeTexMusgrave is gone from 4.0 onward — always use ShaderNodeTexNoise here.
# Only gate a legacy Musgrave path on bpy.app.version < (4, 0, 0).
```

---

## §4. Tileable Bake Strategies

### Method A — Object coordinates on unit plane (simplest)

Use Object coordinate input → Mapping node (scale 1,1,1). UV-unwrap the plane to fill [0,1]².
Bake the procedural texture. The baked PNG tiles correctly at scale 1 Blender unit.
Works well for low-Detail noise (Detail ≤ 4) or for patterns that are naturally periodic (Checker, Brick).

### Method B — Seamless post-processing (wrap-padding cross-blend)

For high-Detail noise that shows seams at the tile boundary:

```python
import cv2, numpy as np

def make_seamless(img_path: str, out_path: str, blend_width: float = 0.15):
    """
    Wrap-pad + linear cross-blend. Eliminates seams on any RGB/L PNG.
    blend_width: fraction of image width/height used for blending zone.
    """
    img = cv2.imread(img_path, cv2.IMREAD_UNCHANGED)
    if img is None:
        from PIL import Image
        import numpy as np
        img = np.array(Image.open(img_path))[:, :, ::-1].copy()  # RGB->BGR for cv2
    h, w = img.shape[:2]
    bw, bh = int(w * blend_width), int(h * blend_width)
    img_f = img.astype(np.float32)

    # Horizontal blend: wrap right strip over left
    alpha = np.linspace(0, 1, bw, dtype=np.float32)[np.newaxis, :, np.newaxis]
    blended = img_f[:, w-bw:] * (1 - alpha) + img_f[:, :bw] * alpha
    img_f[:, w-bw:] = blended

    # Vertical blend: wrap bottom strip over top
    alpha_v = np.linspace(0, 1, bh, dtype=np.float32)[:, np.newaxis, np.newaxis]
    blended_v = img_f[h-bh:, :] * (1 - alpha_v) + img_f[:bh, :] * alpha_v
    img_f[h-bh:, :] = blended_v

    cv2.imwrite(out_path, img_f.astype(img.dtype))
    print(f"[forge] Seamless: {out_path}")
```

---

## §5. AI Texture Generation via codex-imagegen

For bespoke matcap gradients, stylized surface patterns, or reference albedo images:

```powershell
# PowerShell — generate a seamless matcap texture (pure ASCII prompt required)
& "$env:CLAUDE_CONFIG_DIR\skills\codex-imagegen\scripts\codex-image.ps1" `
    -Prompt "seamless tileable matcap gradient texture, flat 2D design, no people, no photography, radial gradient from bright white center to dark navy blue edge, top-left specular highlight, matte oil-paint quality, square 1:1 format" `
    -Size "1024x1024" `
    -OutDir "C:\tmp\forge_textures"
```

**Critical constraints:**
- Prompt must be **pure ASCII** — no em-dashes (`—`), curly quotes, or Unicode (PowerShell 5.1 ANSI parse bug)
- Lead with `"seamless tileable [type] texture, flat 2D design, no people, no photography"`
- If generation fails (exit 2 or solid-color stub): retry with `-Model gpt-5.1-codex` as fallback
- Post-process for tileability with `make_seamless()` (§4 Method B) before using in production

**Call from SKILL.md:** `Skill("codex-imagegen")` — do not invoke the PS1 script directly unless
the Skill tool is unavailable; the skill manages prompt validation and retry logic.

---

## §6. Free PBR Asset Download

### PolyHaven (CC0)

```python
import urllib.request, json, os, urllib.parse

POLYHAVEN_BASE = "https://api.polyhaven.com"
UA = "ForgeSkill/1.0 (Lumicity)"

def ph_get(path: str) -> dict:
    req = urllib.request.Request(POLYHAVEN_BASE + path, headers={"User-Agent": UA})
    with urllib.request.urlopen(req) as r:
        return json.load(r)

def polyhaven_download(slug: str, resolution: str, out_dir: str, fmt: str = "png") -> list:
    """resolution: '1k'|'2k'|'4k'|'8k' (lowercase). Returns downloaded file paths."""
    files = ph_get(f"/files/{slug}")
    os.makedirs(out_dir, exist_ok=True)
    saved = []
    for map_type, res_dict in files.items():
        if map_type in ("blend", "gltf", "mtlx"):
            continue
        if resolution not in res_dict:
            continue
        fmt_dict = res_dict[resolution]
        if fmt not in fmt_dict:
            fmt = next(iter(fmt_dict))
        url = fmt_dict[fmt]["url"]
        dest = os.path.join(out_dir, f"{slug}_{map_type}_{resolution}.{fmt}")
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req) as r, open(dest, "wb") as f:
            f.write(r.read())
        print(f"[PH] {map_type} -> {dest}")
        saved.append(dest)
    return saved

# Example: polyhaven_download("concrete_wall_008", "2k", r"C:\tmp\ph_tex")
```

**Note:** Always set User-Agent — requests without it risk 403/429.

### ambientCG (CC0)

```python
import urllib.request, json, zipfile, tempfile, shutil, os

ACGBASE = "https://ambientCG.com/api/v2"

def ambientcg_download(asset_id: str, resolution: str, out_dir: str, fmt: str = "PNG") -> list:
    """asset_id e.g. 'PavingStones036'. resolution e.g. '2K'. fmt 'PNG'|'JPG'|'EXR'."""
    params = f"?id={asset_id}&include=downloadData"
    req = urllib.request.Request(ACGBASE + "/full_json" + params)
    with urllib.request.urlopen(req) as r:
        data = json.load(r)

    asset = data.get("foundAssets", [{}])[0]
    key   = f"{resolution}-{fmt}"
    downloads = asset.get("downloadFolders", {})
    if key not in downloads:
        raise KeyError(f"{key!r} not found; available: {list(downloads.keys())}")

    zip_url = downloads[key].get("downloadLink") or downloads[key].get("rawLink")
    os.makedirs(out_dir, exist_ok=True)

    with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp:
        tmp_path = tmp.name
    with urllib.request.urlopen(zip_url) as r, open(tmp_path, "wb") as f:
        f.write(r.read())

    extracted = []
    with zipfile.ZipFile(tmp_path, "r") as z:
        for member in z.namelist():
            safe = os.path.basename(member)
            if not safe:
                continue
            dest = os.path.join(out_dir, safe)
            with z.open(member) as src, open(dest, "wb") as dst:
                shutil.copyfileobj(src, dst)
            extracted.append(dest)

    os.unlink(tmp_path)
    return extracted

# Example: ambientcg_download("BrickWall001", "2K", r"C:\tmp\acg_tex")
```

---

## §7. Substance-Style Layering (Blender Approximation)

Substance Designer generators are parameterized procedural sub-graphs. Approximate in Blender:

| SD concept | Blender equivalent |
|---|---|
| Generator (noise type) | `ShaderNodeTexNoise` / `ShaderNodeTexVoronoi` |
| Mask (float map) | `ShaderNodeTexNoise → ColorRamp → Mix Shader` weight |
| Warp filter | Feed Noise output into Voronoi's Vector input |
| Blur filter | `ShaderNodeBlur` (compositor only) or post-process with cv2 Gaussian |
| Levels / Histogram | `ShaderNodeValToRGB` (ColorRamp) with precise element positions |
| Layer blend | `ShaderNodeMix` with data_type='RGBA' |

**MaterialX** (Apache-2.0, supported by Blender/Houdini/USD) provides a portable node-graph
representation of these same patterns — useful for cross-DCC material sharing.
