"""
forge-intake/scripts/cleanup.py
Blender-headless mesh cleanup pipeline for the Forge intake suite (tracks A, D, E, F).

Imports a raw scan / AI-generated mesh, fixes scale, applies transforms, voxel-remeshes,
retopologises with Quadriflow (pinned seed = deterministic), UV-unwraps with smart_project,
bakes the high-poly source diffuse onto the clean low-poly target (selected-to-active, Cycles),
and exports a Y-up GLB. Assembled from references/mesh-cleanup.md §3 so the single most
failure-prone intake step is a pinned, re-runnable, idempotent artifact.

Usage (PowerShell — run via Blender subprocess; the `--` separator is MANDATORY):
    $blender = "C:/Program Files/Blender Foundation/Blender 4.4/blender.exe"
    & $blender -b --factory-startup --python-exit-code 1 `
        -P "$CLAUDE_CONFIG_DIR/skills/forge-intake/scripts/cleanup.py" `
        -- "input_raw.glb" "output_clean.glb" 2048 20000 --seed 0

Positional args (after the mandatory `--` separator):
    <input>      raw mesh to clean  (.glb/.gltf/.obj/.fbx)
    <output>     destination GLB    (overwritten idempotently)
    <bake_res>   bake texture resolution in px (e.g. 1024, 2048)
    <target_tris>  target triangle count for the retopo (Quadriflow target_faces = target_tris // 2)

Optional flags:
    --seed N           Quadriflow seed (default 0; same seed => same topology => idempotent)
    --voxel F          override voxel_size (default auto: max_extent / 200, clamped 0.001..0.2)
    --scale F          extra uniform scale applied before transform_apply (default 1.0;
                       Meshy GLB is centimeters => pass 0.01)
    --no-bake          skip the selected-to-active bake (geometry/UV only)
    --samples N        Cycles bake samples (default 128; 64 for validation)
    --json             emit a JSON summary to stdout

Platform: Native Windows 11. Runs under Blender's bundled Python (bpy). Cycles only for the
bake (EEVEE/EEVEE-Next are unsupported headless on Windows). Forward-slash absolute paths.
"""

import sys
import io
import math
import json
import argparse
import pathlib

import bpy

# UTF-8 stdout wrapper (Windows cp1252 default breaks non-ASCII console output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="forge-intake Blender cleanup pipeline", add_help=False)
    p.add_argument("input")
    p.add_argument("output")
    p.add_argument("bake_res", type=int)
    p.add_argument("target_tris", type=int)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--voxel", type=float, default=0.0)   # 0 => auto
    p.add_argument("--scale", type=float, default=1.0)
    p.add_argument("--no-bake", action="store_true", default=False)
    p.add_argument("--samples", type=int, default=128)
    p.add_argument("--json", action="store_true", default=False)
    return p.parse_args(argv)


def fwd(path: str) -> str:
    """Absolute forward-slash path for Blender filepath (never '//' relative)."""
    return str(pathlib.Path(path).resolve().as_posix())


def import_mesh(path: str):
    """Import by extension; Blender 4.x native importers. Returns the active mesh object."""
    ext = pathlib.Path(path).suffix.lower()
    fp = fwd(path)
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=fp)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=fp)        # Blender 4.x native OBJ importer
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=fp)
    else:
        raise ValueError(f"unsupported input extension: {ext}")

    meshes = [o for o in bpy.context.scene.objects if o.type == "MESH"]
    if not meshes:
        raise RuntimeError(f"no mesh objects found after importing {path}")
    obj = meshes[0]
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    return obj, meshes


def join_meshes(meshes: list):
    """Join all mesh objects into one so retopo treats the asset as a single surface."""
    if len(meshes) <= 1:
        return meshes[0]
    bpy.ops.object.select_all(action="DESELECT")
    for o in meshes:
        o.select_set(True)
    bpy.context.view_layer.objects.active = meshes[0]
    bpy.ops.object.join()
    return bpy.context.view_layer.objects.active


def fix_scale_and_transforms(obj, extra_scale: float):
    """Apply optional unit scale, then bake rotation+scale into the mesh before any remesh.
    Quadriflow/Voxel Remesh operate on world-space geometry: unapplied scale => wrong voxels.
    """
    if extra_scale != 1.0:
        obj.scale = (extra_scale, extra_scale, extra_scale)
    bpy.ops.object.transform_apply(location=False, rotation=True, scale=True)
    dims = [obj.dimensions[i] for i in range(3)]
    print(f"[cleanup] post-scale extents (m): {[round(d, 4) for d in dims]}")
    return max(dims) if dims else 0.0


def remesh_voxel(obj, voxel_size: float):
    mod = obj.modifiers.new(name="VoxelRemesh", type="REMESH")
    mod.mode = "VOXEL"
    mod.voxel_size = voxel_size
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_apply(modifier=mod.name)


def retopo_quadriflow(obj, target_tris: int, seed: int):
    # Quadriflow counts quads, not tris; pass target_tris // 2.
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.quadriflow_remesh(
        use_preserve_sharp=True,
        use_preserve_boundary=True,
        mode="FACES",
        target_faces=max(target_tris // 2, 4),
        seed=seed,
    )


def uv_unwrap(obj, bake_res: int):
    # island_margin: ~3 texels at 1024, ~2 texels at 2048.
    margin = 0.003 if bake_res <= 1024 else 0.002
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode="EDIT")
    bpy.ops.mesh.select_all(action="SELECT")
    # smart_project angle_limit is in RADIANS — radians(66deg) ~= 1.152.
    # Passing 66.0 directly = 66 rad and every face becomes its own island.
    bpy.ops.uv.smart_project(angle_limit=math.radians(66.0), island_margin=margin, area_weight=0.0)
    bpy.ops.object.mode_set(mode="OBJECT")


