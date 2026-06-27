# Texel Density, UV Conventions & ORM Packing — forge-standards reference

## Contents
- §1. Texel density formula and tier table
- §2. UV Channel 1 — primary texture map conventions
- §3. UV Channel 2 — lightmap conventions
- §4. ORM channel-pack (AO + Roughness + Metallic)
- §5. bpy calculation snippet (no add-on required)
- §6. Lightmap UV auto-generation (bpy)
- §7. Common UV / TD pitfalls

---

## §1. Texel density formula and tier table

**Formula:**
```
Texel Density (px/m) = texture_resolution_px / object_dimension_m
```

Example: a 1×1 m floor tile with a 1024×1024 texture = **1024 px/m**.
A 0.5 m wide barrel with a 1024×1024 texture on its UV map (assuming 100% UV utilization) = **2048 px/m**.

**Industry standard tiers (2025):**

| Tier / Target | px/cm | px/m | Texture for 1 m² surface | When to use |
|--------------|-------|------|--------------------------|-------------|
| Hero (FPS weapon, main char face, key prop) | 20.48 | 2048 | 2048² for 1 m² | Screen-filling, player-scrutinized |
| Standard PC/console foreground prop | 10.24 | 1024 | 1024² for 1 m², or 2048² for 2 m² | Default for most props |
| Mid-range environment prop | 5.12 | 512 | 512² for 1 m², or 1024² tiled | Background, low-prominence |
| Distant / background element | 2.56 | 256 | 256² or tiled atlas | Rarely close to camera |
| Mobile foreground | 5.12 | 512 | 512² for 1 m² | Mid-range Android target |
| Mobile background | 1.28–2.56 | 128–256 | Tiled material, atlas | Memory-constrained |
| WebAR / WebGL | 5.12–10.24 | 512–1024 | Keep GLB total ≤ 4 MB | Balance quality vs file size |
| CryEngine / AAA baseline (Crytek reference) | 5.12 | 512 | "Green" in their TD debug view | Historical reference |

**UV utilization floors:**
- Hero assets: **≥ 85%** of the 0–1 UV space covered.
- Environment / background props: **≥ 75%**.
- Mobile assets: **≥ 80%** (memory is tight; waste is expensive).
- A UV utilization below 60% is a red flag — wasted texel budget or incorrect UV scale.

---

## §2. UV Channel 1 (index 0) — primary texture map

| Requirement | Rule |
|------------|------|
| Overlapping islands | **No overlaps** unless intentionally mirrored for symmetrical geometry (document it) |
| Island range | All islands within **0–1 UV space** (no UDIM unless engine explicitly supports it) |
| Island padding | **≥ 2 px** at target texture resolution (e.g. 4 px padding at 2048²; 2 px at 1024²) |
| Seam placement | Low-visibility areas: inside geometry, along natural material breaks, under edges |
| Utilization | ≥ 85% (hero) / ≥ 75% (env) of 0–1 space covered |
| Mirrored UV | Acceptable for symmetrical props (left=right half); mark clearly in FORGE_STANDARDS.json |

**Island padding formula:** `padding_px = 2 * ceil(texture_res / 256)`
At 2048²: 16 px. At 1024²: 8 px. Minimum 2 px even at 256².
Insufficient padding causes **texel bleeding** at mip levels — dark/light halos along UV island edges
visible in-engine at typical viewing distances.

---

## §3. UV Channel 2 (index 1) — lightmap UV

| Requirement | Rule |
|------------|------|
| Overlapping islands | **Zero overlaps** — hard requirement. Overlap = lightmap bake bleeds across faces |
| Island range | All islands strictly inside 0–1 UV space |
| Mirrored islands | **Forbidden** — breaks baking (both faces receive the same baked light) |
| Stacked islands | **Forbidden** — same reason |
| Padding | **2–4% of texture resolution** (e.g. `margin=0.02` in Blender Lightmap Pack) |
| Naming | `LightmapUV` in Blender (UE5 auto-detects this name) |

UE5 auto-selects UV channel for lightmap based on either:
1. UV channel named `LightmapUV`, OR
2. UV channel index 1 (second UV layer, zero-indexed)

