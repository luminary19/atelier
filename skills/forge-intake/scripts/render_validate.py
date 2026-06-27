"""
forge-intake/scripts/render_validate.py
Quick 4-angle headless QA render for cleaned intake meshes.

Imports a GLB/OBJ/FBX, places a camera at 4 angles (front / right / back / top), and renders
small PNGs the model reads back to confirm: no exploded geometry, no inverted normals, and no
baked-in directional lighting. Assembled from references/mesh-cleanup.md §4.

Usage (PowerShell — run via Blender subprocess; the `--` separator is MANDATORY):
    $blender = "C:/Program Files/Blender Foundation/Blender 4.4/blender.exe"
    & $blender -b --factory-startup --python-exit-code 1 `
        -P "$CLAUDE_CONFIG_DIR/skills/forge-intake/scripts/render_validate.py" `
        -- "output_clean.glb" "C:/Forge/renders/check.png" [--engine CYCLES] [--samples 16] [--size 512]
    # Produces: check_front.png, check_right.png, check_back.png, check_top.png

Positional args (after the mandatory `--` separator):
    <input>   mesh to render (.glb/.gltf/.obj/.fbx)
    <output>  base PNG path; per-angle suffix is inserted before the extension

Optional flags:
    --engine {CYCLES,BLENDER_WORKBENCH}   default BLENDER_WORKBENCH (headless-safe, ~1s/frame).
                                          EEVEE / EEVEE-Next are REJECTED (unsupported headless on Win).
    --samples N    Cycles samples when --engine CYCLES (default 16 for validation)
    --size N       square resolution (default 512)
    --json         emit a JSON summary to stdout

Platform: Native Windows 11. Workbench for fast geometry QA; CYCLES (low samples) for shaded
checks. Never EEVEE. Forward-slash absolute paths in scene.render.filepath.
"""

import sys
import io
import math
import json
import argparse
import pathlib

import bpy
import mathutils

# UTF-8 stdout wrapper (Windows cp1252 default breaks non-ASCII console output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="forge-intake 4-angle QA render", add_help=False)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("--engine", default="BLENDER_WORKBENCH",
                   choices=["CYCLES", "BLENDER_WORKBENCH"])
    p.add_argument("--samples", type=int, default=16)
    p.add_argument("--size", type=int, default=512)
    p.add_argument("--json", action="store_true", default=False)
    return p.parse_args(argv)


def fwd(path: str) -> str:
    return str(pathlib.Path(path).resolve().as_posix())


def import_mesh(path: str) -> list:
    ext = pathlib.Path(path).suffix.lower()
    fp = fwd(path)
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=fp)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=fp)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=fp)
    else:
        raise ValueError(f"unsupported input extension: {ext}")
    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"no mesh objects found after importing {path}")
    return meshes


def compute_bbox(meshes: list):
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
    return centroid, diagonal


def setup_engine(scene, engine: str, size: int, samples: int) -> str:
    # Hard gate: EEVEE/EEVEE-Next are unsupported headless on Windows.
    if "EEVEE" in engine.upper():
        print("[render_validate] ERROR: EEVEE is unsupported headless on Windows. "
              "Using BLENDER_WORKBENCH.", file=sys.stderr)
        engine = "BLENDER_WORKBENCH"
    scene.render.resolution_x = size
    scene.render.resolution_y = size
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = "PNG"
    if engine == "CYCLES":
        scene.render.engine = "CYCLES"
        scene.cycles.samples = samples
        scene.cycles.use_denoising = False
        scene.cycles.device = "CPU"
        scene.view_settings.view_transform = "AgX"
    else:
        scene.render.engine = "BLENDER_WORKBENCH"
        d = scene.display.shading
        d.light = "STUDIO"
        d.color_type = "MATERIAL"
        d.show_cavity = True
        d.show_shadows = True
    return engine


def place_camera(centroid, diagonal: float, direction: mathutils.Vector):
    scene = bpy.context.scene
    dist = diagonal * 1.8 if diagonal > 0 else 1.0
    loc = centroid + direction.normalized() * dist
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.rotation_euler = (centroid - cam.location).to_track_quat("-Z", "Y").to_euler()
    cam.data.type = "PERSP"
    cam.data.angle = math.radians(50)
    scene.camera = cam
    return cam


def main() -> None:
    args = parse_args()
    base = pathlib.Path(args.output)
    base.parent.mkdir(parents=True, exist_ok=True)
    stem = base.with_suffix("")
    ext = base.suffix or ".png"

    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    meshes = import_mesh(args.input)
    centroid, diagonal = compute_bbox(meshes)
    engine = setup_engine(scene, args.engine, args.size, args.samples)

    V = mathutils.Vector
    angles = {
        "front": V((0, -1, 0)),
        "right": V((1, 0, 0)),
        "back":  V((0, 1, 0)),
        "top":   V((0, 0, 1)),
    }

    outputs = []
    for name, direction in angles.items():
        cam = place_camera(centroid, diagonal, direction)
        out_path = f"{stem}_{name}{ext}"
        scene.render.filepath = out_path.replace("\\", "/")
        bpy.ops.render.render(write_still=True)
        bpy.data.objects.remove(cam, do_unlink=True)
        outputs.append(out_path)
        print(f"[render_validate] {name} -> {out_path}")

    summary = {
        "input": args.input,
        "engine": engine,
        "size": f"{args.size}x{args.size}",
        "outputs": outputs,
        "count": len(outputs),
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"[render_validate] done ({engine}). Read each PNG to confirm: no exploded "
              "geometry, no inverted normals, no baked-in directional lighting.")
        for o in outputs:
            p = pathlib.Path(o)
            kb = round(p.stat().st_size / 1024, 1) if p.exists() else 0
            status = "OK" if kb > 1 else "WARN (tiny)"
            print(f"  [{status}] {o} ({kb} KB)")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[render_validate] FATAL: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
