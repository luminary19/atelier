# forge-topology — Topology Audit & Repair Reference

## Contents
- §1. Headless invocation patterns (Windows PowerShell)
- §2. topo_audit.py — full bmesh audit script
- §3. topo_repair.py — auto-repair script
- §4. Wireframe QA render script
- §5. Pole detection & edge-density analysis
- §6. Quality gates (pass/fail thresholds)
- §7. Polygon type rules
- §8. Pole placement rules
- §9. Deformation / rigging topology rules
- §10. Subdivision surface rules
- §11. Gotchas → fixes

---

## §1. Headless Invocation Patterns

```powershell
$b = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"

# Audit a .blend file
& $b --background --python "C:\forge\topo_audit.py" -- `
    --input  "C:\assets\char.blend" `
    --output "C:\reports\char_topo.json"

# Audit a foreign format (.glb / .gltf / .fbx / .obj) — SAME script.
# topo_audit.py's load_input() dispatcher (see §2) branches on the suffix and imports
# into a fresh empty scene, so no extra import_audit_export.py is needed.
& $b --background --python "C:\forge\topo_audit.py" -- `
    --input  "C:\assets\model.fbx" `
    --output "C:\reports\model_topo.json"

# Render wireframe overlay PNG for visual QA
& $b --background --python "C:\forge\render_wireframe_qa.py" -- `
    --input  "C:\assets\char.blend" `
    --output "C:\renders\wire_check.png"

# Capture all Blender stdout to a log file
$output = & $b --background --python topo_audit.py -- `
    --input mesh.blend 2>&1
$output | Out-File "blender_log.txt"
```

**Critical:** `--` separates Blender args from script args. Omitting it causes Blender to
treat your `--input` as a blend filename — silent failure.

**Input formats:** `topo_audit.py` accepts `.blend` (opened directly) and `.glb`/`.gltf`/
`.fbx`/`.obj` (imported into a fresh empty scene) via the §2 `load_input()` dispatcher.
`topo_repair.py` (§3) and the wireframe QA render (§4) operate on whatever scene is loaded,
so feed them either a `.blend` or run them in the same process right after `load_input()`.
When Blender is unavailable, the SKILL decide-first table's **pure-Python fallback tier**
(`trimesh` / Open3D / PyMeshLab — see `references/mesh-libs.md`) audits and repairs triangle
meshes loaded from `.glb`/`.obj`/`.stl`/`.ply`, but cannot read `.blend` and reports no
quad/pole statistics (triangle soup only).

---

## §2. topo_audit.py — Full bmesh Audit

```python
"""
topo_audit.py — Headless Blender topology auditor.
Usage: blender --background --python topo_audit.py -- --input mesh.blend --output report.json
Accepts .blend / .glb / .gltf / .fbx / .obj — the suffix dispatcher below picks the loader.
Blender 4.5 LTS / 5.x compatible.
"""
import sys, json, argparse, math
from pathlib import Path
import bpy, bmesh
from mathutils import Vector

argv = sys.argv
if "--" in argv:
    argv = argv[argv.index("--") + 1:]
else:
    argv = []

parser = argparse.ArgumentParser()
parser.add_argument("--input",  required=True)
parser.add_argument("--output", required=True)
args = parser.parse_args(argv)


def load_input(path: str):
    """Branch on file suffix. .blend opens the file directly; foreign formats import
    into a fresh empty scene so no startup objects pollute the audit."""
    ext = Path(path).suffix.lower()
    if ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
        return
    # Foreign format: start from an empty scene, then import.
    bpy.ops.wm.read_factory_settings(use_empty=True)
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)     # Blender 4.x native OBJ importer
    else:
        raise ValueError(f"Unsupported input format: {ext} "
                         "(use .blend/.glb/.gltf/.fbx/.obj, or a pure-Python fallback)")


load_input(args.input)

