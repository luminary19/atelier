# forge-uv — Validation & QA Reference

# Contents
- §1. Full UV QA suite (programmatic)
- §2. Checker-map render (headless)
- §3. UV layout export PNG
- §4. Overlap detection
- §5. Out-of-bounds detection
- §6. Interpreting the checker-map PNG (visual read-back guide)
- §7. Determinism checklist (reproducible checker render)

---

## §1. Full UV QA suite (programmatic)

Run after every unwrap + pack cycle. Returns a dict of results; any `[ERROR]` blocks the pipeline.

```python
import bpy
import bmesh
import math

def validate_uvs(obj, texture_px=2048, target_td=1024.0, target_utilization=75.0) -> dict:
    """
    Full UV QA for one mesh object.
    Returns a results dict; prints [WARN]/[ERROR] for log parsing.

    texture_px: texture resolution driving TD calculation (e.g. 2048)
    target_td: desired texel density in px/m
    target_utilization: minimum UV space utilization % (75 for env, 85 for hero)

    Checks:
      1. Scale applied
      2. UV map exists
      3. UV overlaps (ERROR if > 0 for bake channel)
      4. UV utilization (WARN if < target)
      5. Out-of-bounds UVs (WARN)
      6. Texel density vs target (WARN if deviation > 20%)
    """
    results = {
        'object': obj.name,
        'scale_applied': True,
        'has_uv': False,
        'overlaps': 0,
        'out_of_bounds': 0,
        'texel_density': 0.0,
        'td_deviation_pct': None,
        'utilization_pct': 0.0,
        'pass': False,
    }

    # 1. Scale check
    if not all(abs(s - 1.0) < 0.0001 for s in obj.scale):
        print(f"[ERROR] {obj.name}: scale not applied {tuple(round(s,4) for s in obj.scale)}")
        results['scale_applied'] = False
        return results

    # 2. UV exists
    if not obj.data.uv_layers:
        print(f"[ERROR] {obj.name}: no UV maps found")
        return results
    results['has_uv'] = True

    # 3. Overlap detection
    #    NOTE: bpy.ops.uv.select_overlap needs an IMAGE_EDITOR/VIEW_3D area and FAILS in
    #    pure `blender --background` (poll() failed). Under the Forge headless default, call
    #    detect_overlaps_bmesh() (seams-packing.md §8) instead — same count, no area context:
    #        results['overlaps'] = detect_overlaps_bmesh(obj)
    #    The operator path below is kept for runs that have a screen (GUI / offscreen window).
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.uv.select_overlap(extend=False)
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    results['overlaps'] = sum(1 for f in bm.faces if f.select)

    # 4. UV area utilization
    uv_layer = bm.loops.layers.uv.active
    total_uv_area = 0.0
    for face in bm.faces:
        loops = list(face.loops)
        for i in range(1, len(loops) - 1):
            vA = loops[0][uv_layer].uv
            vB = loops[i][uv_layer].uv
            vC = loops[i + 1][uv_layer].uv
            total_uv_area += abs(
                (vB.x - vA.x) * (vC.y - vA.y) -
                (vC.x - vA.x) * (vB.y - vA.y)
            ) * 0.5
    results['utilization_pct'] = total_uv_area * 100.0
    bm.free()
    bpy.ops.object.mode_set(mode='OBJECT')

    # 5. Out-of-bounds check
    results['out_of_bounds'] = _count_out_of_bounds(obj)

    # 6. Texel density
    results['texel_density'] = _compute_td(obj, texture_px)
    if target_td > 0 and results['texel_density'] > 0:
        dev = abs(results['texel_density'] - target_td) / target_td * 100.0
        results['td_deviation_pct'] = dev

    # Print summary
    if results['overlaps'] > 0:
        print(f"[ERROR] {obj.name}: {results['overlaps']} overlapping UV faces — BLOCK pipeline")
    if results['utilization_pct'] < target_utilization:
        print(f"[WARN]  {obj.name}: UV utilization {results['utilization_pct']:.1f}% "
              f"(target {target_utilization:.0f}%)")
    if results['out_of_bounds'] > 0:
        print(f"[WARN]  {obj.name}: {results['out_of_bounds']} UV verts outside 0-1 range")
    td_dev = results.get('td_deviation_pct')
    if td_dev is not None and td_dev > 20:
        print(f"[WARN]  {obj.name}: TD deviation {td_dev:.1f}% "
              f"(actual {results['texel_density']:.1f} px/m, target {target_td:.1f})")

    results['pass'] = (
        results['scale_applied'] and
        results['has_uv'] and
        results['overlaps'] == 0
    )
    return results


# ── Helpers used by validate_uvs ─────────────────────────────────────────────

def _count_out_of_bounds(obj, tolerance=0.001) -> int:
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return 0
    count = 0
    for face in bm.faces:
        for loop in face.loops:
            u, v = loop[uv_layer].uv
            if u < -tolerance or u > 1.0 + tolerance or \
               v < -tolerance or v > 1.0 + tolerance:
                count += 1
    bm.free()
    return count


def _compute_td(obj, texture_px: int) -> float:
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    bm.faces.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return 0.0
    total_uv = 0.0
    total_3d = 0.0
    for face in bm.faces:
        loops = list(face.loops)
        for i in range(1, len(loops) - 1):
            vA = loops[0][uv_layer].uv
            vB = loops[i][uv_layer].uv
            vC = loops[i + 1][uv_layer].uv
            total_uv += abs((vB.x - vA.x)*(vC.y - vA.y) - (vC.x - vA.x)*(vB.y - vA.y)) * 0.5
        total_3d += face.calc_area()
    bm.free()
    if total_3d == 0 or total_uv == 0:
        return 0.0
    return math.sqrt(total_uv) * texture_px / math.sqrt(total_3d)
```

