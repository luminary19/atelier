"""
forge-render/scripts/render.py
Headless Blender render driver for the Forge suite.

Usage (PowerShell — run via Blender subprocess):
    blender -b --factory-startup --python-exit-code 1 -P render.py -- [OPTIONS]

Options (after the mandatory '--' separator):
    --input PATH         Mesh to import (.glb/.gltf/.fbx/.obj/.stl/.ply) or existing .blend path
    --out DIR            Output directory (created if absent)
    --mode MODE          beauty | turntable | 6view | wireframe | matcap | normals | uv | diagnostic | passes
    --engine ENGINE      CYCLES | BLENDER_WORKBENCH (default varies by mode)
    --device DEVICE      OPTIX | CUDA | HIP | CPU  (Cycles only; default tries OPTIX then CPU)
    --samples N          Cycles path-trace samples (default 64)
    --seed N             Cycles sampling seed (default 0 → byte-comparable rebuilds)
    --size WxH           Resolution e.g. 1024x1024 or just N for square (default 512)
    --n-angles N         Turntable frame count (default 12)
    --elev-deg F         Camera elevation in degrees (default 25.0)
    --no-transparent     Disable transparent background (default: transparent on)
    --no-clean           Keep prior outputs in --out (default: clear this skill's stems first)
    --json               Emit JSON summary to stdout instead of human-readable
    --qa                 Quick QA preset: 50% res, 16 samples, no denoise

Platform: Native Windows 11. forward-slash paths in scene.render.filepath always.
EEVEE Next is NOT supported headless on Windows — do not pass --engine BLENDER_EEVEE_NEXT.
"""

import sys
import io
import os
import bpy
import math
import json
import argparse
import pathlib
import mathutils

# UTF-8 stdout wrapper (Windows cp1252 default breaks non-ASCII console output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing (everything after the mandatory '--' separator)
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(
        description="forge-render headless Blender driver",
        add_help=False,
    )
    p.add_argument("--input",          default="")
    p.add_argument("--out",            default="C:/forge/out")
    p.add_argument("--mode",           default="turntable",
                   choices=["beauty", "turntable", "6view", "wireframe",
                             "matcap", "normals", "uv", "diagnostic", "passes"])
    p.add_argument("--engine",         default="")  # empty = auto-pick by mode
    p.add_argument("--device",         default="OPTIX",
                   choices=["OPTIX", "CUDA", "HIP", "ONEAPI", "CPU"])
    p.add_argument("--samples",        type=int, default=64)
    p.add_argument("--seed",           type=int, default=0,
                   help="Cycles sampling seed (default 0 → byte-comparable rebuilds)")
    p.add_argument("--size",           default="512")
    p.add_argument("--n-angles",       type=int, default=12)
    p.add_argument("--elev-deg",       type=float, default=25.0)
    p.add_argument("--no-transparent", action="store_true", default=False)
    p.add_argument("--no-clean",       action="store_true", default=False,
                   help="Keep prior outputs (default: clear this skill's output stems first)")
    p.add_argument("--json",           action="store_true", default=False)
    p.add_argument("--qa",             action="store_true", default=False)
    return p.parse_args(argv)


# ─────────────────────────────────────────────────────────────────────────────
# Resolution helpers
# ─────────────────────────────────────────────────────────────────────────────

def parse_resolution(size_str: str) -> tuple[int, int]:
    """Parse '512', '1920x1080', '1024x1024' → (w, h)."""
    if "x" in size_str or "X" in size_str:
        parts = size_str.lower().split("x")
        return int(parts[0]), int(parts[1])
    n = int(size_str)
    return n, n


# ─────────────────────────────────────────────────────────────────────────────
# GPU activation (Cycles headless — devices NOT auto-detected)
# ─────────────────────────────────────────────────────────────────────────────

def activate_cycles_gpu(prefer: str = "OPTIX") -> str:
    """
    Activate Cycles GPU devices. Falls back to CPU if none found.
    Returns "GPU" or "CPU".
    """
    prefs = bpy.context.preferences.addons["cycles"].preferences

    for backend in (prefer, "OPTIX", "CUDA", "HIP", "ONEAPI", "NONE"):
        try:
            prefs.compute_device_type = backend
            break
        except TypeError:
            continue

    # refresh_devices() is the Blender 4.x API; get_devices() is the 3.x fallback
    try:
        prefs.refresh_devices()
    except AttributeError:
        prefs.get_devices()

    non_cpu = False
    for d in prefs.devices:
        if d.type != "CPU":
            d.use = True
            non_cpu = True
            print(f"[forge-render] GPU enabled: {d.name!r} ({d.type})")

    if non_cpu and prefs.compute_device_type != "NONE":
        bpy.context.scene.cycles.device = "GPU"
        return "GPU"
    else:
        bpy.context.scene.cycles.device = "CPU"
        print("[forge-render] No GPU found — Cycles will use CPU.")
        return "CPU"


