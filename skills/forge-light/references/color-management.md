# forge-light — Color Management
# AgX / ACES / OCIO for Blender headless rendering

## Contents
- §1. Configure color management in bpy (Blender 4.x / 5.0)
- §2. Texture color space tagging rules
- §3. Headless render with correct color management
- §4. False Color QA pass (exposure verification)
- §5. ACES workflow in Blender
- §6. Standalone OCIO transform (outside Blender)
- §7. Gotchas quick-reference table

> Three.js web matching + programmatic QA checks: **`references/color-management-qa.md`**

---

## §1. Configure color management in bpy

```python
import bpy

def configure_color_management(
    view_transform: str = "AgX",     # "AgX" | "Standard" | "False Color" | "Raw"
    look: str = "None",              # "None" | "Punchy" | "High Contrast" | etc.
    exposure: float = 0.0,           # stops; applied BEFORE view transform
    gamma: float = 1.0,              # applied AFTER transform; always reset to 1.0
    display_device: str = "sRGB",    # "sRGB" | "Display P3" | "Rec. 2020"
):
    """
    Set all color management properties explicitly.
    NEVER rely on .blend file defaults — a 3.x file retains Filmic, not AgX.
    Always call this in every automation script.

    View transform options (Blender default OCIO config):
      "AgX"         → default in Blender 4.0+; 16.5 stops DR; highlights go white (correct)
      "Filmic"      → deprecated in 4.x; still present but not recommended for new work
      "Standard"    → no tone mapping; raw scene-linear → display; use for game-engine exports
      "False Color" → luminance heat map; use for exposure QA only, not production
      "Raw"         → bypass all transforms; data inspection only
      "Khronos PBR Neutral" → 4.5+; matches PBR viewer defaults for neutral preview

    Look modifiers (applied BEFORE view transform):
      "None"               → baseline (recommended for accurate material QA)
      "Punchy"             → more saturated/contrasty
      "Very High Contrast" | "High Contrast" | "Medium High Contrast"
      "Medium Contrast" | "Medium Low Contrast" | "Low Contrast" | "Very Low Contrast"
      "Greyscale"

    Exposure vs. Gamma:
      Use exposure (stops) for brightness — it preserves highlight compression behavior.
      Use gamma ONLY for artistic override after the view transform. Default must be 1.0.
    """
    # Data-level scene access — safe in headless mode
    scene = bpy.data.scenes[0]
    scene.display_settings.display_device = display_device
    scene.view_settings.view_transform = view_transform
    scene.view_settings.look = look
    scene.view_settings.exposure = exposure
    scene.view_settings.gamma = gamma   # always reset; saved files may differ


def query_valid_looks() -> list:
    """
    Return the look identifiers valid for the current config + display + view.
    Call before setting .look to avoid ValueError with non-default OCIO configs.
    """
    prop = bpy.context.scene.view_settings.bl_rna.properties["look"]
    return [item.identifier for item in prop.enum_items]
```

---

## §2. Texture color space tagging rules

**The single most important rule: data maps must be `Non-Color`.**

| Texture type | Correct tag | Wrong tag causes |
|---|---|---|
| Albedo / base color | `sRGB` | Too-dark, under-saturated materials |
| Emissive | `sRGB` | Incorrect emissive intensity |
| Normal map | `Non-Color` | Faceted/triangulated artifacts on smooth mesh |
| Roughness | `Non-Color` | Wrong surface response (too glossy or too rough) |
| Metallic | `Non-Color` | Partial metal shading instead of binary |
| Displacement / height | `Non-Color` | Extreme or inverted displacement |
| AO (as color blend) | `sRGB` | — |
| AO (as factor/multiplier) | `Non-Color` | Wrong darkening magnitude |
| Alpha mask | `Non-Color` | Non-linear alpha cutoff edge |
| HDRI / EXR environment | `Linear` or `Linear Rec.709` | Blown-out or flat render (G1 gotcha) |

