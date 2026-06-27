# Blender bpy Material Scripts — forge-material reference

# Contents
- §1. Build a full PBR material from Python (ORM + normal + displacement)
- §2. Quick material preview render (sphere, Cycles headless)
- §3. Principled BSDF 4.x full socket index table
- §4. ORM node wiring for glTF exporter auto-detection
- §5. Advanced material patterns (coat, transmission, sheen, emission)
- §6. Programmatic material validation (node tree check)
- §7. Batch headless invocation patterns (PowerShell)
- §8. Material library: save and append from .blend

---

## §1. Full PBR Material Build Script

Headless invocation:
```powershell
# PowerShell (Windows-native)
$blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
& $blender --background "C:\path\to\scene.blend" `
    --python "C:\forge\scripts\build_pbr_material.py" `
    --python-exit-code 1 `
    -- `
    --albedo   "C:/forge/textures/albedo.png" `
    --orm      "C:/forge/textures/orm.png" `
    --normal   "C:/forge/textures/normal_gl.png" `
    --output   "C:/forge/renders/mat_check.png" `
    --samples  128
```

The `--` separator is mandatory — everything after it goes to `sys.argv` in the script.
`--python-exit-code 1` ensures Python errors fail the process (not silent success).
Forward slashes in Blender filepath — never backslashes (see §7 gotcha).