# ─────────────────────────────────────────────────────────────────────────────
# Scene bootstrap
# ─────────────────────────────────────────────────────────────────────────────

def reset_scene() -> None:
    bpy.ops.wm.read_factory_settings(use_empty=True)


def _import_obj(fwd: str) -> None:
    """OBJ import. Blender 4.x: wm.obj_import (C++); 3.x fallback: import_scene.obj."""
    if hasattr(bpy.ops.wm, "obj_import"):
        bpy.ops.wm.obj_import(filepath=fwd)
    else:
        bpy.ops.import_scene.obj(filepath=fwd)


def _import_stl(fwd: str) -> None:
    """STL import. Blender 4.2+: wm.stl_import (C++); older fallback: import_mesh.stl."""
    if hasattr(bpy.ops.wm, "stl_import"):
        bpy.ops.wm.stl_import(filepath=fwd)
    else:
        bpy.ops.import_mesh.stl(filepath=fwd)


def _import_ply(fwd: str) -> None:
    """PLY import. Blender 4.x: wm.ply_import (C++); 3.x fallback: import_mesh.ply."""
    if hasattr(bpy.ops.wm, "ply_import"):
        bpy.ops.wm.ply_import(filepath=fwd)
    else:
        bpy.ops.import_mesh.ply(filepath=fwd)


def import_mesh(input_path: str) -> list:
    """Import a mesh file and return the list of mesh objects added."""
    ext = pathlib.Path(input_path).suffix.lower()
    fwd = str(pathlib.Path(input_path).as_posix())  # forward slashes for Blender

    before = set(o.name for o in bpy.context.scene.objects)

    # glTF/FBX operator IDs are unchanged in 4.x; OBJ/STL/PLY moved to the
    # C++ wm.*_import operators (legacy import_scene.obj / import_mesh.* removed in 4.0/4.2).
    dispatch = {
        ".glb":  lambda: bpy.ops.import_scene.gltf(filepath=fwd),
        ".gltf": lambda: bpy.ops.import_scene.gltf(filepath=fwd),
        ".fbx":  lambda: bpy.ops.import_scene.fbx(filepath=fwd),
        ".obj":  lambda: _import_obj(fwd),
        ".stl":  lambda: _import_stl(fwd),
        ".ply":  lambda: _import_ply(fwd),
    }
    if ext not in dispatch:
        raise ValueError(f"[forge-render] Unsupported format: {ext}. "
                         f"Supported: {list(dispatch.keys())}")
    dispatch[ext]()

    new_objs = [o for o in bpy.context.scene.objects
                if o.name not in before and o.type == "MESH"]
    if not new_objs:
        raise RuntimeError(f"[forge-render] No mesh objects found after importing: {input_path}")
    print(f"[forge-render] Imported {len(new_objs)} mesh object(s) from {input_path}")
    return new_objs


def compute_bbox(meshes: list) -> tuple:
    """Return (centroid, diagonal, min_co, max_co) for a list of mesh objects."""
    corners = [obj.matrix_world @ mathutils.Vector(v)
               for obj in meshes for v in obj.bound_box]
    min_co = mathutils.Vector((min(c.x for c in corners),
                                min(c.y for c in corners),
                                min(c.z for c in corners)))
    max_co = mathutils.Vector((max(c.x for c in corners),
                                max(c.y for c in corners),
                                max(c.z for c in corners)))
    centroid = (min_co + max_co) / 2
    diagonal = (max_co - min_co).length
    return centroid, diagonal, min_co, max_co


# ─────────────────────────────────────────────────────────────────────────────
# Workbench setup helpers
# ─────────────────────────────────────────────────────────────────────────────

def setup_workbench(scene, res_w: int, res_h: int, transparent: bool = True) -> None:
    scene.render.engine                       = "BLENDER_WORKBENCH"
    scene.render.resolution_x                 = res_w
    scene.render.resolution_y                 = res_h
    scene.render.resolution_percentage        = 100
    scene.render.image_settings.file_format   = "PNG"
    scene.render.image_settings.color_mode    = "RGBA" if transparent else "RGB"
    scene.render.film_transparent             = transparent
    # Idempotent rebuilds: overwrite stale frames, never leave .png_ placeholders.
    scene.render.use_overwrite                = True
    scene.render.use_placeholder              = False
    d = scene.display.shading
    d.light       = "STUDIO"
    d.color_type  = "MATERIAL"
    d.show_cavity = True
    d.show_shadows = True


