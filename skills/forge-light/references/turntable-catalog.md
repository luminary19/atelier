# forge-light — Turntable & Catalog Lighting Rig
# IBL + kicker for material QA + 360° animation setup

## Contents
- §1. Catalog lighting (IBL + kicker)
- §2. Turntable animation (rotate product, not camera)
- §3. Render turntable frames
- §4. Material read QA (metallic vs. diffuse vs. glass classification)

---

## §1. Catalog lighting (IBL + kicker)

For material QA and catalog renders. IBL provides neutral fill; kicker gives
a predictable specular highlight that moves as the product rotates.

```python
import bpy
from mathutils import Vector
import math


def build_catalog_lighting(
    center: Vector,
    radius: float,
    hdri_path: str = None,
    hdri_strength: float = 0.8,
    key_energy_w: float = 500.0,
):
    """
    Catalog / turntable lighting: HDRI dominant + single area kicker.
    IBL gives neutral fill from all angles; kicker provides specular cue.

    If hdri_path is None: falls back to three-point rig (no HDRI available).

    The kicker is placed at 45° front-right, above center — as the product
    rotates, the specular highlight sweeps in a predictable arc that correctly
    reveals metal/glass surface behavior.

    Kicker energy guide:
      Diffuse products: 200–400 W (barely visible; mainly for shadow definition)
      Metal / gloss:    400–800 W (clear specular sweep across the surface)
      Jewellery / gem: 800–1500 W (strong highlight for facet read)
    """
    if hdri_path:
        # load_hdri is defined in hdri-ibl.md references
        load_hdri(hdri_path, strength=hdri_strength, rotation_z_deg=0.0)
    else:
        # Fallback: three-point rig with fill dominant
        build_three_point_rig(center, radius,
                              key_energy_w=key_energy_w,
                              fill_ratio=0.5,
                              rim_ratio=0.4)
        return

    # Tight kicker — stays fixed in world space; product rotates under it
    kicker_loc = center + Vector((radius * 2.5, -radius * 2.5, radius * 2.0))
    make_area_light(
        'Forge_Kicker', kicker_loc,
        energy_w=key_energy_w,
        size_m=radius * 0.8,
        aim_at=center,
    )
```

---

## §2. Turntable animation (rotate product, not camera)

The correct pattern: parent product to an Empty pivot and rotate the pivot.
Do NOT rotate the camera. This keeps the IBL rotation fixed in world space,
so specular highlights sweep predictably as the product turns.

```python
def setup_turntable_animation(
    product_obj: bpy.types.Object,
    frame_start: int = 1,
    frame_end: int = 72,    # 72 frames at 24fps = 3 s = 5°/frame = full 360°
    fps: int = 24,
) -> bpy.types.Object:
    """
    Parent product to an Empty and keyframe 360° Z rotation.

    Returns the pivot Empty.

    Frame count → duration:
      24 frames = 1 s (fast preview, 15°/frame)
      48 frames = 2 s (standard product)
      72 frames = 3 s (smooth; 5°/frame)
      120 frames = 5 s (slow, cinematic)

    The LINEAR interpolation on the rotation curve ensures constant angular speed.
    """
    scene = bpy.data.scenes[0]
    scene.frame_start = frame_start
    scene.frame_end   = frame_end
    scene.render.fps  = fps

    # Create pivot empty at product origin
    bpy.ops.object.empty_add(type='PLAIN_AXES', location=product_obj.location)
    pivot = bpy.context.active_object
    pivot.name = "Forge_TurntablePivot"

    # Parent product to pivot (keep transform)
    product_obj.parent = pivot
    product_obj.matrix_parent_inverse = pivot.matrix_world.inverted()

    # Keyframe Z rotation: 0° at start, 360° at end
    scene.frame_set(frame_start)
    pivot.rotation_euler[2] = 0.0
    pivot.keyframe_insert(data_path='rotation_euler', index=2)

    scene.frame_set(frame_end)
    pivot.rotation_euler[2] = math.radians(360.0)
    pivot.keyframe_insert(data_path='rotation_euler', index=2)

    # Set LINEAR interpolation for constant angular speed
    for fc in pivot.animation_data.action.fcurves:
        for kp in fc.keyframe_points:
            kp.interpolation = 'LINEAR'

    return pivot
```

---

## §3. Render turntable frames

```python
def render_turntable_frames(
    output_dir: str,
    filename_pattern: str = "frame_####",   # #### = zero-padded frame number
):
    """
    Render all frames as individual PNGs (headless).
    Call AFTER setup_turntable_animation() and camera configuration.

    filename_pattern uses Blender's frame padding syntax:
      "frame_####" → frame_0001.png, frame_0072.png
      "turntable_##" → turntable_01.png (two-digit padding)
    """
    import os
    from pathlib import Path
    os.makedirs(output_dir, exist_ok=True)

    scene = bpy.data.scenes[0]
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.filepath = Path(output_dir).as_posix() + "/" + filename_pattern

    # animation=True renders all frames in range; write_still=True saves each frame
    bpy.ops.render.render(animation=True, write_still=True)
    print(f"[forge-light] Turntable frames saved to: {output_dir}")
```

**Invocation (Windows PowerShell):**
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe" `
    -b --factory-startup `
    -P "C:\forge\turntable_render.py" `
    -- "C:\assets\widget.glb" "C:\renders\turntable"
```

---

## §4. Material read QA (luminance variance across angles)

For material QA, render at 0°, 90°, 180° and compare luminance variance.
Metallic/gloss shows high variance; diffuse shows low variance.

```python
def verify_material_class(renders: dict) -> str:
    """
    Classify material from turntable frames at 0°, 90°, 180°.
    renders = {'0': '/path/frame_0001.png', '90': '/path/frame_0019.png', '180': '/path/frame_0037.png'}
    Returns: 'metallic' | 'diffuse' | 'glass' | 'unknown'

    Thresholds:
      variance > 0.15 → metallic/gloss (specular sweeps sharply as angle changes)
      variance < 0.05 → diffuse (near-constant luminance across angles)
      else            → semi-gloss or unclassified
    """
    from PIL import Image
    import numpy as np

    means = {}
    for angle, path in renders.items():
        img = np.array(Image.open(path).convert('RGB')).astype(np.float32) / 255.0
        lum = 0.2126 * img[:, :, 0] + 0.7152 * img[:, :, 1] + 0.0722 * img[:, :, 2]
        means[angle] = float(lum.mean())

    variance = max(means.values()) - min(means.values())
    print(f"[forge-light] Angle luminance means: {means}")
    print(f"[forge-light] Variance: {variance:.4f}")

    if variance > 0.15:
        return 'metallic'
    elif variance < 0.05:
        return 'diffuse'
    else:
        return 'unknown'
```

### Turntable render timing reference

| Frames | Duration at 24fps | Degrees/frame | Use |
|---|---|---|---|
| 24 | 1 s | 15° | Fast QA preview |
| 48 | 2 s | 7.5° | Standard product turntable |
| 72 | 3 s | 5° | Smooth product showcase |
| 120 | 5 s | 3° | Cinematic / jewellery |

For web delivery, pipe the PNG sequence through FFmpeg to MP4 or WebM after rendering.
See `forge-render` for the contact-sheet compositing step.