```python
# build_pbr_material.py
# Blender 4.2 LTS target; socket names are OpenPBR v2 (changed from 3.x)
import bpy, sys, os, argparse

# ---- Parse args after "--" separator ----------------------------------------
argv = sys.argv
argv = argv[argv.index("--") + 1:] if "--" in argv else []
p = argparse.ArgumentParser()
p.add_argument("--albedo",   default=None)
p.add_argument("--orm",      default=None)     # R=AO, G=Roughness, B=Metallic
p.add_argument("--normal",   default=None)
p.add_argument("--disp",     default=None)     # optional true displacement
p.add_argument("--output",   default="C:/forge/renders/mat_check.png")
p.add_argument("--samples",  type=int, default=128)
args = p.parse_args(argv)

# ---- Scene/render setup ------------------------------------------------------
scene = bpy.context.scene
scene.render.engine = 'CYCLES'                 # EEVEE-Next unsupported headless on Windows
scene.cycles.samples = args.samples
scene.cycles.use_denoising = True
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode  = 'RGBA'
scene.render.film_transparent = True           # transparent BG for isolated mat check

# Use forward slashes for bpy filepath (avoid backslash issues on Windows)
out_path = args.output.replace("\\", "/")
scene.render.filepath = out_path

# GPU activation (OptiX → CUDA → HIP → ONEAPI → CPU fallback).
# CRITICAL: GPU devices are NOT auto-detected headless. You MUST call
# refresh_devices() after setting compute_device_type, then enable each
# non-CPU device (d.use = True) — otherwise the device list stays empty and
# cycles.device='GPU' silently renders on CPU (the "rough metals dark / slow
# render" failure). This is the canonical activate_cycles_gpu() helper lifted
# from forge-render references/cycles-gpu-passes.md §GPU.
def setup_gpu(prefer='OPTIX'):
    prefs = bpy.context.preferences.addons['cycles'].preferences
    for backend in (prefer, 'OPTIX', 'CUDA', 'HIP', 'ONEAPI', 'NONE'):
        try:
            prefs.compute_device_type = backend
            break
        except TypeError:
            continue
    # Blender 4.x: refresh_devices() replaces deprecated get_devices()
    try:
        prefs.refresh_devices()
    except AttributeError:
        prefs.get_devices()                 # Blender 3.x fallback
    non_cpu = False
    for d in prefs.devices:
        if d.type != 'CPU':
            d.use = True                    # enable each discovered GPU device
            non_cpu = True
    scene.cycles.device = 'GPU' if non_cpu else 'CPU'
    print(f"[forge-material] Cycles device: {scene.cycles.device} "
          f"(backend={prefs.compute_device_type})")
    return scene.cycles.device

setup_gpu()

# ---- Clear scene, add preview sphere ----------------------------------------
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.mesh.primitive_uv_sphere_add(segments=64, ring_count=32, radius=1.0,
                                      location=(0, 0, 0))
sphere = bpy.context.active_object
bpy.ops.object.shade_smooth()

# ---- Build material ---------------------------------------------------------
mat = bpy.data.materials.new(name="ForgePBR")
mat.use_nodes = True
nodes = mat.node_tree.nodes
links = mat.node_tree.links
nodes.clear()

out  = nodes.new('ShaderNodeOutputMaterial')
out.location = (1200, 0)

bsdf = nodes.new('ShaderNodeBsdfPrincipled')
bsdf.location = (800, 0)
bsdf.distribution = 'MULTI_GGX'               # energy-conserving; prevents dark rough metals
bsdf.inputs['IOR'].default_value = 1.5
links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

# UV mapping chain (POINT type required for glTF KHR_texture_transform)
tex_coord = nodes.new('ShaderNodeTexCoord')
tex_coord.location = (-800, 0)
mapping = nodes.new('ShaderNodeMapping')
mapping.location = (-600, 0)
mapping.vector_type = 'POINT'
links.new(tex_coord.outputs['UV'], mapping.inputs['Vector'])

def load_tex(path, colorspace='Non-Color', loc=(0, 0)):
    """Load image texture node with explicit color space. Forward-slash path required."""
    fwd = path.replace("\\", "/")
    if not os.path.isfile(fwd):
        print(f"[forge-material] WARNING: texture not found: {fwd}")
        return None
    img = bpy.data.images.load(fwd, check_existing=True)
    img.colorspace_settings.name = colorspace
    node = nodes.new('ShaderNodeTexImage')
    node.image = img
    node.location = loc
    node.interpolation = 'Linear'
    node.extension = 'REPEAT'
    links.new(mapping.outputs['Vector'], node.inputs['Vector'])
    return node

# Albedo (sRGB — color data)
if args.albedo:
    bc_node = load_tex(args.albedo, colorspace='sRGB', loc=(-200, 400))
    if bc_node:
        links.new(bc_node.outputs['Color'], bsdf.inputs['Base Color'])

# ORM (Non-Color — R=AO, G=Roughness, B=Metallic, glTF convention)
if args.orm:
    orm_node = load_tex(args.orm, colorspace='Non-Color', loc=(-200, 0))
    if orm_node:
        sep = nodes.new('ShaderNodeSeparateColor')   # 4.2+ (replaces deprecated SeparateRGB)
        sep.mode = 'RGB'
        sep.location = (100, 0)
        links.new(orm_node.outputs['Color'], sep.inputs['Color'])
        links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])   # G → roughness
        links.new(sep.outputs['Blue'],  bsdf.inputs['Metallic'])    # B → metallic
        # Wire AO to glTF Material Output (for occlusionTexture export)
        # The 'glTF Material Output' node group is created by the glTF IO add-on.
        gltf_out_group = bpy.data.node_groups.get('glTF Material Output')
        if gltf_out_group:
            gltf_mat_out = nodes.new('ShaderNodeGroup')
            gltf_mat_out.node_tree = gltf_out_group
            gltf_mat_out.location = (1200, -200)
            links.new(sep.outputs['Red'], gltf_mat_out.inputs['Occlusion'])  # R → AO

# Normal map (Non-Color; requires NormalMap node between texture and BSDF)
if args.normal:
    nm_tex = load_tex(args.normal, colorspace='Non-Color', loc=(-200, -300))
    if nm_tex:
        nm_node = nodes.new('ShaderNodeNormalMap')
        nm_node.space = 'TANGENT'                # only mode glTF supports
        nm_node.inputs['Strength'].default_value = 1.0
        nm_node.location = (200, -300)
        links.new(nm_tex.outputs['Color'],  nm_node.inputs['Color'])
        links.new(nm_node.outputs['Normal'], bsdf.inputs['Normal'])

# True displacement (Cycles only; requires subdivision modifier)
if args.disp:
    disp_tex = load_tex(args.disp, colorspace='Non-Color', loc=(-200, -600))
    if disp_tex:
        disp_node = nodes.new('ShaderNodeDisplacement')
        disp_node.location = (700, -400)
        disp_node.inputs['Midlevel'].default_value = 0.5   # 0.5 = neutral
        disp_node.inputs['Scale'].default_value    = 0.05  # world-space meters
        links.new(disp_tex.outputs['Color'], disp_node.inputs['Height'])
        links.new(disp_node.outputs['Displacement'], out.inputs['Displacement'])
        mat.cycles.displacement_method = 'DISPLACEMENT'    # or 'BOTH'
        scene.cycles.feature_set = 'EXPERIMENTAL'          # adaptive subdivision
        sub = sphere.modifiers.new("Subd", 'SUBSURF')
        sub.levels = 0
        sub.render_levels = 0
        sub.use_adaptive_subdivision = True

sphere.data.materials.append(mat)

# ---- World (neutral gray IBL fallback) -------------------------------------
world = bpy.data.worlds.get('World') or bpy.data.worlds.new('World')
world.use_nodes = True
bg = world.node_tree.nodes.get('Background')
if bg:
    bg.inputs['Color'].default_value    = (0.05, 0.05, 0.05, 1.0)
    bg.inputs['Strength'].default_value = 1.0
scene.world = world

# ---- Camera ----------------------------------------------------------------
bpy.ops.object.camera_add(location=(0, -3.0, 0.5))
cam = bpy.context.active_object
cam.rotation_euler = (1.3, 0, 0)
scene.camera = cam

# ---- Key light (area) -------------------------------------------------------
bpy.ops.object.light_add(type='AREA', location=(2, -2, 3))
key = bpy.context.active_object
key.data.energy = 400
key.data.size   = 1.5

# ---- Render -----------------------------------------------------------------
bpy.ops.render.render(write_still=True)
print(f"[forge-material] Render written to: {out_path}")
```