results = {}

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    me = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(me)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()

        n_tris  = sum(1 for f in bm.faces if len(f.verts) == 3)
        n_quads = sum(1 for f in bm.faces if len(f.verts) == 4)
        n_ngons = sum(1 for f in bm.faces if len(f.verts) > 4)
        total   = len(bm.faces)

        # Non-manifold: edges shared by != 2 faces (and not boundary)
        nm_edges   = [e.index for e in bm.edges if not e.is_manifold and not e.is_boundary]
        boundary_e = [e.index for e in bm.edges if e.is_boundary]
        wire_e     = [e.index for e in bm.edges if e.is_wire]
        nm_verts   = [v.index for v in bm.verts if not v.is_manifold]
        is_wt      = (len(boundary_e) == 0 and len(nm_edges) == 0 and len(wire_e) == 0)

        # Flipped normals heuristic (convex meshes; see §11 G1 for concave caveat)
        obj_center  = Vector(obj.location)
        flipped     = []
        for f in bm.faces:
            centroid = f.calc_center_median()
            outward  = (centroid - obj_center).normalized()
            if outward.length > 0 and f.normal.dot(outward) < 0:
                flipped.append(f.index)

        # Poles: valence != 4
        poles_3    = [v.index for v in bm.verts if len(v.link_edges) == 3]
        poles_5    = [v.index for v in bm.verts if len(v.link_edges) == 5]
        poles_high = [v.index for v in bm.verts if len(v.link_edges) > 5]

        # Degenerate: zero-area faces
        degenerate = [f.index for f in bm.faces if f.calc_area() < 1e-8]

        # Edge density coefficient of variation (CV < 0.5 = acceptable)
        lengths = [e.calc_length() for e in bm.edges if not e.is_wire]
        cv = 0.0
        if lengths:
            mean = sum(lengths) / len(lengths)
            var  = sum((l - mean) ** 2 for l in lengths) / len(lengths)
            cv   = round(math.sqrt(var) / mean, 4) if mean > 0 else 0.0

        results[obj.name] = {
            "faces": total, "verts": len(bm.verts), "edges": len(bm.edges),
            "tris": n_tris, "quads": n_quads, "ngons": n_ngons,
            "pct_quads": round(n_quads / max(total, 1) * 100, 1),
            "non_manifold_edges": len(nm_edges),
            "boundary_edges": len(boundary_e),
            "wire_edges": len(wire_e),
            "non_manifold_verts": len(nm_verts),
            "is_watertight": is_wt,
            "flipped_faces": len(flipped),
            "poles_3": len(poles_3), "poles_5": len(poles_5),
            "poles_high_valence": len(poles_high),
            "degenerate_faces": len(degenerate),
            "density_cv": cv,
            "issues": {
                "non_manifold_edge_indices": nm_edges[:50],
                "boundary_edge_indices":     boundary_e[:50],
                "flipped_face_indices":      flipped[:50],
                "high_pole_vert_indices":    poles_high[:50],
                "degenerate_face_indices":   degenerate[:50],
            }
        }
    finally:
        bm.free()   # CRITICAL — prevents OOM on batch jobs

with open(args.output, "w", encoding="utf-8") as f:
    json.dump(results, f, indent=2)
print(f"[topo_audit] Written: {args.output}")
```

---

## §3. topo_repair.py — Auto-Repair

```python
"""
topo_repair.py — Auto-repairs common topology issues.
Run AFTER topo_audit.py confirms issues exist.
Repair order: merge doubles → delete wire/isolated → recalc normals.
Usage: blender -b in.blend --python topo_repair.py -- --output C:/out/in_repaired.blend
NEVER overwrites the source — writes to --output (default <stem>_repaired.blend).
"""
import sys, argparse
from pathlib import Path
import bpy, bmesh

def repair_object(obj):
    me = obj.data
    bm = bmesh.new()
    try:
        bm.from_mesh(me)

        # 1. Merge by distance (removes duplicate verts/edges)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)

        # 2. Delete wire edges
        wire_edges = [e for e in bm.edges if e.is_wire]
        bmesh.ops.delete(bm, geom=wire_edges, context="EDGES")

        # 3. Delete isolated vertices (after wire deletion, lookup stale)
        bm.verts.ensure_lookup_table()
        iso_verts = [v for v in bm.verts if not v.link_edges]
        bmesh.ops.delete(bm, geom=iso_verts, context="VERTS")

        # 4. Recalculate face normals outward
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])

        bm.to_mesh(me)
        me.update()
    finally:
        bm.free()

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--output", default=None,
                    help="Repaired .blend path. Defaults to <source-stem>_repaired.blend; "
                         "NEVER overwrites the source.")
args = parser.parse_args(argv)

for obj in bpy.data.objects:
    if obj.type == "MESH":
        repair_object(obj)
        print(f"[topo_repair] Repaired: {obj.name}")

src = Path(bpy.data.filepath)
out = Path(args.output) if args.output else src.with_name(f"{src.stem}_repaired.blend")
if out.resolve() == src.resolve():
    raise SystemExit("[topo_repair] Refusing to overwrite the source .blend — pass a distinct --output")
