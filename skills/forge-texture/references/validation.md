# Forge Texture — Validation, QA & Normal Map Convention

## Contents
- §1. Pixel-level stat checks (per map type)
- §2. Tileability check
- §3. Visual QA render (preview sphere)
- §4. Normal map convention reference and G-channel flip
- §5. Height-to-normal conversion (Sobel)
- §6. PBR set from single albedo (approximate)

---

## §1. Pixel-Level Stat Checks

Run after every bake. Use Pillow (no bpy needed — runs outside Blender).

```python
import numpy as np
from pathlib import Path
from PIL import Image


def validate_normal_map(path: str) -> dict:
    """
    Checks:
    - B channel mean >= 160 (Z-component pointing up in tangent space)
    - R and G channel means near 128 (neutral in [-1,1])
    - Saturated pixel count < 5% (no clamped normals)
    """
    img = np.array(Image.open(path).convert("RGB"), dtype=np.float32)
    r, g, b = img[:, :, 0], img[:, :, 1], img[:, :, 2]
    saturated_pct = float(np.mean((img == 0) | (img == 255)) * 100)
    result = {
        "b_min":  float(b.min()),
        "b_mean": float(b.mean()),
        "r_mean": float(r.mean()),
        "g_mean": float(g.mean()),
        "saturated_pct": saturated_pct,
    }
    result["pass"] = (
        result["b_min"] >= 80 and
        result["b_mean"] >= 160 and
        90 <= result["r_mean"] <= 166 and
        result["saturated_pct"] < 5.0
    )
    return result


def validate_ao_map(path: str) -> dict:
    """AO should be mostly bright (max > 128) with darker occlusion regions."""
    img = np.array(Image.open(path).convert("L"), dtype=np.float32)
    result = {
        "min":  float(img.min()),
        "max":  float(img.max()),
        "mean": float(img.mean()),
    }
    result["pass"] = result["max"] > 128 and result["min"] < result["max"]
    return result


def validate_roughness_map(path: str) -> dict:
    """
    Roughness should vary (std > 10) and not be clamped at 0 or 255.
    A flat roughness map (std <= 10) is usually a bake error.
    """
    img = np.array(Image.open(path).convert("L"), dtype=np.float32)
    result = {
        "min":  float(img.min()),
        "max":  float(img.max()),
        "mean": float(img.mean()),
        "std":  float(img.std()),
    }
    result["pass"] = result["std"] > 10 and result["min"] > 0
    return result


def validate_curvature_map(path: str) -> dict:
    """Curvature: grey (128) base, black=concave, white=convex. Should have range."""
    img = np.array(Image.open(path).convert("L"), dtype=np.float32)
    result = {
        "min":   float(img.min()),
        "max":   float(img.max()),
        "mean":  float(img.mean()),
        "range": float(img.max() - img.min()),
    }
    result["pass"] = result["range"] > 20   # < 20 = suspiciously flat
    return result


# Usage example:
# stats = validate_normal_map(r"C:\tmp\hero_normal.png")
# if not stats["pass"]:
#     print(f"FAIL: {stats}")
# else:
#     print(f"OK: b_mean={stats['b_mean']:.1f}")
```

---

## §2. Tileability Check

```python
def check_tileability(path: str, tolerance: float = 5.0) -> dict:
    """
    Compare left/right and top/bottom edge strips.
    A truly tileable texture has matching edges (mean diff < tolerance).
    """
    img = np.array(Image.open(path).convert("RGB"), dtype=np.float32)
    h, w = img.shape[:2]
    strip = max(4, w // 32)

    left_diff  = float(np.abs(img[:, :strip]    - img[:, w-strip:]).mean())
    top_diff   = float(np.abs(img[:strip, :]    - img[h-strip:, :]).mean())
    return {
        "left_right_diff": left_diff,
        "top_bottom_diff": top_diff,
        "pass": left_diff < tolerance and top_diff < tolerance,
    }
```

---

## §3. Visual QA Render (Preview Sphere)

After baking, render a sphere with the maps applied to verify material wiring and color spaces.

