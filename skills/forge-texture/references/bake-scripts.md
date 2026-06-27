# Forge Texture — Bake Scripts Reference

Copy-paste ready bpy Python patterns for all standard bake types.
All scripts assume Blender 4.1–5.2 LTS. Run with:
  `blender --background scene.blend --python script.py --python-exit-code 1 -- <args>`

Advanced topics (UDIM workaround, full PowerShell pipeline, sys.argv, gotcha table):
**`references/bake-advanced.md`**

## Contents
- §1. Shared helpers (assign/remove bake image node, GPU setup)
- §2. High-poly → Low-poly bake (Selected-to-Active)
- §3. Multires sculpt → Normal map
- §4. AO bake
- §5. Curvature bake (Geometry Pointiness → EMIT)
- §6. Roughness / Metallic via Emission trick (brief summary; full pattern in bake-advanced §2)

---

## §1. Shared Helpers

```python
import bpy, os, sys

def setup_cycles(samples: int = 64, prefer_gpu: bool = True) -> str:
    """Set Cycles as render engine and probe for GPU. Returns 'GPU' or 'CPU'."""
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples

    if not prefer_gpu:
        scene.cycles.device = "CPU"
        return "CPU"

    prefs = bpy.context.preferences.addons["cycles"].preferences
    for device_type in ("OPTIX", "CUDA", "HIP", "ONEAPI"):
        try:
            prefs.compute_device_type = device_type
            prefs.refresh_devices()        # REQUIRED — devices list is empty without this
            gpu_devs = [d for d in prefs.devices if d.type != "CPU"]
            if gpu_devs:
                for d in prefs.devices:
                    d.use = (d.type != "CPU")
                scene.cycles.device = "GPU"
                print(f"[forge] GPU: {device_type}")
                return "GPU"
        except (TypeError, AttributeError):
            continue

    scene.cycles.device = "CPU"
    print("[forge] No GPU; CPU fallback")
    return "CPU"


def assign_bake_image_node(obj: bpy.types.Object, img: bpy.types.Image) -> None:
    """Add a selected+active Image Texture node targeting img to every material slot."""
    for slot in obj.material_slots:
        mat = slot.material
        if mat is None:
            continue
        if not mat.use_nodes:
            mat.use_nodes = True
        nodes = mat.node_tree.nodes
        for n in nodes:
            n.select = False
        tex = nodes.new("ShaderNodeTexImage")
        tex["forge_bake_node"] = True
        tex.image = img
        tex.select = True
        nodes.active = tex   # active node = bake target; NOT wired into any socket


def remove_bake_image_nodes(obj: bpy.types.Object) -> None:
    """Clean up temporary bake target nodes tagged forge_bake_node."""
    for slot in obj.material_slots:
        mat = slot.material
        if mat and mat.use_nodes:
            for n in [n for n in mat.node_tree.nodes if n.get("forge_bake_node")]:
                mat.node_tree.nodes.remove(n)


def make_bake_image(name: str, resolution: int, colorspace: str = "Non-Color",
                    float_buffer: bool = False) -> bpy.types.Image:
    """Create (or replace) a blank image for use as a bake target."""
    if name in bpy.data.images:
        bpy.data.images.remove(bpy.data.images[name])
    img = bpy.data.images.new(name, resolution, resolution,
                               alpha=False, float_buffer=float_buffer)
    img.colorspace_settings.name = colorspace
    return img


def save_image(img: bpy.types.Image, out_path: str,
               fmt: str = "PNG") -> None:
    """Save baked image to disk. Use forward slashes in out_path (Windows safe)."""
    img.file_format = fmt
    img.filepath_raw = out_path   # forward slashes; never raw backslashes
    img.save()
    print(f"[forge] Saved: {out_path}")
```

---

## §2. High-poly → Low-poly Bake (Selected-to-Active)

