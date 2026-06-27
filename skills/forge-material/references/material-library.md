# Material Library Pattern — forge-material reference

Reusable Blender material library: save materials to `.blend` files, append them in other
scenes, and build node groups for shared PBR sub-graphs.

---

## Save a Material to a Library File

```python
# Inside Blender bpy context (run via: blender -b -P script.py)
from pathlib import Path
import bpy

def save_material_to_library(mat: bpy.types.Material, lib_path: str) -> None:
    """
    Pack images into the blend and write material to a library .blend file.
    Creates parent directories if they don't exist.
    lib_path example: "C:/forge/material_library/metals.blend"
    """
    # Pack all images so the library is self-contained
    for img in bpy.data.images:
        if img.users > 0 and not img.packed_file:
            img.pack()

    data_blocks = {mat}
    # Include node groups used by the material
    for node in mat.node_tree.nodes:
        if node.type == 'GROUP' and node.node_tree:
            data_blocks.add(node.node_tree)

    Path(lib_path).parent.mkdir(parents=True, exist_ok=True)
    bpy.data.libraries.write(
        lib_path,
        data_blocks,
        fake_user=True,    # prevent garbage collection in the library file
        compress=False,    # uncompressed for faster disk reads
    )
    print(f"[forge-material] Saved '{mat.name}' to {lib_path}")
```

## Append a Material from a Library

```python
def append_material(mat_name: str, lib_blend: str) -> bpy.types.Material:
    """
    Append (local editable copy) a material from a library .blend file.
    Returns the material, or raises ValueError if mat_name not found.
    """
    existing = bpy.data.materials.get(mat_name)
    if existing:
        return existing

    mats_before = set(bpy.data.materials)
    with bpy.data.libraries.load(lib_blend, link=False, relative=False) as (src, dst):
        if mat_name not in src.materials:
            raise ValueError(
                f"Material '{mat_name}' not found in {lib_blend}. "
                f"Available: {list(src.materials)}"
            )
        dst.materials = [mat_name]

    new_mats = set(bpy.data.materials) - mats_before
    mat = next(iter(new_mats), None) or bpy.data.materials.get(mat_name)
    if mat:
        mat.use_fake_user = True  # prevent garbage collection on scene save
    return mat
```

## Recommended Library Structure on Disk

```
C:\forge\material_library\
    metals.blend           # Metal_Chrome, Metal_Gold, Metal_Iron, ...
    dielectrics.blend      # Plastic_Matte, Plastic_Glossy, Rubber, ...
    naturals.blend         # Concrete, Wood_Oak, Stone_Granite, ...
    emissives.blend        # LED_Panel, Neon_Tube, ...
    blender_assets.cats.txt   # catalog hierarchy for Asset Browser
```

`blender_assets.cats.txt` format:
```
VERSION 1
# <UUID>:<path>:<display-name>
e4e57f2c-1234-5678-abcd-aabbccddeeff:Metals:Metals
a1b2c3d4-abcd-efgh-1234-000000000001:Metals/Ferrous:Metals/Ferrous
```

## Reusable Node Group (PBR Core)

A node group encapsulates the ORM + Normal Map wiring and can be reused across materials:

```python
def create_pbr_node_group(group_name: str = "PBR_Core") -> bpy.types.NodeGroup:
    """
    Create a reusable node group:
      Inputs:  Base Color (RGBA), ORM (Color), Normal Map (Color)
      Output:  BSDF (Shader)
    """
    ng = bpy.data.node_groups.new(group_name, 'ShaderNodeTree')
    in_node  = ng.nodes.new('NodeGroupInput')
    out_node = ng.nodes.new('NodeGroupOutput')

    # 4.0+ interface API
    ng.interface.new_socket('Base Color', in_out='INPUT',  socket_type='NodeSocketColor')
    ng.interface.new_socket('ORM',        in_out='INPUT',  socket_type='NodeSocketColor')
    ng.interface.new_socket('Normal Map', in_out='INPUT',  socket_type='NodeSocketColor')
    ng.interface.new_socket('BSDF',       in_out='OUTPUT', socket_type='NodeSocketShader')

    bsdf = ng.nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.distribution = 'MULTI_GGX'

    sep = ng.nodes.new('ShaderNodeSeparateColor')  # 4.2+
    sep.mode = 'RGB'

    norm = ng.nodes.new('ShaderNodeNormalMap')
    norm.space = 'TANGENT'

    links = ng.links
    links.new(in_node.outputs['Base Color'], bsdf.inputs['Base Color'])
    links.new(in_node.outputs['ORM'],        sep.inputs['Color'])
    links.new(sep.outputs['Green'],          bsdf.inputs['Roughness'])
    links.new(sep.outputs['Blue'],           bsdf.inputs['Metallic'])
    links.new(in_node.outputs['Normal Map'], norm.inputs['Color'])
    links.new(norm.outputs['Normal'],        bsdf.inputs['Normal'])
    links.new(bsdf.outputs['BSDF'],          out_node.inputs['BSDF'])

    return ng


def use_node_group_in_material(mat: bpy.types.Material,
                               ng: bpy.types.NodeGroup) -> bpy.types.Node:
    """Instantiate the node group inside a material. Caller wires textures to inputs."""
    nodes = mat.node_tree.nodes
    group_node = nodes.new('ShaderNodeGroup')
    group_node.node_tree = ng
    return group_node
```

## Usage Example

```python
# Build a Chrome material and save to library
def build_chrome(name="Metal_Chrome") -> bpy.types.Material:
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes['Principled BSDF']
    bsdf.distribution = 'MULTI_GGX'
    bsdf.inputs['Base Color'].default_value = (0.916, 0.923, 0.924, 1.0)  # Al F0
    bsdf.inputs['Metallic'].default_value   = 1.0
    bsdf.inputs['Roughness'].default_value  = 0.05
    bsdf.inputs['IOR'].default_value        = 1.5
    return mat

chrome = build_chrome()
save_material_to_library(chrome, "C:/forge/material_library/metals.blend")

# In a different scene, load it back
chrome_copy = append_material("Metal_Chrome", "C:/forge/material_library/metals.blend")
# Assign to object
obj = bpy.data.objects.get("SphereObj")
if obj:
    if obj.data.materials:
        obj.data.materials[0] = chrome_copy
    else:
        obj.data.materials.append(chrome_copy)
```
