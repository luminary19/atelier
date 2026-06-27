# forge-uv — Seams & Island Packing Reference

# Contents
- §1. Seam placement rules
- §2. Marking seams via bpy
- §3. Island packing API
- §4. Margin / padding table
- §5. Overlap rules table
- §6. Island orientation
- §7. Manual AABB island packer (pure bmesh, no operator context)
- §8. Overlap detection (pure bmesh, no operator context)

---

## §1. Seam placement rules

**Hard rules (enforce always):**
1. Place seams along hard/sharp edges first — they are invisible at material breaks.
2. Prefer hidden surfaces: undersides, backs, inside curves, under armpits, soles of feet.
3. Avoid silhouette edges — seams on silhouettes appear in normal maps as edge artifacts.
4. Each island should unfold to a roughly rectangular shape with minimal stretching.

**Hard-surface checklist:**
- Every sharp edge (>30°) is a seam candidate.
- Use `mark_seams_from_sharp(sharpness=radians(30))` as the automatic starting point.
- Manually add seams where Smart UV Project or angle-based grouping would create awkward islands.

**Organic / character checklist:**
- Seams behind ears, inside elbows, under armpits, crotch, soles of feet.
- Head: seam from crown down through center-back of neck.
- Eyes/mouth: keep as single islands if possible (fewer seams = less visual artifact risk).
- Fingers: seam along the back of each finger, not the palm-facing side.

**After unwrapping — back-propagate:**
```python
def seams_from_islands(obj):
    """Lock in current island boundaries as mesh seams (after any unwrap)."""
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.uv.seams_from_islands(mark_seams=True, mark_sharp=False)
    bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §2. Marking seams via bpy

```python
import bpy
from math import radians