```python
def bake_highpoly_to_lowpoly(
    highpoly_names: list[str],
    lowpoly_name: str,
    bake_type: str,           # 'NORMAL', 'AO', 'DIFFUSE', 'EMIT', etc.
    out_path: str,
    resolution: int = 2048,
    samples: int = 64,
    cage_extrusion: float = 0.02,   # 1-2% of bounding box longest axis
    max_ray_distance: float = 0.0,  # 0 = use extrusion only
    use_cage: bool = False,
    cage_obj_name: str = None,
    margin_px: int = 16,
    normal_space: str = "TANGENT",  # 'TANGENT' or 'OBJECT'
    normal_g: str = "POS_Y",        # 'POS_Y'=OpenGL / 'NEG_Y'=DirectX/Unreal
) -> bpy.types.Image:
    """
    Bake from one or more high-poly sources onto a low-poly mesh.
    Selection protocol: all high-polys selected; low-poly is ACTIVE.
    """
    setup_cycles(samples)

    # Color space: sRGB for color maps, Non-Color for data maps
    color_maps = {"DIFFUSE", "EMIT", "COMBINED", "ENVIRONMENT"}
    colorspace = "sRGB" if bake_type in color_maps else "Non-Color"

    img_name = f"{lowpoly_name}_{bake_type.lower()}"
    img = make_bake_image(img_name, resolution, colorspace)

    lowpoly = bpy.data.objects[lowpoly_name]
    assign_bake_image_node(lowpoly, img)

    # Selection: high-polys selected; low-poly is active
    bpy.ops.object.select_all(action="DESELECT")
    for name in highpoly_names:
        hp = bpy.data.objects[name]
        hp.hide_set(False)
        hp.hide_render = False
        hp.select_set(True)
    lowpoly.hide_set(False)
    lowpoly.hide_render = False
    lowpoly.select_set(True)
    bpy.context.view_layer.objects.active = lowpoly

    # Bake settings
    bake = bpy.context.scene.render.bake
    bake.use_selected_to_active = True
    bake.use_cage               = use_cage
    bake.cage_extrusion         = cage_extrusion
    bake.max_ray_distance       = max_ray_distance if not use_cage else 0.0
    bake.margin                 = margin_px
    bake.margin_type            = "EXTEND"
    bake.use_clear              = True

    if cage_obj_name and use_cage:
        bake.cage_object = bpy.data.objects[cage_obj_name]

    if bake_type == "NORMAL":
        bake.normal_space = normal_space
        bake.normal_r = "POS_X"
        bake.normal_g = normal_g
        bake.normal_b = "POS_Z"
    elif bake_type == "DIFFUSE":
        bake.use_pass_direct   = False
        bake.use_pass_indirect = False
        bake.use_pass_color    = True

    bpy.ops.object.bake(type=bake_type)

    save_image(img, out_path)
    remove_bake_image_nodes(lowpoly)
    return img
```

---

## §3. Multires Sculpt → Normal Map

```python
def bake_normal_from_multires(
    obj_name: str,
    out_path: str,
    resolution: int = 2048,
    samples: int = 16,
    normal_g: str = "POS_Y",   # 'NEG_Y' for Unreal/DX
) -> bpy.types.Image:
    """
    Bake tangent-space normal from a Multires modifier.
    Multires viewport level = low-poly base; render level = sculpt detail.
    The modifier must already be configured (levels set appropriately).
    """
    setup_cycles(samples)

    obj = bpy.data.objects[obj_name]
    img_name = f"{obj_name}_normal_multires"
    img = make_bake_image(img_name, resolution, "Non-Color")

    assign_bake_image_node(obj, img)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bake = bpy.context.scene.render.bake
    bake.use_selected_to_active = False
    bake.use_multires            = True
    bake.normal_space            = "TANGENT"
    bake.normal_r                = "POS_X"
    bake.normal_g                = normal_g
    bake.normal_b                = "POS_Z"
    bake.margin                  = 16
    bake.margin_type             = "EXTEND"

    bpy.ops.object.bake(type="NORMAL")

    save_image(img, out_path)
    remove_bake_image_nodes(obj)
    return img
```

---

## §4. AO Bake

```python
def bake_ao(
    obj_name: str,
    out_path: str,
    resolution: int = 2048,
    samples: int = 128,        # AO is stochastic; 128 minimum, 256 recommended
    ao_distance: float = 1.0,  # World AO probe distance in meters
) -> bpy.types.Image:
    """
    Bake ambient occlusion. AO ignores all lights; uses World AO settings.
    Denoiser does NOT apply to AO — use higher samples instead.
    """
    setup_cycles(samples)

    scene = bpy.context.scene
    if scene.world and hasattr(scene.world, "light_settings"):
        scene.world.light_settings.distance = ao_distance

    obj = bpy.data.objects[obj_name]
    img = make_bake_image(f"{obj_name}_ao", resolution, "Non-Color")

    assign_bake_image_node(obj, img)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bake = scene.render.bake
    bake.use_selected_to_active = False
    bake.margin                  = 16
    bake.margin_type             = "EXTEND"
    bake.use_clear               = True

    bpy.ops.object.bake(type="AO")
    save_image(img, out_path)
    remove_bake_image_nodes(obj)
```

---

## §5. Curvature Bake (Geometry Pointiness → EMIT)

Blender has no native CURVATURE bake type. Extract from `Geometry > Pointiness` via ColorRamp and
bake as EMIT. Sample count of 1 suffices — Emission is deterministic.