---

## §2. Quick Material Preview Render (Headless Sphere)

Minimal script for a fast material check without loading a full scene:

```powershell
# PowerShell one-liner (solid material, no textures)
$blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
& $blender --background --python-expr `
    "import bpy; s=bpy.context.scene; s.render.engine='CYCLES'; s.cycles.samples=64; bpy.ops.mesh.primitive_uv_sphere_add(); m=bpy.data.materials.new('M'); m.use_nodes=True; b=m.node_tree.nodes['Principled BSDF']; b.inputs['Metallic'].default_value=1.0; b.inputs['Roughness'].default_value=0.3; bpy.context.active_object.data.materials.append(m); s.render.filepath='C:/renders/check'; bpy.ops.render.render(write_still=True)" `
    --python-exit-code 1 `
    -o "C:/renders/check_####" -F PNG -f 1
```

Post-render pixel check (system Python, outside Blender):

```python
# verify_render.py — run with: python verify_render.py C:\renders\check_0001.png
import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from PIL import Image          # pip install pillow
import numpy as np
from pathlib import Path

def verify(png_path: str, min_mean=0.02, max_mean=0.98) -> bool:
    p = Path(png_path)
    if not p.exists():
        print(f"FAIL: output file does not exist: {png_path}")
        return False
    if p.stat().st_size < 1024:
        print(f"FAIL: output suspiciously small ({p.stat().st_size} bytes)")
        return False
    img = Image.open(p).convert('RGB')
    arr = np.array(img, dtype=np.float32) / 255.0
    mean, std = arr.mean(), arr.std()
    if mean < min_mean:
        print(f"FAIL: too dark (mean={mean:.4f}) — render crash or no material?")
        return False
    if mean > max_mean:
        print(f"FAIL: overexposed (mean={mean:.4f})")
        return False
    if std < 0.005:
        print(f"FAIL: zero variance (std={std:.4f}) — uniform color, material broken?")
        return False
    print(f"OK: mean={mean:.3f} std={std:.3f} size={p.stat().st_size//1024}KB")
    return True

