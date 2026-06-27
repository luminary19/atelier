# forge-light — Three-Point Area-Light Rig
# Full Python code: bounding sphere + three-point builder + Kelvin conversion

## Contents
- §1. Bounding sphere helpers (prerequisite)
- §2. `make_area_light()` — single light factory
- §3. `build_three_point_rig()` — full three-point builder
- §4. `_kelvin_to_linear()` — color temperature conversion
- §5. Parameter tables and tuning guide
- §6. Scene-prep helpers (`clear_scene`)

---

## §1. Bounding sphere helpers

All light distances and sizes are computed from the object bounding sphere so
the rig scales correctly to any asset. Call this BEFORE building any rig.

```python
# forge_lighting_helpers.py  (place in your render script or import it)
import bpy
from mathutils import Vector
import math


def clear_scene():
    """Remove all objects + orphan data. Call before import in batch mode."""
    bpy.ops.object.select_all(action='SELECT')
    bpy.ops.object.delete(use_global=False)
    for block in bpy.data.meshes:
        if block.users == 0:
            bpy.data.meshes.remove(block)
    for block in bpy.data.materials:
        if block.users == 0:
            bpy.data.materials.remove(block)
    for block in bpy.data.images:
        if block.users == 0:
            bpy.data.images.remove(block)


def get_bounding_sphere(objects=None):
    """
    Return (center: Vector, radius: float) of the world-space bounding sphere
    for all renderable mesh objects (or the provided list).
    Uses matrix_world transform — handles any position/rotation/scale.
    """
    if objects is None:
        objects = [o for o in bpy.context.scene.objects
                   if o.type == 'MESH' and not o.hide_render]
    all_corners = []
    for obj in objects:
        for corner in obj.bound_box:
            all_corners.append(obj.matrix_world @ Vector(corner))
    if not all_corners:
        return Vector((0, 0, 0)), 1.0
    center = sum(all_corners, Vector()) / len(all_corners)
    radius = max((c - center).length for c in all_corners)
    return center, max(radius, 0.01)  # guard against degenerate geometry
```

---

## §2. `make_area_light()` — single light factory

```python
def make_area_light(name, location, energy_w, size_m,
                    color=(1.0, 1.0, 1.0), shape='SQUARE',
                    aim_at=None, collection=None):
    """
    Create an AREA light and optionally aim it at a target point.

    Args:
        energy_w: Watts (W). AreaLight.energy is radiant power over the
                  whole emitting surface, in all directions. Default in API: 10 W.
        size_m:   Width (and height if SQUARE/DISK) in meters.
        shape:    'SQUARE' | 'RECTANGLE' | 'DISK' | 'ELLIPSE'
        aim_at:   Vector — if given, rotates light to face this world point.

    Notes on AreaLight.normalize (default True in Blender 4.5):
        normalize=True  → total Watts stays constant when you resize the panel.
                          Bigger panel = lower radiance = softer shadows, same energy.
        normalize=False → constant radiance regardless of size (non-physical, artist-friendly).
        To add BOTH softness AND brightness: increase energy_w when increasing size_m.
    """
    light_data = bpy.data.lights.new(name=name, type='AREA')
    light_data.energy = energy_w
    light_data.size = size_m
    light_data.shape = shape
    light_data.color = color

    light_obj = bpy.data.objects.new(name=name, object_data=light_data)
    col = collection or bpy.context.scene.collection
    col.objects.link(light_obj)
    light_obj.location = location

    if aim_at is not None:
        direction = Vector(aim_at) - Vector(location)
        light_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()

    return light_obj
```

---

## §3. `build_three_point_rig()` — full three-point builder

```python
def build_three_point_rig(
    center: Vector,
    radius: float,
    key_energy_w: float = 1000.0,
    fill_ratio: float = 0.35,     # fill = key * ratio
    rim_ratio: float = 0.60,      # rim  = key * ratio
    distance_mult: float = 3.0,   # light distance = radius * mult
    key_size_mult: float = 1.5,   # area light size = radius * mult
    color_temp_k: int = 5500,     # 5500 K = daylight white
) -> dict:
    """
    Build a three-point area-light rig scaled to object bounding sphere.

    Key:  45° front-left,  elevation 30°
    Fill: 45° front-right, elevation 20°  (softer, lower, larger panel)
    Rim:  directly behind, elevation 60°  (edge separation, narrow panel)

    Returns dict of light objects keyed 'key', 'fill', 'rim'.

    Proven ratios for product packshot:
      Key : Fill : Rim = 1.0 : 0.35 : 0.60
      - Fill at 0.35 prevents shadow side going > 2 EV darker (packshot style)
      - Rim at 0.60 creates edge separation without spilling on background
      - For dramatic editorial: fill_ratio=0.15, rim_ratio=0.80
    """
    d = radius * distance_mult
    h_key  = d * math.tan(math.radians(30))
    h_fill = d * math.tan(math.radians(20))
    h_rim  = d * math.tan(math.radians(60))

    key_size  = radius * key_size_mult
    fill_size = radius * key_size_mult * 1.8   # wider for wrap
    rim_size  = radius * key_size_mult * 0.8   # narrower for rim crispness

    key_color  = _kelvin_to_linear(color_temp_k)
    fill_color = _kelvin_to_linear(color_temp_k + 200)  # slightly warmer fill
    rim_color  = (1.0, 1.0, 1.0)                        # pure white rim

    key_loc  = center + Vector(( d * 0.7, -d * 0.7, h_key ))
    fill_loc = center + Vector((-d * 0.7, -d * 0.7, h_fill))
    rim_loc  = center + Vector(( 0.0,      d * 1.0, h_rim ))

    lights = {}
    lights['key']  = make_area_light('Forge_Key',  key_loc,
                                     key_energy_w,
                                     key_size,  color=key_color,  aim_at=center)
    lights['fill'] = make_area_light('Forge_Fill', fill_loc,
                                     key_energy_w * fill_ratio,
                                     fill_size, color=fill_color, aim_at=center)
    lights['rim']  = make_area_light('Forge_Rim',  rim_loc,
                                     key_energy_w * rim_ratio,
                                     rim_size,  color=rim_color,  aim_at=center)
    return lights
```