```python
def bake_curvature(
    obj_name: str,
    out_path: str,
    resolution: int = 2048,
    ramp_low: float = 0.4,    # concave clamping threshold
    ramp_high: float = 0.6,   # convex clamping threshold
) -> bpy.types.Image:
    """
    Grey=flat, black=concave, white=convex.
    Creates a temporary 'forge_curvature_mat', bakes EMIT (1 sample), removes it.
    """
    setup_cycles(samples=1)

    obj = bpy.data.objects[obj_name]

    # Build temporary curvature material
    mat_name = "forge_curvature_mat"
    if mat_name in bpy.data.materials:
        bpy.data.materials.remove(bpy.data.materials[mat_name])
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    geo    = nodes.new("ShaderNodeNewGeometry")
    ramp   = nodes.new("ShaderNodeValToRGB")
    emit   = nodes.new("ShaderNodeEmission")
    out    = nodes.new("ShaderNodeOutputMaterial")
    target = nodes.new("ShaderNodeTexImage")

    ramp.color_ramp.elements[0].position = ramp_low
    ramp.color_ramp.elements[1].position = ramp_high

    img = make_bake_image(f"{obj_name}_curvature", resolution, "Non-Color")
    target.image = img
    target.select = True
    nodes.active = target     # bake target

    links.new(ramp.inputs["Fac"],    geo.outputs["Pointiness"])
    links.new(emit.inputs["Color"],  ramp.outputs["Color"])
    links.new(out.inputs["Surface"], emit.outputs["Emission"])

    # Temporarily replace all materials
    original_mats = [slot.material for slot in obj.material_slots]
    obj.data.materials.clear()
    obj.data.materials.append(mat)

    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj

    bpy.context.scene.render.bake.margin = 8
    bpy.ops.object.bake(type="EMIT")

    save_image(img, out_path)

    # Restore materials
    obj.data.materials.clear()
    for m in original_mats:
        if m:
            obj.data.materials.append(m)
    bpy.data.materials.remove(mat)
```

---

## §6. Roughness / Metallic via Emission Trick

The native `ROUGHNESS` and `METALLIC` bake types are unreliable with Principled BSDF in Blender 4.x.
Route the socket → Emission → Surface output, bake as `EMIT`, then restore the original wiring.

**Pattern (condensed — implement for any scalar BSDF input):**
```python
# 1. Create bake image (Non-Color, 1024x1024, 4 samples sufficient for scalar data)
img = make_bake_image(f"{obj.name}_roughness", 1024, "Non-Color")

# 2. Add Image Texture node as active bake target
img_node = nodes.new("ShaderNodeTexImage")
img_node.image = img; img_node.select = True; nodes.active = img_node

# 3. Temporarily wire: [Roughness upstream] → Emission.Color
#                       Emission.Emission  → Output.Surface
emit = nodes.new("ShaderNodeEmission")
src  = pbsdf.inputs["Roughness"].links[0].from_socket  # the upstream node
links.new(emit.inputs["Color"],      src)
links.remove(out.inputs["Surface"].links[0])           # disconnect BSDF
links.new(out.inputs["Surface"],     emit.outputs["Emission"])

# 4. Bake
bpy.ops.object.bake(type="EMIT")
save_image(img, "C:/out/roughness.png")

# 5. Restore: remove temp nodes, reconnect BSDF
nodes.remove(emit); nodes.remove(img_node)
links.new(out.inputs["Surface"], pbsdf.outputs["BSDF"])
```

This pattern works for: "Roughness", "Metallic", "Specular IOR Level", "Anisotropic", "Sheen Weight",
and any other scalar Principled BSDF input that drives upstream procedural nodes.

---

## §7. Displacement / Position Maps

```python
# Position bake (Blender 4.1+) — save as EXR float32; PNG loses sub-pixel precision
scene.render.engine  = "CYCLES"
scene.cycles.samples = 1      # deterministic
bpy.ops.object.bake(type="POSITION")
img.file_format  = "OPEN_EXR"
img.filepath_raw = "C:/out/position.exr"
img.save()

# Displacement — use Emission trick (same as §6): wire Height socket → Emission → bake EMIT
# Save as 32-bit EXR; PNG clips sub-pixel displacements
img = make_bake_image("displacement", 2048, "Non-Color", float_buffer=True)
# [assign bake node, wire Emission, bake EMIT]
img.file_format  = "OPEN_EXR"
img.filepath_raw = "C:/out/displacement.exr"
img.save()
```

See **`references/bake-advanced.md`** for: UDIM tile-shift workaround, full PowerShell pipeline
script, sys.argv parsing, and Gotcha → Fix table (G1–G15).
