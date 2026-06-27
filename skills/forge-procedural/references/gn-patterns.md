# Geometry Nodes via Python — Reference

**Blender target:** 4.2 LTS – 4.5 / 5.x  
**All API shown uses Blender 4.0+ interface (ng.interface.new_socket).**

## Contents
§1 Headless invocation · §2 Idempotent boilerplate · §3 Node identifier table · §4 Set modifier inputs · §5 Scatter script · §6 Curve-to-mesh sweep · §7 Greeble pattern · §8 Noise attribute · §9 Export helpers · §10 Gotcha table

---

## §1. Headless invocation (PowerShell)

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender\blender.exe"

# Canonical: run script against blank scene
& $blender -b --factory-startup -P "C:\MyProject\build.py" -- --seed 42 --density 3.0

# With existing .blend as base
& $blender -b "C:\MyProject\base.blend" -P "C:\MyProject\modify.py" -- --seed 7

# Render a single frame after the script
& $blender -b --factory-startup -P "C:\MyProject\build.py" `
    -o "C:/out/frame_####" -F PNG -f 1 `
    -- --seed 42

# --factory-startup: disables user addons/themes → deterministic, faster CI
# -P must come BEFORE -f / -a (render trigger); script runs first, render last
# -- is MANDATORY; everything after it goes to sys.argv in the Python script
```

**Parse custom args inside the script:**
```python
import sys, argparse
argv = sys.argv
user_args = argv[argv.index("--") + 1:] if "--" in argv else []
p = argparse.ArgumentParser()
p.add_argument("--seed",    type=int,   default=0)
p.add_argument("--density", type=float, default=2.0)
p.add_argument("--out",     type=str,   default="C:/out/result.png")
args = p.parse_args(user_args)
```

---

## §2. Idempotent node-tree boilerplate (Blender 4.0+)

```python
import bpy