---

## §4. `_kelvin_to_linear()` — color temperature conversion

```python
def _kelvin_to_linear(kelvin: int) -> tuple:
    """
    Approximate RGB for a blackbody color temperature (Tanner Helland method).
    Returns linear-light RGB tuple (NOT sRGB). Accurate range: 1000K – 12000K.

    Common values:
      1900K — candlelight (deep amber)
      2700K — tungsten / warm white LED
      4000K — neutral white fluorescent
      5500K — daylight / electronic flash
      6500K — overcast daylight / reference white D65
      9000K — clear blue sky
    """
    temp = kelvin / 100.0
    if temp <= 66:
        r = 1.0
        g = max(0.0, min(1.0, (99.4708025861 * math.log(temp) - 161.1195681661) / 255.0))
    else:
        r = max(0.0, min(1.0, 329.698727446 * ((temp - 60) ** -0.1332047592) / 255.0))
        g = max(0.0, min(1.0, 288.1221695283 * ((temp - 60) ** -0.0755148492) / 255.0))
    if temp >= 66:
        b = 1.0
    elif temp <= 19:
        b = 0.0
    else:
        b = max(0.0, min(1.0, (138.5177312231 * math.log(temp - 10) - 305.0447927307) / 255.0))
    return (r, g, b)
```

---

## §5. Parameter tables and tuning guide

### Energy vs. object size (starting points)

| Object diameter | Key energy (W) | Distance mult | Notes |
|---|---|---|---|
| < 5 cm (jewellery, coins) | 200–500 | 4.0 | Tight, sharp lights; 4K HDRI recommended |
| 5–30 cm (products, phones) | 500–1500 | 3.0 | Standard product packshot range |
| 30 cm–1 m (shoes, bags, helmets) | 1500–3000 | 2.5 | May add kicker for specular |
| > 1 m (furniture, vehicles) | 3000–8000 | 2.0 | IBL + 3-point hybrid |

### Area light shape selection

| Shape | Best for |
|---|---|
| `SQUARE` | General purpose; most product work |
| `RECTANGLE` (2:1 or 3:1) | Horizontal products (watches, phones flat) |
| `DISK` | Round/compact products; mimics octabox |
| `ELLIPSE` | Narrow vertical products (bottles, cans) |

### Spread parameter (0..π) — `light_data.spread`

- Default `π` = omnidirectional emission (standard softbox)
- `~1.0` = gridded softbox, more directional quality
- `~0.4` = hard-edged projection, nearly spotlight behavior

### Ratio presets

| Style | fill_ratio | rim_ratio | Notes |
|---|---|---|---|
| Packshot / clean | 0.35 | 0.60 | ≤ 2 EV shadow ratio; clean product catalog |
| Commercial / bright | 0.50 | 0.40 | Near flat; high-key e-commerce |
| Dramatic editorial | 0.15 | 0.80 | 3+ EV ratio; fashion, moody product |
| Portrait | 0.50 | 0.30 | Wide fill, soft rim |
| Clamshell (beauty) | 0.70 | 0.00 | Large fill below lens; no rim |

---

## §6. Complete usage example

```python
"""
forge_three_point_example.py
Invoke: blender -b --factory-startup -P forge_three_point_example.py -- widget.glb out.png
"""
import bpy, sys, os, math
from mathutils import Vector
from pathlib import Path

# UTF-8 stdout fix (Windows cp1252 default)
import io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Parse args after --
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
glb_path  = Path(argv[0]).as_posix() if len(argv) > 0 else None
out_path  = Path(argv[1]).as_posix() if len(argv) > 1 else "C:/renders/out.png"

# --- Scene prep ---
clear_scene()
if glb_path:
    bpy.ops.import_scene.gltf(filepath=glb_path)

# --- Rig ---
center, radius = get_bounding_sphere()
lights = build_three_point_rig(center, radius, key_energy_w=1000.0)

# --- Color management ---
scene = bpy.data.scenes[0]   # safe in headless; avoid bpy.context.scene in timers
scene.display_settings.display_device = "sRGB"
scene.view_settings.view_transform = "AgX"
scene.view_settings.look = "None"
scene.view_settings.exposure = 0.0
scene.view_settings.gamma = 1.0   # always reset — saved files may have non-1.0

# --- Render settings ---
scene.render.engine = 'CYCLES'
scene.render.resolution_x = 2048
scene.render.resolution_y = 2048
scene.render.film_transparent = True
scene.render.image_settings.file_format = 'PNG'
scene.render.image_settings.color_mode = 'RGBA'  # REQUIRED with film_transparent
scene.render.image_settings.color_depth = '16'

cy = scene.cycles
cy.samples = 256
cy.use_denoising = True
cy.denoiser = 'OPENIMAGEDENOISE'
cy.device = 'CPU'  # GPU requires re-applying prefs after --factory-startup; CPU always works

os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
scene.render.filepath = out_path

bpy.ops.render.render(write_still=False)
result = bpy.data.images.get("Render Result")
result.save_render(filepath=out_path, scene=scene)  # save_render bakes view transform
print(f"[forge-light] Saved: {out_path}")
```

**Invocation:**
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b --factory-startup `
    -P "C:\forge\forge_three_point_example.py" `
    -- "C:\assets\widget.glb" "C:\renders\widget_hero.png"
```
