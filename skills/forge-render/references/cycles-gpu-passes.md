# forge-render — Cycles GPU, Render Settings & Passes Reference

## Contents
- §GPU. GPU device activation (headless Windows)
- §settings. Render settings (resolution, samples, color management)
- §passes. Enabling render passes / AOVs
- §normals. Normal pass: world-space → PNG remap
- §compositor. Compositor node setup (multi-output EXR)
- §gotchas. Gotcha → fix table

---

## §GPU. GPU device activation (headless Windows)

GPU devices are NOT auto-detected at headless startup. Always call `refresh_devices()`
before setting `cycles.device = 'GPU'`.

```python
# forge_gpu_setup.py — call this function at the top of any Cycles render script
import bpy

def activate_cycles_gpu(prefer: str = "OPTIX") -> str:
    """
    Activate Cycles GPU devices. Falls back to CPU if none found.
    prefer: "OPTIX" (NVIDIA RTX, best), "CUDA" (older NVIDIA), "HIP" (AMD), "ONEAPI" (Intel Arc)
    Returns the string "GPU" or "CPU" so caller can set scene.cycles.device.
    """
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"

    prefs = bpy.context.preferences.addons["cycles"].preferences

    # Step 1: try preferred backend; fall back through the list
    for backend in (prefer, "OPTIX", "CUDA", "HIP", "ONEAPI", "NONE"):
        try:
            prefs.compute_device_type = backend
            break
        except TypeError:
            continue

    # Step 2: enumerate devices (REQUIRED — Blender won't see them otherwise)
    # Blender 4.x: refresh_devices() replaces deprecated get_devices()
    try:
        prefs.refresh_devices()
    except AttributeError:
        prefs.get_devices()   # Blender 3.x fallback

    # Step 3: enable all non-CPU devices of the selected backend
    non_cpu_found = False
    for d in prefs.devices:
        if d.type != "CPU":
            d.use = True
            non_cpu_found = True
            print(f"[Forge] GPU device enabled: {d.name!r} (type={d.type})")
        # Optionally enable CPU alongside GPU (comment out if unwanted):
        # else: d.use = True

    if non_cpu_found:
        scene.cycles.device = "GPU"
        print(f"[Forge] Cycles backend: {prefs.compute_device_type}, device: GPU")
        return "GPU"
    else:
        scene.cycles.device = "CPU"
        print("[Forge] No GPU found — falling back to CPU.")
        return "CPU"
```

**Diagnostic block** — add to every render script for console confirmation:
```python
scene = bpy.context.scene
prefs = bpy.context.preferences.addons["cycles"].preferences
print(f"[Forge] Engine:  {scene.render.engine}")
print(f"[Forge] Device:  {scene.cycles.device}")
print(f"[Forge] Backend: {prefs.compute_device_type}")
print(f"[Forge] Res:     {scene.render.resolution_x}×{scene.render.resolution_y}")
print(f"[Forge] Samples: {scene.cycles.samples}")
print(f"[Forge] Denoise: {scene.cycles.use_denoising} ({scene.cycles.denoiser})")
print(f"[Forge] Output:  {scene.render.filepath}")
```

**Windows GPU TDR timeout fix** (if heavy Cycles renders crash with "driver lost connection"):
- Registry: `HKLM\System\CurrentControlSet\Control\GraphicsDrivers\TdrDelay` → DWORD → 60 (seconds). Requires reboot.
- Or: reduce `scene.cycles.tile_size` to 512 instead of 2048.

---

## §settings. Render settings