def create_gn_modifier(obj: bpy.types.Object, tree_name: str):
    """
    Create a blank GeometryNodes modifier on obj.
    Idempotent: removes existing modifier/node-group with same name first.
    Returns (modifier, node_tree).
    """
    # Remove stale modifier
    existing = obj.modifiers.get(tree_name)
    if existing:
        obj.modifiers.remove(existing)

    # Remove stale node group (prevents .001 accumulation)
    old_ng = bpy.data.node_groups.get(tree_name)
    if old_ng:
        bpy.data.node_groups.remove(old_ng)

    # Create node group
    ng = bpy.data.node_groups.new(tree_name, "GeometryNodeTree")

    # Blender 4.0+ interface API — NEVER use ng.inputs.new / ng.outputs.new
    ng.interface.new_socket(name="Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
    ng.interface.new_socket(name="Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")

    nodes = ng.nodes
    n_in  = nodes.new("NodeGroupInput");  n_in.location  = (-800, 0)
    n_out = nodes.new("NodeGroupOutput"); n_out.location = ( 800, 0)
    # Bare passthrough so modifier is valid before inner nodes are added
    ng.links.new(n_in.outputs["Geometry"], n_out.inputs["Geometry"])

    mod = obj.modifiers.new(tree_name, "NODES")
    mod.node_group = ng
    return mod, ng
```

---

## §3. Core node identifier table

| Node label | `nodes.new()` identifier | Key properties |
|---|---|---|
| Group Input | `NodeGroupInput` | outputs auto-match interface sockets |
| Group Output | `NodeGroupOutput` | inputs auto-match interface sockets |
| Mesh Grid | `GeometryNodeMeshGrid` | `vertices_x`, `vertices_y`, `size_x`, `size_y` |
| Mesh Cube | `GeometryNodeMeshCube` | `inputs["Size"].default_value` (Vector) |
| UV Sphere | `GeometryNodeMeshUVSphere` | `segments`, `rings`, `inputs["Radius"]` |
| Subdivide Mesh | `GeometryNodeSubdivideMesh` | `inputs["Level"].default_value` |
| Set Position | `GeometryNodeSetPosition` | `inputs["Offset"]` |
| **Distribute Points on Faces** | `GeometryNodeDistributePointsOnFaces` | `distribute_method` (`'RANDOM'`/`'POISSON'`), `inputs["Density"]`, `inputs["Density Max"]`, `inputs["Distance Min"]`, `inputs["Seed"]` |
| **Instance on Points** | `GeometryNodeInstanceOnPoints` | `inputs["Pick Instance"]`, `inputs["Instance Index"]`, `inputs["Rotation"]`, `inputs["Scale"]` |
| Realize Instances | `GeometryNodeRealizeInstances` | — |
| Join Geometry | `GeometryNodeJoinGeometry` | multi-input: call `links.new()` multiple times to same input |
| Collection Info | `GeometryNodeCollectionInfo` | `transform_space`, `inputs["Collection"].default_value`, `inputs["Separate Children"]` |
| Store Named Attribute | `GeometryNodeStoreNamedAttribute` | `data_type`, `domain`, `inputs["Name"].default_value` |
| Capture Attribute | `GeometryNodeCaptureAttribute` | 4.2+: `node.capture_items.new(socket_type, name)` |
| Random Value | `FunctionNodeRandomValue` | `data_type` (`'FLOAT'`/`'INT'`/`'FLOAT_VECTOR'`/`'BOOLEAN'`); Min/Max are duplicated per type — set by INDEX, not name: Float=`inputs[2]/[3]` (scalars), Int=`inputs[4]/[5]` (ints), Vector=`inputs[0]/[1]` (3-tuples) |
| Noise Texture | `ShaderNodeTexNoise` | `inputs["Scale"]`, `inputs["Detail"]`, `inputs["Roughness"]`, `inputs["W"]` |
| Math | `ShaderNodeMath` | `operation` (`'ADD'`, `'MULTIPLY'`, `'SINE'`, etc.) |
| Vector Math | `ShaderNodeVectorMath` | `operation` (`'ADD'`, `'NORMALIZE'`, `'LENGTH'`) |
| Map Range | `ShaderNodeMapRange` | `data_type`, `interpolation_type` |
| Combine XYZ | `ShaderNodeCombineXYZ` | — |
| Separate XYZ | `ShaderNodeSeparateXYZ` | — |
| Position | `GeometryNodeInputPosition` | field: outputs per-vertex world position |
| Index | `GeometryNodeInputIndex` | — |
| Curve to Mesh | `GeometryNodeCurveToMesh` | `inputs["Fill Caps"].default_value` |
| Resample Curve | `GeometryNodeResampleCurve` | `mode` (`'COUNT'`/`'LENGTH'`), `inputs["Count"]` |
| Curve Circle | `GeometryNodeCurvePrimitiveCircle` | `mode = 'RADIUS'`, `inputs["Radius"]` |
| Align Rotation to Vector | `GeometryNodeAlignRotationToVector` | `axis` (`'Z'`), `factor` |
| Set Material | `GeometryNodeSetMaterial` | `inputs["Material"].default_value = bpy.data.materials["MyMat"]` |
| Set Shade Smooth | `GeometryNodeSetShadeSmooth` | — |
| Transform Geometry | `GeometryNodeTransform` | `inputs["Translation"]`, `inputs["Rotation"]`, `inputs["Scale"]` |
| Object Info | `GeometryNodeObjectInfo` | `inputs["Object"]` |
| Delete Geometry | `GeometryNodeDeleteGeometry` | `domain`, `mode` |

---

## §4. Setting modifier inputs by name (Blender 4.0+)

```python
def set_gn_input(obj, mod_name: str, socket_name: str, value):
    """Set a GN modifier input by display name. Blender 4.0+ compatible."""
    mod = obj.modifiers[mod_name]
    items = mod.node_group.interface.items_tree
    sock = next(
        (s for s in items if getattr(s, "in_out", None) == "INPUT" and s.name == socket_name),
        None
    )
    if sock is None:
        raise KeyError(f"No INPUT socket '{socket_name}' in modifier '{mod_name}'")
    mod[sock.identifier] = value

# Usage
set_gn_input(obj, "ForgeScatter", "Seed", 42)
set_gn_input(obj, "ForgeScatter", "Density", 3.5)
```

**Never** use `mod["Density"] = value` by display name — it silently fails. Use `mod[sock.identifier]`.

---

## §5. Scatter system — full working script

```python
# Usage: blender -b --factory-startup -P forge_scatter.py -- --seed 7 --density 3.0 --out C:/out/scatter.png
import bpy, sys, argparse, math, os, io
from mathutils import Vector
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
argv = sys.argv; user_args = argv[argv.index("--") + 1:] if "--" in argv else []
p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=0); p.add_argument("--density", type=float, default=2.0)
p.add_argument("--out",  type=str, default="C:/out/scatter.png")
args = p.parse_args(user_args)

bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=True)
bpy.ops.mesh.primitive_plane_add(size=10, location=(0, 0, 0))
obj = bpy.context.active_object

NG = "ForgeScatter"
existing = obj.modifiers.get(NG)
if existing: obj.modifiers.remove(existing)
old_ng = bpy.data.node_groups.get(NG)
if old_ng: bpy.data.node_groups.remove(old_ng)

ng = bpy.data.node_groups.new(NG, "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
nodes = ng.nodes; links = ng.links

n_in  = nodes.new("NodeGroupInput");  n_in.location  = (-800, 0)
n_out = nodes.new("NodeGroupOutput"); n_out.location  = ( 800, 0)

dist = nodes.new("GeometryNodeDistributePointsOnFaces")
dist.distribute_method = 'POISSON'           # no overlap
dist.inputs["Distance Min"].default_value = 0.4
dist.inputs["Density Max"].default_value  = args.density
dist.inputs["Seed"].default_value         = args.seed
dist.location = (-500, 0)

cube = nodes.new("GeometryNodeMeshCube")
cube.inputs["Size"].default_value = (0.3, 0.3, 0.3)
cube.location = (-400, -300)

rand_rot = nodes.new("FunctionNodeRandomValue")
rand_rot.data_type = "FLOAT_VECTOR"
# FLOAT_VECTOR: the active Min/Max ARE the Vector sockets (index 0/1) → named access
# is correct here and a 3-tuple is required. (For FLOAT/INT, index by socket — see §10.)
rand_rot.inputs["Max"].default_value = (0.0, 0.0, math.tau)
rand_rot.inputs["Seed"].default_value = args.seed + 1
rand_rot.location = (-200, -200)

rand_scale = nodes.new("FunctionNodeRandomValue")
rand_scale.data_type = "FLOAT"
# Min/Max are duplicated per data_type — index the FLOAT pair (2/3) with scalars.
# inputs["Min"] resolves to the FIRST "Min" = the Vector socket (index 0) → wrong socket / ValueError.
rand_scale.inputs[2].default_value = 0.5          # Float Min
rand_scale.inputs[3].default_value = 1.5          # Float Max
rand_scale.inputs["Seed"].default_value = args.seed + 2
rand_scale.location = (-200, -400)

combine_s = nodes.new("ShaderNodeCombineXYZ"); combine_s.location = (0, -400)

inst = nodes.new("GeometryNodeInstanceOnPoints"); inst.location = (200, 0)
realize = nodes.new("GeometryNodeRealizeInstances"); realize.location = (500, 0)

links.new(n_in.outputs["Geometry"],        dist.inputs["Mesh"])
links.new(dist.outputs["Points"],          inst.inputs["Points"])
links.new(rand_rot.outputs["Value"],       inst.inputs["Rotation"])
links.new(rand_scale.outputs["Value"],     combine_s.inputs["X"])
links.new(rand_scale.outputs["Value"],     combine_s.inputs["Y"])
links.new(rand_scale.outputs["Value"],     combine_s.inputs["Z"])
links.new(combine_s.outputs["Vector"],     inst.inputs["Scale"])
links.new(cube.outputs["Mesh"],            inst.inputs["Instance"])
links.new(inst.outputs["Instances"],       realize.inputs["Geometry"])
links.new(realize.outputs["Geometry"],     n_out.inputs["Geometry"])

mod = obj.modifiers.new(NG, "NODES")
mod.node_group = ng

# Cycles render (EEVEE-Next unsupported headless on Windows)
scene = bpy.context.scene
scene.render.engine = 'CYCLES'; scene.cycles.samples = 64; scene.cycles.use_denoising = True
scene.render.resolution_x = 1280; scene.render.resolution_y = 720
scene.render.image_settings.file_format = 'PNG'
os.makedirs(os.path.dirname(args.out), exist_ok=True)
scene.render.filepath = args.out.replace("\\", "/")
bpy.ops.object.camera_add(location=(0, -15, 10), rotation=(math.radians(55), 0, 0))
scene.camera = bpy.context.active_object
bpy.ops.object.light_add(type='SUN', location=(5, 5, 10)); bpy.context.object.data.energy = 3.0
bpy.ops.render.render(write_still=True); print(f"[Forge] Rendered → {args.out}")
```

---

## §6. Curve-to-mesh sweep

```python
# Pattern: Curve → Resample → CurveToMesh (profile=CurveCircle) → SetShadeSmooth
import bpy
bpy.ops.object.select_all(action='SELECT'); bpy.ops.object.delete(use_global=True)

bpy.ops.curve.primitive_bezier_curve_add()
path_obj = bpy.context.active_object

ng = bpy.data.node_groups.new("ForgeRail", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
# Expose radius as group parameter
sock_r = ng.interface.new_socket("Radius", in_out="INPUT", socket_type="NodeSocketFloat")
sock_r.default_value = 0.1; sock_r.min_value = 0.01; sock_r.max_value = 2.0

nodes = ng.nodes; links = ng.links
n_in  = nodes.new("NodeGroupInput");  n_in.location  = (-800, 0)
n_out = nodes.new("NodeGroupOutput"); n_out.location  = ( 600, 0)

resample = nodes.new("GeometryNodeResampleCurve")
resample.mode = 'COUNT'; resample.inputs["Count"].default_value = 64; resample.location = (-500, 0)

circle = nodes.new("GeometryNodeCurvePrimitiveCircle")
circle.mode = 'RADIUS'; circle.inputs["Resolution"].default_value = 16; circle.location = (-300, -200)

c2m = nodes.new("GeometryNodeCurveToMesh")
c2m.inputs["Fill Caps"].default_value = True; c2m.location = (100, 0)

shade = nodes.new("GeometryNodeSetShadeSmooth"); shade.location = (350, 0)

links.new(n_in.outputs["Geometry"],  resample.inputs["Curve"])
links.new(n_in.outputs["Radius"],    circle.inputs["Radius"])
links.new(resample.outputs["Curve"], c2m.inputs["Curve"])
links.new(circle.outputs["Curve"],   c2m.inputs["Profile Curve"])
links.new(c2m.outputs["Mesh"],       shade.inputs["Geometry"])
links.new(shade.outputs["Geometry"], n_out.inputs["Geometry"])

mod = path_obj.modifiers.new("ForgeRail", "NODES")
mod.node_group = ng
```

---

## §7. Greeble pattern

```python
# Requires collection "GreeblePieces" to exist in the scene.
import bpy, math

ng = bpy.data.node_groups.new("ForgeGreeble", "GeometryNodeTree")
ng.interface.new_socket("Geometry", in_out="INPUT",  socket_type="NodeSocketGeometry")
ng.interface.new_socket("Geometry", in_out="OUTPUT", socket_type="NodeSocketGeometry")
seed_s = ng.interface.new_socket("Seed", in_out="INPUT", socket_type="NodeSocketInt")
seed_s.default_value = 0
dens_s = ng.interface.new_socket("Density", in_out="INPUT", socket_type="NodeSocketFloat")
dens_s.default_value = 4.0; dens_s.min_value = 0.1; dens_s.max_value = 20.0

nodes = ng.nodes; links = ng.links
n_in  = nodes.new("NodeGroupInput");  n_in.location  = (-900, 0)
n_out = nodes.new("NodeGroupOutput"); n_out.location  = ( 800, 0)

dist = nodes.new("GeometryNodeDistributePointsOnFaces")
dist.distribute_method = 'POISSON'; dist.inputs["Distance Min"].default_value = 0.15; dist.location = (-600, 0)
links.new(n_in.outputs["Geometry"], dist.inputs["Mesh"])
links.new(n_in.outputs["Density"],  dist.inputs["Density Max"])
links.new(n_in.outputs["Seed"],     dist.inputs["Seed"])

col_info = nodes.new("GeometryNodeCollectionInfo")
col_info.transform_space = 'RELATIVE'
col_info.inputs["Collection"].default_value = bpy.data.collections.get("GreeblePieces")
col_info.inputs["Separate Children"].default_value = True; col_info.location = (-600, -300)

rand_idx = nodes.new("FunctionNodeRandomValue")
rand_idx.data_type = "INT"
rand_idx.inputs[4].default_value = 0; rand_idx.inputs[5].default_value = 7   # Int Min/Max (plain ints)
rand_idx.location = (-300, -200)
links.new(n_in.outputs["Seed"], rand_idx.inputs["Seed"])

rand_rot = nodes.new("FunctionNodeRandomValue")
# FLOAT_VECTOR: the active Min/Max ARE the Vector sockets (index 0/1), so the first
# "Max" by name is correct here, and a 3-tuple is required.
rand_rot.data_type = "FLOAT_VECTOR"; rand_rot.inputs["Max"].default_value = (0.0, 0.0, math.tau)
rand_rot.location = (-300, -400)

rand_scale = nodes.new("FunctionNodeRandomValue")
rand_scale.data_type = "FLOAT"
rand_scale.inputs[2].default_value = 0.7; rand_scale.inputs[3].default_value = 1.3   # Float Min/Max (scalars)
rand_scale.location = (-300, -600)

combine_s = nodes.new("ShaderNodeCombineXYZ"); combine_s.location = (-50, -600)
links.new(rand_scale.outputs["Value"], combine_s.inputs["X"])
links.new(rand_scale.outputs["Value"], combine_s.inputs["Y"])
links.new(rand_scale.outputs["Value"], combine_s.inputs["Z"])

inst = nodes.new("GeometryNodeInstanceOnPoints")
inst.inputs["Pick Instance"].default_value = True; inst.location = (100, 0)
links.new(dist.outputs["Points"],        inst.inputs["Points"])
links.new(rand_rot.outputs["Value"],     inst.inputs["Rotation"])
links.new(col_info.outputs["Instances"], inst.inputs["Instance"])
links.new(rand_idx.outputs["Value"],     inst.inputs["Instance Index"])
links.new(combine_s.outputs["Vector"],   inst.inputs["Scale"])

realize = nodes.new("GeometryNodeRealizeInstances"); realize.location = (400, 0)
join = nodes.new("GeometryNodeJoinGeometry"); join.location = (600, 0)
links.new(inst.outputs["Instances"],   realize.inputs["Geometry"])
links.new(n_in.outputs["Geometry"],    join.inputs["Geometry"])
links.new(realize.outputs["Geometry"], join.inputs["Geometry"])  # second link = multi-input
links.new(join.outputs["Geometry"],    n_out.inputs["Geometry"])
```

---

## §8. Noise attribute storage (condensed)

Pattern: `Position` → `TexNoise` → `StoreNamedAttribute(domain='POINT', data_type='FLOAT', name="surface_noise")`. Wire into the chain between existing geometry links. The named attribute is accessible downstream via the **Attribute** shader node (by name) or exported as vertex color. Key: `noise.noise_dimensions = '3D'`; `noise.inputs["W"].default_value = seed` (treats W as seed axis).

---

## §9. Export helpers

```python
import bpy, os

def export_gn_as_glb(obj, out_path: str):
    """Export object with GN modifier applied (realizes instances). Absolute path required."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True); bpy.context.view_layer.objects.active = obj
    bpy.ops.export_scene.gltf(
        filepath=out_path, export_format='GLB',
        use_selection=True, export_apply=True, export_materials='EXPORT'
    )
    print(f"[Forge] GLB → {out_path}")

def batch_export_variants(obj, mod_name, out_dir, seeds=(0, 1, 2, 3)):
    """Export one GLB per seed, non-destructive (export_apply copies)."""
    for seed in seeds:
        set_gn_input(obj, mod_name, "Seed", seed)
        export_gn_as_glb(obj, os.path.join(out_dir, f"variant_seed{seed:03d}.glb"))
```

---

## §10. Gotcha → fix table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AttributeError: 'GeometryNodeTree' object has no attribute 'inputs'` | Using pre-4.0 API | Replace with `ng.interface.new_socket(name, in_out, socket_type)` |
| `TypeError: NodeLinks.new(): expected NodeSocket, not NodeTreeInterfaceSocketFloat` | Linking interface object instead of node socket | Link via `n_in.outputs["SocketName"]`, NOT the `interface.new_socket()` return value |
| No file output after render | Output directory missing | `os.makedirs(out_dir, exist_ok=True)` before `render.render()` |
| `RuntimeError: Operator bpy.ops.export_scene.gltf.poll() failed` | No active object | `bpy.context.view_layer.objects.active = obj; obj.select_set(True)` |
| Exported GLB is empty (0 KB) | Instances not realized | Add `GeometryNodeRealizeInstances` before Group Output, OR use `export_apply=True` |
| `KeyError: key "Density" not found` | Socket name changed between Blender versions | Use integer index as fallback: `node.inputs[0]`; or print `list(node.inputs.keys())` |
| Windows path backslash error | Raw `\\` in filepath string | `scene.render.filepath = path.replace("\\", "/")` |
| `FunctionNodeRandomValue` writes wrong socket / `ValueError: sequence size is 1, expected 3` | Min/Max are duplicated per `data_type`; `inputs["Min"]` hits the FIRST "Min" = the Vector socket (index 0) | Never set Min/Max by the name `"Min"`/`"Max"`. Index the active type: Float=`inputs[2]/[3]` (scalars), Int=`inputs[4]/[5]` (ints), Vector=`inputs[0]/[1]` (3-tuples) |
| `ForgeScatter.001`, `.002` accumulate | Not cleaning up before recreating | `obj.modifiers.get(name)` → remove; `bpy.data.node_groups.get(name)` → remove |
| `bpy.ops.object.modifier_apply()` RuntimeError | Wrong context | `bpy.ops.object.mode_set(mode='OBJECT')` first, set active + selected |
| `GeometryNodeCaptureAttribute` `AttributeError: data_type` | Blender 4.2 changed API | Use `node.capture_items.new(socket_type='VALUE', name='MyCapture')` |
| `bpy.ops.export_scene.obj` not found | Removed in Blender 4.0 | Use `bpy.ops.wm.obj_export` instead |
| Script hangs at start | Windows AV scanning Blender Python | Add blender executable to AV exclusions |
