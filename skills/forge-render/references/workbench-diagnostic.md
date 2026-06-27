# forge-render — Workbench Diagnostic Renders Reference

## Contents
- §turntable. Turntable render pattern (Workbench, N angles)
- §6view. 6-view orthographic render
- §wireframe. Wireframe variant
- §matcap. Matcap variant
- §uvchecker. UV checker (temporary Cycles switch)
- §normals-wb. Flat-normal variant (Workbench, per-object color)
- §qa-table. Engine selection quick reference

---

## §turntable. Turntable render pattern

**Workbench** is the correct engine for all iterative QA turntables on Windows. It is
headless-safe, requires no GPU, and renders at ~0.3–2 s per 512×512 frame.

**Do not use `bpy.ops.render.opengl()`** — it requires an active GUI window and fails in
`-b` mode with `RuntimeError: Operator bpy.ops.render.opengl.poll() failed`. Always use
`bpy.ops.render.render(write_still=True)`.

```python
# forge_turntable_wb.py
# Usage (PowerShell — backtick line-continuation):
#   blender -b --factory-startup --python-exit-code 1 -P forge_turntable_wb.py `
#       -- --input "C:/forge/model.glb" --out "C:/forge/out/turntable" `
#          --n-angles 12 --size 512
import sys, io, bpy, math, pathlib, argparse, mathutils

# UTF-8 stdout wrapper (Windows cp1252 fix)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# Parse args (everything after --)
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--input",    required=True)
p.add_argument("--out",      required=True)
p.add_argument("--n-angles", type=int, default=12)
p.add_argument("--size",     type=int, default=512)
p.add_argument("--elev-deg", type=float, default=25.0)  # camera elevation
args = p.parse_args(argv)

# Ensure output directory exists (Blender does NOT create it)
outdir = pathlib.Path(args.out)
outdir.mkdir(parents=True, exist_ok=True)

# Scene reset
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene

# Engine: Workbench — headless-safe on Windows
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = args.size
scene.render.resolution_y = args.size
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.image_settings.color_mode  = "RGBA"
scene.render.film_transparent           = True   # transparent bg for silhouette QA

# Workbench shading: studio with cavity reveals depth cues
d = scene.display.shading
d.light           = "STUDIO"      # FLAT | STUDIO | MATCAP
d.color_type      = "MATERIAL"    # SINGLE | OBJECT | RANDOM | MATERIAL | TEXTURE
d.show_cavity     = True          # reveals concavities (curvature hot-spots)
d.show_shadows    = True
d.show_wireframe  = False         # off for beauty; on for wireframe variant

# Import mesh
# Blender 4.x: OBJ/STL/PLY use the C++ wm.*_import operators (the legacy
# import_scene.obj / import_mesh.stl / import_mesh.ply were removed in 4.0/4.2).
# glTF + FBX operator IDs are unchanged. getattr keeps 3.x working as a fallback.
ext = pathlib.Path(args.input).suffix.lower()
fwd_path = str(pathlib.Path(args.input).as_posix())  # forward slashes for Blender
def _imp_obj(fp): (getattr(bpy.ops.wm, "obj_import", None) or bpy.ops.import_scene.obj)(filepath=fp)
def _imp_stl(fp): (getattr(bpy.ops.wm, "stl_import", None) or bpy.ops.import_mesh.stl)(filepath=fp)
def _imp_ply(fp): (getattr(bpy.ops.wm, "ply_import", None) or bpy.ops.import_mesh.ply)(filepath=fp)
{
    ".glb":  lambda fp: bpy.ops.import_scene.gltf(filepath=fp),
    ".gltf": lambda fp: bpy.ops.import_scene.gltf(filepath=fp),
    ".fbx":  lambda fp: bpy.ops.import_scene.fbx(filepath=fp),
    ".obj":  _imp_obj,
    ".stl":  _imp_stl,
    ".ply":  _imp_ply,
}[ext](fwd_path)

# Compute bounding box centroid + diagonal
meshes = [o for o in scene.objects if o.type == "MESH"]
if not meshes:
    raise RuntimeError("No mesh objects found after import.")
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
cam_dist = diagonal * 1.8   # 1.8× diagonal = generous framing

