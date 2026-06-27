# forge-uv — UDIM Reference

# Contents
- §1. UDIM numbering scheme
- §2. When to use UDIMs
- §3. Create a TILED image and add tiles (bpy)
- §4. Distribute UV islands to UDIM tiles
- §5. UDIM export and UV layout PNG

---

## §1. UDIM numbering scheme

UDIM tiles are numbered starting at **1001** using the formula:

```
UDIM = 1001 + col + (10 × row)
```

Where `col` ∈ 0–9 and `row` ∈ 0–9, giving a maximum 10×10 = 100 tiles.

| UV offset | UDIM number | Col | Row |
|-----------|------------|-----|-----|
| (0, 0) | 1001 | 0 | 0 |
| (1, 0) | 1002 | 1 | 0 |
| (2, 0) | 1003 | 2 | 0 |
| (0, 1) | 1011 | 0 | 1 |
| (1, 1) | 1012 | 1 | 1 |
| (0, 2) | 1021 | 0 | 2 |

**Reverse formula** (given a UDIM number):
```
col = (udim - 1001) % 10
row = (udim - 1001) // 10
UV offset = (col, row)
```

**Software support:**
- Blender 4.x: native TILED image source; UV editor shows UDIM tiles as grid.
- Substance Painter: full UDIM support; import the TILED .exr/.png sequence.
- Mari: native UDIM; the original UDIM-aware DCC.
- Photoshop: manual tile management only.
- Three.js / glTF: NO native UDIM support. Must flatten to a single texture atlas before export.

---

## §2. When to use UDIMs

**Use UDIM when:**
- Asset requires >4096 × 4096 texture detail (film/VFX hero characters, vehicles).
- Target DCC is Substance Painter + Mari workflow.
- Asset has many distinct material regions (character body, face, armor, accessories) that each
  deserve full texture resolution.
- Texel density target > 2048 px/m (impossible to fit in a single 4K tile).

**Do NOT use UDIM when:**
- Target is three.js / glTF / web — UDIMs must be flattened to a single tile before export.
- Target is a game engine (Unity/Unreal) for real-time rendering — bake to atlas instead.
- Asset is a background/LOD prop — single 1K or 2K tile is sufficient.

---

## §3. Create a TILED image and add tiles (bpy)

```python
import bpy

def create_udim_image(name: str, tile_ids: list, width=4096, height=4096, color=(0,0,0,1)):
    """
    Create a new TILED (UDIM) image datablock in Blender.

    tile_ids: list of UDIM numbers, e.g. [1001, 1002, 1003, 1011]
    The image is created empty (procedurally generated); assign texture paths later
    when painting in Substance Painter / Mari.
    """
    img = bpy.data.images.new(name=name, width=width, height=height, alpha=True)
    img.source = 'TILED'    # Switch to UDIM/TILED mode

    # Tile 1001 already exists; add remaining tiles
    existing = {t.number for t in img.tiles}
    for uid in tile_ids:
        if uid not in existing:
            img.tiles.new(tile_number=uid)
            existing.add(uid)

    print(f"[INFO] UDIM image '{name}' created with tiles: {sorted(existing)}")
    return img


def add_tiles_to_existing(image_name: str, tile_ids: list):
    """Add UDIM tiles to an existing TILED image datablock."""
    img = bpy.data.images.get(image_name)
    if not img:
        print(f"[ERROR] Image '{image_name}' not found")
        return
    if img.source != 'TILED':
        print(f"[ERROR] '{image_name}' is not a TILED image (source={img.source})")
        return
    existing = {t.number for t in img.tiles}
    for uid in tile_ids:
        if uid not in existing:
            img.tiles.new(tile_number=uid)
    print(f"[INFO] Tiles for '{image_name}': {sorted(t.number for t in img.tiles)}")
```

---

## §4. Distribute UV islands to UDIM tiles