out.parent.mkdir(parents=True, exist_ok=True)
# save_as_mainfile to a NEW path; copy=True keeps the in-memory file pointed at the source,
# so re-running on the source always starts from the same untouched geometry (idempotent).
bpy.ops.wm.save_as_mainfile(filepath=str(out), copy=True)
print(f"[topo_repair] Written (source left untouched): {out}")
```

**Output / idempotency:** repair NEVER overwrites the input. It writes a separate
`<stem>_repaired.blend` (or your `--output`), so a botched auto-repair is always rollback-safe
— the original geometry is intact. Re-running `topo_repair.py` on an already-clean
`*_repaired.blend` is effectively a no-op (merge-doubles, wire/isolated deletion and
normal-recalc all find nothing to change), matching forge-procedural's idempotent-rebuild
discipline. The wireframe QA render (§4) and audit (§2) should be pointed at the
`*_repaired.blend`, never the source.

---

## §4. Wireframe QA Render

```python
"""
render_wireframe_qa.py — Workbench wireframe render for visual topology inspection.
Use: blender --background scene.blend --python render_wireframe_qa.py -- out.png
CYCLES is NOT used here; Workbench is lighter for wireframe overlays.
"""
import bpy, sys

argv = sys.argv
out_path = argv[argv.index("--") + 1] if "--" in argv else "C:/tmp/wire_qa.png"

scene = bpy.context.scene
scene.render.engine = "BLENDER_WORKBENCH"
scene.render.filepath = out_path
scene.render.image_settings.file_format = "PNG"
scene.render.resolution_x = 1920
scene.render.resolution_y = 1080

scene.display.shading.type = "SOLID"
scene.display.shading.show_object_outline = True

for obj in bpy.data.objects:
    if obj.type == "MESH":
        obj.show_wire = True
        obj.show_all_edges = True

bpy.ops.render.render(write_still=True)
print(f"[render_qa] Wireframe PNG → {out_path}")
```

**After rendering:** call `Read` on the PNG. Visually confirm:
- Continuous, unbroken loops around joints (eyes, mouth, shoulders, elbows, knees)
- Even loop spacing (denser at joints, not random)
- No star-shaped pole clusters in bent zones
- No T-junctions or dangling wire edges
- Clean silhouette, no jagged ngon edges

**Wireframe-render failure table (what you see → cause → fix):**

| What the PNG shows | Cause | Fix |
|--------------------|-------|-----|
| All black / empty frame | No camera or world set in the scene | Add a camera (`bpy.ops.object.camera_add`) + set `scene.camera`; raise `scene.display.shading.studiolight` or set a world background |
| Solid faces, no wires visible | `show_wire` / `show_all_edges` not enabled on the objects | Set `obj.show_wire = True` and `obj.show_all_edges = True` (already in the script — confirm the loop ran on each mesh) |
| Dense black mass, edges unreadable | Resolution too low for the poly count | Raise to 1920×1080+ or render a cropped detail region; render LODs individually |
| Flat grey faces, edges washed out | Workbench cavity/outline off | Enable `scene.display.shading.show_object_outline = True` and turn on cavity (`shading.show_cavity = True`) for edge contrast |

---

## §5. Pole Detection & Edge Density

```python
"""
pole_check.py — Run inside Blender background mode.
Reports valence distribution and edge density coefficient of variation.
"""
import bmesh, bpy, math

for obj in bpy.data.objects:
    if obj.type != "MESH":
        continue
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()

        valence_dist = {}
        high_val = []
        for v in bm.verts:
            val = len(v.link_edges)
            valence_dist[val] = valence_dist.get(val, 0) + 1
            if val > 5:
                high_val.append({"vert": v.index, "valence": val, "co": list(v.co)})

        lengths = [e.calc_length() for e in bm.edges if not e.is_wire]
        cv = 0.0
        if lengths:
            mean = sum(lengths) / len(lengths)
            std  = math.sqrt(sum((l - mean)**2 for l in lengths) / len(lengths))
            cv   = round(std / mean, 4) if mean > 0 else 0.0

        print(f"{obj.name}: valence={valence_dist} cv={cv} high_val={len(high_val)}")
    finally:
        bm.free()
```

---

## §6. Quality Gates

```python
QUALITY_GATES = {
    "pct_quads_min":          90.0,  # % quads; <90 = warn; <70 = fail
    "ngon_max":               0,     # 0 for subdiv/deform; 5% for flat hard-surface statics
    "non_manifold_edges_max": 0,     # always 0 for print/boolean/subdiv
    "require_watertight":     True,  # for print; optional for render-only
    "flipped_faces_max":      0,
    "high_valence_poles_max": 0,     # verts with valence > 5
    "degenerate_faces_max":   0,
    "density_cv_max":         0.5,   # edge length CV; > 0.5 = uneven loops
}