def apply_wireframe_shading(scene) -> None:
    d = scene.display.shading
    d.light                = "FLAT"
    d.color_type           = "SINGLE"
    d.single_color         = (0.6, 0.6, 0.6)
    d.show_wireframe       = True
    d.wireframe_color_type = "THEME"
    d.show_cavity          = False
    d.show_xray            = False


def apply_matcap_shading(scene) -> None:
    d = scene.display.shading
    d.light          = "MATCAP"
    d.color_type     = "MATERIAL"
    d.show_cavity    = True
    d.show_shadows   = False
    d.show_wireframe = False


# ─────────────────────────────────────────────────────────────────────────────
# Camera helpers
# ─────────────────────────────────────────────────────────────────────────────

def make_perspective_camera(centroid, diagonal: float, elev_deg: float,
                             azimuth_deg: float, name: str = "ForgeCamera"):
    """Create a perspective camera positioned at (elev_deg, azimuth_deg) from centroid."""
    scene = bpy.context.scene
    elev_rad = math.radians(elev_deg)
    azim_rad = math.radians(azimuth_deg)
    cam_dist = diagonal * 1.8
    cam_x = cam_dist * math.cos(elev_rad) * math.sin(azim_rad)
    cam_y = -cam_dist * math.cos(elev_rad) * math.cos(azim_rad)
    cam_z = cam_dist * math.sin(elev_rad) + centroid.z

    bpy.ops.object.camera_add(location=(cam_x + centroid.x, cam_y + centroid.y, cam_z))
    cam_obj = bpy.context.active_object
    cam_obj.name = name
    direction = centroid - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    cam_obj.data.type = "PERSP"
    cam_obj.data.angle = math.radians(50)   # 50° FOV — natural-looking for QA
    scene.camera = cam_obj
    return cam_obj


def make_ortho_camera(centroid, dims, name: str, offset: mathutils.Vector) -> object:
    """Create an orthographic camera at centroid+offset, pointing at centroid."""
    scene = bpy.context.scene
    ortho_scale = max(dims.x, dims.y, dims.z) * 1.15
    cam_dist    = max(dims.x, dims.y, dims.z) * 4.0
    loc = centroid + offset.normalized() * cam_dist

    bpy.ops.object.camera_add(location=loc)
    cam_obj = bpy.context.active_object
    cam_obj.name = name
    cam_obj.data.type        = "ORTHO"
    cam_obj.data.ortho_scale = ortho_scale
    direction = centroid - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam_obj
    return cam_obj


# ─────────────────────────────────────────────────────────────────────────────
# Cycles setup helpers
# ─────────────────────────────────────────────────────────────────────────────

def setup_cycles(scene, res_w: int, res_h: int, samples: int,
                 device_str: str, transparent: bool = True,
                 qa_mode: bool = False, seed: int = 0) -> None:
    """Configure Cycles engine with the given parameters."""
    scene.render.engine                       = "CYCLES"
    scene.render.resolution_x                 = res_w
    scene.render.resolution_y                 = res_h
    scene.render.resolution_percentage        = 50 if qa_mode else 100
    scene.render.image_settings.file_format   = "PNG"
    scene.render.image_settings.color_mode    = "RGBA" if transparent else "RGB"
    scene.render.image_settings.color_depth   = "8"
    scene.render.film_transparent             = transparent
    scene.render.use_persistent_data          = True
    # Idempotent rebuilds: overwrite stale frames, never leave .png_ placeholders.
    scene.render.use_overwrite                = True
    scene.render.use_placeholder              = False

    # Color management: AgX (Blender 4.0+ default for new files)
    scene.view_settings.view_transform  = "AgX"
    scene.view_settings.look            = "None"
    scene.display_settings.display_device = "sRGB"

    # Samples
    c = scene.cycles
    c.samples               = 16 if qa_mode else samples
    # Deterministic noise: pin the seed and disable per-frame time jitter so two
    # builds of the same scene produce byte-comparable renders (FORGE_PLAN §A).
    c.seed                  = seed
    c.use_animated_seed     = False
    c.use_adaptive_sampling = not qa_mode
    c.adaptive_threshold    = 0.01
    c.adaptive_min_samples  = 16
    c.use_auto_tile         = True
    c.max_bounces           = 4 if qa_mode else 12
    c.diffuse_bounces       = 2 if qa_mode else 4
    c.glossy_bounces        = 2 if qa_mode else 4
    c.transmission_bounces  = 4 if qa_mode else 12

    # GPU activation FIRST — so the denoiser is chosen from the ACTUAL device, not
    # the requested one. On the headless-Windows CPU-fallback path, OptiX is
    # unavailable; OPENIMAGEDENOISE runs on CPU so denoising degrades gracefully.
    if device_str.upper() != "CPU":
        actual = activate_cycles_gpu(prefer=device_str)
    else:
        c.device = "CPU"
        actual = "CPU"

    # Denoising (skip in QA mode for speed)
    c.use_denoising = not qa_mode
    if not qa_mode:
        use_optix = (actual == "GPU") and device_str.upper() in ("OPTIX", "GPU")
        c.denoiser = "OPTIX" if use_optix else "OPENIMAGEDENOISE"
        for vl in scene.view_layers:
            vl.cycles.use_denoising = True
        print(f"[forge-render] denoiser={c.denoiser} (device={actual}, requested={device_str})")