```python
import bpy
import bmesh

def move_island_to_udim(obj, face_indices: list, udim_number: int):
    """
    Offset selected face UVs to the UDIM tile corresponding to udim_number.

    udim_number: e.g. 1002 → col=1, row=0 → UV offset (+1, 0)
    face_indices: list of face.index integers to move (all other faces are deselected)

    IMPORTANT: Only moves faces in the active UV layer.
    Run ensure_uv_layer(obj, "UVMap") before calling if needed.
    """
    col = (udim_number - 1001) % 10
    row = (udim_number - 1001) // 10

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer = bm.loops.layers.uv.active

    face_set = set(face_indices)
    for face in bm.faces:
        face.select = face.index in face_set
        for loop in face.loops:
            luv = loop[uv_layer]
            luv.select = face.index in face_set

    # Offset UVs to target tile
    for face in bm.faces:
        if face.index in face_set:
            for loop in face.loops:
                loop[uv_layer].uv.x += col
                loop[uv_layer].uv.y += row

    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[INFO] {len(face_indices)} faces moved to UDIM {udim_number} (tile offset {col},{row})")


def distribute_by_material_to_udim(obj, material_to_udim: dict):
    """
    Map each material slot to a UDIM tile and distribute face UVs accordingly.

    material_to_udim: e.g. {'Body': 1001, 'Face': 1002, 'Armor': 1003}

    Typical workflow:
    1. Model with separate material slots per body region.
    2. Call this function to distribute UV islands to the correct UDIM tiles.
    3. Pack each UDIM tile individually (using udim_source='ACTIVE_UDIM' in pack_islands).
    4. Export to Substance Painter for UDIM-aware painting.
    """
    bpy.context.view_layer.objects.active = obj
    me = obj.data

    # Build face index lists per material index
    mat_to_faces = {}
    for poly in me.polygons:
        mat_idx = poly.material_index
        if mat_idx not in mat_to_faces:
            mat_to_faces[mat_idx] = []
        mat_to_faces[mat_idx].append(poly.index)

    # Apply UDIM offsets
    for mat_name, udim_num in material_to_udim.items():
        mat_idx = None
        for i, slot in enumerate(obj.material_slots):
            if slot.material and slot.material.name == mat_name:
                mat_idx = i
                break
        if mat_idx is None:
            print(f"[WARN] Material '{mat_name}' not found on {obj.name} — skip")
            continue
        face_list = mat_to_faces.get(mat_idx, [])
        if not face_list:
            print(f"[WARN] No faces with material '{mat_name}' — skip")
            continue
        move_island_to_udim(obj, face_list, udim_num)
```

---

## §5. UDIM export and UV layout PNG

```python
import bpy
import os
import addon_utils

def export_udim_uv_layout(obj, output_dir: str, size=(4096, 4096)):
    """
    Export UV layout PNGs for a UDIM-tiled UV map.
    Creates one PNG per UDIM tile: e.g. <obj.name>_1001.png, <obj.name>_1002.png ...

    Requires io_mesh_uv_layout addon (enabled by default in Blender 4.x; must be
    explicitly enabled in --background mode).
    """
    addon_utils.enable("io_mesh_uv_layout", default_set=True, persistent=True)
    os.makedirs(output_dir, exist_ok=True)

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # The filepath uses Blender's UDIM tile substitution: <UDIM> in the path
    udim_path = os.path.join(output_dir, f"{obj.name}_<UDIM>.png").replace("\\", "/")
    bpy.ops.uv.export_layout(
        filepath=udim_path,
        export_all=True,
        export_tiles='UDIM',        # 'NONE' = 0-1 only | 'UDIM' = UDIM scheme | 'UV' = UVTILE
        mode='PNG',
        size=size,
        opacity=0.0,                # 0.0 = wire-only; 1.0 = filled
        check_existing=False,
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[INFO] UDIM UV layout exported to {output_dir}/")


def flatten_udim_for_gltf(obj, texture_px=4096):
    """
    Flatten UDIM UVs back into the 0-1 range for glTF export.
    Three.js / glTF does not support UDIM; all UVs must be in [0, 1] × [0, 1].

    Strategy: scale the entire UV layout to fit within 0-1 by dividing by the
    tile extent (e.g., 2 tiles wide × 2 tiles tall = divide U by 2, V by 2).
    This bakes all UDIM detail into a single atlas texture.

    After calling this, rebake all textures to a single atlas at texture_px resolution.
    """
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return

    # Find UV extents
    min_u = min_v = float('inf')
    max_u = max_v = float('-inf')
    for face in bm.faces:
        for loop in face.loops:
            u, v = loop[uv_layer].uv
            min_u = min(min_u, u); max_u = max(max_u, u)
            min_v = min(min_v, v); max_v = max(max_v, v)

    u_range = max(max_u - min_u, 1.0)
    v_range = max(max_v - min_v, 1.0)

    # Normalize to 0-1
    for face in bm.faces:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            uv.x = (uv.x - min_u) / u_range
            uv.y = (uv.y - min_v) / v_range

    bm.to_mesh(obj.data)
    bm.free()
    obj.data.update()
    print(f"[INFO] {obj.name}: UDIMs flattened to 0-1 range (U/{u_range:.0f} V/{v_range:.0f})")
    print(f"[WARN] Rebake all textures to a {texture_px}px atlas — UDIM detail is now compressed.")
```

**UDIM → glTF pipeline:**
1. Author in UDIM → paint in Substance Painter → bake per-tile textures.
2. Call `flatten_udim_for_gltf()` to collapse UV space.
3. Bake all maps to a single 4096 × 4096 atlas.
4. Export to GLB via `Skill("forge-export")`.
5. Optimize with `Skill("forge-optimize")` (KTX2 compression, Draco/Meshopt geometry).
