# forge-model — Scene, Render & Mesh Validation

## Contents
- §1. Programmatic mesh validation (full + quick)
- §2. Render-to-PNG for QA (Cycles headless) + multi-angle spot-check
- §3. Quick PBR material for QA renders
- §4. Sample count reference table
- §5. Determinism checklist

---

## §1. Programmatic Mesh Validation

Run INSIDE the Blender script after building geometry, before rendering.

```python
import bpy, bmesh as _bmesh
import logging
log = logging.getLogger("forge-model")


def validate_mesh(obj: "bpy.types.Object") -> dict:
    """
    Full mesh health check. Returns a results dict.
    Call on base mesh (before modifiers) to catch authoring errors.
    For export validation, also call on depsgraph-evaluated mesh.
    """
    bm = _bmesh.new()
    bm.from_mesh(obj.data)
    bm.verts.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.faces.ensure_lookup_table()

    dups = _bmesh.ops.find_doubles(bm, verts=bm.verts, dist=0.0001)
    results = {
        "name": obj.name,
        "total_verts": len(bm.verts),
        "total_edges": len(bm.edges),
        "total_faces": len(bm.faces),
        "non_manifold_edges": sum(1 for e in bm.edges if len(e.link_faces) != 2),
        "isolated_verts":     sum(1 for v in bm.verts if not v.link_edges),
        "zero_area_faces":    sum(1 for f in bm.faces if f.calc_area() < 1e-8),
        "duplicate_verts":    len(dups.get("targetmap", {})),
        "ngons":              sum(1 for f in bm.faces if len(f.verts) > 4),
        "triangles":          sum(1 for f in bm.faces if len(f.verts) == 3),
    }
    bm.free()
    return results


def assert_mesh_valid(
    obj: "bpy.types.Object",
    allow_tris: bool = False,
    allow_ngons: bool = False,
    manifold_required: bool = True,
) -> None:
    """
    Raise ValueError if mesh has critical issues.
    manifold_required=True: boolean targets + export meshes require manifold.
    allow_tris=True: game-engine output (triangulate is expected).
    allow_ngons=True: organic bases may have temporary ngons during sculpt.
    """
    r = validate_mesh(obj)
    errors = []
    if manifold_required and r["non_manifold_edges"] > 0:
        errors.append(f"{r['non_manifold_edges']} non-manifold edges")
    if r["isolated_verts"] > 0:
        errors.append(f"{r['isolated_verts']} isolated vertices")
    if r["zero_area_faces"] > 0:
        errors.append(f"{r['zero_area_faces']} zero-area faces")
    if r["duplicate_verts"] > 0:
        errors.append(f"{r['duplicate_verts']} duplicate vertex pairs")
    if not allow_ngons and r["ngons"] > 0:
        errors.append(f"{r['ngons']} ngons (subsurf + game export require quads/tris)")
    if errors:
        raise ValueError(
            f"Mesh '{obj.name}' has issues: {'; '.join(errors)}. "
            f"Stats: {r['total_verts']}v {r['total_faces']}f"
        )
    log.info("Mesh '%s' OK: %dv %de %df", obj.name,
             r['total_verts'], r['total_edges'], r['total_faces'])


def validate_mesh_quick(obj: "bpy.types.Object") -> None:
    """
    Fast inline check: non-manifold + zero-area only.
    Use when full validate_mesh() is too slow (e.g., high-poly base meshes).
    """
    bm = _bmesh.new()
    bm.from_mesh(obj.data)
    nm = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    za = sum(1 for f in bm.faces if f.calc_area() < 1e-8)
    bm.free()
    issues = []
    if nm: issues.append(f"{nm} non-manifold edges")
    if za: issues.append(f"{za} zero-area faces")
    if issues:
        raise ValueError(f"Mesh '{obj.name}': {'; '.join(issues)}")
```

**Also call Blender's built-in mesh validation** (catches topology issues bmesh misses):
```python
fixed = obj.data.validate(verbose=True)
if fixed:
    log.warning("Mesh '%s': built-in validate fixed degenerate geometry", obj.name)
```

---

## §2. Render-to-PNG for QA (Cycles Headless)

```python
import bpy, os
import logging
log = logging.getLogger("forge-model")


def render_to_png(
    output_path: str,
    engine: str = 'CYCLES',
    samples: int = 32,
) -> None:
    """
    Configure scene render settings and render to PNG.
    ALWAYS use Cycles CPU for headless Windows — EEVEE Next requires GPU/display context.
    Call after setup_scene_for_qa() (from bpy-patterns.md §2).

    output_path: absolute path. Never // prefix (undefined without saved .blend).
    """
    scene = bpy.context.scene
    r = scene.render
    r.engine = engine
    r.image_settings.file_format = 'PNG'
    r.image_settings.color_mode = 'RGB'
    r.image_settings.color_depth = '8'

    out = os.path.abspath(output_path)          # NEVER // on Windows
    os.makedirs(os.path.dirname(out), exist_ok=True)
    r.filepath = out

    if engine == 'CYCLES':
        scene.cycles.samples = samples
        scene.cycles.device = 'CPU'             # CPU: guaranteed headless on Windows
        scene.cycles.use_denoising = True
        scene.cycles.denoiser = 'OPENIMAGEDENOISE'
        scene.cycles.seed = 0                   # deterministic noise
        scene.cycles.diffuse_bounces = 3
        scene.cycles.glossy_bounces = 3
        scene.cycles.transparent_max_bounces = 4
    else:
        # Forge is Cycles-only headless. EEVEE Next (4.2+, id BLENDER_EEVEE_NEXT) needs a
        # GPU/display context and renders black headless on Windows — see gotchas.md §G6.
        raise ValueError(
            f"Unsupported headless engine {engine!r}; Forge headless renders use 'CYCLES'."
        )

    bpy.ops.render.render(write_still=True)

    # Structural verification (visual check via Read is done by the calling agent)
    if not os.path.exists(out):
        raise RuntimeError(f"Render produced no output file: {out}")
    sz = os.path.getsize(out)
    if sz < 10_000:
        raise RuntimeError(
            f"Render output suspiciously small ({sz} bytes): {out} "
            "— possible black frame (EEVEE GPU unavailable?) or silent Cycles crash"
        )
    with open(out, 'rb') as f:
        header = f.read(8)
    if header != b'\x89PNG\r\n\x1a\n':
        raise RuntimeError(f"Output is not a valid PNG: {out}")
    log.info("Render OK: %s (%d bytes)", out, sz)
```