```python
# Blender: add LightmapUV channel if absent and pack islands
import bpy

def add_lightmap_uv(obj, margin=0.02):
    if 'LightmapUV' not in [ul.name for ul in obj.data.uv_layers]:
        obj.data.uv_layers.new(name='LightmapUV')

    obj.data.uv_layers['LightmapUV'].active = True

    with bpy.context.temp_override(active_object=obj, selected_objects=[obj]):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.uv.select_all(action='SELECT')
        bpy.ops.uv.lightmap_pack(
            PREF_CONTEXT='ALL_FACES',
            PREF_PACK_IN_ONE=True,
            PREF_NEW_UVLAYER=False,
            PREF_BOX_DIV=12,
            PREF_MARGIN_DIV=margin,
        )
        bpy.ops.object.mode_set(mode='OBJECT')

    print(f"LightmapUV added/updated: {obj.name}")

for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        add_lightmap_uv(obj)
```

**Overlap detection (Python):**
```python
def check_lightmap_overlap(obj, uv_layer_name='LightmapUV'):
    """Simple overlap detection via coordinate deduplication (catches exact stacked islands)."""
    import bmesh
    if uv_layer_name not in obj.data.uv_layers:
        print(f"  NO LightmapUV: {obj.name}")
        return True  # counts as an error

    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv[uv_layer_name]

    seen = set()
    overlaps = 0
    for face in bm.faces:
        key = tuple(round(l[uv_layer].uv.x, 3) for l in face.loops)
        if key in seen:
            overlaps += 1
        seen.add(key)
    bm.free()

    if overlaps:
        print(f"  WARN lightmap UV overlap: {obj.name}  ({overlaps} potential overlaps)")
    return overlaps == 0
```

---

## §4. ORM channel-pack (AO + Roughness + Metallic)

**Channel assignment:**
- R = Ambient Occlusion
- G = Roughness ← **most bit precision** under BC1/BC3 compression (6 bits vs 5 for R/B)
- B = Metallic

**Why pack:** One ORM replaces three separate maps → saves ~4 MB per 2048² material at BC1.
This is the UE5 PBR default and Substance Painter's "Unreal Engine 4" export preset.

**Color space:** ORM must be imported as **Linear / Non-Color** in ALL engines. Importing as sRGB
applies a gamma curve to the values, incorrectly brightening roughness and AO values.

### ORM creation script (Pillow, headless)

```python
# forge_pack_orm.py — pack standalone AO, Roughness, Metallic into ORM texture
# Requires Pillow: python -m pip install Pillow
import sys, io, os, argparse
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

try:
    from PIL import Image
except ImportError:
    print("ERROR: Pillow not installed. Run: python -m pip install Pillow")
    sys.exit(1)

def load_channel(path, size):
    """Load a grayscale image; return white (255) if path missing."""
    if path and Path(path).exists():
        return Image.open(path).convert('L').resize(size, Image.LANCZOS)
    return Image.new('L', size, 255)

def pack_orm(ao_path, roughness_path, metallic_path, output_path, size=(2048, 2048)):
    ao  = load_channel(ao_path,       size)
    rgh = load_channel(roughness_path, size)
    mtl = load_channel(metallic_path,  size)
    orm = Image.merge('RGB', (ao, rgh, mtl))
    orm.save(output_path, format='PNG')
    print(f"ORM saved: {output_path}  ({size[0]}×{size[1]})")

def main():
    ap = argparse.ArgumentParser(description="Pack AO+Roughness+Metallic into ORM texture.")
    ap.add_argument("--ao",        help="Path to AO grayscale PNG")
    ap.add_argument("--roughness", help="Path to Roughness grayscale PNG")
    ap.add_argument("--metallic",  help="Path to Metallic grayscale PNG")
    ap.add_argument("--out",       required=True, help="Output ORM PNG path")
    ap.add_argument("--size",      default="2048", help="Output size in pixels (square), e.g. 2048")
    args = ap.parse_args()
    sz = int(args.size)
    pack_orm(args.ao, args.roughness, args.metallic, args.out, size=(sz, sz))

if __name__ == "__main__":
    main()
```