---

## §2. Checker-map render (headless)

Apply a UV_GRID or COLOR_GRID checker texture and render headlessly to PNG.
The agent then calls `Read` on the PNG for visual inspection.

```python
import bpy
import os

def apply_checker_material(obj, checker_type='UV_GRID', resolution=1024):
    """
    Apply Blender's built-in checker texture to detect UV stretching / distortion.
    checker_type: 'UV_GRID' (numbered squares) | 'COLOR_GRID' (color checker)
    After this, render to PNG and inspect with Read tool.
    """
    import addon_utils

    checker_name = f"__forge_checker_{checker_type}_{resolution}"
    if checker_name not in bpy.data.images:
        img = bpy.data.images.new(name=checker_name, width=resolution, height=resolution)
        img.generated_type = checker_type
    else:
        img = bpy.data.images[checker_name]

    mat_name = "__forge_checker_mat"
    if mat_name not in bpy.data.materials:
        mat = bpy.data.materials.new(mat_name)
        mat.use_nodes = True
        nodes = mat.node_tree.nodes
        links = mat.node_tree.links
        nodes.clear()
        bsdf    = nodes.new('ShaderNodeBsdfPrincipled')
        output  = nodes.new('ShaderNodeOutputMaterial')
        tex_node = nodes.new('ShaderNodeTexImage')
        tex_node.image = img
        links.new(tex_node.outputs['Color'], bsdf.inputs['Base Color'])
        links.new(bsdf.outputs['BSDF'], output.inputs['Surface'])
    else:
        mat = bpy.data.materials[mat_name]

    if obj.data.materials:
        obj.data.materials[0] = mat
    else:
        obj.data.materials.append(mat)


def render_checker_to_png(output_path: str, resolution=(1024, 1024), samples=32):
    """
    Render checker material to PNG using Cycles (CPU fallback — EEVEE Next unsupported headless on Windows).

    IMPORTANT Windows headless truth: EEVEE Next is UNSUPPORTED headless on Windows.
    Always use engine='CYCLES' for headless renders.

    DETERMINISM: sets cycles.seed=0, use_denoising=True, fixed samples, CPU device and
    frame 1 so the checker image is byte-stable run-to-run. This is required because the
    QA loop re-renders iteratively (unwrap → render → Read → fix → re-render); without a
    fixed seed, Cycles noise changes every run and "did my fix change the image" diffs
    become meaningless. Launch Blender with --factory-startup (see §Determinism checklist).

    samples: 32 is sufficient for a flat checker QA render; lower for speed.
    output_path: absolute path with forward slashes or normalized via Path.as_posix().
    """
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    # CPU fallback — no GPU required headless (GPU output varies across machines)
    scene.cycles.device = 'CPU'
    scene.cycles.samples = samples
    scene.cycles.seed = 0                 # deterministic noise — byte-stable across runs
    scene.cycles.use_denoising = True     # stable, low-variance checker image for diffing
    scene.frame_set(1)                    # don't rely on the default frame
    scene.render.resolution_x = resolution[0]
    scene.render.resolution_y = resolution[1]
    scene.render.image_settings.file_format = 'PNG'
    # Blender filepath: absolute, forward slashes only
    scene.render.filepath = output_path.replace("\\", "/")
    bpy.ops.render.render(write_still=True)
    print(f"[INFO] Checker render saved: {output_path}")
```