```python
import bpy
from pathlib import Path


def tag_texture_color_space(image_path: str, color_space: str) -> bpy.types.Image:
    """
    Load an image and set the correct color space.

    color_space valid values (Blender default OCIO config):
      "sRGB"          → albedo, emissive, color AO bakes
      "Non-Color"     → normal, roughness, metallic, height, AO factor, alpha
      "Linear Rec.709"→ HDR maps, EXR textures in linear light
      "ACEScg"        → textures in ACES AP1 linear (ACES pipelines)
      "Raw"           → same as Non-Color; prefer Non-Color for clarity
    """
    img = bpy.data.images.load(image_path, check_existing=True)
    img.colorspace_settings.name = color_space
    return img


def setup_pbr_material_with_tags(mat_name: str, tex_dir: str) -> bpy.types.Material:
    """
    Correct PBR material with all color spaces properly tagged.
    """
    import os
    mat = bpy.data.materials.new(name=mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out  = nodes.new("ShaderNodeOutputMaterial");  out.location  = (600, 0)
    bsdf = nodes.new("ShaderNodeBsdfPrincipled");  bsdf.location = (300, 0)
    links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])

    def tex(fname, cs, x, y):
        n = nodes.new("ShaderNodeTexImage")
        n.location = (x, y)
        fpath = Path(os.path.join(tex_dir, fname)).as_posix()
        n.image = tag_texture_color_space(fpath, cs)
        return n

    # Albedo — sRGB (Blender linearises on use)
    t = tex("albedo.png", "sRGB", -300, 200)
    links.new(t.outputs["Color"], bsdf.inputs["Base Color"])

    # Normal — Non-Color (raw vector data; sRGB decode corrupts XYZ)
    t = tex("normal.png", "Non-Color", -300, 0)
    nm = nodes.new("ShaderNodeNormalMap"); nm.location = (0, 0)
    links.new(t.outputs["Color"], nm.inputs["Color"])
    links.new(nm.outputs["Normal"], bsdf.inputs["Normal"])

    # Roughness — Non-Color
    t = tex("roughness.png", "Non-Color", -300, -200)
    links.new(t.outputs["Color"], bsdf.inputs["Roughness"])

    # Metallic — Non-Color
    t = tex("metallic.png", "Non-Color", -300, -400)
    links.new(t.outputs["Color"], bsdf.inputs["Metallic"])

    return mat
```

---

## §3. Headless render with correct color management

```python
"""
render_with_color_mgmt.py
Run: blender.exe -b scene.blend -P render_with_color_mgmt.py -- --output C:/out.png
"""
import bpy, sys, os, argparse
from pathlib import Path


def parse_args():
    argv = sys.argv
    if "--" in argv:
        argv = argv[argv.index("--") + 1:]
    p = argparse.ArgumentParser()
    p.add_argument("--output", required=True)
    p.add_argument("--view-transform", default="AgX",
                   choices=["AgX", "Filmic", "Standard", "False Color", "Raw",
                            "Khronos PBR Neutral"])
    p.add_argument("--look", default="None")
    p.add_argument("--exposure", type=float, default=0.0)
    p.add_argument("--format", default="PNG", choices=["PNG", "OPEN_EXR"])
    return p.parse_args(argv)


def main():
    import io
    if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

    args = parse_args()
    scene = bpy.data.scenes[0]

    # Color management — must be explicit; never trust .blend defaults
    scene.display_settings.display_device = "sRGB"
    scene.view_settings.view_transform = args.view_transform
    scene.view_settings.look = args.look
    scene.view_settings.exposure = args.exposure
    scene.view_settings.gamma = 1.0   # always reset

    # Output format
    out = Path(args.output).as_posix()
    os.makedirs(os.path.dirname(os.path.abspath(args.output)), exist_ok=True)
    scene.render.filepath = out
    fmt = scene.render.image_settings
    fmt.file_format = args.format
    if args.format == "PNG":
        fmt.color_mode = "RGBA"
        fmt.color_depth = "16"       # 16-bit for QA; 8-bit for final web
        fmt.compression = 15
        # FOLLOW_SCENE: view transform IS baked into the PNG
        fmt.color_management = "FOLLOW_SCENE"
    else:  # EXR
        fmt.color_mode = "RGBA"
        fmt.exr_codec = "ZIP"
        # EXR always stays scene-linear; view transform is NOT applied

    # Render
    bpy.ops.render.render(write_still=False)
    result = bpy.data.images.get("Render Result")
    if result is None:
        print("[forge-light] ERROR: No Render Result after render.", file=sys.stderr)
        sys.exit(1)

    # CRITICAL: use save_render(), NOT save()
    # save_render() → applies view transform → display-ready file
    # save()        → writes raw buffer; no view transform; wrong for PNG QA
    result.save_render(filepath=out, scene=scene)
    print(f"[forge-light] Saved: {out}  view_transform={args.view_transform}")


if __name__ == "__main__":
    main()
```