def bake_diffuse(low_obj, high_obj, bake_res: int, samples: int, out_dir: pathlib.Path) -> str:
    """Selected-to-active diffuse bake from the high-poly source onto the low-poly target.
    CYCLES only (EEVEE/EEVEE-Next unsupported headless on Windows).
    """
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = samples
    scene.cycles.device = "CPU"   # headless-safe default; flip to GPU only if confirmed available

    # Target needs a material with an image node selected for the bake destination.
    img = bpy.data.images.new("forge_bake_diffuse", width=bake_res, height=bake_res)
    mat = bpy.data.materials.new("forge_bake_mat")
    mat.use_nodes = True
    low_obj.data.materials.clear()
    low_obj.data.materials.append(mat)
    nodes = mat.node_tree.nodes
    tex = nodes.new("ShaderNodeTexImage")
    tex.image = img
    tex.select = True
    nodes.active = tex

    bpy.ops.object.select_all(action="DESELECT")
    high_obj.select_set(True)            # source (selected)
    low_obj.select_set(True)             # target (active)
    bpy.context.view_layer.objects.active = low_obj

    # cage_extrusion controls light-leak prevention: 0.02-0.05 hard-surface, 0.10-0.15 organic.
    bpy.ops.object.bake(
        type="DIFFUSE",
        pass_filter={"COLOR"},
        use_selected_to_active=True,
        cage_extrusion=0.05,
        max_ray_distance=0.1,
    )
    bake_png = out_dir / "bake_diffuse.png"
    img.filepath_raw = fwd(str(bake_png))
    img.file_format = "PNG"
    img.save()
    return str(bake_png)


def export_glb(obj, output: str):
    out = pathlib.Path(output)
    out.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.object.select_all(action="DESELECT")
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=fwd(output),         # absolute forward-slash path; overwrites idempotently
        export_format="GLB",
        use_selection=True,
        export_normals=True,
        export_tangents=True,         # required when exporting normal maps
        export_materials="EXPORT",
        export_texcoords=True,
        export_yup=True,              # Forge standard: Y-up for web (three.js / R3F)
    )


def main() -> None:
    args = parse_args()
    out_path = pathlib.Path(args.output)
    out_dir = out_path.parent if out_path.parent.as_posix() else pathlib.Path(".")
    out_dir.mkdir(parents=True, exist_ok=True)

    # Empty factory scene for determinism.
    bpy.ops.wm.read_factory_settings(use_empty=True)

    raw_obj, meshes = import_mesh(args.input)
    raw_obj = join_meshes(meshes)

    max_ext = fix_scale_and_transforms(raw_obj, args.scale)

    # Keep an untouched copy of the dense source so we can bake high->low.
    src = raw_obj.copy()
    src.data = raw_obj.data.copy()
    bpy.context.collection.objects.link(src)
    src.name = "forge_highpoly_source"

    # Auto voxel size: max_extent / 200, clamped to a sane range.
    voxel = args.voxel if args.voxel > 0 else max(min(max_ext / 200.0, 0.2), 0.001)
    print(f"[cleanup] voxel_size = {voxel:.5f} (max_extent {max_ext:.4f} m)")

    bpy.context.view_layer.objects.active = raw_obj
    remesh_voxel(raw_obj, voxel)
    retopo_quadriflow(raw_obj, args.target_tris, args.seed)
    uv_unwrap(raw_obj, args.bake_res)

    bake_png = None
    if not args.no_bake:
        try:
            bake_png = bake_diffuse(raw_obj, src, args.bake_res, args.samples, out_dir)
        except Exception as exc:   # noqa: BLE001 — bake is best-effort; geometry is the hard deliverable
            print(f"[cleanup] WARNING: bake failed ({exc}); exporting geometry without baked map.",
                  file=sys.stderr)

    # Remove the high-poly source before export.
    bpy.data.objects.remove(src, do_unlink=True)

    export_glb(raw_obj, args.output)

    final_tris = sum(len(p.vertices) - 2 for p in raw_obj.data.polygons)  # fan triangulation estimate
    summary = {
        "input": args.input,
        "output": args.output,
        "exists": out_path.exists(),
        "size_kb": round(out_path.stat().st_size / 1024, 1) if out_path.exists() else 0,
        "target_tris": args.target_tris,
        "approx_tris": final_tris,
        "voxel_size": round(voxel, 5),
        "seed": args.seed,
        "bake_png": bake_png,
        "baked": bake_png is not None,
    }
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print(f"[cleanup] wrote {args.output} ({summary['size_kb']} KB, "
              f"~{final_tris} tris, seed={args.seed}, baked={summary['baked']})")
        print("[cleanup] NEXT: re-run trimesh pre-flight on the OUTPUT (references/mesh-cleanup.md §1), "
              "then forge-validate. A failed retopo is caught by re-checking the output, not the input.")


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[cleanup] FATAL: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
