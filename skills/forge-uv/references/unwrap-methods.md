# forge-uv — Unwrap Methods Reference

# Contents
- §1. API signatures for all unwrap operators
- §2. Method selection guide
- §3. Headless context override
- §4. Pinning
- §5. Gotchas table

---

## §1. API signatures for all unwrap operators

All functions below assume the caller has already applied object scale. Run in a headless
Blender script via: `blender --background <scene.blend> --python <script.py> --python-exit-code 1 -- <args>`

```python
import bpy
from math import radians

# ── HELPER ──────────────────────────────────────────────────────────────────
def enter_edit_select_all(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

# ── METHOD 1: Angle Based ────────────────────────────────────────────────────
def unwrap_angle_based(obj, margin=0.001):
    """
    Best for: organic meshes, characters, curved hard-surface.
    Requires seams placed first. Follows seams to split islands.
    margin_method='SCALED' keeps margin proportional to island size.
    """
    enter_edit_select_all(obj)
    bpy.ops.uv.unwrap(
        method='ANGLE_BASED',
        fill_holes=True,
        correct_aspect=True,
        use_subsurf_data=False,     # Set True if Subdivision modifier is present
        margin_method='SCALED',     # 'SCALED' | 'ADD' | 'FRACTION'
        margin=margin,
        no_flip=False,
        iterations=10,              # Only used by MINIMUM_STRETCH; ignored here
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── METHOD 2: Conformal ──────────────────────────────────────────────────────
def unwrap_conformal(obj, margin=0.001):
    """
    Best for: quick iterations, background assets, simple shapes.
    Faster than Angle Based. Less seam control.
    """
    enter_edit_select_all(obj)
    bpy.ops.uv.unwrap(
        method='CONFORMAL',
        fill_holes=False,
        correct_aspect=True,
        margin=margin,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── METHOD 3: Minimum Stretch ────────────────────────────────────────────────
def unwrap_minimum_stretch(obj, margin=0.001, iterations=500):
    """
    Best for: hero assets, displacement maps, print textures.
    Cap iterations at 500 headlessly — unlimited iterations will hang.
    """
    enter_edit_select_all(obj)
    bpy.ops.uv.unwrap(
        method='MINIMUM_STRETCH',
        fill_holes=True,
        correct_aspect=True,
        margin=margin,
        iterations=iterations,      # 0 = unlimited — dangerous headless
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── METHOD 4: Smart UV Project ───────────────────────────────────────────────
def unwrap_smart_project(obj, angle_deg=66.0, island_margin=0.02):
    """
    Best for: architecture, hard-surface boxes, no-seam workflow.
    angle_limit is in RADIANS — passing 66 directly gives 66 rad ≈ 3783°
    which causes every face to become its own island (Gotcha #5).
    Does NOT follow manually placed seams.
    """
    enter_edit_select_all(obj)
    bpy.ops.uv.smart_project(
        angle_limit=radians(angle_deg),     # RADIANS — always use radians()
        margin_method='SCALED',
        rotate_method='AXIS_ALIGNED_Y',
        island_margin=island_margin,
        area_weight=0.0,
        correct_aspect=True,
        scale_to_bounds=False,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── METHOD 5: Cube Projection ────────────────────────────────────────────────
def unwrap_cube(obj, cube_size=1.0):
    """
    Best for: box-shaped objects, quick atlas, detail-free geometry.
    Results overlap by default; always run pack_islands() after.
    """
    enter_edit_select_all(obj)
    bpy.ops.uv.cube_project(
        cube_size=cube_size,
        correct_aspect=True,
        clip_to_bounds=False,
        scale_to_bounds=True,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── METHOD 6: Cylinder Projection ───────────────────────────────────────────
def unwrap_cylinder(obj):
    """Best for: cylindrical objects (pipes, columns, bottles)."""
    enter_edit_select_all(obj)
    bpy.ops.uv.cylinder_project(
        direction='ALIGN_TO_OBJECT',
        align='POLAR_ZX',
        pole='PINCH',               # 'FAN' to spread pole UVs
        seam=True,
        correct_aspect=True,
    )
    bpy.ops.object.mode_set(mode='OBJECT')

# ── METHOD 7: Lightmap Pack ──────────────────────────────────────────────────
def unwrap_lightmap(obj, margin_div=0.05, new_uv_layer=True):
    """
    Dedicated non-overlapping lightmap channel. Creates UV1 by default.
    Never overwrite diffuse UVs — always new_uv_layer=True for lightmaps.
    PREF_BOX_DIV controls packing quality: 1–48; higher = better fit, slower.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.lightmap_pack(
        PREF_CONTEXT='ALL_FACES',
        PREF_PACK_IN_ONE=True,
        PREF_NEW_UVLAYER=new_uv_layer,
        PREF_BOX_DIV=12,
        PREF_MARGIN_DIV=margin_div,
    )
    bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §2. Method selection guide

```
Is the asset organic (character, plant, cloth)?
    └─ YES → ANGLE_BASED (seams from body landmarks)
    └─ NO →
        Is it hard-surface with sharp edges?
        └─ YES → Smart UV Project (auto-groups by normal) or ANGLE_BASED + mark_seams_from_sharp
        └─ NO →
            Is it cylindrical (pipe, bottle)?
            └─ YES → Cylinder Projection
            └─ NO →
                Is it boxy / axis-aligned?
                └─ YES → Cube Projection + pack_islands
                └─ NO →
                    Hero asset needing best possible quality?
                    └─ YES → MINIMUM_STRETCH (iterations=500)
                    └─ NO → CONFORMAL (quick iteration)