if __name__ == '__main__':
    ok = verify(sys.argv[1] if len(sys.argv) > 1 else 'render.png')
    sys.exit(0 if ok else 1)
```

---

## §3. Principled BSDF 4.x Full Socket Index Table

Blender 4.0 shipped a complete rewrite based on OpenPBR. Always use socket NAMES, not indices —
indices are an implementation detail that has already changed once.

| Idx | Name                  | Type   | Range / Default       | Notes                                    |
|-----|-----------------------|--------|-----------------------|------------------------------------------|
| 0   | Base Color            | RGBA   | sRGB, default white   | albedo / specular tint for metals        |
| 1   | Metallic              | Float  | 0–1, binary in practice | 0=dielectric, 1=conductor             |
| 2   | Roughness             | Float  | 0–1, default 0.5      | 0=mirror, 1=fully diffuse               |
| 3   | IOR                   | Float  | 1.0–4.0, default 1.5  | index of refraction; 1.0=F0 impossible  |
| 4   | Alpha                 | Float  | 0–1, default 1.0      | 1=opaque; drives alphaMode in glTF      |
| 5   | Normal                | Vector | tangent-space          | connect via NormalMap node only         |
| 6   | Weight                | Float  | multi-shader blending  |                                          |
| 7   | Subsurface Weight     | Float  | 0–1                   | was 'Subsurface' blend in 3.x           |
| 8   | Subsurface Radius     | RGB    | scattering distances   | X=R, Y=G, Z=B channels                  |
| 9   | Subsurface Scale      | Float  | world-space multiplier |                                          |
| 10  | Subsurface IOR        | Float  | 1.0–4.0               | for skin layering                        |
| 11  | Subsurface Anisotropy | Float  | 0–1                   |                                          |
| 12  | Specular IOR Level    | Float  | 0–1, default 0.5      | was 'Specular' (0–1 in 3.x); 0.5=no adj|
| 13  | Specular Tint         | RGBA   | color multiplier       |                                          |
| 14  | Anisotropic           | Float  | 0–1, Cycles only       | elongated specular lobe                  |
| 15  | Anisotropic Rotation  | Float  | 0–1                   |                                          |
| 16  | Tangent               | Vector |                        |                                          |
| 17  | Transmission Weight   | Float  | 0–1                   | was 'Transmission'; 1=full glass        |
| 18  | Coat Weight           | Float  | 0–1                   | was 'Clearcoat'; thin protective lacquer|
| 19  | Coat Roughness        | Float  | 0–1                   | was 'Clearcoat Roughness'               |
| 20  | Coat IOR              | Float  | 1.0–4.0, default 1.5  | fixed 1.5 in glTF KHR_clearcoat spec   |
| 21  | Coat Tint             | RGBA   |                        |                                          |
| 22  | Coat Normal           | Vector |                        |                                          |
| 23  | Sheen Weight          | Float  | 0–1                   | cloth/velvet retroreflection            |
| 24  | Sheen Roughness       | Float  | 0–1                   |                                          |
| 25  | Sheen Tint            | RGBA   |                        |                                          |
| 26  | Emission Color        | RGBA   | sRGB                  | was 'Emission' scalar color             |
| 27  | Emission Strength     | Float  | default 1.0           | >1 → KHR_materials_emissive_strength    |

**Node properties (set on node object, not via inputs):**
```python
bsdf.distribution = 'MULTI_GGX'         # always; 'GGX' loses energy at high roughness
bsdf.subsurface_method = 'RANDOM_WALK_SKIN'  # for skin; 'RANDOM_WALK' otherwise
```

---

## §4. ORM Node Wiring for glTF Exporter Auto-Detection

The Blender glTF exporter auto-detects this exact node arrangement and packs AO + roughness +
metallic into a single ORM texture in the GLB, zero re-encode:

```python
# Canonical ORM wiring for glTF export (Blender 4.2+)
# Uses ShaderNodeSeparateColor (4.2+) not ShaderNodeSeparateRGB (deprecated)