```python
# forge_render_settings.py — complete render settings reference
import bpy

scene = bpy.context.scene
render = scene.render

# ── Resolution ────────────────────────────────────────────────────────────────
render.resolution_x          = 1920
render.resolution_y          = 1080
render.resolution_percentage = 100   # 50 for half-res QA, 25 for ultra-fast QA

# ── Output format ─────────────────────────────────────────────────────────────
render.image_settings.file_format   = "PNG"   # PNG | OPEN_EXR | OPEN_EXR_MULTILAYER | JPEG
render.image_settings.color_mode    = "RGBA"  # RGB | RGBA (for transparent bg)
render.image_settings.color_depth   = "8"     # '8' for QA, '16' for production
render.image_settings.compression   = 15      # PNG compression 0-100 (higher = smaller)
render.filepath                     = "C:/forge/out/frame_####"  # #### = zero-padded frame
render.use_file_extension           = True    # appends .png automatically

# ── Transparent background ────────────────────────────────────────────────────
render.film_transparent = True    # alpha = transparency (not black); works in both Cycles + Workbench

# ── Performance ───────────────────────────────────────────────────────────────
render.use_persistent_data = True   # reuse BVH across frames — big win for multi-frame renders

# ── Cycles samples ────────────────────────────────────────────────────────────
cycles = scene.cycles
cycles.samples                 = 128    # path-trace samples per pixel
cycles.use_adaptive_sampling   = True   # stop early when noise < threshold
cycles.adaptive_threshold      = 0.01  # 1% noise tolerance
cycles.adaptive_min_samples    = 32    # minimum even with adaptive

# ── Cycles denoising ─────────────────────────────────────────────────────────
cycles.use_denoising           = True
cycles.denoiser                = "OPTIX"       # "OPTIX" (NVIDIA RTX) | "OPENIMAGEDENOISE" (CPU/AMD)
for vl in scene.view_layers:
    vl.cycles.use_denoising = True             # BOTH must be set — see §gotchas G7

# ── Cycles tiles (Blender 3.0+ API) ──────────────────────────────────────────
cycles.use_auto_tile = True          # let Blender choose tile size (recommended)
cycles.tile_size     = 2048          # used only when use_auto_tile = False; GPU optimal: 2048

# ── Cycles light paths (reduce for faster QA) ────────────────────────────────
cycles.max_bounces              = 12   # total bounces
cycles.diffuse_bounces          = 4
cycles.glossy_bounces           = 4
cycles.transmission_bounces     = 12
cycles.volume_bounces           = 0
cycles.transparent_max_bounces  = 8

# ── PRESET: QA (very fast, acceptable noise for geometry inspection) ──────────
def set_qa_mode(scene):
    scene.render.resolution_percentage = 50
    scene.cycles.samples                = 16
    scene.cycles.use_adaptive_sampling  = False
    scene.cycles.use_denoising          = False
    scene.cycles.max_bounces            = 4
    scene.cycles.diffuse_bounces        = 2
    scene.cycles.glossy_bounces         = 2
    scene.cycles.transmission_bounces   = 4

# ── PRESET: production still ──────────────────────────────────────────────────
def set_production_mode(scene):
    scene.render.resolution_percentage = 100
    scene.cycles.samples                = 256
    scene.cycles.use_adaptive_sampling  = True
    scene.cycles.adaptive_threshold     = 0.005
    scene.cycles.use_denoising          = True
    scene.cycles.denoiser               = "OPTIX"
    scene.cycles.max_bounces            = 12
```

### Color management

```python
# AgX (Blender 4.0+ default for new files) — best for photorealistic renders
scene.view_settings.view_transform  = "AgX"
scene.view_settings.look            = "None"  # or "AgX - Punchy", "AgX - High Contrast"
scene.view_settings.exposure        = 0.0
scene.view_settings.gamma           = 1.0
scene.display_settings.display_device = "sRGB"  # must be set for correct PNG inspection

# Never use "Standard" or "Raw" for PNG QA renders — no tone mapping, colors clip.
# For EXR archival use view_transform = "Raw" (EXR is always linear, no baking).
```

---

## §passes. Enabling render passes / AOVs

All pass toggles live on `bpy.context.view_layer`. Enable BEFORE `bpy.ops.render.render()`.