Always add a lightmap channel (unwrap_lightmap, new_uv_layer=True) for:
    - Real-time engine targets (Unity, Unreal, Godot)
    - Assets that will receive baked lighting
```

---

## §3. Headless context override

Many `bpy.ops.uv.*` operators require `context.area.type == 'IMAGE_EDITOR'` or `'VIEW_3D'`.
In `--background` mode there is no active area, so operators fail with:
`RuntimeError: Operator bpy.ops.uv.pack_islands.poll() failed`

**Solution A — context override (Blender 4.x):**

```python
def with_image_editor_context(func, *args, **kwargs):
    """
    Run a UV operator with a temporary IMAGE_EDITOR context override.
    Works if Blender was launched without --background (has a screen).
    Falls through to func() directly if no screen areas exist.
    """
    if bpy.context.screen:
        for area in bpy.context.screen.areas:
            if area.type == 'IMAGE_EDITOR':
                with bpy.context.temp_override(area=area):
                    return func(*args, **kwargs)
        # No IMAGE_EDITOR found — use first area
        with bpy.context.temp_override(area=bpy.context.screen.areas[0]):
            return func(*args, **kwargs)
    else:
        # Pure --background: no screen, no areas
        return func(*args, **kwargs)

# Usage:
with_image_editor_context(bpy.ops.uv.pack_islands, margin=0.005)
```

**Solution B — direct bmesh UV manipulation (works in pure --background, the Forge default):**

The three core UV ops have **complete, operator-free bmesh implementations** that run with no area
context. These are the canonical headless path — use them under plain `blender --background`:

| Operation | Operator (needs area) | Headless bmesh replacement |
|---|---|---|
| Pack islands | `bpy.ops.uv.pack_islands` | `pack_islands_bmesh()` — **`references/seams-packing.md §7`** |
| Overlap check | `bpy.ops.uv.select_overlap` | `detect_overlaps_bmesh()` — **`references/seams-packing.md §8`** |
| TD scale | `bpy.ops.transform.resize` | `normalize_texel_density_bmesh()` — **`references/texel-density.md §4`** |

```python
# Headless pack: no screen, no area, no temp_override needed.
from seams_packing import pack_islands_bmesh        # §7 — AABB shelf packer
from seams_packing import detect_overlaps_bmesh      # §8 — SAT overlap test