**Post-render visual check (the human-facing QA step):**

After running the render, the calling agent reads the PNG with the `Read` tool and visually
inspects it. Check for:
- Correct silhouette and proportions
- No missing faces or flipped normals (black patches on Cycles)
- Shading seams where none should exist (WeightedNormal + SmoothByAngle order issue)
- Object not clipping camera or falling outside frame

If the visual fails → fix the script → re-render → re-read.

**Multi-angle spot-check (recommended for any closed/manifold export mesh):**

A single 3/4 view hides back-facing problems — inverted normals on the far side, missing rear
faces, asymmetric bevel errors behind the silhouette. For an export/manifold mesh, render front-3/4,
back-3/4, and top, then `Read` all three. This is a spot-check, not a turntable — for a full
turntable / wireframe / normals contact sheet invoke `Skill("forge-render")`.

```python
def render_qa_multiangle(
    target_obj: "bpy.types.Object",
    output_stem: str,
    engine: str = 'CYCLES',
    samples: int = 32,
    angles=((35, 45), (35, 225), (90, 0)),   # front-3/4, back-3/4, top
) -> list:
    """
    Render target_obj from several (elevation_deg, azimuth_deg) angles for QA.
    Writes <output_stem>_a0.png, _a1.png, ... and returns the absolute paths.
    Re-frames the camera per angle; lights/world/resolution are left as set by
    setup_scene_for_qa(). Caller Reads every PNG to inspect all sides.
    """
    import os
    paths = []
    stem = os.path.abspath(output_stem)
    os.makedirs(os.path.dirname(stem), exist_ok=True)
    for i, (el, az) in enumerate(angles):
        # Re-frame: drop the prior QA camera, build a fresh one at this angle.
        old = bpy.data.objects.get("ForgeQA_Camera")
        if old is not None:
            bpy.data.objects.remove(old, do_unlink=True)
        create_camera_auto(target_obj, elevation_deg=el, azimuth_deg=az)  # from bpy-patterns.md §2
        out_i = f"{stem}_a{i}.png"
        render_to_png(out_i, engine, samples)
        paths.append(out_i)
    return paths
```

---

## §3. Quick PBR Material for QA Renders

```python
def assign_qa_material(
    obj: "bpy.types.Object",
    base_color: tuple = (0.4, 0.6, 0.9, 1.0),
    metallic: float = 0.0,
    roughness: float = 0.4,
    mat_name: str = "ForgeQA_Mat",
) -> "bpy.types.Material":
    """
    Assign a simple Principled BSDF material to obj for QA renders.
    Works with Cycles. For full PBR authoring → Skill("forge-material").
    """
    mat = bpy.data.materials.new(mat_name)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes; links = mat.node_tree.links
    nodes.clear()

    bsdf = nodes.new('ShaderNodeBsdfPrincipled')
    bsdf.inputs['Base Color'].default_value = base_color
    bsdf.inputs['Metallic'].default_value   = metallic
    bsdf.inputs['Roughness'].default_value  = roughness

    out = nodes.new('ShaderNodeOutputMaterial')
    links.new(bsdf.outputs['BSDF'], out.inputs['Surface'])

    if obj.data.materials: obj.data.materials[0] = mat
    else:                   obj.data.materials.append(mat)
    return mat
```

---

## §4. Sample Count Reference Table

| Purpose | Cycles samples | Notes |
|---|---|---|
| Agent visual check | 32–64 | Fast; enough for spatial reasoning |
| QA / automated test | 128 | Stable, noise-free result |
| Final deliverable | 512–2048 | Use forge-render for this, not forge-model |

For geometry checks (silhouette, proportions) — 32 samples is sufficient.
For material/normal inspection — use 64–128.
Full production render → invoke `Skill("forge-render")`.

---

## §5. Determinism Checklist

For reproducible renders (same input → same pixel output):

- [ ] `--factory-startup` in PowerShell invocation (no user prefs/startup.blend)
- [ ] `scene.cycles.seed = 0` (Cycles noise seed)
- [ ] Fixed sample count (not adaptive termination)
- [ ] `scene.frame_set(1)` (not relying on default frame = 1)
- [ ] No time-dependent data (no drivers using frame unless explicitly set)
- [ ] `scene.cycles.device = 'CPU'` (GPU varies across machines)
- [ ] Same Blender version (document the version in FORGE.md)
- [ ] Absolute paths for all output files