**PowerShell wrapper — end-to-end checker render:**

```powershell
# Run checker render headlessly from PowerShell
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
$script  = "C:\Path\To\checker_render_script.py"
$model   = "C:\assets\prop.blend"
$output  = "C:/forge-build/out/prop_checker.png"

# --factory-startup: ignore user prefs/startup.blend → reproducible, byte-stable render
& $blender --background $model --factory-startup --python $script --python-exit-code 1 -- `
    --output $output --samples 32
if ($LASTEXITCODE -ne 0) {
    Write-Error "Blender checker render failed (exit $LASTEXITCODE)"
    exit 1
}
Write-Host "QA render: $output"
```

After the render completes, call `Read("C:/forge-build/out/prop_checker.png")` to display the PNG
inline and inspect it visually (see §6 for the reading guide).

---

## §3. UV layout export PNG

```python
import bpy
import os
import addon_utils

def export_uv_png(obj, output_path: str, size=(2048, 2048), opacity=0.0,
                  export_tiles='NONE'):
    """
    Export UV layout as PNG. Wire-only at opacity=0.0 (transparent fill).

    export_tiles: 'NONE' = 0-1 range only | 'UDIM' = UDIM scheme | 'UV' = UVTILE

    CRITICAL: io_mesh_uv_layout addon MUST be enabled headless.
    Blender does not auto-enable addons in --background mode.

    CRITICAL: output directory MUST exist (Blender's open() does not create it).
    """
    # Enable the addon that provides bpy.ops.uv.export_layout
    addon_utils.enable("io_mesh_uv_layout", default_set=True, persistent=True)

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)

    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')

    # Normalize path: Blender prefers forward slashes on Windows
    fp = output_path.replace("\\", "/")
    bpy.ops.uv.export_layout(
        filepath=fp,
        export_all=True,
        export_tiles=export_tiles,
        modified=False,
        mode='PNG',
        size=size,
        opacity=opacity,
        check_existing=False,   # Overwrite without dialog (headless-safe)
    )
    bpy.ops.object.mode_set(mode='OBJECT')
    print(f"[INFO] UV layout exported: {output_path}")
```

---

## §4. Overlap detection

```python
def detect_overlaps(obj) -> int:
    """
    Returns count of faces that participate in UV overlaps.
    Uses bpy.ops.uv.select_overlap (Blender built-in) — requires an area context, so this
    works only when Blender has a screen. For pure `blender --background` (the Forge default)
    use detect_overlaps_bmesh() in seams-packing.md §8 instead (operator-free, same result).
    0 = pass for bake channel; any > 0 = BLOCK.
    """
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='DESELECT')
    bpy.ops.uv.select_overlap(extend=False)
    me = obj.data
    bm = bmesh.from_edit_mesh(me)
    count = sum(1 for f in bm.faces if f.select)
    bm.free()
    bpy.ops.object.mode_set(mode='OBJECT')
    if count > 0:
        print(f"[ERROR] {obj.name}: {count} faces have overlapping UVs — BLOCK bake pipeline")
    return count
