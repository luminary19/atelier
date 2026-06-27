# forge-light — Shadow Catcher, Cyclorama & Render Settings
# Contact shadows on transparent backgrounds + infinite white + production Cycles config

## Contents
- §1. Shadow catcher ground plane
- §2. Cyclorama (infinite white backdrop)
- §3. Configuring Cycles for production
- §4. Shadow catcher gotchas and fixes

---

## §1. Shadow catcher ground plane

Use when: product needs contact shadow on a transparent background (packshot).
Requires Cycles (not EEVEE). The catcher plane is invisible in camera but shows shadows.

```python
import bpy
from pathlib import Path


def add_shadow_catcher_ground(z_offset: float = 0.0, size: float = 20.0) -> bpy.types.Object:
    """
    Invisible ground plane that catches/shows shadows only.
    Works in Cycles only. Renders as transparent with shadow alpha channel.

    Usage pattern:
        center, radius = get_bounding_sphere()
        plane = add_shadow_catcher_ground(
            z_offset=center.z - radius,
            size=radius * 10
        )
        # Enable shadow catcher pass on view layer:
        scene = bpy.data.scenes[0]
        scene.view_layers[0].cycles.use_pass_shadow_catcher = True
        scene.render.film_transparent = True
        scene.render.image_settings.color_mode = 'RGBA'   # REQUIRED

    Gotcha — colour cast:
        The catcher plane's diffuse material can bounce light onto the product underside.
        For pure packshot (no colour bleed), disable ray visibility:
            plane.visible_diffuse = False
            plane.visible_glossy  = False
        Keep visible_shadow = True (this is what makes the shadow appear).
    """
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0.0, 0.0, z_offset))
    plane = bpy.context.active_object
    plane.name = "Forge_ShadowCatcher"

    # The Cycles shadow catcher flag is on the OBJECT, not the material
    plane.cycles.is_shadow_catcher = True

    # Neutral diffuse material (white, fully rough)
    mat = bpy.data.materials.new("Forge_ShadowCatcherMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (0.8, 0.8, 0.8, 1.0)
        bsdf.inputs['Roughness'].default_value  = 1.0
    plane.data.materials.append(mat)

    return plane


def configure_shadow_catcher_scene(scene=None):
    """
    Apply all render settings required for shadow catcher to work correctly.
    Call AFTER add_shadow_catcher_ground().
    """
    if scene is None:
        scene = bpy.data.scenes[0]

    # Transparent film — required or background is solid black/white
    scene.render.film_transparent = True

    # RGBA output — required or alpha channel is discarded even with transparent film
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.image_settings.file_format = 'PNG'   # PNG and EXR support alpha

    # Shadow catcher pass (Cycles view layer setting)
    scene.view_layers[0].cycles.use_pass_shadow_catcher = True

    # Light tree must be enabled for any scene using light linking (shadows behave better)
    scene.cycles.use_light_tree = True
```

---

## §2. Cyclorama (infinite white backdrop)

Use when: product is rendered on a clean, seamless white or colored backdrop (not transparent).
The cyclorama is a visible background — not a shadow catcher.

```python
import bpy
import bmesh


def add_cyclorama(
    center_z: float = 0.0,
    width: float = 10.0,
    depth: float = 8.0,
    height: float = 6.0,
    color: tuple = (1.0, 1.0, 1.0),
) -> bpy.types.Object:
    """
    Flat floor with a plain diffuse backdrop.
    For a proper seamless swept cyclorama (curved floor-to-wall join),
    build a subdivided mesh and add a Subdivision + Smooth modifier.

    For basic studio work, a large flat plane is usually sufficient.
    """
    bpy.ops.mesh.primitive_plane_add(size=1, location=(0.0, 0.0, center_z))
    floor = bpy.context.active_object
    floor.name = "Forge_Cyclorama"
    floor.scale = (width / 2, depth / 2, 1.0)
    bpy.ops.object.transform_apply(scale=True)

    mat = bpy.data.materials.new("Forge_CycloramaMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Roughness'].default_value  = 1.0
    floor.data.materials.append(mat)
    return floor


def add_cyclorama_with_curved_back(
    width: float = 8.0,
    depth: float = 6.0,
    height: float = 5.0,
    curve_segments: int = 8,
    color: tuple = (1.0, 1.0, 1.0),
) -> bpy.types.Object:
    """
    Seamless cyclorama: flat floor + curved back wall with no visible corner.
    Built programmatically via bmesh.

    Segments: floor = 1 segment; back wall = curve_segments; no seam visible.
    """
    import math

    mesh = bpy.data.meshes.new("Forge_Cyclorama")
    obj  = bpy.data.objects.new("Forge_Cyclorama", mesh)
    bpy.data.scenes[0].collection.objects.link(obj)

    bm = bmesh.new()

    # Floor verts (front to back: y = depth/2 to 0)
    floor_verts = [
        bm.verts.new((-width/2, -depth/2, 0)),
        bm.verts.new(( width/2, -depth/2, 0)),
        bm.verts.new(( width/2,  0,       0)),
        bm.verts.new((-width/2,  0,       0)),
    ]
    bm.faces.new(floor_verts)

    # Curved back wall (arc from z=0 to z=height)
    prev_row = [floor_verts[2], floor_verts[3]]
    r = height * 0.6   # radius of curvature
    for i in range(1, curve_segments + 1):
        angle = math.radians(90.0 * i / curve_segments)
        z = r - r * math.cos(angle)
        y = r * math.sin(angle)
        new_row = [
            bm.verts.new(( width/2, y, z)),
            bm.verts.new((-width/2, y, z)),
        ]
        bm.faces.new([prev_row[0], prev_row[1], new_row[1], new_row[0]])
        prev_row = new_row

    bm.to_mesh(mesh)
    bm.free()

    # Material
    mat = bpy.data.materials.new("Forge_CycloramaMat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs['Base Color'].default_value = (*color, 1.0)
        bsdf.inputs['Roughness'].default_value = 1.0
    obj.data.materials.append(mat)

    # Subdivision for seamless curve
    sub = obj.modifiers.new("Subdivision", 'SUBSURF')
    sub.levels = 2

    return obj
```