# Camera rig: empty at centroid, camera parented to it
bpy.ops.object.empty_add(type="PLAIN_AXES", location=centroid)
rig = bpy.context.active_object; rig.name = "CameraRig"

elev_rad = math.radians(args.elev_deg)
cam_y = -cam_dist * math.cos(elev_rad)
cam_z =  cam_dist * math.sin(elev_rad) + centroid.z
bpy.ops.object.camera_add(location=(0, cam_y, cam_z))
cam_obj = bpy.context.active_object; cam_obj.name = "ForgeCamera"
cam_obj.parent = rig
cam_obj.rotation_euler = (centroid - cam_obj.location).to_track_quat("-Z", "Y").to_euler()
scene.camera = cam_obj

# Render each angle
step = 360.0 / args.n_angles
for i in range(args.n_angles):
    angle_deg = i * step
    rig.rotation_euler.z = math.radians(angle_deg)
    bpy.context.view_layer.update()   # REQUIRED: force depsgraph refresh after transform
    scene.render.filepath = str(outdir / f"turntable_{i:03d}_{int(angle_deg):03d}deg.png")
    bpy.ops.render.render(write_still=True)
    print(f"[forge-render] turntable {i+1}/{args.n_angles}  ({angle_deg:.0f}°) → {scene.render.filepath}")

print(f"[forge-render] turntable complete: {args.n_angles} frames → {outdir}")
```

---

## §6view. 6-view orthographic render

Six principal axes (front/back/right/left/top/bottom) with orthographic camera sized to the
bounding box. Use for dimensional QA — confirm proportions vs brief from all axes.

```python
# forge_6view.py
# Usage (PowerShell — backtick line-continuation):
#   blender -b --factory-startup --python-exit-code 1 -P forge_6view.py `
#       -- --input "C:/forge/model.glb" --out "C:/forge/out/6view" --size 512
import sys, io, bpy, pathlib, argparse, mathutils

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
p = argparse.ArgumentParser()
p.add_argument("--input",  required=True)
p.add_argument("--out",    required=True)
p.add_argument("--size",   type=int, default=512)
args = p.parse_args(argv)

outdir = pathlib.Path(args.out); outdir.mkdir(parents=True, exist_ok=True)
bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.resolution_x = scene.render.resolution_y = args.size
scene.render.resolution_percentage = 100
scene.render.image_settings.file_format = "PNG"
scene.render.film_transparent = True
scene.display.shading.light      = "STUDIO"
scene.display.shading.color_type = "MATERIAL"

ext = pathlib.Path(args.input).suffix.lower()
# 4.x C++ importers for OBJ/STL/PLY (getattr fallback to 3.x legacy operators);
# glTF + FBX operator IDs unchanged.
def _imp_obj(fp): (getattr(bpy.ops.wm, "obj_import", None) or bpy.ops.import_scene.obj)(filepath=fp)
def _imp_stl(fp): (getattr(bpy.ops.wm, "stl_import", None) or bpy.ops.import_mesh.stl)(filepath=fp)
def _imp_ply(fp): (getattr(bpy.ops.wm, "ply_import", None) or bpy.ops.import_mesh.ply)(filepath=fp)
{".glb": lambda fp: bpy.ops.import_scene.gltf(filepath=fp),
 ".gltf": lambda fp: bpy.ops.import_scene.gltf(filepath=fp),
 ".fbx": lambda fp: bpy.ops.import_scene.fbx(filepath=fp),
 ".obj": _imp_obj, ".stl": _imp_stl, ".ply": _imp_ply
}[ext](str(pathlib.Path(args.input).as_posix()))

meshes  = [o for o in scene.objects if o.type == "MESH"]
corners = [obj.matrix_world @ mathutils.Vector(v) for obj in meshes for v in obj.bound_box]
min_co  = mathutils.Vector((min(c.x for c in corners), min(c.y for c in corners), min(c.z for c in corners)))
max_co  = mathutils.Vector((max(c.x for c in corners), max(c.y for c in corners), max(c.z for c in corners)))
centroid = (min_co + max_co) / 2
dims     = max_co - min_co
ortho    = max(dims.x, dims.y, dims.z) * 1.15    # 15% padding
cdist    = max(dims.x, dims.y, dims.z) * 4.0