# ─────────────────────────────────────────────────────────────────────────────
# Render mode implementations
# ─────────────────────────────────────────────────────────────────────────────

def render_turntable(args, scene, meshes, outdir: pathlib.Path) -> list[str]:
    """Render N evenly-spaced angles around the asset (Workbench, perspective camera)."""
    centroid, diagonal, _, _ = compute_bbox(meshes)

    # Rig: empty at centroid, camera parented to it
    bpy.ops.object.empty_add(type="PLAIN_AXES", location=centroid)
    rig = bpy.context.active_object; rig.name = "CameraRig"

    elev_rad = math.radians(args.elev_deg)
    cam_dist = diagonal * 1.8
    bpy.ops.object.camera_add(
        location=(0, -cam_dist * math.cos(elev_rad), cam_dist * math.sin(elev_rad) + centroid.z)
    )
    cam_obj = bpy.context.active_object; cam_obj.name = "ForgeCamera"
    cam_obj.parent = rig
    direction = centroid - cam_obj.location
    cam_obj.rotation_euler = direction.to_track_quat("-Z", "Y").to_euler()
    scene.camera = cam_obj

    outputs = []
    step = 360.0 / args.n_angles
    for i in range(args.n_angles):
        angle_deg = i * step
        rig.rotation_euler.z = math.radians(angle_deg)
        bpy.context.view_layer.update()   # REQUIRED: force depsgraph refresh
        out_path = str(outdir / f"turntable_{i:03d}_{int(angle_deg):03d}deg.png")
        scene.render.filepath = out_path.replace("\\", "/")
        bpy.ops.render.render(write_still=True)
        outputs.append(out_path)
        print(f"[forge-render] turntable {i+1}/{args.n_angles} ({angle_deg:.0f}°) → {out_path}")

    return outputs


def render_6view(args, scene, meshes, outdir: pathlib.Path) -> list[str]:
    """Render 6 orthographic views (Workbench)."""
    centroid, _, min_co, max_co = compute_bbox(meshes)
    dims = max_co - min_co
    V = mathutils.Vector
    VIEWS = [
        ("front",  V((0, -1,  0))),
        ("back",   V((0,  1,  0))),
        ("right",  V((1,  0,  0))),
        ("left",   V((-1, 0,  0))),
        ("top",    V((0,  0,  1))),
        ("bottom", V((0,  0, -1))),
    ]
    outputs = []
    for name, direction in VIEWS:
        cam = make_ortho_camera(centroid, dims, f"cam_{name}", direction)
        out_path = str(outdir / f"6view_{name}.png")
        scene.render.filepath = out_path.replace("\\", "/")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
        outputs.append(out_path)
        print(f"[forge-render] 6-view {name} → {out_path}")
    return outputs