# ── Auto-mark from sharp edges ───────────────────────────────────────────────
def mark_seams_from_sharp(obj, sharpness_rad=radians(30)):
    """
    Mark seams on every edge sharper than sharpness_rad (default 30°).
    Standard starting point for hard-surface meshes.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.mesh.edges_select_sharp(sharpness=sharpness_rad)
    bpy.ops.mesh.mark_seam(clear=False)       # Mark selected edges as seams
    bpy.ops.object.mode_set(mode='OBJECT')

def clear_all_seams(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.mesh.mark_seam(clear=True)
    bpy.ops.object.mode_set(mode='OBJECT')

# ── Ensure a canonical UV layer name ─────────────────────────────────────────
def ensure_uv_layer(obj, name="UVMap"):
    """
    Create or activate a UV layer by name.
    IMPORTANT: UV operators always act on the ACTIVE UV layer.
    When batch-processing multiple objects, layers may be named differently
    ('UV0', 'UVChannel_0', 'UVMap.001'). Always call this before operating.
    """
    if name not in obj.data.uv_layers:
        obj.data.uv_layers.new(name=name)
    obj.data.uv_layers.active = obj.data.uv_layers[name]
```

---

## §3. Island packing API

```python
import bpy

# ── Standard pack ─────────────────────────────────────────────────────────────
def pack_islands(obj, margin=0.005, rotate=True, shape_method='CONCAVE'):
    """
    Pack UV islands into UV space.

    margin: Space between islands in UV coordinates.
        Formula: margin = px_gap / texture_resolution
        4 px gap at 2048: 4/2048 = 0.00195 → use 0.002
        See §4 for the full margin table.

    shape_method:
        'CONCAVE' — exact silhouette; best packing density; slowest
        'CONVEX'  — convex hull; faster; wastes ~5-10% more space
        'AABB'    — axis-aligned bounding box; fastest; most wasteful

    rotate: True allows any rotation for best packing.
        Set False or use rotate_method='CARDINAL' for lightmaps
        where engines require axis-aligned islands.

    udim_source:
        'CLOSEST_UDIM' — pack each island into its nearest UDIM tile
        'ACTIVE_UDIM'  — pack into the currently selected UDIM tile
        'ORIGINAL_AABB' — use island's bounding-box tile assignment
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(
        udim_source='CLOSEST_UDIM',
        rotate=rotate,
        rotate_method='ANY',            # 'ANY' | 'CARDINAL' (90° only) | 'AXIS_ALIGNED'
        scale=True,                     # Scale islands to fill space
        merge_overlap=False,            # True: overlapping islands treated as one (stacking)
        margin_method='SCALED',
        margin=margin,
        pin=False,
        pin_method='LOCKED',
        shape_method=shape_method,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── Lightmap pack (axis-aligned) ─────────────────────────────────────────────
def pack_islands_lightmap(obj, margin=0.005):
    """
    Cardinal-rotation only packing for lightmap UV channels.
    Many real-time engines require axis-aligned lightmap islands.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(
        rotate=True,
        rotate_method='CARDINAL',       # Only 90° rotations
        margin=margin,
        shape_method='CONVEX',          # Speed over density for lightmaps
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── Stacked / mirrored UVs ───────────────────────────────────────────────────
def pack_with_stacking(obj, margin=0.005):
    """
    Pack where overlapping islands are intentional (e.g., mirrored diffuse UVs).
    merge_overlap=True groups overlapping islands and moves them together.
    Only use for diffuse channel — never for bake channels.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pack_islands(
        merge_overlap=True,
        margin=margin,
    )
    bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §4. Margin / padding table

| Texture Resolution | Min margin (px) | `pack_islands margin` value | Rationale |
|-------------------|----------------|----------------------------|-----------|
| 512 × 512 | 2 px | 0.004 | Mip-map level 1 uses 256 px |
| 1024 × 1024 | 2–4 px | 0.004 | Standard small game prop |
| 2048 × 2048 | 4 px | 0.002 | Standard environment asset |
| 4096 × 4096 | 4–8 px | 0.001–0.002 | Hero asset, VFX |

**Formula:** `margin = px_gap / texture_resolution`
Example: 4 px gap at 2048 × 2048 → `4 / 2048 = 0.00195` → use `0.002`.

**Why margin matters:** Each mip-map level halves the texture. Without adequate margin, neighboring
islands bleed into each other at lower mip levels, causing visible color smearing at distance.

---

## §5. Overlap rules table

| Scenario | Overlapping UVs allowed? |
|----------|------------------------|
| Diffuse / albedo tiling textures | YES — intentional (mirrored, trim sheets) |
| Baking (normal, AO, lightmap) | NO — causes light/shadow bleeding |
| Lightmap UV channel | NEVER — strict engine requirement |
| Mirrored character geometry (diffuse only) | YES for diffuse; NO for bake channel |
| UDIM tiles (different integer tiles) | YES — islands in different tiles don't overlap |

**For bake channels:** assert 0 overlapping faces before proceeding to `forge-texture` — a hard
block in the pipeline. In pure `blender --background` use `detect_overlaps_bmesh()` (§8); use
`bpy.ops.uv.select_overlap()` only when Blender has a screen.

---

## §6. Island orientation

```python
# Align island to dominant edge direction
bpy.ops.uv.align_rotation(method='AUTO')        # Blender 4.x — align to dominant edge

# Straighten planar surface island
bpy.ops.uv.align(axis='ALIGN_AUTO')             # Straighten along auto-detected axis

# Align all islands to X or Y axis (tiling textures)
bpy.ops.uv.align(axis='ALIGN_X')
bpy.ops.uv.align(axis='ALIGN_Y')
```

**Island orientation rules:**
- For tiling textures: keep islands axis-aligned and 1:1 scale so the pattern tiles predictably.
- For hero props: align major planar surfaces (floor, wall, top) to grid axes for clean painting.
- For characters: orientation matters less than minimizing stretching at silhouette edges.

---

## §7. Manual AABB island packer (pure bmesh, no operator context)

`bpy.ops.uv.pack_islands` (§3) needs an `IMAGE_EDITOR`/`VIEW_3D` area and **fails in pure
`blender --background`** with `RuntimeError: poll() failed` (unwrap-methods.md §3, §5 Gotcha #4).
This section is the **headless-safe replacement**: an axis-aligned-bounding-box **shelf (strip)
packer** built only from `bm.loops.layers.uv` reads/writes. It runs with zero area context, so it
is the path the SKILL.md flow uses under plain `--background`. It is less dense than Blender's
`CONCAVE` packer (rectangles only, no rotation), but it is deterministic, never overlaps islands,
and keeps every UV inside the 0–1 tile.

```python
import bmesh

def _uv_islands(bm, uv_layer):
    """
    Group faces into UV islands by shared UV-coordinate connectivity.
    Two faces are in the same island if they share a loop position in UV space
    (i.e. a UV edge). Returns a list of face lists. Pure bmesh; no operators.
    """
    # Union-Find over faces, joined when two faces share a UV vertex position.
    parent = {f.index: f.index for f in bm.faces}

    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    # Map a quantized UV position -> list of (face.index) touching it.
    # Quantize to 1e-5 so float jitter at a shared seam still matches.
    pos_to_faces = {}
    for f in bm.faces:
        for loop in f.loops:
            uv = loop[uv_layer].uv
            key = (round(uv.x, 5), round(uv.y, 5))
            pos_to_faces.setdefault(key, []).append(f.index)
    for faces_here in pos_to_faces.values():
        first = faces_here[0]
        for other in faces_here[1:]:
            union(first, other)

    groups = {}
    by_index = {f.index: f for f in bm.faces}
    for f in bm.faces:
        groups.setdefault(find(f.index), []).append(by_index[f.index])
    return list(groups.values())


def _island_bounds(island, uv_layer):
    """Return (min_u, min_v, max_u, max_v) for one island (list of faces)."""
    min_u = min_v = float("inf")
    max_u = max_v = float("-inf")
    for f in island:
        for loop in f.loops:
            u, v = loop[uv_layer].uv
            if u < min_u: min_u = u
            if v < min_v: min_v = v
            if u > max_u: max_u = u
            if v > max_v: max_v = v
    return min_u, min_v, max_u, max_v


def pack_islands_bmesh(obj, margin=0.005, scale_to_fit=True):
    """
    Headless AABB shelf-packer. Works in pure `blender --background` (no area context).

    margin: gap between island AABBs in UV units (same meaning as §4 margin table).
    scale_to_fit: uniformly scale the packed layout so it fills the 0-1 tile.

    Algorithm (deterministic):
      1. Split faces into UV islands (_uv_islands).
      2. Normalize each island to its own origin and record its AABB w/h.
      3. Sort islands by height descending, lay them out in shelves left->right,
         wrapping to a new shelf when the row exceeds width 1.0.
      4. Uniformly rescale the whole layout to fit 0-1 (keeps aspect, never overlaps).
    Returns a dict with island_count and final utilization estimate.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        bm.free()
        print(f"[ERROR] {obj.name}: no active UV layer — cannot pack")
        return {"island_count": 0, "utilization_pct": 0.0}

    islands = _uv_islands(bm, uv_layer)

    # Measure + translate each island to its local origin (so layout offsets are clean).
    boxes = []  # (island, w, h)
    for isl in islands:
        min_u, min_v, max_u, max_v = _island_bounds(isl, uv_layer)
        w = max(max_u - min_u, 1e-6)
        h = max(max_v - min_v, 1e-6)
        for f in isl:
            for loop in f.loops:
                loop[uv_layer].uv.x -= min_u
                loop[uv_layer].uv.y -= min_v
        boxes.append([isl, w, h])

    # Shelf layout: tallest first, wrap rows at width 1.0.
    boxes.sort(key=lambda b: b[2], reverse=True)
    cursor_u = 0.0
    cursor_v = 0.0
    shelf_h = 0.0
    layout_w = 0.0
    for box in boxes:
        isl, w, h = box
        if cursor_u + w + margin > 1.0 and cursor_u > 0.0:
            # wrap to next shelf
            cursor_v += shelf_h + margin
            cursor_u = 0.0
            shelf_h = 0.0
        for f in isl:
            for loop in f.loops:
                loop[uv_layer].uv.x += cursor_u
                loop[uv_layer].uv.y += cursor_v
        cursor_u += w + margin
        shelf_h = max(shelf_h, h)
        layout_w = max(layout_w, cursor_u)
    layout_h = cursor_v + shelf_h

    # Uniformly rescale to fit 0-1 (preserve aspect → no stretch, no overlap).
    if scale_to_fit:
        s = 1.0 / max(layout_w, layout_h, 1e-6)
        if s != 1.0:
            for f in bm.faces:
                for loop in f.loops:
                    loop[uv_layer].uv.x *= s
                    loop[uv_layer].uv.y *= s

    bm.to_mesh(me)
    bm.free()
    me.update()
    used = (layout_w * layout_h)
    util = min(used, 1.0) * 100.0 if scale_to_fit is False else None
    print(f"[INFO] {obj.name}: pack_islands_bmesh packed {len(islands)} islands "
          f"(margin={margin}, shelf layout {layout_w:.3f}x{layout_h:.3f})")
    return {"island_count": len(islands), "utilization_pct": util}
```

**When to use which packer:**

| Context | Packer | Quality |
|---|---|---|
| Blender launched WITH a screen (GUI / offscreen window) | `pack_islands()` §3 (`temp_override`) | Best (CONCAVE, rotation) |
| Pure `blender --background` (the Forge default) | `pack_islands_bmesh()` §7 | Good (AABB shelf, no rotation) |
| Bake channel that must never overlap, headless | `pack_islands_bmesh()` §7 + `detect_overlaps_bmesh()` §8 | Guaranteed non-overlap |

---

## §8. Overlap detection (pure bmesh, no operator context)

`bpy.ops.uv.select_overlap` (validation.md §1/§4) also needs an area and **fails in pure
`--background`**. This is the headless-safe replacement: a UV-triangle intersection test
(AABB broad-phase → segment/SAT narrow-phase) over `bm.loops.layers.uv`. Returns the count of
faces that participate in any cross-face UV overlap. `0` = pass for a bake channel; any `> 0` =
BLOCK the bake pipeline (overlap rules §5).

```python
import bmesh

def _tri_uvs(face, uv_layer):
    """Fan-triangulate a face's UVs into a list of (a, b, c) tuples of (x, y)."""
    loops = list(face.loops)
    base = loops[0][uv_layer].uv
    tris = []
    for i in range(1, len(loops) - 1):
        b = loops[i][uv_layer].uv
        c = loops[i + 1][uv_layer].uv
        tris.append(((base.x, base.y), (b.x, b.y), (c.x, c.y)))
    return tris


def _aabb(tri):
    xs = (tri[0][0], tri[1][0], tri[2][0])
    ys = (tri[0][1], tri[1][1], tri[2][1])
    return (min(xs), min(ys), max(xs), max(ys))


def _aabb_overlap(a, b, eps=1e-7):
    return not (a[2] < b[0] - eps or b[2] < a[0] - eps or
                a[3] < b[1] - eps or b[3] < a[1] - eps)


def _tris_intersect(t1, t2, eps=1e-9):
    """SAT for two triangles in 2D. True if their interiors overlap (shared
    edges/verts of adjacent faces do NOT count as overlap)."""
    def axes(t):
        for i in range(3):
            x1, y1 = t[i]
            x2, y2 = t[(i + 1) % 3]
            # edge normal
            yield (-(y2 - y1), (x2 - x1))
    for tri in (t1, t2):
        for ax in axes(tri):
            ax_len = (ax[0] * ax[0] + ax[1] * ax[1]) ** 0.5
            if ax_len < eps:
                continue
            axn = (ax[0] / ax_len, ax[1] / ax_len)
            p1 = [axn[0] * p[0] + axn[1] * p[1] for p in t1]
            p2 = [axn[0] * p[0] + axn[1] * p[1] for p in t2]
            # strict separation with a small epsilon so touching edges don't flag
            if max(p1) <= min(p2) + eps or max(p2) <= min(p1) + eps:
                return False
    return True


def detect_overlaps_bmesh(obj) -> int:
    """
    Headless UV-overlap face count. Works in pure `blender --background`.
    Replaces bpy.ops.uv.select_overlap. O(n^2) worst case but AABB-pruned;
    fine for the per-mesh sizes Forge unwraps. For very dense meshes (>50k
    faces) the AABB broad-phase keeps the candidate set small.

    Returns: count of faces touching any cross-face overlap. 0 = pass.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.active
    if uv_layer is None:
        bm.free()
        return 0

    # Precompute per-face triangles + a face-level AABB.
    face_tris = []   # (face_index, [tris], face_aabb)
    for f in bm.faces:
        tris = _tri_uvs(f, uv_layer)
        if not tris:
            continue
        fb = (min(t[0][0] for t in tris), min(t[0][1] for t in tris),
              max(max(p[0] for p in t) for t in tris),
              max(max(p[1] for p in t) for t in tris))
        # recompute proper face AABB across all tri verts
        xs = [p[0] for t in tris for p in t]
        ys = [p[1] for t in tris for p in t]
        fb = (min(xs), min(ys), max(xs), max(ys))
        face_tris.append((f.index, tris, fb))

    overlapping = set()
    n = len(face_tris)
    for i in range(n):
        fi, tris_i, ab_i = face_tris[i]
        for j in range(i + 1, n):
            fj, tris_j, ab_j = face_tris[j]
            if not _aabb_overlap(ab_i, ab_j):
                continue
            hit = False
            for ti in tris_i:
                for tj in tris_j:
                    if _aabb_overlap(_aabb(ti), _aabb(tj)) and _tris_intersect(ti, tj):
                        hit = True
                        break
                if hit:
                    break
            if hit:
                overlapping.add(fi)
                overlapping.add(fj)

    bm.free()
    count = len(overlapping)
    if count > 0:
        print(f"[ERROR] {obj.name}: {count} faces have overlapping UVs (bmesh) — BLOCK bake pipeline")
    return count
```

**Note on adjacent faces:** the SAT test uses a strict-separation epsilon, so faces that merely
share a seam edge or a vertex are NOT counted as overlapping — only genuine interior overlap
(stacked/mirrored islands, folded UVs) trips the counter.