---

## §4. False Color QA pass (exposure verification)

```python
import bpy


def render_false_color(output_path: str, scene=None):
    """
    Render a False Color pass to verify exposure, then restore original settings.
    Agent reads the PNG and checks that mid-gray lands in the "Gray" zone.

    False Color luminance bands (Blender manual):
      Black       < 0.0001  underexposed
      Blue        0.0001–0.0005
      Blue-Cyan   0.0005–0.005
      Cyan        0.005–0.16
      Gray        0.16–0.22  ← 18% gray / correct middle exposure
      Green-Yellow 0.22–0.35
      Yellow      0.35–0.55
      Orange      0.55–0.80  approaching overexposure
      Red         0.80–0.97  near clipping
      White       > 0.97     clipped / overexposed
    """
    if scene is None:
        scene = bpy.data.scenes[0]

    # Store
    orig_transform = scene.view_settings.view_transform
    orig_look      = scene.view_settings.look

    # Switch
    scene.view_settings.view_transform = "False Color"
    scene.view_settings.look = "None"

    bpy.ops.render.render(write_still=False)
    result = bpy.data.images.get("Render Result")
    result.save_render(filepath=output_path, scene=scene)

    # Restore
    scene.view_settings.view_transform = orig_transform
    scene.view_settings.look = orig_look
    print(f"[forge-light] False Color saved: {output_path}")
    print("[forge-light] Read the PNG: middle gray (~18% reflectance surfaces) "
          "should appear as the Gray zone (RGB ~128,128,128 area in the output).")
```

---

## §5. ACES workflow in Blender

```python
import bpy
import os


def setup_aces_pipeline(use_external_config: bool = False):
    """
    Two modes:
      use_external_config=False → Blender's built-in ACES2065-1/ACEScg support (4.x / 5.0)
      use_external_config=True  → Full ACES CG config via OCIO env var

    For use_external_config=True, set the env var BEFORE launching Blender:
        $env:OCIO = "ocio://cg-config-v4.0.0_aces-v2.0_ocio-v2.5"
    Built-in URI strings work in any OCIO 2.2+ application; no file download needed.

    Blender 5.0: exposes working_space property; can be set to "ACEScg" for full ACES.
    Blender 4.x: working space is always Linear Rec.709 internally; ACES view transforms
                 are available through the bundled config.
    """
    scene = bpy.data.scenes[0]

    if use_external_config:
        # Requires $env:OCIO set before launch; view transforms from ACES CG config
        scene.display_settings.display_device = "sRGB"
        scene.view_settings.view_transform = "ACES 2.0 - SDR 100nits"
    else:
        # Built-in: AgX is close enough for most product work
        scene.display_settings.display_device = "sRGB"
        scene.view_settings.view_transform = "AgX"   # or "ACES 2.0 sRGB" on 5.0

    scene.view_settings.exposure = 0.0
    scene.view_settings.gamma = 1.0

    # EXR delivery for ACES archival
    scene.render.image_settings.file_format = "OPEN_EXR"
    scene.render.image_settings.exr_codec = "ZIP"


# Texture tagging rules in ACES pipeline:
# sRGB textures (Substance, Photoshop exports) → tag "sRGB"  (auto-converted by OCIO)
# Pre-linearized textures / HDRIs             → tag "Linear Rec.709" or "ACEScg"
# Data maps (normal, rough, metal, disp)      → always "Non-Color"
```