def render_normal_pass(args, scene, outdir: pathlib.Path, out_stem: str) -> list[str]:
    """
    Render world-space normal map via Cycles compositor: Normal → ×0.5 → +0.5 → PNG.
    1 sample is sufficient (deterministic per-pixel, no noise).
    """
    scene.render.engine          = "CYCLES"
    scene.cycles.samples         = 1
    scene.cycles.seed            = getattr(args, "seed", 0)
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising   = False
    scene.cycles.device          = "CPU"   # normals need no GPU

    vl = scene.view_layers[0]
    vl.use_pass_normal = True

    scene.use_nodes = True
    tree  = scene.node_tree; nodes = tree.nodes; links = tree.links; nodes.clear()

    rl  = nodes.new("CompositorNodeRLayers"); rl.location  = (-400, 0)
    mul = nodes.new("CompositorNodeMixRGB");  mul.location = (-100, 0)
    mul.blend_type = "MULTIPLY"; mul.inputs[0].default_value = 1.0
    mul.inputs[2].default_value = (0.5, 0.5, 0.5, 1.0)
    add = nodes.new("CompositorNodeMixRGB");  add.location = (150, 0)
    add.blend_type = "ADD";      add.inputs[0].default_value = 1.0
    add.inputs[2].default_value = (0.5, 0.5, 0.5, 0.0)
    fo  = nodes.new("CompositorNodeOutputFile"); fo.location = (400, 0)
    fo.base_path = str(outdir.as_posix())
    fo.format.file_format = "PNG"
    fo.layer_slots.clear(); fo.layer_slots.new(f"{out_stem}_")
    comp = nodes.new("CompositorNodeComposite"); comp.location = (400, -200)

    links.new(rl.outputs["Normal"],  mul.inputs[1])
    links.new(mul.outputs["Image"],  add.inputs[1])
    links.new(add.outputs["Image"],  fo.inputs[f"{out_stem}_"])
    links.new(rl.outputs["Image"],   comp.inputs["Image"])

    # Main output path: different from fo.base_path to avoid collision
    scene.render.filepath = str((outdir / f"_combined_{out_stem}").as_posix())
    bpy.ops.render.render(write_still=True)
    scene.use_nodes = False

    out_path = str(outdir / f"{out_stem}_0001.png")
    print(f"[forge-render] normals → {out_path}")
    return [out_path]


def render_uv_checker(args, scene, meshes, outdir: pathlib.Path,
                      angle_deg: float = 30.0) -> list[str]:
    """
    Temporary Cycles UV checker render (Workbench ignores shader nodes).
    Saves and restores original materials.
    """
    MAT_NAME = "__forge_uv_checker__"
    if MAT_NAME not in bpy.data.materials:
        mat = bpy.data.materials.new(MAT_NAME); mat.use_nodes = True
        ns = mat.node_tree.nodes; ls = mat.node_tree.links; ns.clear()
        out_n   = ns.new("ShaderNodeOutputMaterial")
        bsdf    = ns.new("ShaderNodeBsdfDiffuse")
        checker = ns.new("ShaderNodeTexChecker")
        uv      = ns.new("ShaderNodeTexCoord")
        checker.inputs["Scale"].default_value  = 8.0
        checker.inputs["Color1"].default_value = (1.0, 0.3, 0.1, 1.0)
        checker.inputs["Color2"].default_value = (0.9, 0.9, 0.9, 1.0)
        ls.new(uv.outputs["UV"],          checker.inputs["Vector"])
        ls.new(checker.outputs["Color"],  bsdf.inputs["Color"])
        ls.new(bsdf.outputs["BSDF"],      out_n.inputs["Surface"])
    else:
        mat = bpy.data.materials[MAT_NAME]

    saved = {}
    for obj in meshes:
        saved[obj.name] = [slot.material for slot in obj.material_slots]
        for slot in obj.material_slots: slot.material = mat
        if not obj.material_slots: obj.data.materials.append(mat)

    scene.render.engine          = "CYCLES"
    scene.cycles.samples         = 16
    scene.cycles.seed            = getattr(args, "seed", 0)
    scene.cycles.use_animated_seed = False
    scene.cycles.use_denoising   = False
    scene.cycles.device          = "CPU"

    out_path = str(outdir / f"uv_checker_{int(angle_deg):03d}deg.png")
    scene.render.filepath = out_path.replace("\\", "/")
    bpy.ops.render.render(write_still=True)

    # Restore originals
    for obj in meshes:
        if obj.name in saved:
            for i, slot in enumerate(obj.material_slots):
                if i < len(saved[obj.name]): slot.material = saved[obj.name][i]
    bpy.data.materials.remove(mat, do_unlink=True)
    scene.render.engine = "BLENDER_WORKBENCH"

    print(f"[forge-render] uv_checker → {out_path}")
    return [out_path]


# ─────────────────────────────────────────────────────────────────────────────
# Idempotent rebuild + output verification (FORGE_PLAN §A, authoring-meta §6.1)
# ─────────────────────────────────────────────────────────────────────────────

