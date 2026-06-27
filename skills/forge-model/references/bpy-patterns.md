# forge-model — bpy Script Patterns

## Contents
- §1. Script boilerplate (arg-parse, UTF-8 fix, error handling)
- §2. Scene setup: clear, camera, lights, world
- §3. Mesh creation: bmesh from scratch + from_pydata
- §4. → See scene-render.md for validation, render-to-PNG, QA material

---

## §1. Script Boilerplate

Every Forge headless Blender script must follow this structure.

```python
"""
build_mesh.py — forge-model headless script
Usage (PowerShell):
  & $BLENDER_EXE --background --factory-startup --python-exit-code 1 `
      --python "C:\absolute\path\build_mesh.py" `
      -- --output "C:\absolute\path\out\qa.png" --samples 32
"""
import sys, os, argparse, logging, io, math

# UTF-8 stdout fix — Windows PowerShell defaults to cp1252
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("forge-model")


def parse_args():
    """Extract args that come AFTER '--' in sys.argv."""
    try:
        idx = sys.argv.index("--"); argv = sys.argv[idx + 1:]
    except ValueError:
        argv = []
    p = argparse.ArgumentParser()
    p.add_argument("--output",  required=True)
    p.add_argument("--samples", type=int, default=32)
    p.add_argument("--width",   type=int, default=1280)
    p.add_argument("--height",  type=int, default=720)
    # Cycles only — EEVEE Next is unsupported headless on Windows (see gotchas.md §G6).
    p.add_argument("--engine",  default="CYCLES", choices=["CYCLES"])
    return p.parse_args(argv)


# Parse args BEFORE importing bpy — surfaces arg errors immediately
args = parse_args()
log.info("Output: %s  samples: %d", args.output, args.samples)

import bpy, bmesh
from mathutils import Vector


def main():
    # 1. Clear default scene
    for obj in list(bpy.data.objects):
        bpy.data.objects.remove(obj, do_unlink=True)

    # 2. Build geometry (replace this block per asset)
    obj = create_beveled_cube("MyAsset")
    validate_mesh_quick(obj)       # from scene-render.md

    # 3. QA render
    setup_scene_for_qa(obj, args.width, args.height)
    render_to_png(args.output, args.engine, args.samples)
    log.info("FORGE_MODEL_PASS: %s", args.output)


try:
    main()
except Exception:
    import traceback; traceback.print_exc(); sys.exit(1)
```

**Discipline checklist:**
- `bm.free()` always called after `bm.to_mesh()` — no exceptions
- `--python-exit-code 1` in the PowerShell invocation (not in script, but enforce it)
- `sys.exit(1)` in the except block — Blender exits 0 on exception without this
- Output path via `os.path.abspath()` — never `//` prefix (undefined without a .blend file)
- Parse args before `import bpy` so errors surface immediately

---

## §2. Scene Setup: Clear, Camera, Lights, World

