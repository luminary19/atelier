# Forge Validate — Mesh & Spec Checklist
# Contents
- §1. Manifold / watertight checks
- §2. Normal consistency
- §3. Scale & units
- §4. Polycount budgets
- §5. UV checks
- §6. Topology quality gates (quads/tris/ngons, poles)
- §7. GLB structural checks

---

## §1. Manifold / Watertight Checks

**Authoritative trimesh checks (run after `mesh.process(validate=True)`):**

```python
import trimesh, trimesh.repair as repair

mesh = trimesh.load(path, force="mesh")
if isinstance(mesh, trimesh.Scene):
    mesh = trimesh.util.concatenate(list(mesh.geometry.values()))

mesh.process(validate=True)        # merges duplicates, removes degenerate faces
repair.fix_normals(mesh, multibody=True)
mesh.fill_holes()

checks = {
    "is_watertight":         mesh.is_watertight,          # every edge used by exactly 2 faces
    "is_winding_consistent": mesh.is_winding_consistent,  # adjacent faces have opposite edge dirs
    "is_volume":             mesh.is_volume,               # watertight + consistent + vol > 0
    "volume_positive":       mesh.is_volume and mesh.volume > 0,
    "euler_number_ok":       mesh.euler_number == 2,       # genus-0 simple solid
    "has_nan_verts":         not __import__("numpy").isfinite(mesh.vertices).all(),
    "broken_faces":          len(repair.broken_faces(mesh)),
    "body_count":            len(mesh.split(only_watertight=False)),
}
```

**Gate thresholds:**

| Check | Print target | Render-only | Web GLB |
|-------|-------------|-------------|---------|
| is_watertight | REQUIRED | WARN | RECOMMENDED |
| is_winding_consistent | REQUIRED | REQUIRED | REQUIRED |
| is_volume | REQUIRED | WARN | RECOMMENDED |
| euler_number == 2 | REQUIRED (simple solid) | INFO | INFO |
| has_nan_verts | FAIL always | FAIL always | FAIL always |
| broken_faces == 0 | REQUIRED | WARN | WARN |
| body_count == 1 | RECOMMENDED | OK | OK |

**Open3D extra checks (more granular — install: `pip install open3d`):**

```python
import open3d as o3d

mesh_o3d = o3d.io.read_triangle_mesh(path)
mesh_o3d.compute_vertex_normals()

extra = {
    "edge_manifold":       mesh_o3d.is_edge_manifold(allow_boundary_edges=False),
    "vertex_manifold":     mesh_o3d.is_vertex_manifold(),
    "self_intersecting":   mesh_o3d.is_self_intersecting(),
    "orientable":          mesh_o3d.is_orientable(),
}
```

**Common gotchas:**

| Symptom | Cause | Fix |
|---------|-------|-----|
| `mesh.volume < 0` (watertight but negative) | Normals all point inward | `repair.fix_inversion(mesh)` |
| `fill_holes()` returns False | Holes > 4 edges | `repair.fill_holes(mesh, use_fan=True)` or PyMeshLab `meshing_close_holes(maxholesize=200)` |
| trimesh loads as Scene not Trimesh | Multi-body STL or GLTF | `trimesh.util.concatenate(list(loaded.geometry.values()))` |
| `is_watertight` False on multi-body | Two separate shells look non-manifold at aggregate | `mesh.split()`, check each body separately |
| `Boolean fails "Not all meshes are volumes"` | Input mesh not watertight | Repair each input; check `a.is_volume and b.is_volume` before boolean |

---

## §2. Normal Consistency

**Trimesh fix:**
```python
import trimesh.repair as repair
repair.fix_normals(mesh, multibody=True)  # traverses adjacency, flips mismatched faces
# If volume is negative after fix (all normals consistently inward):
if mesh.is_volume and mesh.volume < 0:
    mesh.invert()   # flip all face normals + winding at once
```

**bmesh fix (inside Blender headless):**
```python
import bmesh
bm = bmesh.new()
bm.from_mesh(obj.data)
bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
bm.to_mesh(obj.data)
obj.data.update()
bm.free()
```

**Visual confirmation:** matcap render — black patches = inverted normals.
Normal map render (Cycles, 1 sample) — abrupt color reversals (red next to cyan) = discontinuity.

**Heuristic caveat:** centroid-dot-product normal check gives false positives on concave/hollow
meshes (cups, tubes, arches). If > 30% of faces flag, the mesh is concave — use `recalc_face_normals`
(connectivity-based) rather than the heuristic.