# Output filename stems this skill produces. Used by --clean so a re-run with
# fewer frames (or after a partial failure) never leaves stale PNGs that pass
# the size check and get tiled into the contact sheet as if current.
_OUTPUT_GLOBS = (
    "turntable_*.png", "6view_*.png", "wireframe_*.png", "matcap_*.png",
    "uv_checker_*.png", "normals*.png", "beauty_*.png", "passes_beauty_*.png",
    "_combined_*.png",
)


def clean_outputs(outdir: pathlib.Path) -> int:
    """Remove prior render outputs matching this skill's stems. Returns count removed."""
    removed = 0
    for pat in _OUTPUT_GLOBS:
        for f in outdir.glob(pat):
            try:
                f.unlink()
                removed += 1
            except OSError:
                pass
    if removed:
        print(f"[forge-render] clean: removed {removed} stale output file(s) from {outdir}")
    return removed


def _blank_frame_status(path: pathlib.Path) -> str:
    """
    Cheap blank-frame check (Pillow-optional, same pattern as contact_sheet.py).
    Returns 'blank', 'ok', or 'unknown' (Pillow absent / unreadable).
    A transparent (mean alpha 0) or flat (stddev < 1.0) frame is the most common
    silent render failure on a mis-lit or empty scene.
    """
    try:
        from PIL import Image, ImageStat  # noqa: PLC0415
    except ImportError:
        return "unknown"
    try:
        img = Image.open(path)
        img.load()
        if "A" in img.getbands():
            alpha_mean = ImageStat.Stat(img.getchannel("A")).mean[0]
            if alpha_mean == 0:
                return "blank"
        rgb = img.convert("RGB")
        stddev = ImageStat.Stat(rgb).stddev
        if max(stddev) < 1.0:
            return "blank"
        return "ok"
    except Exception:
        return "unknown"


def verify_outputs(outputs: list) -> dict:
    """
    Verify every render output: exists, size >= 1 KB, and not a blank frame.
    Returns {"files": [{path, exists, size_kb, blank, ok}], "health": "OK|WARN|FAIL"}.
    """
    files = []
    any_missing = False
    any_warn = False
    for o in outputs:
        p = pathlib.Path(o)
        exists = p.exists()
        size_kb = round(p.stat().st_size / 1024, 1) if exists else 0.0
        blank = _blank_frame_status(p) if exists else "n/a"
        ok = exists and size_kb >= 1.0 and blank != "blank"
        if not exists:
            any_missing = True
        elif not ok:
            any_warn = True
        files.append({
            "path": o, "exists": exists, "size_kb": size_kb,
            "blank": blank, "ok": ok,
        })
    if any_missing or not outputs:
        health = "FAIL"
    elif any_warn:
        health = "WARN"
    else:
        health = "OK"
    return {"files": files, "health": health}