```

**Stacked UV exception:** for mirrored/instanced geometry using intentional stacking (diffuse UV
channel only), do not run overlap detection on that channel. Instead run it only on the dedicated
bake channel (UV1 / "UVMap.001").

---

## §5. Out-of-bounds detection

```python
def count_out_of_bounds(obj, tolerance=0.001) -> int:
    """
    Count UV loops outside the 0-1 range (ignoring UDIM tiles).
    For UDIM workflows, every tile's local 0-1 space is valid — this function
    is only meaningful for single-tile (non-UDIM) UV maps.
    """
    me = obj.data
    bm = bmesh.new()
    bm.from_mesh(me)
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free()
        return 0
    count = 0
    for face in bm.faces:
        for loop in face.loops:
            u, v = loop[uv_layer].uv
            if (u < -tolerance or u > 1.0 + tolerance or
                    v < -tolerance or v > 1.0 + tolerance):
                count += 1
    bm.free()
    if count > 0:
        print(f"[WARN] {obj.name}: {count} UV loops outside 0-1 range")
    return count
```

---

## §6. Interpreting the checker-map PNG (visual read-back guide)

After `Read`ing the checker PNG, evaluate each criterion:

| What to look for | Pass | Fail — action |
|-----------------|------|---------------|
| Square grid cells are uniform in size across the surface | Consistent texel density | Re-run `normalize_texel_density()` |
| Grid cells are square (not stretched into rectangles) | No UV distortion | Adjust seams; re-unwrap |
| No abrupt size jumps at polygon/island boundaries | Smooth TD transitions | Check for detached islands; re-pack |
| No repeating/mirrored patterns where unique UVs expected | Unique bake channel | Move one mirrored side to separate island |
| No blank regions (all polys covered) | Full coverage | Check for unassigned faces (no UV) |
| No double-exposed bright spots (overlap artifacts) | Zero overlaps | Re-run `detect_overlaps()`; fix before bake |
| Straight lines on planar surfaces (not curved) | Correct projection | Re-run `unwrap_angle_based` or `smart_project` |

**Read-back call (multimodal):**
After confirming the render file exists (`Path(output_path).stat().st_size > 1024`), call:
```
Read("C:/forge-build/out/prop_checker.png")
```
The model inspects the PNG image inline. If issues are found, amend the UV script and re-render.
This is the primary headless verification loop — numbers alone cannot catch seam-direction errors.

---

## §7. Determinism checklist (reproducible checker render)

The checker render is re-run iteratively in the QA loop (unwrap → render → `Read` → fix →
re-render). For "did my fix change the image" diffs to be meaningful, the render must be
**byte-stable** across runs given the same UVs. Mirror forge-model's determinism contract:

- [ ] `--factory-startup` in the PowerShell invocation (no user prefs / startup.blend)
- [ ] `scene.cycles.seed = 0` (fixed Cycles noise seed)
- [ ] `scene.cycles.use_denoising = True` (low-variance, stable image)
- [ ] Fixed sample count (32 for a flat checker — NOT adaptive termination)
- [ ] `scene.cycles.device = 'CPU'` (GPU output varies across machines)
- [ ] `scene.frame_set(1)` (do not rely on the default frame)
- [ ] Absolute forward-slash paths for the output PNG
- [ ] Pinned Blender version (document it in FORGE.md; Cycles output can shift between versions)

With all boxes checked, the checker PNG is identical run-to-run, so a binary/visual diff against
the previous render reliably isolates the effect of a UV change. `render_checker_to_png()` (§2)
already sets seed, denoising, CPU, samples and frame; the remaining boxes are invocation-level
(`--factory-startup`, absolute paths, pinned version).