---

## §6. Standalone OCIO transform (outside Blender)

Apply AgX to a linear EXR batch without opening Blender.
```powershell
pip install opencolorio   # v2.5.2; wheels for CPython 3.10-3.12 on Windows x64
# If Python 3.13+: pip install simple-ocio (bundles Blender config + OCIO wheel)
```

```python
"""
Apply AgX tone mapping to linear EXR → sRGB PNG using Blender's bundled OCIO config.
Run with system Python (NOT Blender's internal Python).
Requires: pip install opencolorio imageio[freeimage] numpy
"""
import os
import numpy as np
import PyOpenColorIO as OCIO   # pip install opencolorio

BLENDER_OCIO = (
    r"C:\Program Files\Blender Foundation\Blender 4.5"
    r"\4.5\datafiles\colormanagement\config.ocio"
)
os.environ["OCIO"] = BLENDER_OCIO

config = OCIO.Config.CreateFromEnv()
transform = OCIO.DisplayViewTransform()
transform.setSrc("Linear Rec.709")
transform.setDisplay("sRGB")
transform.setView("AgX")

processor = config.getProcessor(transform)
cpu       = processor.getDefaultCPUProcessor()


def apply_agx_to_exr(exr_path: str, png_out: str):
    import imageio.v3 as iio
    img  = iio.imread(exr_path, plugin="EXR")   # float32 linear HxWxC
    h, w, c = img.shape
    flat = img.reshape(-1, c)
    if c == 4:
        out_flat = np.array([cpu.applyRGBA(list(px)) for px in flat], dtype=np.float32)
    else:
        out_flat = np.array([cpu.applyRGB(list(px[:3])) for px in flat], dtype=np.float32)
    out = np.clip(out_flat, 0, 1).reshape(h, w, c)
    iio.imwrite(png_out, (out * 255).astype(np.uint8))
    print(f"[color-mgmt] {exr_path} → {png_out} (AgX/sRGB)")
```

OCIO env var tip: set in the same PowerShell session as the launch command.
`BLENDER_OCIO` (Blender 5.0+) avoids conflicting with other OCIO-aware apps.

---

## §7. Gotchas quick-reference table

| # | Symptom | Fix |
|---|---|---|
| C-G1 | Normal maps → faceted artifacts | Tag `Non-Color`, not `sRGB` |
| C-G2 | Re-imported PNG looks washed out | Tag render PNGs `Non-Color` as compositing input; use EXR intermediates |
| C-G3 | `save_as()` fails headless | Use `image.save_render(filepath=..., scene=scene)` — not an operator |
| C-G4 | EXR looks dark in Image Editor | Enable "View as Render" (`image.use_view_as_render = True`) |
| C-G5 | OCIO env var ignored by Blender | Set `$env:OCIO` in SAME PowerShell session before launching |
| C-G6 | `pip install opencolorio` fails Python 3.13+ | Use Python 3.10–3.12; or `pip install simple-ocio` |
| C-G10 | Filmic still active in old `.blend` | Always set `view_transform = "AgX"` explicitly in every script |
| C-G11 | `.look = "Punchy"` raises ValueError | Query valid looks: `[i.identifier for i in scene.view_settings.bl_rna.properties["look"].enum_items]` |
| C-G12 | OCIO config .cube LUT not found on Windows | Ensure `src:` in config.ocio use forward slashes; set config working directory |

> Three.js gotchas (C-G7 through C-G9) and programmatic QA checks: **`references/color-management-qa.md`**