def wire_orm_for_gltf(nodes, links, mat, orm_img):
    """
    Wire an ORM image texture correctly for Blender glTF exporter auto-detection.
    The exporter's __gather_orm_texture() detects this arrangement and writes a single
    texture to both occlusionTexture and metallicRoughnessTexture in the GLB.

    orm_img: bpy.types.Image with colorspace_settings.name = 'Non-Color'
    """
    orm_img.colorspace_settings.name = 'Non-Color'   # CRITICAL

    tex_orm = nodes.new('ShaderNodeTexImage')
    tex_orm.image = orm_img
    tex_orm.location = (-200, 0)

    sep = nodes.new('ShaderNodeSeparateColor')
    sep.mode = 'RGB'
    sep.location = (100, 0)
    links.new(tex_orm.outputs['Color'], sep.inputs['Color'])

    # G → Roughness, B → Metallic (on Principled BSDF)
    # Find the BSDF node
    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if bsdf:
        links.new(sep.outputs['Green'], bsdf.inputs['Roughness'])
        links.new(sep.outputs['Blue'],  bsdf.inputs['Metallic'])

    # R → Occlusion (on glTF Material Output group node)
    gltf_group = bpy.data.node_groups.get('glTF Material Output')
    if gltf_group:
        gltf_out = nodes.new('ShaderNodeGroup')
        gltf_out.node_tree = gltf_group
        gltf_out.location = (1200, -200)
        links.new(sep.outputs['Red'], gltf_out.inputs['Occlusion'])

    return tex_orm, sep
```

---

## §5. Advanced Material Patterns

### Glass / Transmission

```python
# Thin-walled glass (KHR_materials_transmission in glTF)
bsdf.inputs['Transmission Weight'].default_value = 1.0
bsdf.inputs['IOR'].default_value = 1.52          # borosilicate glass
bsdf.inputs['Roughness'].default_value = 0.0
bsdf.inputs['Base Color'].default_value = (1.0, 1.0, 1.0, 1.0)
# alphaMode MUST be OPAQUE (not BLEND) for transmission to work in engines
# Do NOT mix transmission + alphaMode BLEND — undefined behavior

# Thick glass / volume (KHR_materials_volume in glTF)
# Requires closed/manifold mesh. Combine with KHR_materials_transmission.
bsdf.inputs['Transmission Weight'].default_value = 1.0
bsdf.inputs['IOR'].default_value = 1.5
# Volume properties set at export time via pygltflib or in the JSON directly
```

### Clearcoat / Car Paint

```python
bsdf.inputs['Metallic'].default_value      = 0.9
bsdf.inputs['Roughness'].default_value     = 0.4
bsdf.inputs['Coat Weight'].default_value   = 1.0
bsdf.inputs['Coat Roughness'].default_value = 0.05  # near-mirror coat
bsdf.inputs['Coat IOR'].default_value      = 1.5    # fixed in glTF spec; cannot override
```

### Cloth / Velvet (Sheen)

```python
bsdf.inputs['Metallic'].default_value     = 0.0
bsdf.inputs['Roughness'].default_value    = 0.8
bsdf.inputs['Sheen Weight'].default_value = 1.0
bsdf.inputs['Sheen Roughness'].default_value = 0.5
bsdf.inputs['Sheen Tint'].default_value   = (0.6, 0.4, 0.2, 1.0)  # warm textile
```

### HDR Emission (Bloom)

```python
bsdf.inputs['Emission Color'].default_value    = (1.0, 0.5, 0.1, 1.0)  # warm orange
bsdf.inputs['Emission Strength'].default_value = 5.0  # >1 → KHR_materials_emissive_strength
# In glTF: emissiveFactor = [1,1,1], emissiveStrength = 5.0
# Set emissiveFactor to [1,1,1] (white) and color via emissiveTexture (BP-5)
```

### Brushed Metal (Anisotropy)

```python
bsdf.inputs['Metallic'].default_value          = 1.0
bsdf.inputs['Roughness'].default_value         = 0.3
bsdf.inputs['Anisotropic'].default_value       = 0.8
bsdf.inputs['Anisotropic Rotation'].default_value = 0.0  # 0=along U axis
# CRITICAL: mesh must have NORMAL + TANGENT attributes, or normalTexture must be set.
# Without tangent space, anisotropy silently produces wrong results.
# Verify with gltf-validator after export — it will flag missing TANGENT.
```

### Mixing Two BSDFs (Dirt Over Clean Metal)

```python
def add_shader_mix(nodes, links, bsdf_a, bsdf_b, factor=0.5):
    mix = nodes.new('ShaderNodeMixShader')
    mix.inputs['Fac'].default_value = factor   # 0 = pure A, 1 = pure B
    links.new(bsdf_a.outputs['BSDF'], mix.inputs[1])
    links.new(bsdf_b.outputs['BSDF'], mix.inputs[2])
    return mix