V = mathutils.Vector
VIEWS = [
    ("front",  centroid + V(( 0, -cdist,  0)), V((0, 0, 1))),
    ("back",   centroid + V(( 0,  cdist,  0)), V((0, 0, 1))),
    ("right",  centroid + V(( cdist, 0,   0)), V((0, 0, 1))),
    ("left",   centroid + V((-cdist, 0,   0)), V((0, 0, 1))),
    ("top",    centroid + V(( 0, 0,  cdist)), V((0, 1, 0))),
    ("bottom", centroid + V(( 0, 0, -cdist)), V((0,-1, 0))),
]
for name, loc, _up in VIEWS:
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object; cam.name = f"cam_{name}"
    cam.data.type        = "ORTHO"
    cam.data.ortho_scale = ortho
    cam.rotation_euler   = (centroid - cam.location).to_track_quat("-Z", "Y").to_euler()
    scene.camera         = cam
    scene.render.filepath = str(outdir / f"6view_{name}.png")
    bpy.ops.render.render(write_still=True)
    bpy.data.objects.remove(cam, do_unlink=True)
    print(f"[forge-render] 6-view {name} → {scene.render.filepath}")
```

---

## §wireframe. Wireframe variant

Use Workbench with `show_wireframe = True`. The solid mesh color is set to neutral grey so
wire edges are clearly visible.

```python
# Add after the base Workbench setup (before render):
d = scene.display.shading
d.light                   = "FLAT"
d.color_type              = "SINGLE"
d.single_color            = (0.6, 0.6, 0.6)   # neutral grey base
d.show_wireframe          = True
d.wireframe_color_type    = "THEME"            # THEME | OBJECT | CUSTOM
d.show_cavity             = False
d.show_xray               = False              # True for xray (see-through wire)
d.xray_alpha              = 0.3

scene.render.filepath = str(outdir / f"wireframe_{int(angle_deg):03d}deg.png")
bpy.ops.render.render(write_still=True)

# Restore for next variant:
d.show_wireframe = False
```

**Wireframe QA checklist:**
- Edge density uniform — no dense pole clusters (>6 edges at vertex is a red flag for SDS)
- No stray floating edges or isolated vertices (appear as disconnected dots)
- N-gons (faces with >4 edges) appear as irregular polygons — flag for subdivision compatibility
- Concave/hollow geometry shows correctly (edge flow readable)

---

## §matcap. Matcap variant

Matcap is the fastest way to visually detect inverted normals and shading seams. Black
patches on a smooth surface = inverted normals.

```python
d = scene.display.shading
d.light          = "MATCAP"
d.color_type     = "MATERIAL"
d.show_cavity    = True       # cavity reveals curvature breaks and seams
d.show_shadows   = False
d.show_wireframe = False

# Optionally select a specific matcap:
# d.studio_light = "metal_carpaint.exr"  # from Blender's built-in matcap library
```

**Matcap QA checklist:**
- Smooth gradient across surfaces → correct normals + smooth shading
- Black patches → inverted normals (fix: `bmesh.ops.recalc_face_normals`)
- Hard seam where smooth shading should flow → missing auto-smooth or wrong crease angle
- Faceting where subdivision should round → subdivision level too low or not applied

---

## §uvchecker. UV checker (temporary Cycles switch)

Workbench ignores shader node graphs — a checker node material renders as flat grey.
For accurate UV checker visualization, temporarily switch to Cycles CPU (16 samples).

```python
# Create the checker material
MAT_NAME = "__forge_uv_checker__"
if MAT_NAME not in bpy.data.materials:
    mat   = bpy.data.materials.new(MAT_NAME); mat.use_nodes = True
    nodes = mat.node_tree.nodes; links = mat.node_tree.links; nodes.clear()
    out     = nodes.new("ShaderNodeOutputMaterial")
    bsdf    = nodes.new("ShaderNodeBsdfDiffuse")
    checker = nodes.new("ShaderNodeTexChecker")
    uv      = nodes.new("ShaderNodeTexCoord")
    checker.inputs["Scale"].default_value      = 8.0
    checker.inputs["Color1"].default_value     = (1.0, 0.3, 0.1, 1.0)   # orange
    checker.inputs["Color2"].default_value     = (0.9, 0.9, 0.9, 1.0)   # near-white
    links.new(uv.outputs["UV"],       checker.inputs["Vector"])
    links.new(checker.outputs["Color"], bsdf.inputs["Color"])
    links.new(bsdf.outputs["BSDF"],   out.inputs["Surface"])