```python
# forge_passes_enable.py
import bpy

scene = bpy.context.scene
vl    = bpy.context.view_layer
scene.render.engine = "CYCLES"  # Passes availability: Cycles > EEVEE > Workbench

# ── DATA PASSES (Cycles + EEVEE) ─────────────────────────────────────────────
vl.use_pass_combined           = True   # Beauty render (always on)
vl.use_pass_z                  = True   # Depth — raw Z in Blender units, unbounded float
vl.use_pass_mist               = True   # Depth normalized [0,1] via World mist settings — prefer this
vl.use_pass_normal             = True   # World-space normals, range [-1,1] encoded in RGB
vl.use_pass_position           = True   # World-space XYZ position
vl.use_pass_vector             = False  # Motion vectors — disable when Motion Blur is ON (they zero out)
vl.use_pass_uv                 = True   # UV coordinates (Cycles only in 4.2)

# ── LIGHT PASSES (Cycles only) ────────────────────────────────────────────────
vl.use_pass_diffuse_direct     = True   # Direct diffuse irradiance
vl.use_pass_diffuse_indirect   = True   # Indirect diffuse (GI)
vl.use_pass_diffuse_color      = True   # Diffuse albedo (BSDF color)
vl.use_pass_glossy_direct      = True
vl.use_pass_glossy_indirect    = True
vl.use_pass_glossy_color       = True
vl.use_pass_emit               = True   # Emission (self-illumination)
vl.use_pass_environment        = True   # World/HDRI background contribution
vl.use_pass_ambient_occlusion  = True   # AO grayscale [0=occluded, 1=open]

# ── CRYPTOMATTE (Cycles + EEVEE 4.2+) ────────────────────────────────────────
vl.use_pass_cryptomatte_object   = True
vl.use_pass_cryptomatte_material = True
vl.pass_cryptomatte_depth        = 2    # Each +2 adds one more CryptoObject socket

# ── DENOISING DATA (required for compositor Denoise node) ────────────────────
vl.cycles.denoising_store_passes = True  # Stores Denoising Albedo + Denoising Normal

# ── CUSTOM AOVs (max 16 Color + 16 Value per scene) ──────────────────────────
aov = vl.aovs.add()
aov.name = "roughness_debug"
aov.type = "VALUE"   # "COLOR" for RGB, "VALUE" for float
# Then in the material: add ShaderNodeOutputAOV, set name to "roughness_debug"
# The compositor RenderLayers node exposes the socket automatically after AOV registration.
```

**Pass selection discipline:** enable only passes needed for the current QA goal.
- QA contact sheet: Combined + Normal + Mist + AO + Wireframe (separate Workbench render)
- Shader debugging: add diffuse/glossy decomposition passes
- Full production archive: all passes above → multilayer EXR

---

## §normals. Normal pass: world-space → PNG remap

World-space normals are in `[-1, 1]`. To visualize as RGB in a PNG, remap to `[0, 1]`:
`png_value = (normal * 0.5) + 0.5`

**Do NOT use CompositorNodeNormalize** — it rescales to the pixel min/max, not to `[-1,1]`.

```python
# In compositor, after enabling vl.use_pass_normal = True:
scene.use_nodes = True
tree  = scene.node_tree
nodes = tree.nodes
links = tree.links
nodes.clear()

rl  = nodes.new("CompositorNodeRLayers");  rl.location  = (-400, 0)

# Multiply by 0.5 (scale from [-1,1] to [-0.5, 0.5])
mul = nodes.new("CompositorNodeMixRGB");   mul.location = (-100, 0)
mul.blend_type = "MULTIPLY";              mul.inputs[0].default_value = 1.0
mul.inputs[2].default_value = (0.5, 0.5, 0.5, 1.0)

# Add 0.5 (shift from [-0.5, 0.5] to [0, 1])
add = nodes.new("CompositorNodeMixRGB");   add.location = (150, 0)
add.blend_type = "ADD";                   add.inputs[0].default_value = 1.0
add.inputs[2].default_value = (0.5, 0.5, 0.5, 0.0)

# File output → PNG
fo = nodes.new("CompositorNodeOutputFile"); fo.location = (400, 0)
fo.base_path = "C:/forge/out/normals"
fo.format.file_format = "PNG"
fo.layer_slots.clear(); fo.layer_slots.new("normals_")

# Composite node (required — prevents blank main output)
comp = nodes.new("CompositorNodeComposite"); comp.location = (400, -200)

links.new(rl.outputs["Normal"],   mul.inputs[1])
links.new(mul.outputs["Image"],   add.inputs[1])
links.new(add.outputs["Image"],   fo.inputs["normals_"])
links.new(rl.outputs["Image"],    comp.inputs["Image"])   # beauty to composite

# Cycles: 1 sample is enough for normals (deterministic per-pixel, no noise)
scene.cycles.samples = 1
scene.cycles.use_denoising = False
```