pack_islands_bmesh(obj, margin=0.005)                # fills 0-1, never overlaps islands
assert detect_overlaps_bmesh(obj) == 0, "bake channel must have zero UV overlaps"
```

`compute_texel_density()` / `_count_out_of_bounds()` in texel-density.md §3 and validation.md are
already pure-bmesh, so the **entire** UV pipeline (seams → unwrap → pack → TD → validate) runs in
pure `--background`. The one exception is `bpy.ops.uv.unwrap` / `smart_project` themselves (§1):
those solvers run headless fine (they do not require an `IMAGE_EDITOR`); it is only the
*post-process* operators (pack/select/resize) that need the override or the bmesh path above.

**Which steps need an area context vs. pure `--background`:**

| Step | Pure `--background`? | How |
|---|---|---|
| `mark_seams_from_sharp`, `seams_from_islands` | Yes | mesh-edit operators, no area needed |
| `bpy.ops.uv.unwrap` / `smart_project` / projections (§1) | Yes | solver runs headless |
| Pack islands | Yes | `pack_islands_bmesh()` §7 (NOT `bpy.ops.uv.pack_islands`) |
| Overlap detection | Yes | `detect_overlaps_bmesh()` §8 (NOT `bpy.ops.uv.select_overlap`) |
| TD scale | Yes | `normalize_texel_density_bmesh()` (NOT `bpy.ops.transform.resize`) |
| `bpy.ops.uv.export_layout` (layout PNG) | No | needs an EDIT-mode area; use Solution A `temp_override`, or render a checker map instead |

**Recommendation:** stay in pure `blender --background` (the Forge headless mandate) and use the
bmesh functions above for pack / overlap / TD. Only `export_layout` (the optional reference PNG)
benefits from a screen; if you cannot get one, skip it and rely on the checker-map render
(validation.md §2) for visual QA — that render works in pure `--background` via Cycles CPU.

---

## §4. Pinning

```python
import bmesh

def pin_uv_boundary(obj):
    """
    Lock UV boundary vertices (seam-adjacent loops) to prevent them from moving
    during a subsequent unwrap. Use when manually adjusting corners first.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    for face in bm.faces:
        for loop in face.loops:
            luv = loop[uv_layer]
            luv.pin_uv = loop.edge.seam   # Pin if loop edge is a seam
    bmesh.update_edit_mesh(me)
    bpy.ops.object.mode_set(mode='OBJECT')

def clear_all_pins(obj):
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.ops.uv.pin(clear=True)
    bpy.ops.object.mode_set(mode='OBJECT')
```

---

## §5. Gotchas table

| # | Problem | Detect | Fix |
|---|---------|--------|-----|
| 1 | Unapplied scale corrupts TD | `obj.scale != (1,1,1)` | `transform_apply(scale=True)` before any UV op |
| 2 | Smart UV Project ~100× slower via Python on >100k faces | `time.time()` wrap; >60 s is the signal | Use Blender 4.x (solver fixed in 3.6+); split mesh by material; or use `CONFORMAL` fallback |
| 3 | `export_layout` silent fail if directory missing | `$LASTEXITCODE != 0` | `os.makedirs(os.path.dirname(path), exist_ok=True)` before calling |
| 4 | `bpy.ops.uv.*` context error headless | `RuntimeError: poll() failed` | Use the pure-bmesh replacements: `pack_islands_bmesh` (seams-packing §7), `detect_overlaps_bmesh` (seams-packing §8), `normalize_texel_density_bmesh` (texel-density §4). `temp_override` (§3) only if a screen exists |
| 5 | `smart_project` angle in radians, UI shows degrees | Island count explodes (every face = own island) | Always `from math import radians; angle_limit=radians(66.0)` |
| 6 | Modifier stack unapplied — UVs don't match final mesh | Vertex count mismatch vs evaluated mesh | Apply modifiers before unwrap; or `use_subsurf_data=True` |
| 7 | UV layers named inconsistently across objects | Operators act on wrong layer | `ensure_uv_layer(obj, "UVMap")` before every batch op |
| 8 | Windows path separators in `filepath` | Silent fail or wrong path | `path.replace("\\\\", "/")` or `Path(p).as_posix()` |
| 9 | Mirrored UVs break asymmetric bakes | `select_overlap()` catches seam faces | Move one side +1 U before baking; or use separate bake channel |
| 10 | `io_mesh_uv_layout` not enabled headless | `AttributeError: bpy.ops.uv.export_layout` | `addon_utils.enable("io_mesh_uv_layout", default_set=True, persistent=True)` |
