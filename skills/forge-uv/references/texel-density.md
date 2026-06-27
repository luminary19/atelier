# forge-uv — Texel Density Reference

# Contents
- §1. Formula and definition
- §2. Budget table by asset class
- §3. Compute texel density (bpy)
- §4. Normalize texel density (bpy)
- §5. Batch normalization across a collection
- §6. UV space utilization targets
- §7. Per-LOD texel density targets

---

## §1. Formula and definition

**Texel density (TD)** = pixels mapped per unit of 3D surface length.
Units: **px/m** (pixels per meter) when scene scale is 1 unit = 1 m.

```
TD (px/m) = sqrt(uv_area_fraction) × texture_px / sqrt(surface_area_m²)
```

Where:
- `uv_area_fraction` = fraction of UV space (0–1) occupied by the island
- `texture_px` = texture resolution in pixels (e.g., 2048)
- `surface_area_m²` = 3D surface area in world units (meters²)

**Pre-condition:** Object scale MUST be applied (`transform_apply(scale=True)`) before computing TD.
Unapplied scale (e.g., 2×) reads as 4× higher TD because surface area is computed in local space.

---

## §2. Budget table by asset class

| Asset class | Target TD (px/m) | Typical texture | Notes |
|-------------|-----------------|-----------------|-------|
| Game background / LOD3 | 256 | 512–1024 | Low-visibility; kept off-screen |
| Game environment prop | 512–1024 | 1024–2048 | Standard environment detail |
| Game hero prop | 1024–2048 | 2048 | Close-up, player-visible |
| Game character body | 1024–2048 | 2048 | Per-character texture budget |
| Game character face | 2048–4096 | 2048–4096 | 2× body TD is common |
| Web / three.js hero (mobile) | 512 | 1024 | KTX2/Basis compressed |
| Web / three.js hero (desktop) | 1024 | 2048 | KTX2/Basis compressed |
| Film / VFX close-up | 2048–4096+ | 4096 UDIM | May span multiple UDIM tiles |
| Print (300 DPI) | ~11 811 | — | 300 DPI × 39.37 in/m |

**How to pick a reference TD:**
Measure the ground plane or a 1 m reference cube that should look crisp at the camera distance.
Set that as the scene target TD. All other objects reference it (hero objects may be 2×).

**Engine-specific notes:**
- **Unity:** UV1 (lightmap) is separate from UV0 (diffuse). Unity's lightmap resolution is set per-mesh in the import inspector, not driven by TD.
- **Unreal:** Lightmap resolution is set per Static Mesh in UE5 — typically a power-of-two value. UV0 = diffuse; UV1 = lightmap (must be non-overlapping).
- **Three.js / web:** TD drives texture resolution selection; stay at 1024 px max for mobile-friendly GLB.

---

## §3. Compute texel density (bpy)

```python
import bpy
import bmesh
import math

def compute_texel_density(obj, texture_px: int) -> float:
    """
    Compute texel density (px/m) for the active UV map on obj.
    Returns 0.0 if no UV data or zero area.

    texture_px: target texture resolution (e.g. 2048 for a 2K texture).
    Pre-condition: obj.scale == (1, 1, 1)  — apply transforms first.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()

    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return 0.0

    total_uv_area = 0.0
    total_3d_area = 0.0

    for face in bm.faces:
        # UV area via shoelace (triangulate fan from loops[0])
        loops = list(face.loops)
        for i in range(1, len(loops) - 1):
            vA = loops[0][uv_layer].uv
            vB = loops[i][uv_layer].uv
            vC = loops[i + 1][uv_layer].uv
            uv_tri = abs((vB.x - vA.x) * (vC.y - vA.y) -
                         (vC.x - vA.x) * (vB.y - vA.y)) * 0.5
            total_uv_area += uv_tri
        # 3D surface area in world units (scale must be applied)
        total_3d_area += face.calc_area()

    bm.free()

    if total_3d_area == 0 or total_uv_area == 0:
        return 0.0

    # sqrt because area is the square of length
    td = math.sqrt(total_uv_area) * texture_px / math.sqrt(total_3d_area)
    return td
```

---

## §4. Normalize texel density (bpy)

```python
def normalize_texel_density(obj, target_td: float, texture_px: int):
    """
    Scale all UV islands uniformly so texel density matches target_td (px/m).
    Does NOT repack — run pack_islands() after if islands fall outside 0-1 space.

    target_td: desired px/m (e.g. 1024 for hero game prop)
    texture_px: texture resolution (e.g. 2048)
    """
    current_td = compute_texel_density(obj, texture_px)
    if current_td < 0.001:
        print(f"[WARN] {obj.name}: could not compute TD (check UV map and applied scale)")
        return

    scale_factor = target_td / current_td

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Scale all UVs uniformly around UV origin
    bpy.ops.transform.resize(
        value=(scale_factor, scale_factor, 1.0),
        orient_type='GLOBAL',
    )
    bpy.ops.object.mode_set(mode='OBJECT')

    print(f"[INFO] {obj.name}: TD {current_td:.1f} → {target_td:.1f} px/m  "
          f"(scale factor = {scale_factor:.4f})")
```

**After normalizing:** islands may extend outside 0–1 UV space. Always run `pack_islands()` after
normalizing TD to re-fit everything within bounds.

**TD deviation threshold:** >20% deviation from target is a [WARN] in the QA suite. >50% is [ERROR].

### Headless TD scaling (pure bmesh, no operator context)