else:
    mat = bpy.data.materials[MAT_NAME]

# Save originals and assign checker
saved = {}
for obj in scene.objects:
    if obj.type == "MESH":
        saved[obj.name] = [slot.material for slot in obj.material_slots]
        for slot in obj.material_slots: slot.material = mat
        if not obj.material_slots: obj.data.materials.append(mat)

# Switch to Cycles CPU (safe headless, no GPU needed, 16 samples enough for UV QA)
scene.render.engine          = "CYCLES"
scene.cycles.samples         = 16
scene.cycles.use_denoising   = False
scene.cycles.device          = "CPU"   # explicit CPU — GPU not needed for UV checker
scene.render.filepath        = str(outdir / f"uv_checker_{int(angle_deg):03d}deg.png")
bpy.ops.render.render(write_still=True)

# Restore original materials + engine
for obj in scene.objects:
    if obj.type == "MESH" and obj.name in saved:
        for i, slot in enumerate(obj.material_slots):
            if i < len(saved[obj.name]): slot.material = saved[obj.name][i]
bpy.data.materials.remove(mat, do_unlink=True)
scene.render.engine = "BLENDER_WORKBENCH"
```

**UV checker QA checklist:**
- Uniform checker square size across the surface → even texel density
- Distorted/elongated squares → UV stretching (>2:1 ratio is problematic)
- Very small squares → over-scaled UV region (wasted texture resolution)
- Seams visible at UV island boundaries → expected; seams at unexpected locations → UV island placement error
- Black/grey result instead of colour → still on Workbench engine (see §gotchas in `cycles-gpu-passes.md`)

---

## §normals-wb. Flat-normal variant (Workbench per-object random color)

For a quick topology read (not true world-space normals — see `cycles-gpu-passes.md §normals`
for accurate normal pass). Each object gets a random color; topology breaks read as
color discontinuities between adjacent faces.

```python
d = scene.display.shading
d.light      = "FLAT"
d.color_type = "RANDOM"   # random-per-object; reveals disconnected pieces
d.show_cavity = False
d.show_shadows = False
```

---

## §qa-table. Engine selection quick reference

| Render variant | Engine | Headless-safe (Win) | Speed | Rationale |
|---|---|---|---|---|
| Turntable QA | `BLENDER_WORKBENCH` | Yes | ~1 s | Fast, no GPU, good enough for silhouette/topology |
| Wireframe | `BLENDER_WORKBENCH` | Yes | ~1 s | Fastest; `show_wireframe = True` |
| Matcap / cavity | `BLENDER_WORKBENCH` | Yes | ~1 s | Built-in matcap library; reveals normal defects |
| 6-view ortho | `BLENDER_WORKBENCH` | Yes | ~1 s | Orthographic projection; no perspective distortion |
| UV checker | `CYCLES` CPU 16 spl | Yes | ~5–15 s | Workbench ignores node materials |
| Normal pass (world-space) | `CYCLES` CPU 1 spl | Yes | ~2–5 s | Compositor normal remap required |
| Beauty / hero still | `CYCLES` GPU/CPU | Yes (CPU; GPU if available) | 30–120 s | PBR path tracing; AgX |
| EEVEE Next | `BLENDER_EEVEE_NEXT` | **NO** | — | Requires GPU display context; crashes headless on Windows |