# ─────────────────────────────────────────────────────────────────────────────
# Main entry point
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()
    res_w, res_h = parse_resolution(args.size)

    # Output directory (Blender does NOT create it)
    outdir = pathlib.Path(args.out)
    outdir.mkdir(parents=True, exist_ok=True)

    # Idempotent rebuild: clear this skill's prior output stems unless --no-clean.
    if not args.no_clean:
        clean_outputs(outdir)

    # Scene reset
    reset_scene()
    scene = bpy.context.scene
    transparent = not args.no_transparent

    # Import mesh (if --input provided)
    meshes = []
    if args.input:
        if args.input.endswith(".blend"):
            bpy.ops.wm.open_mainfile(filepath=str(pathlib.Path(args.input).as_posix()))
            scene = bpy.context.scene
            meshes = [o for o in scene.objects if o.type == "MESH"]
        else:
            meshes = import_mesh(args.input)

    # Pick engine based on mode (if not explicitly overridden)
    engine = args.engine.upper() if args.engine else ""
    if not engine:
        if args.mode in ("beauty", "normals", "passes", "uv"):
            engine = "CYCLES"
        else:
            engine = "BLENDER_WORKBENCH"

    # Validate engine (hard gate against EEVEE on Windows)
    if "EEVEE" in engine:
        print("[forge-render] ERROR: EEVEE is not supported headless on Windows. "
              "Switching to CYCLES.", file=sys.stderr)
        engine = "CYCLES"

    # Setup engine
    if engine == "CYCLES":
        setup_cycles(scene, res_w, res_h, args.samples, args.device,
                     transparent, qa_mode=args.qa, seed=args.seed)
    else:
        setup_workbench(scene, res_w, res_h, transparent)

    outputs = []

    # ── MODE dispatch ──────────────────────────────────────────────────────────
    if args.mode == "beauty":
        # Single beauty still at default camera (or scene camera if .blend loaded)
        if meshes and not args.input.endswith(".blend"):
            centroid, diagonal, _, _ = compute_bbox(meshes)
            make_perspective_camera(centroid, diagonal, args.elev_deg, 45.0)
        out_path = str((outdir / "beauty_0001.png").as_posix())
        scene.render.filepath = out_path.replace("\\", "/")
        bpy.ops.render.render(write_still=True)
        outputs = [out_path]
        print(f"[forge-render] beauty → {out_path}")

    elif args.mode == "turntable":
        setup_workbench(scene, res_w, res_h, transparent)
        outputs = render_turntable(args, scene, meshes, outdir)

    elif args.mode == "6view":
        setup_workbench(scene, res_w, res_h, transparent)
        outputs = render_6view(args, scene, meshes, outdir)

    elif args.mode == "wireframe":
        setup_workbench(scene, res_w, res_h, transparent)
        centroid, diagonal, _, _ = compute_bbox(meshes)
        rig_empty = None
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=centroid)
        rig_empty = bpy.context.active_object; rig_empty.name = "RigWireframe"
        cam_dist = diagonal * 1.8
        elev_rad = math.radians(args.elev_deg)
        bpy.ops.object.camera_add(
            location=(0, -cam_dist * math.cos(elev_rad),
                      cam_dist * math.sin(elev_rad) + centroid.z)
        )
        cam_obj = bpy.context.active_object; cam_obj.parent = rig_empty
        cam_obj.rotation_euler = (centroid - cam_obj.location).to_track_quat("-Z","Y").to_euler()
        scene.camera = cam_obj
        apply_wireframe_shading(scene)
        for i, angle_deg in enumerate([0.0, 45.0, 90.0, 180.0]):
            rig_empty.rotation_euler.z = math.radians(angle_deg)
            bpy.context.view_layer.update()
            out_path = str(outdir / f"wireframe_{i:02d}_{int(angle_deg):03d}deg.png")
            scene.render.filepath = out_path.replace("\\", "/")
            bpy.ops.render.render(write_still=True)
            outputs.append(out_path)
            print(f"[forge-render] wireframe {angle_deg:.0f}° → {out_path}")

    elif args.mode == "matcap":
        setup_workbench(scene, res_w, res_h, transparent)
        centroid, diagonal, _, _ = compute_bbox(meshes)
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=centroid)
        rig_m = bpy.context.active_object; rig_m.name = "RigMatcap"
        cam_dist = diagonal * 1.8
        elev_rad = math.radians(args.elev_deg)
        bpy.ops.object.camera_add(
            location=(0, -cam_dist * math.cos(elev_rad),
                      cam_dist * math.sin(elev_rad) + centroid.z)
        )
        cam_obj = bpy.context.active_object; cam_obj.parent = rig_m
        cam_obj.rotation_euler = (centroid - cam_obj.location).to_track_quat("-Z","Y").to_euler()
        scene.camera = cam_obj
        apply_matcap_shading(scene)
        for i, angle_deg in enumerate([30.0, 150.0, 270.0]):
            rig_m.rotation_euler.z = math.radians(angle_deg)
            bpy.context.view_layer.update()
            out_path = str(outdir / f"matcap_{i:02d}_{int(angle_deg):03d}deg.png")
            scene.render.filepath = out_path.replace("\\", "/")
            bpy.ops.render.render(write_still=True)
            outputs.append(out_path)
            print(f"[forge-render] matcap {angle_deg:.0f}° → {out_path}")

    elif args.mode == "normals":
        # Position a perspective camera at 30° elevation for the normal pass
        centroid, diagonal, _, _ = compute_bbox(meshes)
        make_perspective_camera(centroid, diagonal, args.elev_deg, 45.0, "NormalsCam")
        outputs = render_normal_pass(args, scene, outdir, "normals")

    elif args.mode == "uv":
        centroid, diagonal, _, _ = compute_bbox(meshes)
        make_perspective_camera(centroid, diagonal, args.elev_deg, 30.0, "UVCheckerCam")
        outputs = render_uv_checker(args, scene, meshes, outdir, angle_deg=30.0)

    elif args.mode == "diagnostic":
        # Full diagnostic suite: turntable + wireframe + matcap + normals + UV checker
        setup_workbench(scene, res_w, res_h, transparent)
        centroid, diagonal, _, _ = compute_bbox(meshes)

        # Shared rig
        bpy.ops.object.empty_add(type="PLAIN_AXES", location=centroid)
        rig_d = bpy.context.active_object; rig_d.name = "DiagRig"
        cam_dist = diagonal * 1.8
        elev_rad = math.radians(args.elev_deg)
        bpy.ops.object.camera_add(
            location=(0, -cam_dist * math.cos(elev_rad),
                      cam_dist * math.sin(elev_rad) + centroid.z)
        )
        cam_d = bpy.context.active_object; cam_d.parent = rig_d
        cam_d.rotation_euler = (centroid - cam_d.location).to_track_quat("-Z","Y").to_euler()
        scene.camera = cam_d

        diag_angles = [0.0, 45.0, 180.0, 270.0]

        # Turntable (quick 8-frame)
        step_d = 360.0 / 8
        for i in range(8):
            ang = i * step_d
            rig_d.rotation_euler.z = math.radians(ang)
            bpy.context.view_layer.update()
            d = scene.display.shading
            d.light = "STUDIO"; d.color_type = "MATERIAL"
            d.show_wireframe = False; d.show_cavity = True
            op = str(outdir / f"turntable_{i:03d}_{int(ang):03d}deg.png")
            scene.render.filepath = op.replace("\\", "/")
            bpy.ops.render.render(write_still=True)
            outputs.append(op)

        # Wireframe passes
        for ang in diag_angles:
            rig_d.rotation_euler.z = math.radians(ang)
            bpy.context.view_layer.update()
            apply_wireframe_shading(scene)
            op = str(outdir / f"wireframe_{int(ang):03d}deg.png")
            scene.render.filepath = op.replace("\\", "/")
            bpy.ops.render.render(write_still=True)
            outputs.append(op)

        # Matcap passes
        for ang in diag_angles[:2]:
            rig_d.rotation_euler.z = math.radians(ang)
            bpy.context.view_layer.update()
            apply_matcap_shading(scene)
            op = str(outdir / f"matcap_{int(ang):03d}deg.png")
            scene.render.filepath = op.replace("\\", "/")
            bpy.ops.render.render(write_still=True)
            outputs.append(op)

        # Normal pass (Cycles CPU, 1 sample)
        outputs += render_normal_pass(args, scene, outdir, "normals_030deg")

        # UV checker pass (Cycles CPU, 16 samples)
        outputs += render_uv_checker(args, scene, meshes, outdir, angle_deg=30.0)

    elif args.mode == "passes":
        # Enable standard passes and render to multilayer EXR + beauty PNG
        vl = scene.view_layers[0]
        vl.use_pass_combined           = True
        vl.use_pass_z                  = True
        vl.use_pass_mist               = True
        vl.use_pass_normal             = True
        vl.use_pass_ambient_occlusion  = True
        vl.use_pass_diffuse_direct     = True
        vl.use_pass_diffuse_indirect   = True
        vl.use_pass_diffuse_color      = True
        vl.use_pass_glossy_direct      = True
        vl.use_pass_glossy_indirect    = True
        vl.use_pass_emit               = True
        vl.cycles.denoising_store_passes = True

        if meshes and not args.input.endswith(".blend"):
            centroid, diagonal, _, _ = compute_bbox(meshes)
            make_perspective_camera(centroid, diagonal, args.elev_deg, 45.0)

        # World mist settings for mist pass
        if scene.world:
            scene.world.mist_settings.start   = 0.5
            scene.world.mist_settings.depth   = 25.0
            scene.world.mist_settings.falloff = "LINEAR"

        out_path = str((outdir / "passes_beauty_####").as_posix())
        scene.render.filepath = out_path
        bpy.ops.render.render(write_still=True)
        outputs = [str(outdir / "passes_beauty_0001.png")]
        print(f"[forge-render] passes render → {outputs[0]}")

    # ── Verify + Summary ─────────────────────────────────────────────────────────
    verdict = verify_outputs(outputs)
    summary = {
        "mode":    args.mode,
        "engine":  engine,
        "res":     f"{res_w}×{res_h}",
        "samples": args.samples,
        "seed":    args.seed,
        "outputs": outputs,
        "count":   len(outputs),
        "health":  verdict["health"],
        "files":   verdict["files"],
    }

    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"[forge-render] Done. {len(outputs)} file(s) written to {outdir}")
        for f in verdict["files"]:
            if not f["exists"]:
                status = "FAIL (missing)"
            elif f["size_kb"] < 1.0:
                status = "WARN (tiny)"
            elif f["blank"] == "blank":
                status = "WARN (blank)"
            else:
                status = "OK"
            print(f"  [{status}]  {f['path']}  ({f['size_kb']} KB)")
        print(f"[forge-render] health: {verdict['health']}")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[forge-render] FATAL: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc(file=sys.stderr)
        sys.exit(1)