```python
import bpy, bmesh, math
from mathutils import Vector


def clear_scene() -> None:
    """Remove all objects, meshes, lights, cameras."""
    for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
    for m in list(bpy.data.meshes):    bpy.data.meshes.remove(m)
    for c in list(bpy.data.cameras):   bpy.data.cameras.remove(c)
    for l in list(bpy.data.lights):    bpy.data.lights.remove(l)


def create_camera_auto(
    target_obj: "bpy.types.Object",
    elevation_deg: float = 35.0,
    azimuth_deg: float = 45.0,
    distance_factor: float = 3.0,
    focal_mm: float = 50.0,
) -> "bpy.types.Object":
    """Position a camera to frame target_obj automatically."""
    radius = max(target_obj.dimensions) * distance_factor
    el = math.radians(elevation_deg)
    az = math.radians(azimuth_deg)
    x = radius * math.cos(el) * math.sin(az)
    y = radius * math.cos(el) * -math.cos(az)
    z = radius * math.sin(el)

    cam_data = bpy.data.cameras.new("ForgeQA_Camera")
    cam_data.lens = focal_mm
    cam_data.sensor_width = 36.0
    cam_obj = bpy.data.objects.new("ForgeQA_Camera", cam_data)
    bpy.context.scene.collection.objects.link(cam_obj)
    cam_obj.location = (x, y, z)
    direction = target_obj.location - Vector((x, y, z))
    cam_obj.rotation_euler = direction.to_track_quat('-Z', 'Y').to_euler()
    bpy.context.scene.camera = cam_obj
    return cam_obj


def create_three_point_lights() -> list:
    """Standard 3-point area light rig: Key (front-left), Fill (front-right), Rim (back)."""
    def _make(name, loc, energy, size=2.0):
        d = bpy.data.lights.new(name, 'AREA'); d.energy = energy; d.size = size
        o = bpy.data.objects.new(name, d)
        bpy.context.scene.collection.objects.link(o)
        o.location = loc
        o.rotation_euler = (Vector((0,0,0)) - Vector(loc)).to_track_quat('-Z','Y').to_euler()
        return o
    return [
        _make("ForgeKey",  ( 4, -3, 5),  800, 2.0),
        _make("ForgeFill", (-3, -2, 3),  200, 3.0),
        _make("ForgeRim",  (-1,  4, 4),  400, 1.5),
    ]


def setup_world_neutral() -> None:
    """Dark neutral world (0.03 luminance) for QA renders."""
    w = bpy.data.worlds.new("ForgeQA_World"); w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs["Color"].default_value = (0.03, 0.03, 0.03, 1.0)
        bg.inputs["Strength"].default_value = 1.0
    bpy.context.scene.world = w


def setup_scene_for_qa(target_obj, width=1280, height=720) -> None:
    """Full scene setup for a quick QA render."""
    create_camera_auto(target_obj)
    create_three_point_lights()
    setup_world_neutral()
    r = bpy.context.scene.render
    r.resolution_x = width; r.resolution_y = height; r.resolution_percentage = 100
```

---

## §3. Mesh Creation

### 3A. bmesh from scratch (preferred for headless)

```python
def create_mesh_object(name: str, build_fn) -> "bpy.types.Object":
    """
    Generic factory: build_fn receives a bmesh, populates it.
    Flushes to Blender data, wraps in Object, links to scene.
    """
    bm = bmesh.new(use_operators=True)
    try:
        build_fn(bm)
        bm.normal_update()
        mesh = bpy.data.meshes.new(name)
        bm.to_mesh(mesh)
    finally:
        bm.free()   # ALWAYS free — C-level memory leak if omitted
    mesh.validate(); mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


def create_beveled_cube(name: str = "BeveledCube", size: float = 1.0) -> "bpy.types.Object":
    """Cube with small bevel — canonical forge-model test asset."""
    def _build(bm):
        bmesh.ops.create_cube(bm, size=size)
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=size*0.04,
                        offset_type='OFFSET', segments=2, profile=0.5,
                        affect='EDGES', clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return create_mesh_object(name, _build)


def create_box_mesh(name: str, w=1.0, h=1.0, d=1.0) -> "bpy.types.Object":
    """Box with explicit W/H/D dimensions. Z-up: height maps to Z."""
    def _build(bm):
        bmesh.ops.create_cube(bm, size=1.0)
        bmesh.ops.scale(bm, vec=Vector((w, d, h)), verts=bm.verts)
    return create_mesh_object(name, _build)
```

### 3B. from_pydata (fastest for known geometry / numpy outputs)

```python
def create_mesh_from_pydata(
    name: str,
    verts: list,   # [(x,y,z), ...]
    faces: list,   # [(i,j,k,...), ...]
    edges: list = None,
) -> "bpy.types.Object":
    """Build mesh from explicit vertex/face lists (fast path for generated geometry)."""
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(verts, edges or [], faces)
    mesh.validate(verbose=True)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.scene.collection.objects.link(obj)
    return obj


# Cube via from_pydata:
CUBE_VERTS = [(-1,-1,-1),(1,-1,-1),(1,1,-1),(-1,1,-1),(-1,-1,1),(1,-1,1),(1,1,1),(-1,1,1)]
CUBE_FACES = [(0,1,2,3),(4,7,6,5),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]
```

---

## §4. Validation + Render + QA Material

See **`references/scene-render.md`** for:
- `validate_mesh(obj)` + `assert_mesh_valid(obj)` — programmatic mesh health check
- `render_to_png(output, engine, samples)` — Cycles headless render with PNG verification
- `render_qa_multiangle(obj, output_stem, ...)` — front-3/4 + back-3/4 + top spot-check for export meshes
- `assign_qa_material(obj)` — quick Principled BSDF for QA renders
- `validate_mesh_quick(obj)` — inline fast check (non-manifold + zero-area only)
