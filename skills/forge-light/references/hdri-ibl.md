# forge-light — HDRI / IBL Setup
# World environment texture wiring + PolyHaven download + when-to-use guide

## Contents
- §1. HDRI node graph setup (`load_hdri`)
- §2. Packshot mode (IBL lights, transparent background)
- §3. PolyHaven HDRI download (headless, no plugin)
- §4. When IBL alone is enough vs. add a kicker
- §5. Turntable catalog rig (IBL + kicker)

---

## §1. HDRI node graph setup

```python
# forge_hdri.py
import bpy
import math
import os
from pathlib import Path


def load_hdri(
    hdr_path: str,
    strength: float = 1.0,
    rotation_z_deg: float = 0.0,
    hide_background: bool = False,
) -> None:
    """
    Wire an HDRI into the scene World using Environment Texture + Mapping nodes.

    Args:
        hdr_path:       Absolute path to .hdr or .exr file.
                        ALWAYS use forward slashes or Path(...).as_posix() —
                        backslashes cause RuntimeError in bpy.data.images.load().
        strength:       Background node Strength input. 1.0 = neutral.
                        2–4 for bright studio fills; 0.3–0.7 for dark moody.
        rotation_z_deg: Rotate HDRI around Z to reposition the key highlight.
        hide_background: IBL lights but camera sees transparent/black BG (packshot mode).

    Node graph (standard):
        TexCoord.Generated → Mapping → EnvTexture → Background → WorldOutput

    Node graph (hide_background=True — packshot):
        TexCoord → Mapping → EnvTexture → Background ─────────────────┐
        Transparent(strength=0) ───────────────────── MixShader → WorldOutput
                                                          ↑
                                               LightPath.Is Camera Ray

    CRITICAL: EXR/HDR must be tagged Linear colorspace, not sRGB.
    Wrong colorspace → blown-out or flat renders. Verify the tag on every load.
    """
    hdr_path = Path(hdr_path).as_posix()   # normalize separators
    if not os.path.isfile(hdr_path):
        raise FileNotFoundError(f"HDRI not found: {hdr_path}")

    # In headless mode, bpy.context.scene can be None; use data-level access
    world = bpy.data.worlds.get("ForgeWorld") or bpy.data.worlds.new("ForgeWorld")
    bpy.data.scenes[0].world = world
    world.use_nodes = True

    nodes = world.node_tree.nodes
    links = world.node_tree.links
    nodes.clear()

    # --- Core nodes ---
    n_coord = nodes.new('ShaderNodeTexCoord')
    n_map   = nodes.new('ShaderNodeMapping')
    n_env   = nodes.new('ShaderNodeTexEnvironment')
    n_bg    = nodes.new('ShaderNodeBackground')
    n_out   = nodes.new('ShaderNodeOutputWorld')

    n_env.image = bpy.data.images.load(hdr_path, check_existing=True)
    # CRITICAL: EXR/HDR must stay scene-linear; sRGB would double-encode → blown-out/flat.
    # In Blender 4.x's default OCIO config the canonical name is 'Linear Rec.709';
    # plain 'Linear' only exists on some configs, so try it as a fallback.
    for cs in ('Linear Rec.709', 'Linear', 'Linear sRGB'):
        try:
            n_env.image.colorspace_settings.name = cs
            break
        except (TypeError, ValueError):
            continue
    else:
        # Last resort: pick the first linear-ish name the active config exposes.
        for cs in enumerate_colorspaces():
            if 'linear' in cs.lower():
                n_env.image.colorspace_settings.name = cs
                break
    n_env.projection = 'EQUIRECTANGULAR'   # standard for PolyHaven HDRIs

    n_map.inputs['Rotation'].default_value[2] = math.radians(rotation_z_deg)
    n_bg.inputs['Strength'].default_value = strength

    # --- Node layout (cosmetic only) ---
    n_coord.location = (-800, 0)
    n_map.location   = (-600, 0)
    n_env.location   = (-350, 0)
    n_bg.location    = ( -50, 0)
    n_out.location   = ( 200, 0)

    if not hide_background:
        links.new(n_coord.outputs['Generated'], n_map.inputs['Vector'])
        links.new(n_map.outputs['Vector'],      n_env.inputs['Vector'])
        links.new(n_env.outputs['Color'],       n_bg.inputs['Color'])
        links.new(n_bg.outputs['Background'],   n_out.inputs['Surface'])
    else:
        # Packshot: IBL lights scene but camera sees transparent BG
        _wire_packshot(nodes, links, n_coord, n_map, n_env, n_bg, n_out)


def _wire_packshot(nodes, links, n_coord, n_map, n_env, n_bg, n_out):
    """Packshot: IBL illuminates but camera rays see transparent background."""
    n_lp    = nodes.new('ShaderNodeLightPath')
    n_trans = nodes.new('ShaderNodeBackground')   # transparent (strength 0)
    n_mix   = nodes.new('ShaderNodeMixShader')

    n_trans.inputs['Strength'].default_value = 0.0
    n_lp.location  = (-200, 300)
    n_mix.location = ( 100, 0)

    links.new(n_coord.outputs['Generated'],   n_map.inputs['Vector'])
    links.new(n_map.outputs['Vector'],        n_env.inputs['Vector'])
    links.new(n_env.outputs['Color'],         n_bg.inputs['Color'])
    links.new(n_lp.outputs['Is Camera Ray'],  n_mix.inputs['Fac'])
    links.new(n_trans.outputs['Background'],  n_mix.inputs[1])
    links.new(n_bg.outputs['Background'],     n_mix.inputs[2])
    links.new(n_mix.outputs['Shader'],        n_out.inputs['Surface'])


def enumerate_colorspaces():
    """
    Query available colorspace names from Blender's OCIO config.
    Call this when 'Linear' raises a ValueError — the name depends on config version.
    """
    img = bpy.data.images.new("__tmp__", 1, 1)
    prop = img.colorspace_settings.bl_rna.properties['name']
    spaces = [item.identifier for item in prop.enum_items]
    bpy.data.images.remove(img)
    return spaces
```