`bpy.ops.transform.resize` (above) needs a `VIEW_3D`/`IMAGE_EDITOR` area and **fails in pure
`blender --background`**. This variant scales the UVs directly via `bm.loops.layers.uv` — same
math, zero area context, so it is the path used under plain `--background`. Scales about the UV
origin `(0,0)` to match the operator's `orient_type='GLOBAL'` behavior; pass a pivot if you need
to scale about the layout center instead.

```python
import bmesh

def normalize_texel_density_bmesh(obj, target_td: float, texture_px: int, pivot=(0.0, 0.0)):
    """
    Headless equivalent of normalize_texel_density(). Works in pure --background.
    Uniformly scales every UV so texel density matches target_td (px/m).
    Re-pack afterwards (pack_islands_bmesh, seams-packing.md §7) to re-fit 0-1.
    """
    current_td = compute_texel_density(obj, texture_px)   # §3 — pure bmesh, headless-safe
    if current_td < 0.001:
        print(f"[WARN] {obj.name}: could not compute TD (check UV map and applied scale)")
        return
    s = target_td / current_td
    px, py = pivot

    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        bm.free()
        print(f"[WARN] {obj.name}: no active UV layer")
        return
    for face in bm.faces:
        for loop in face.loops:
            uv = loop[uv_layer].uv
            uv.x = px + (uv.x - px) * s
            uv.y = py + (uv.y - py) * s
    bm.to_mesh(me)
    bm.free()
    me.update()
    print(f"[INFO] {obj.name}: TD {current_td:.1f} → {target_td:.1f} px/m "
          f"(scale factor = {s:.4f}, bmesh)")
```

Note `compute_texel_density()` (§3) is already pure bmesh, so the whole TD read→scale→re-pack
loop runs headless with no operator context. Use the operator version only when Blender was
launched with a screen.

---

## §5. Batch normalization across a collection

```python
def batch_normalize_collection(collection_name: str, target_td: float, texture_px: int):
    """
    Normalize TD for every mesh object in a named collection.
    Skips non-mesh objects silently.
    """
    col = bpy.data.collections.get(collection_name)
    if not col:
        print(f"[ERROR] Collection '{collection_name}' not found in scene")
        return

    for obj in col.objects:
        if obj.type != 'MESH':
            continue
        if not all(abs(s - 1.0) < 0.0001 for s in obj.scale):
            print(f"[ERROR] {obj.name}: scale not applied — skip")
            continue
        normalize_texel_density(obj, target_td, texture_px)

    print(f"[INFO] Batch TD normalize complete for collection '{collection_name}'")


def report_collection_td(collection_name: str, texture_px: int):
    """
    Print a TD report for every mesh in a collection without modifying anything.
    Useful for pre-flight inspection before normalizing.
    """
    col = bpy.data.collections.get(collection_name)
    if not col:
        print(f"[ERROR] Collection '{collection_name}' not found")
        return
    print(f"\n{'Object':30s} {'TD (px/m)':12s} {'Scale OK':9s}")
    print("-" * 55)
    for obj in col.objects:
        if obj.type != 'MESH':
            continue
        scale_ok = all(abs(s - 1.0) < 0.0001 for s in obj.scale)
        td = compute_texel_density(obj, texture_px) if scale_ok else 0.0
        scale_str = "YES" if scale_ok else "NO (apply!)"
        print(f"{obj.name:30s} {td:12.1f} {scale_str:9s}")
```

---

## §6. UV space utilization targets

| Asset class | Min utilization | Target utilization |
|-------------|----------------|-------------------|
| Background / LOD props | 60% | 70%+ |
| Environment assets | 70% | 75%+ |
| Hero props | 75% | 85%+ |
| Characters | 80% | 90%+ |
| UDIM tiles (individual) | 70% | 80%+ |

**Compute utilization:**

```python
def compute_uv_utilization(obj) -> float:
    """
    Returns UV space utilization as a percentage (0–100).
    Computes total UV area of all faces in the active UV map.
    For UDIM workflows, this measures total area across all tiles; divide by tile count for per-tile.
    """
    import bmesh, math
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return 0.0
    total = 0.0
    for face in bm.faces:
        loops = list(face.loops)
        for i in range(1, len(loops) - 1):
            vA = loops[0][uv_layer].uv
            vB = loops[i][uv_layer].uv
            vC = loops[i + 1][uv_layer].uv
            total += abs((vB.x - vA.x) * (vC.y - vA.y) -
                         (vC.x - vA.x) * (vB.y - vA.y)) * 0.5
    bm.free()
    return total * 100.0   # UV space is 0-1; multiply by 100 for %
```

---

## §7. Per-LOD texel density targets

LODs share the same texture but use progressively lower TD due to reduced screen coverage.

| LOD | Polycount vs LOD0 | TD vs LOD0 | Notes |
|-----|-------------------|-----------|-------|
| LOD0 | 100% | 100% (e.g., 1024 px/m) | Full hero detail |
| LOD1 | 50–60% | 75% | Still player-visible but smaller on screen |
| LOD2 | 25–30% | 50% | Distant; texture detail irrelevant |
| LOD3 | 10–15% | 25–33% | Billboard candidate |

**LOD UV approach:** UV atlas each LOD onto the same texture. Scale LOD1/2/3 UV islands down to
match their lower-resolution representation in the atlas. Never re-bake just for LOD — use the
LOD0 bake, scale the UVs.

**forge-topology** handles LOD generation (decimation); forward the resulting LOD meshes here for
UV scaling adjustment before passing to **forge-export**.