def passes_gates(r: dict) -> tuple:
    failures = []
    if r["pct_quads"] < QUALITY_GATES["pct_quads_min"]:
        failures.append(f"Only {r['pct_quads']}% quads (min 90%)")
    if r["ngons"] > QUALITY_GATES["ngon_max"]:
        failures.append(f"{r['ngons']} ngons")
    if r["non_manifold_edges"] > 0:
        failures.append(f"{r['non_manifold_edges']} non-manifold edges")
    if QUALITY_GATES["require_watertight"] and not r["is_watertight"]:
        failures.append("Not watertight")
    if r["flipped_faces"] > 0:
        failures.append(f"{r['flipped_faces']} flipped normals")
    if r["poles_high_valence"] > 0:
        failures.append(f"{r['poles_high_valence']} high-valence poles (>5)")
    if r["degenerate_faces"] > 0:
        failures.append(f"{r['degenerate_faces']} degenerate faces")
    if r.get("density_cv", 0) > QUALITY_GATES["density_cv_max"]:
        failures.append(f"Edge density CV={r['density_cv']} > 0.5")
    return (len(failures) == 0, failures)
```

---

## §7. Polygon Type Rules

| Rule | Rationale |
|------|-----------|
| Default to quads (>95% for subdiv/deform meshes) | Catmull-Clark subdivides quads into quads. Tris/ngons introduce poles at subdivision center, causing pinching |
| Tris: only at export triangulation (last step) | Game engines consume tris, but modeling in tris locks edge-loop flow. Use `quads_convert_to_tris` at export |
| Ngons: only on flat, non-deforming, non-subdividing surfaces | Curved ngons produce unpredictable triangulation, causing shading artifacts |
| Concave quads: split into tris or rework | Concave quads produce broken normals and subdivision artifacts |

---

## §8. Pole Placement Rules

| Pole type | Valence | Placement rule |
|-----------|---------|----------------|
| Regular | 4 | Default; no restrictions |
| N-pole | 3 | OK on flat/low-visibility, away from deformation |
| E-pole | 5 | OK on flat; necessary for loop transitions (e.g., 3→5 expansion) |
| High-pole | ≥6 | Avoid on curved surfaces; max 6 if absolutely necessary |

**Forbidden pole zones:** elbow crease, knee bend, shoulder socket, mouth corners, eyelid edge.
**Allowed pole zones:** top of head, back of heel, underarm flat, any low-curvature region.

---

## §9. Deformation / Rigging Topology Rules

- **Minimum 3 edge loops through every joint** (elbow, knee, finger knuckle); 5+ for ball-and-socket
- **Loop density denser on the compression side** (inside of elbow, knee crease)
- **Loops perpendicular to the bone/rotation axis** — loops parallel to the axis do nothing for bending
- **Extend loops past the deformation zone** into flat surface before terminating (abrupt termination = pinching)
- **Poles away from joints** — if a pole must live near a joint, push it to the flat region adjacent
- **Follow primary muscle direction** with edge flow (pectorals, obliques, deltoid, quads)

---

## §10. Subdivision Surface Rules (Catmull-Clark)

- **Support edges:** add one loop each side of a feature edge. Distance controls sharpness:
  ~2% of local edge length = very sharp; ~20% = soft roundover
- **Cylinder caps:** use quad-grid cap (spider/pinwheel pattern) — all cap verts at valence 4.
  Max 6 spans for circular cross-sections. A single center vert = high-valence pole = wavy artifacts.
- **Use creases instead of extra edge loops** for hard-surface:
  `bmesh.ops.edges_crease` with value 0–1. Sharpness > 5 rarely needed.
- **Even quad density:** CV of edge lengths < 0.5. Very long thin quads cause uneven subdivision.

---

## §11. Gotchas → Fixes

| Gotcha | Fix |
|--------|-----|
| `bmesh.new()` not freed → OOM on batch | Always `try/finally: bm.free()` |
| `bm.faces` indices stale after bmesh ops | Call `bm.verts.ensure_lookup_table()` etc. after any topology-modifying op |
| Flipped-normal heuristic fires on concave mesh (>30% flagged) | Use `bmesh.ops.recalc_face_normals()` (traverses connectivity) instead |
| ngon triangulation differs in engine vs Blender | Apply `quads_convert_to_tris` in test scene before export; resolve ngons first |
| Non-manifold edges after boolean | Run `remove_doubles` + `select_non_manifold` + re-audit |
| `from_edit_mesh` error in background mode | Use `bm.from_mesh(obj.data)` — never `from_edit_mesh` in headless |
| High-valence revolution cap (valence > 6 = wavy artifacts) | Use `bmesh.ops.grid_fill()` for circular boundary loops |
| `trimesh.is_watertight` False on multi-body mesh | Check `mesh.body_count`; split and check each body separately |
| blender.exe not on PATH | `$env:PATH += ";C:\Program Files\Blender Foundation\Blender 4.5"` |
| Windows batch multiple blender calls hang (4.5+) | Use `Start-Process -Wait` in PowerShell; add `--factory-startup` |