```

---

## §6. Programmatic Material Validation

Run inside Blender script to catch errors before export:

```python
def validate_pbr_material(mat: bpy.types.Material) -> list:
    """
    Returns list of error strings. Empty = valid.
    Checks: Principled BSDF present, Output present, data maps are Non-Color,
    normal map uses NormalMap node, no direct image-to-Normal connection.
    """
    errors = []
    if not mat.use_nodes:
        return ["Material does not use nodes"]

    nodes = mat.node_tree.nodes
    links = mat.node_tree.links

    bsdf = next((n for n in nodes if n.type == 'BSDF_PRINCIPLED'), None)
    out  = next((n for n in nodes if n.type == 'OUTPUT_MATERIAL'), None)

    if not bsdf: errors.append("No Principled BSDF node found")
    if not out:  errors.append("No Material Output node found")
    if not bsdf: return errors

    DATA_SOCKETS = {'Roughness', 'Metallic', 'Normal', 'Height',
                    'Specular IOR Level', 'Transmission Weight'}

    for node in nodes:
        if node.type != 'TEX_IMAGE' or not node.image:
            continue
        cs = node.image.colorspace_settings.name
        for link in links:
            if link.from_node != node:
                continue
            target = link.to_socket.name
            if target in DATA_SOCKETS and cs == 'sRGB':
                errors.append(
                    f"Image '{node.image.name}' → '{target}': "
                    f"colorspace is sRGB, expected Non-Color"
                )

    # Normal must go through NormalMap node
    for link in links:
        if link.to_node == bsdf and link.to_socket.name == 'Normal':
            if link.from_node.type != 'NORMAL_MAP':
                errors.append(
                    "BSDF.Normal is not connected via a Normal Map node — "
                    "glTF normalTexture export requires this intermediary"
                )

    return errors


# Usage (inside Blender script)
for mat in bpy.data.materials:
    if mat.use_nodes:
        errs = validate_pbr_material(mat)
        if errs:
            print(f"\n[MATERIAL ERRORS] {mat.name}:")
            for e in errs:
                print(f"  - {e}")
        else:
            print(f"[OK] {mat.name}")
```

---

## §7. Batch Headless Invocation Patterns (PowerShell)

```powershell
# Render all .blend files in a folder — material preview batch
$blender = "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe"
$script  = "C:\forge\scripts\build_pbr_material.py"
$renders = "C:\forge\renders"

Get-ChildItem "C:\scenes\*.blend" | ForEach-Object {
    $out = "$renders\$($_.BaseName)_mat_####"
    & $blender -b $_.FullName -P $script `
        --python-exit-code 1 `
        -o $out -F PNG -f 1
    Write-Host "Done: $($_.Name)"
}
```

**CLI argument order matters:**
- `-b` first (background flag)
- `-P <script>` before `-o`/`-F`/`-f`
- `--` separator before custom script args
- `-f 1` (frame render) or `-a` (animation) LAST

**Common mistake — wrong order:**
```powershell
# WRONG: -f before -P
& $blender -b -f 1 scene.blend -P script.py
# Blender ignores -f because -P resets the evaluation. Always: -b scene.blend -P script.py -f 1
```

---

## §8. Material Library

Full save/append patterns and node group recipes:
**`references/material-library.md`**