```python
# forge_validate_render.py — run with: blender -b -P forge_validate_render.py
import bpy, sys, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def render_material_preview(
    albedo: str,
    normal: str,
    roughness: str,
    output: str = "C:/tmp/preview.png",
    samples: int = 32,
):
    bpy.ops.wm.read_factory_settings(use_empty=True)

    # Basic world light
    world = bpy.data.worlds.new("World")
    world.use_nodes = True
    nt = world.node_tree
    bg = nt.nodes.get("Background") or nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 0.5
    bpy.context.scene.world = world

    # UV sphere
    bpy.ops.mesh.primitive_uv_sphere_add(radius=1, segments=64, ring_count=32)
    sphere = bpy.context.object
    bpy.ops.object.shade_smooth()

    # Add a camera
    bpy.ops.object.camera_add(location=(0, -3.5, 0))
    cam = bpy.context.object
    cam.rotation_euler = (1.5708, 0, 0)   # point toward Y origin
    bpy.context.scene.camera = cam

    # Build verification material
    mat = bpy.data.materials.new("ForgeVerify")
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial")
    pbsdf = nodes.new("ShaderNodeBsdfPrincipled")

    def load_tex(path, colorspace, loc):
        n = nodes.new("ShaderNodeTexImage")
        img = bpy.data.images.load(path)
        img.colorspace_settings.name = colorspace
        n.image = img
        n.location = loc
        return n

    alb = load_tex(albedo,    "sRGB",      (-200,  300))
    nrm = load_tex(normal,    "Non-Color", (-200,    0))
    rgh = load_tex(roughness, "Non-Color", (-200, -200))

    nmap = nodes.new("ShaderNodeNormalMap")
    nmap.space = "TANGENT"
    nmap.location = (100, 0)

    links.new(alb.outputs["Color"], pbsdf.inputs["Base Color"])
    links.new(nrm.outputs["Color"], nmap.inputs["Color"])
    links.new(nmap.outputs["Normal"], pbsdf.inputs["Normal"])
    links.new(rgh.outputs["Color"], pbsdf.inputs["Roughness"])
    links.new(pbsdf.outputs["BSDF"], out.inputs["Surface"])

    sphere.data.materials.append(mat)

    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.render.resolution_x = 512
    scene.render.resolution_y = 512
    scene.render.filepath = output
    scene.render.image_settings.file_format = "PNG"
    scene.render.use_overwrite = True

    bpy.ops.render.render(write_still=True)
    print(f"[forge] Preview render: {output}")


# Parse sys.argv after --
import sys
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--albedo",    default="C:/tmp/albedo.png")
ap.add_argument("--normal",    default="C:/tmp/normal_gl.png")
ap.add_argument("--roughness", default="C:/tmp/roughness.png")
ap.add_argument("--output",    default="C:/tmp/preview.png")
args = ap.parse_args(argv)
render_material_preview(args.albedo, args.normal, args.roughness, args.output)
```

After running, the Forge orchestrator calls `Read(output_png_path)` to visually inspect the sphere:
- Uniform black = image not loaded (check absolute path and forward slashes)
- Uniform grey/flat = roughness bake failed (all-white roughness)  
- Flat shading, no normal detail = normal map not applied or wrong color space
- Correct result: visible surface texture variation and micro-normal lighting response

---

## §4. Normal Map Convention & G-Channel Flip

### Convention table

| Engine | Convention | G channel | `bake.normal_g` |
|--------|------------|-----------|-----------------|
| Blender internal | OpenGL | +Y (green up) | `'POS_Y'` |
| Unity HDRP | OpenGL | +Y | `'POS_Y'` |
| Three.js / glTF | OpenGL | +Y | `'POS_Y'` |
| Unreal Engine 5 | DirectX | −Y (green down/inverted) | `'NEG_Y'` |
| DirectX (general) | DirectX | −Y | `'NEG_Y'` |
| Marmoset Toolbag | OpenGL default | +Y | `'POS_Y'` |

### Flip G channel post-bake (OpenGL → DirectX)

```python
import cv2

def flip_normal_to_dx(input_path: str, output_path: str) -> None:
    """Convert an OpenGL normal map to DirectX convention by inverting the G channel."""
    n = cv2.imread(input_path)   # cv2 loads as BGR
    if n is None:
        from PIL import Image
        import numpy as np
        n = np.array(Image.open(input_path).convert("RGB"))[:, :, ::-1]
    n[:, :, 1] = 255 - n[:, :, 1]   # index 1 = G in BGR
    cv2.imwrite(output_path, n)
    print(f"[forge] DX normal: {output_path}")


# flip_normal_to_dx("C:/out/hero_normal_gl.png", "C:/out/hero_normal_dx.png")
```

### cv2.imread on Windows paths with spaces

cv2.imread returns None for paths containing spaces or non-ASCII characters on Windows.
Use Pillow as an intermediate loader:

```python
import numpy as np
from PIL import Image
def safe_imread(path: str):
    img = Image.open(path).convert("RGB")
    return np.array(img)[:, :, ::-1]   # RGB → BGR for cv2 compatibility
```

---

## §5. Height-to-Normal Conversion (Sobel)