---

## §2. Shadow catcher + HDRI combination

For packshot on transparent background, combine `hide_background=True` with the shadow
catcher plane. The render must also have `film_transparent = True` and `color_mode = 'RGBA'`.

```python
# After load_hdri(hdr_path, hide_background=True):
scene = bpy.data.scenes[0]
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'   # without this, alpha is discarded

# Shadow catcher pass (required for the catcher plane to render correctly)
scene.view_layers[0].cycles.use_pass_shadow_catcher = True
```

HDRI rotation tip: rotate the HDRI (not the product) to position the key specular highlight.
0° = highlight front-centre; 45° = front-left; 180° = behind product.

---

## §3. PolyHaven HDRI download (headless, requires `requests`)

Good studio HDRIs for neutral product renders. All CC0 — free for most use.

```python
# forge_polyhaven.py
"""
Fetch and cache an HDRI from PolyHaven API.
API base: https://api.polyhaven.com
Requires: pip install requests
PolyHaven ToS: always set a unique User-Agent header.
"""
import os
import hashlib
import requests
from pathlib import Path

POLYHAVEN_API  = "https://api.polyhaven.com"
FORGE_HDRI_CACHE = r"C:\forge\hdri_cache"  # adjust to project cache dir


def fetch_hdri(
    asset_id: str,
    resolution: str = "2k",         # "1k" | "2k" | "4k" | "8k"
    file_format: str = "hdr",       # "hdr" | "exr"
    cache_dir: str = FORGE_HDRI_CACHE,
    user_agent: str = "Forge/1.0 (forge@lumicity.dev)",
) -> str:
    """
    Return local path to the HDRI, downloading and caching if needed.

    Recommended studio IDs:
        'studio_small_09'      — soft neutral, low distraction background
        'photo_studio_01'      — classic photo studio, good for packshot
        'studio_country_hall'  — warm mid-key
        'studio_small_08'      — hard directional (good kicker effect from IBL alone)

    API path: GET /files/{asset_id}
    Response: data['hdri'][resolution][format]['url']
    """
    cache_dir_path = Path(cache_dir)
    cache_dir_path.mkdir(parents=True, exist_ok=True)
    local_path = cache_dir_path / f"{asset_id}_{resolution}.{file_format}"

    if local_path.is_file():
        return local_path.as_posix()   # cache hit — forward slashes for bpy

    headers = {"User-Agent": user_agent}

    # 1. Fetch metadata
    resp = requests.get(f"{POLYHAVEN_API}/files/{asset_id}",
                        headers=headers, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    try:
        file_info = data['hdri'][resolution][file_format]
    except KeyError:
        available = list(data.get('hdri', {}).keys())
        raise ValueError(f"Resolution '{resolution}' not available. Have: {available}")

    download_url  = file_info['url']
    expected_md5  = file_info.get('md5', '')

    # 2. Stream download
    print(f"[Forge] Downloading HDRI: {download_url}")
    r = requests.get(download_url, headers=headers, timeout=120, stream=True)
    r.raise_for_status()

    with open(local_path, 'wb') as f:
        for chunk in r.iter_content(chunk_size=65536):
            f.write(chunk)

    # 3. Verify MD5 if provided
    if expected_md5:
        actual = hashlib.md5(local_path.read_bytes()).hexdigest()
        if actual != expected_md5:
            local_path.unlink()
            raise RuntimeError(f"MD5 mismatch for {asset_id} — deleted, retry.")

    return local_path.as_posix()   # always return forward-slash path for bpy


def list_studio_hdris(user_agent: str = "Forge/1.0") -> list:
    """Return list of asset IDs in the PolyHaven 'studio' HDRI category."""
    headers = {"User-Agent": user_agent}
    resp = requests.get(
        f"{POLYHAVEN_API}/assets",
        params={"t": "hdris", "c": "studio"},
        headers=headers, timeout=30,
    )
    resp.raise_for_status()
    return list(resp.json().keys())
```