**Visual interpretation of the normal PNG:**
- Facing-camera surfaces → blue-purple tones (normal toward viewer ≈ +Z in world)
- Abrupt color reversal (red next to cyan) → face normal discontinuity (flipped normal)
- Smooth color gradients across a surface → correct topology

---

## §compositor. Compositor node setup (multi-output EXR)

```python
# forge_compositor_multiout.py
# Writes: beauty PNG (for QA inspection) + multilayer EXR (for archival/re-compositing)
# CRITICAL: scene.render.filepath MUST differ from fo.base_path or they overwrite each other
import bpy, os

scene = bpy.context.scene
scene.use_nodes = True
scene.render.use_compositing = True

tree  = scene.node_tree
nodes = tree.nodes
links = tree.links
nodes.clear()

OUT_DIR = "C:/forge/out"
os.makedirs(OUT_DIR, exist_ok=True)

# ── Source ────────────────────────────────────────────────────────────────────
rl = nodes.new("CompositorNodeRLayers"); rl.location = (-600, 0); rl.scene = scene

# ── Denoise node (Cycles; requires vl.cycles.denoising_store_passes = True) ──
denoise = nodes.new("CompositorNodeDenoise"); denoise.location = (-200, 200)
denoise.use_hdr    = True         # preserve HDR range
denoise.prefilter  = "ACCURATE"   # NONE | FAST | ACCURATE
links.new(rl.outputs["Image"],            denoise.inputs["Image"])
links.new(rl.outputs["Denoising Normal"], denoise.inputs["Normal"])
links.new(rl.outputs["Denoising Albedo"], denoise.inputs["Albedo"])

# ── PNG output (for Read/inspect) ─────────────────────────────────────────────
png_fo = nodes.new("CompositorNodeOutputFile"); png_fo.location = (200, 200)
png_fo.label      = "PNG_Inspect"
png_fo.base_path  = OUT_DIR + "/inspect"
png_fo.format.file_format  = "PNG"
png_fo.format.color_mode   = "RGBA"
png_fo.format.color_depth  = "8"
png_fo.layer_slots.clear(); png_fo.layer_slots.new("beauty_")
links.new(denoise.outputs["Image"], png_fo.inputs["beauty_"])

# ── Multilayer EXR output (archival) ──────────────────────────────────────────
exr_fo = nodes.new("CompositorNodeOutputFile"); exr_fo.location = (200, -200)
exr_fo.label     = "EXR_Multilayer"
exr_fo.base_path = OUT_DIR + "/exr"   # DIFFERENT from scene.render.filepath + inspect
exr_fo.format.file_format = "OPEN_EXR_MULTILAYER"
exr_fo.format.exr_codec   = "ZIP"     # ZIPS for random access; PIZ for noisy data
exr_fo.format.color_depth = "32"      # full float; use '16' for Z pass to save space
exr_fo.layer_slots.clear()

# Wire raw passes to EXR slots
pass_map = {
    "Image":   "beauty_raw",
    "Normal":  "normal",
    "Mist":    "mist",
    "AO":      "ao",
    "DiffDir": "diff_direct",
    "DiffInd": "diff_indirect",
    "DiffCol": "diff_color",
    "Emit":    "emission",
}
for src_socket, slot_name in pass_map.items():
    if src_socket in rl.outputs and rl.outputs[src_socket].enabled:
        exr_fo.layer_slots.new(slot_name)
        links.new(rl.outputs[src_socket], exr_fo.inputs[slot_name])

# ── Composite node (required — prevents blank beauty output) ──────────────────
comp = nodes.new("CompositorNodeComposite"); comp.location = (200, -500)
links.new(denoise.outputs["Image"], comp.inputs["Image"])

# ── Scene main output: must be on a DIFFERENT path from fo.base_path ──────────
scene.render.filepath = OUT_DIR + "/combined_####"
scene.render.image_settings.file_format = "PNG"
```