---

## §3. Scale & Units

**Blender headless scale check:**
```python
import bpy

scene = bpy.context.scene
scale_length = scene.unit_settings.scale_length   # 0.001 = 1 unit is 1 mm; 1.0 = 1 unit is 1 m

# For 3D print: must be 0.001 (mm). For glTF web: 1.0 (meters per unit).
# Check object transforms are applied:
for obj in bpy.data.objects:
    if obj.type == "MESH":
        if abs(obj.scale.x - 1.0) > 1e-4 or abs(obj.scale.y - 1.0) > 1e-4:
            print(f"WARNING: {obj.name} has unapplied scale: {obj.scale}")
# Fix: bpy.ops.object.transform_apply(scale=True)
```

**glTF coordinate system (non-negotiable):**
- Y-up, right-handed, meters (1 glTF unit = 1 m)
- Blender: always export with `export_yup=True` — adds automatic root node rotation
- Never manually rotate to compensate for Z-up → Y-up; the exporter handles this

**Scale check by target:**

| Target | Unit | scale_length | Blender export flag |
|--------|------|-------------|---------------------|
| 3D Print | mm | 0.001 | `use_scene_unit=True` on STL export |
| glTF / web | m | 1.0 | `export_yup=True`, `export_apply=True` |
| Unreal Engine | cm | 0.01 | Scale ×100 in Unreal import or bake |
| Unity | m | 1.0 | Default; apply transform before export |

**Gotcha — 1000× scale error from Blender STL export:**
Blender's default scene scale is 1 m/unit. If `scale_length != 0.001` when exporting to STL for
printing, the file measures 1000× wrong. Fix: set scale to 0.001 AND apply object transforms:
```python
bpy.context.scene.unit_settings.scale_length = 0.001
bpy.ops.object.select_all(action="SELECT")
bpy.ops.object.transform_apply(scale=True)
```

---

## §4. Polycount Budgets

**Default Forge budgets (from forge-standards — read FORGE.md for project overrides):**

| Target | Budget (triangles) | Notes |
|--------|--------------------|-------|
| Web hero (three.js/R3F) | ≤ 100k | Per mesh; scene total ≤ 500k |
| Mobile AR | ≤ 20k | Strict; test on device |
| Game hero character | ≤ 50k–80k | Engine-dependent |
| Background prop | ≤ 5k–10k | |
| 3D print | No budget | But ≤ 1M faces for slicer sanity |
| Sculpt/bake source | No budget | Decimation happens at retopo step |

**trimesh face count check:**
```python
face_count = len(mesh.faces)
budget = int(forge_md.get("budget_faces", 100_000))
status = "PASS" if face_count <= budget else "FAIL"
print(f"Faces: {face_count} / budget {budget} → {status}")
```

**Decimation on budget exceed:** Call `Skill("forge-topology")` — it owns QEM decimation
and LOD generation.

---

## §5. UV Checks

**UV overlap detection (bmesh inside Blender):**
```python
import bpy, bmesh

def count_flipped_uvs(obj):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    uv_layer = bm.loops.layers.uv.active
    flipped = 0
    if uv_layer:
        for f in bm.faces:
            uvs = [loop[uv_layer].uv for loop in f.loops]
            area_uv = 0.0
            for i in range(len(uvs)):
                area_uv += uvs[i-1].cross(uvs[i])
            if area_uv < 0:
                flipped += 1
    bm.free()
    return flipped
```

**Texel density check (trimesh, no Blender needed):**
```python
import trimesh, numpy as np

def texel_density_cv(mesh):
    """
    Coefficient of variation of texel density across faces.
    CV < 0.5 = acceptable uniformity. Requires UV data in mesh.
    """
    if not hasattr(mesh.visual, 'uv') or mesh.visual.uv is None:
        return None
    uv = mesh.visual.uv
    face_uvs = uv[mesh.faces]                     # (N, 3, 2)
    # UV area per face
    v0 = face_uvs[:, 1] - face_uvs[:, 0]
    v1 = face_uvs[:, 2] - face_uvs[:, 0]
    uv_areas = np.abs(v0[:, 0]*v1[:, 1] - v0[:, 1]*v1[:, 0]) * 0.5
    face_areas = mesh.area_faces
    # Texel density = sqrt(uv_area / face_area); avoid div-by-zero
    mask = face_areas > 1e-10
    density = np.sqrt(uv_areas[mask] / face_areas[mask])
    if len(density) == 0:
        return None
    return float(np.std(density) / np.mean(density))  # CV
```