Note: `fetch_hdri` requires internet access. For offline/CI environments, pre-download HDRIs
once and point to the local cache. The function caches by `asset_id + resolution + format`.

---

## §4. When IBL alone is enough vs. add a kicker

### IBL-only (no explicit area lights)

Use when:
- Material is diffuse-dominant (plastic, fabric, painted wood, matte rubber)
- You want soft, even lighting that reveals surface texture without harsh shadows
- Rendering a grid of multiple objects simultaneously (catalog batch)
- HDRI is a studio type — outdoor/landscape HDRIs introduce unwanted colour casts

### Add a kicker light when

- Product has metal, glass, or high-gloss surfaces (needs a specular highlight)
- You need predictable shadow direction for shadow-catcher compositing
- Rim separation from background is required
- Object must "pop" from a white background

### IBL + kicker setup

```python
from mathutils import Vector

def build_catalog_lighting(
    center: Vector,
    radius: float,
    hdri_path: str = None,
    hdri_strength: float = 0.8,
    key_energy_w: float = 500.0,
):
    """
    Catalog / turntable lighting: HDRI dominant + single area kicker.
    IBL gives neutral fill from all directions; kicker provides specular highlight.
    """
    if hdri_path:
        load_hdri(hdri_path, strength=hdri_strength, rotation_z_deg=0.0)
    else:
        # Fallback to three-point if no HDRI available
        build_three_point_rig(center, radius, key_energy_w=key_energy_w, fill_ratio=0.5)
        return

    # Tight kicker at 45° front-left — creates a specular as object rotates
    kicker_loc = center + Vector((radius * 2.5, -radius * 2.5, radius * 2.0))
    make_area_light('Forge_Kicker', kicker_loc,
                    energy_w=key_energy_w,
                    size_m=radius * 0.8,
                    aim_at=center)
```

---

## §5. HDRI strength reference

| Strength | Effect | Typical use |
|---|---|---|
| 0.3–0.5 | Dark, moody; slight IBL fill | Editorial, dramatic product |
| 0.7–1.0 | Neutral balanced | Standard product packshot |
| 1.5–2.0 | Bright, high-key fill | E-commerce white background |
| 2.0–4.0 | Dominant IBL; suppress all area lights | Pure IBL renders |

Rotation tips: try 30° increments to find the position where the main HDRI bright spot
creates the best specular highlight on your product's reflective surfaces.