---

## §3. Configuring Cycles for production

```python
import bpy


def configure_cycles_production(
    width: int = 2048,
    height: int = 2048,
    samples: int = 256,
    transparent_bg: bool = True,
    device: str = 'CPU',              # 'CPU' always works headless; 'GPU' needs prefs reset
    compute_type: str = 'OPTIX',      # 'OPTIX' | 'CUDA' | 'HIP'
    denoiser: str = 'OPENIMAGEDENOISE',
    use_light_tree: bool = True,      # REQUIRED for efficient light linking
):
    """
    Configure Cycles for final production renders.

    samples guide:
      64–128  → QA / iteration (~30 s on RTX 3080 at 2K)
      256     → standard product shot (~2 min)
      512–1024 → glass, caustics, jewellery (~8–15 min)

    GPU note:
      --factory-startup strips GPU device preferences.
      Even with device='GPU', you must re-apply compute_type + refresh_devices()
      (get_devices() on 3.x) in script.
      If GPU setup fails, CPU fallback is always available — set device='CPU' for CI.

    light_tree:
      use_light_tree=True is required for efficient light linking.
      Without it, Cycles falls back to rejection sampling: 10× more noisy,
      requiring many more samples to converge. Default True in Blender 4.x — verify.
    """
    scene = bpy.data.scenes[0]
    scene.render.engine = 'CYCLES'
    scene.render.resolution_x = width
    scene.render.resolution_y = height
    scene.render.resolution_percentage = 100
    scene.render.film_transparent = transparent_bg

    fmt = scene.render.image_settings
    fmt.file_format = 'PNG'
    fmt.color_mode = 'RGBA' if transparent_bg else 'RGB'
    fmt.color_depth = '16'   # 16-bit PNG for QA; 8-bit for web delivery

    cy = scene.cycles
    cy.samples = samples
    cy.use_denoising = True
    cy.denoiser = denoiser
    cy.use_light_tree = use_light_tree
    cy.device = device

    if device == 'GPU':
        try:
            prefs = bpy.context.preferences.addons['cycles'].preferences
            prefs.compute_device_type = compute_type
            # refresh_devices() is the Blender 4.x API; get_devices() is the 3.x fallback
            try:
                prefs.refresh_devices()
            except AttributeError:
                prefs.get_devices()
            for dev in prefs.devices:
                dev.use = True    # enable all available GPU tiles
            print(f"[forge-light] GPU ({compute_type}) configured.")
        except Exception as e:
            print(f"[forge-light] GPU setup failed ({e}), falling back to CPU.")
            cy.device = 'CPU'

    # Shadow catcher pass
    scene.view_layers[0].cycles.use_pass_shadow_catcher = True
```

---

## §4. Shadow catcher gotchas and fixes

**G — Transparent PNG renders as solid black**

Cause: `film_transparent = True` but `color_mode = 'RGB'` — alpha channel is discarded.
Fix:
```python
scene.render.film_transparent = True
scene.render.image_settings.color_mode = 'RGBA'   # required
scene.render.image_settings.file_format = 'PNG'   # or OPEN_EXR (also supports alpha)
```

**G — Shadow catcher plane colour-casts product underside**

Cause: The diffuse material on the shadow catcher plane bounces light onto the product.
Fix (pure packshot):
```python
plane.visible_diffuse = False
plane.visible_glossy  = False
# visible_shadow stays True — that's what shows the shadow
```

**G — Light linking 10× slower with shadow catcher**

Cause: `use_light_tree = False` forces rejection sampling for light linking.
Fix: `scene.cycles.use_light_tree = True` — verify it is set; it's default True in 4.x
but can be unset in old `.blend` files.

**G — Shadow catcher not rendering (appears as object, not shadow)**

Cause: `plane.cycles.is_shadow_catcher` is False (it's on the object, not material).
Fix: Check and set on the OBJECT:
```python
plane.cycles.is_shadow_catcher = True
```

**G — GPU device type is NONE after `--factory-startup`**

Detect: `bpy.context.preferences.addons['cycles'].preferences.compute_device_type == 'NONE'`
Fix: Always re-set GPU device type in the script body after `--factory-startup`:
```python
prefs = bpy.context.preferences.addons['cycles'].preferences
prefs.compute_device_type = 'OPTIX'   # or CUDA, HIP
# refresh_devices() is the Blender 4.x API; get_devices() is the 3.x fallback
try:
    prefs.refresh_devices()
except AttributeError:
    prefs.get_devices()
for d in prefs.devices:
    d.use = True
```