**PowerShell invocation:**
```powershell
python "C:\project\tools\forge_pack_orm.py" `
    --ao        "C:\project\textures\T_Barrel_Oak_AO_01.png" `
    --roughness "C:\project\textures\T_Barrel_Oak_R_01.png" `
    --metallic  "C:\project\textures\T_Barrel_Oak_M_01.png" `
    --out       "C:\project\textures\T_Barrel_Oak_ORM_01.png" `
    --size      2048
```

---

## §5. Texel density calculation snippet (no add-on required)

```python
# calc_texel_density.py — run via: blender -b scene.blend -P calc_texel_density.py
import bpy, bmesh, math, sys, io, json

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def calc_texel_density(obj, texture_res=1024):
    """Returns texel density in px/m for the active UV map of obj."""
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return None

    total_uv_area    = 0.0
    total_world_area = 0.0

    for face in bm.faces:
        uvs = [loop[uv_layer].uv for loop in face.loops]
        if len(uvs) < 3:
            continue
        n = len(uvs)
        # Shoelace formula for UV polygon area
        uv_area = abs(sum(
            uvs[i].x * uvs[(i+1) % n].y - uvs[(i+1) % n].x * uvs[i].y
            for i in range(n)
        ) / 2.0)
        total_uv_area    += uv_area
        total_world_area += face.calc_area()

    bm.free()

    if total_world_area == 0:
        return None

    texels_covered = total_uv_area * (texture_res ** 2)
    td = math.sqrt(texels_covered / total_world_area)
    return td

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--res",  type=int,  default=1024, help="Assumed texture resolution in pixels")
ap.add_argument("--json", action="store_true")
ap.add_argument("--target", type=float, default=1024.0, help="Target td (px/m); flags anything below")
args = ap.parse_args(argv)

results = []
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    td = calc_texel_density(obj, texture_res=args.res)
    if td is None:
        results.append({"name": obj.name, "td_px_m": None, "td_px_cm": None, "ok": False, "reason": "no UV map"})
    else:
        ok = td >= args.target
        results.append({
            "name":     obj.name,
            "td_px_m":  round(td, 1),
            "td_px_cm": round(td / 100, 2),
            "ok":       ok,
        })

if args.json:
    print(json.dumps(results, indent=2))
else:
    print(f"{'Object':<40} {'px/m':>8} {'px/cm':>7} {'OK?'}")
    print("-" * 65)
    for r in results:
        td_str = f"{r['td_px_m']:>8.1f}" if r['td_px_m'] else "       N/A"
        cm_str = f"{r['td_px_cm']:>7.2f}" if r['td_px_cm'] else "    N/A"
        flag   = "  OK" if r["ok"] else "  !! LOW TD"
        print(f"{r['name']:<40}{td_str}{cm_str}{flag}")
```

---

## §6. Common UV / TD pitfalls

| Pitfall | Symptom | Detect | Fix |
|---------|---------|--------|-----|
| Incorrect color space on ORM | Roughness/AO look wrong (too bright or washed) | Engine shows incorrect PBR response | Set texture node → Color Space = Non-Color |
| No UV map on export | `forge-validate` UV error; engine shows no texture | `obj.data.uv_layers` empty | Unwrap in Blender before export |
| UV scale not applied before TD calc | TD appears correct but wrong in-engine | `obj.scale != (1,1,1)` | Apply scale, recalculate TD |
| Lightmap UV has overlap | Bake artifacts: patchy shadows on adjacent faces | `check_lightmap_overlap()` returns >0 | Re-pack with Lightmap Pack; zero margin overlap |
| UV islands outside 0–1 range (UDIMs) | Engine doesn't read UDIM; texture missing on parts | `uv.x > 1.0 or uv.y > 1.0` | Normalize islands into 0–1; use explicit UDIM if engine supports |
| Island padding too small | Mip-level texel bleed: dark halos on island edges | Visual at medium distance in-engine | Increase padding; min 2 px at target res |
| ORM roughness/metallic channels swapped | Unexpected shiny plastic instead of matte metal | Visually wrong PBR response | Verify channel order: R=AO, G=Rough, B=Metal |
| sRGB base-color imported as Linear | Colors too bright / gamma-incorrect | Washed-out appearance | Set Image node → Color Space = sRGB |
| Normal map as sRGB | Subtle shading errors, particularly on curved surfaces | Hard to see until close-up | Set Image node → Color Space = Non-Color |