**EXR codec guide:**
| Codec | Best for | Random access |
|---|---|---|
| `ZIPS` | Per-frame QA | Fast |
| `ZIP` | Archival (better compression) | Moderate |
| `PIZ` | Noisy Cycles renders | Good |
| `NONE` | Scratch / temp files | Fastest write |

---

## §gotchas. Gotcha → fix table

| # | Symptom | Root cause | Fix |
|---|---|---|---|
| G1 | `render.opengl.poll() failed` in headless | `bpy.ops.render.opengl()` requires a GUI window | Use `bpy.ops.render.render(write_still=True)` only; for wireframe use `BLENDER_WORKBENCH` |
| G2 | Two EXR files overwrite each other | `scene.render.filepath` and `fo.base_path` resolve to same filename | Always set them to different directory stems |
| G3 | `rl.outputs['Normal']` KeyError or disabled | Pass enabled AFTER compositor built, or wrong view layer | Enable all passes before building compositor; check `rl.layer` name |
| G4 | Denoise node outputs black | `denoising_store_passes` not set; or inputs not connected; or EEVEE engine | Set `vl.cycles.denoising_store_passes = True`; connect all 3 Denoise node inputs |
| G5 | Windows path separator issue in EXR | Backslash in `fo.base_path` confuses Blender's path parser | Use `Path(OUT_DIR).as_posix()` or replace `\\` with `/` |
| G6 | Vector pass all zeros | Motion Blur enabled, or frame 1 of animation (no prior frame) | Disable Motion Blur when Vector pass needed |
| G7 | Denoise applied globally but render still noisy | `scene.cycles.use_denoising = True` set but `vl.cycles.use_denoising` not set | Both must be True; loop `for vl in scene.view_layers: vl.cycles.use_denoising = True` |
| G8 | `scene.cycles.tile_x`/`tile_y` AttributeError | Pre-3.0 API; removed in Blender 3.0 | Use `cycles.tile_size` + `cycles.use_auto_tile` |
| G9 | `camera_fit_coords` returns wrong scale | Called without evaluated depsgraph | `depsgraph = bpy.context.evaluated_depsgraph_get()` before calling |
| G10 | `scene.cycles.compute_device_type` AttributeError | Wrong attribute location | It lives on `bpy.context.preferences.addons["cycles"].preferences`, not on `scene.cycles` |
| G11 | AO pass all white (EEVEE) | `vl.use_ao` not set | `vl.use_ao = True` in addition to `vl.use_pass_ambient_occlusion = True` |
| G12 | Mist pass all white or black | World mist start/depth not configured | `world.mist_settings.start = 0.5; world.mist_settings.depth = 25.0` |
| G13 | `BLENDER_EEVEE` engine string silently fails | Removed in Blender 4.2 | Use `BLENDER_EEVEE_NEXT` (but still unsupported headless on Windows) |
| G14 | GPU still renders on CPU headless | `get_devices()` / `refresh_devices()` not called after setting `compute_device_type` | Always call `prefs.refresh_devices()` immediately after setting the backend |
| G15 | `write_still` missing, no PNG written | `bpy.ops.render.render()` renders but does not write without the flag | Always: `bpy.ops.render.render(write_still=True)` |