**UV checker visual (render-qa-guide.md §3 explains visual interpretation):**
- Uniform checker square size = good texel density
- Elongated squares > 2:1 = UV stretch — re-unwrap the island
- Mirrored checker pattern on a face = flipped UV winding — fix with `bmesh.ops.reverse_uvs`

---

## §6. Topology Quality Gates

**bmesh topology audit (run inside Blender headless).** This audit is SHIPPED as a runnable
script — `scripts/topology_audit.py` — because trimesh-based `validate.py` cannot produce
bmesh-level fields (non-manifold edges, flipped faces, poles, n-gon %). Run it and read its
`totals` JSON; this is the source the Tier-3 topology reviewer reads:

```powershell
blender -b "C:/path/model.glb" --factory-startup --python-exit-code 1 `
    -P "$CLAUDE_CONFIG_DIR/skills/forge-validate/scripts/topology_audit.py" `
    -- --input "C:/path/model.glb" --json
```

The snippet below is the core of that script (kept here as the reference spec):

```python
import bpy, bmesh

QUALITY_GATES = {
    "pct_quads_min":          90.0,   # < 90% quads = WARN; < 70% = FAIL (subdiv/deform meshes)
    "ngon_max":               0,      # 0 for subdiv; 5% OK for flat hard-surface statics
    "non_manifold_edges_max": 0,      # 0 always (print + subdiv + boolean pipeline)
    "flipped_faces_max":      0,
    "high_valence_poles_max": 0,      # verts with valence > 5
    "degenerate_faces_max":   0,
    "density_cv_max":         0.5,
}

def audit_object(obj):
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        tf = len(bm.faces)
        return {
            "faces":               tf,
            "tris":                sum(1 for f in bm.faces if len(f.verts) == 3),
            "quads":               sum(1 for f in bm.faces if len(f.verts) == 4),
            "ngons":               sum(1 for f in bm.faces if len(f.verts) > 4),
            "pct_quads":           round(sum(1 for f in bm.faces if len(f.verts)==4) / max(tf,1) * 100, 1),
            "non_manifold_edges":  sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary),
            "boundary_edges":      sum(1 for e in bm.edges if e.is_boundary),
            "wire_edges":          sum(1 for e in bm.edges if e.is_wire),
            "high_valence_poles":  sum(1 for v in bm.verts if len(v.link_edges) > 5),
            "degenerate_faces":    sum(1 for f in bm.faces if f.calc_area() < 1e-8),
            "is_watertight":       all(e.is_manifold for e in bm.edges) and not any(e.is_boundary for e in bm.edges),
        }
    finally:
        bm.free()   # CRITICAL: always free; leaks cause OOM on batch jobs
```

**Pole rules:**

| Valence | Name | Rule |
|---------|------|------|
| 4 | Regular | Ideal — no restriction |
| 3 | N-pole | OK on flat surfaces, away from deformation zones |
| 5 | E-pole | OK for loop transitions; keep on flat surfaces |
| ≥ 6 | High-pole | WARN — avoid on curved surfaces; subdivision artifacts |

Never place poles in: elbow crease, knee bend, shoulder socket, mouth corners, eyelid edge.

---

## §7. GLB Structural Checks (stdlib, no trimesh needed)

```python
import struct, pathlib

def check_glb_header(path: str) -> dict:
    """Verify GLB magic bytes, version, and chunk structure."""
    p = pathlib.Path(path)
    if not p.exists():
        return {"ok": False, "error": "file not found"}
    size_bytes = p.stat().st_size
    if size_bytes < 12:
        return {"ok": False, "error": f"file too small: {size_bytes} bytes"}

    with open(path, "rb") as f:
        header = f.read(12)
    magic, version, total_len = struct.unpack_from("<4sII", header, 0)

    return {
        "magic_ok":    magic == b"glTF",
        "version_ok":  version == 2,
        "size_bytes":  size_bytes,
        "size_mb":     round(size_bytes / 1_048_576, 2),
        "header_len_ok": total_len == size_bytes,
        "ok":          magic == b"glTF" and version == 2,
    }
```

**GLB size budget:** web delivery < 5 MB recommended; < 10 MB acceptable with justification;
> 20 MB is a hard WARN (run `Skill("forge-optimize")` before `Skill("atelier-webgl")`).

**Poster presence check:** for web assets, verify `<slug>-hero-poster.webp` exists adjacent
to the GLB and is ≥ 1 KB. The poster is the reduced-motion / no-WebGL fallback.