Use when given a greyscale height/displacement map but needing a tangent-space normal.

```python
import numpy as np, cv2

def height_to_normal(
    height_path: str,
    out_path: str,
    strength: float = 2.0,
    convention: str = "opengl",   # 'opengl' or 'directx'
) -> None:
    """
    Convert grayscale height map to tangent-space normal map via Sobel derivatives.
    strength: higher = more pronounced surface detail (start 2.0, try 3.0-5.0)
    """
    # Safe imread for Windows paths with spaces
    img_pil = Image.open(height_path).convert("L")
    img = np.array(img_pil, dtype=np.float32) / 255.0

    ksize = 3
    dx = cv2.Sobel(img, cv2.CV_32F, 1, 0, ksize=ksize) * strength
    dy = cv2.Sobel(img, cv2.CV_32F, 0, 1, ksize=ksize) * strength

    nz = np.ones_like(dx)
    length = np.sqrt(dx**2 + dy**2 + nz**2)
    nx = -dx / length
    ny = -dy / length
    nz =  nz / length

    if convention == "directx":
        ny = -ny   # flip G for DX

    r = ((nx * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    g = ((ny * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)
    b = ((nz * 0.5 + 0.5) * 255).clip(0, 255).astype(np.uint8)

    normal_bgr = cv2.merge([b, g, r])   # cv2 is BGR
    cv2.imwrite(out_path, normal_bgr)
    print(f"[forge] Normal (height-derived): {out_path}")
```

---

## §6. PBR Set from Single Albedo (Approximate)

Quick generation of a 5-map PBR set when only an albedo is available.
Results are approximate — not a substitute for a proper bake. Suitable for fast iteration.

```python
import cv2, numpy as np
from pathlib import Path
from PIL import Image as PILImage


def generate_pbr_set(
    albedo_path: str,
    out_dir: str,
    normal_strength: float = 3.0,
    roughness_contrast: float = 1.2,
    convention: str = "opengl",
) -> dict:
    """
    From a single albedo PNG, generate:
    albedo, height (luminance), normal_gl, roughness (inverse blur), ao (erosion approx).
    Returns dict of output paths.
    """
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    stem = Path(albedo_path).stem

    # Safe read (handles Windows paths with spaces)
    img_pil = PILImage.open(albedo_path).convert("RGB")
    img = np.array(img_pil)[:, :, ::-1]   # RGB -> BGR

    out = {}

    # Albedo pass-through
    alb_path = f"{out_dir}/{stem}_albedo.png"
    cv2.imwrite(alb_path, img)
    out["albedo"] = alb_path

    # Height = luminance
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    hgt_path = f"{out_dir}/{stem}_height.png"
    cv2.imwrite(hgt_path, gray)
    out["height"] = hgt_path

    # Normal from height
    gray_f = gray.astype(np.float32) / 255.0
    dx = cv2.Sobel(gray_f, cv2.CV_32F, 1, 0, ksize=3) * normal_strength
    dy = cv2.Sobel(gray_f, cv2.CV_32F, 0, 1, ksize=3) * normal_strength
    nz = np.ones_like(dx)
    length = np.sqrt(dx**2 + dy**2 + nz**2)
    nx, ny_c, nz_c = -dx/length, -dy/length, nz/length
    if convention == "directx":
        ny_c = -ny_c
    r = ((nx  * .5 + .5)*255).clip(0, 255).astype(np.uint8)
    g = ((ny_c * .5 + .5)*255).clip(0, 255).astype(np.uint8)
    b = ((nz_c * .5 + .5)*255).clip(0, 255).astype(np.uint8)
    nrm_path = f"{out_dir}/{stem}_normal_gl.png"
    cv2.imwrite(nrm_path, cv2.merge([b, g, r]))
    out["normal"] = nrm_path

    # Roughness = inverse local contrast (bright blur = smooth surface)
    blur = cv2.GaussianBlur(gray, (15, 15), 0)
    rough = cv2.convertScaleAbs(blur, alpha=roughness_contrast)
    rgh_path = f"{out_dir}/{stem}_roughness.png"
    cv2.imwrite(rgh_path, rough)
    out["roughness"] = rgh_path

    # AO = erosion approximation
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (15, 15))
    ao = cv2.erode(gray, kernel)
    ao = cv2.GaussianBlur(ao, (21, 21), 0)
    ao_path = f"{out_dir}/{stem}_ao.png"
    cv2.imwrite(ao_path, ao)
    out["ao"] = ao_path

    print(f"[forge] PBR set in {out_dir}: {list(out.keys())}")
    return out
```
