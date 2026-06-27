"""
forge-validate/scripts/topology_audit.py
Blender-headless bmesh topology audit for the Forge validate gate.

This is the executable home of mesh-checklist.md §6. It emits the bmesh-level topology
fields the Tier-3 topology reviewer reads (adversarial-escalation.md §4) — fields that
trimesh-based validate.py does NOT and cannot produce:
    non_manifold_edges, flipped_faces, degenerate_faces, high_valence_poles, pct_quads, ngons

Usage (PowerShell — run via Blender subprocess; the `--` separator is MANDATORY):
    blender -b --factory-startup --python-exit-code 1 -P topology_audit.py -- \
        --input "C:/path/to/model.glb" [--json] [--poles-min-valence 6]

Run = invoke this through Blender. validate.py (trimesh) does NOT call it; the model fires
it for substantial/print/subdiv targets and feeds the JSON to the topology reviewer.

Platform: Native Windows 11. The trimesh gate runs under the `python` launcher; THIS script
needs Blender's bundled Python (bpy). EEVEE is irrelevant here — no rendering happens.
"""

import sys
import io
import json
import argparse
import pathlib

import bpy
import bmesh

# UTF-8 stdout wrapper (Windows cp1252 default breaks non-ASCII console output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    p = argparse.ArgumentParser(description="forge-validate bmesh topology audit", add_help=False)
    p.add_argument("--input", default="")
    p.add_argument("--json", action="store_true", default=False)
    p.add_argument("--poles-min-valence", type=int, default=6,
                   help="Valence at/above which a vertex counts as a high-valence pole (default 6)")
    return p.parse_args(argv)


def import_mesh(path: str) -> None:
    """Load a mesh/scene into the empty factory scene. Forward-slash absolute paths only."""
    ext = pathlib.Path(path).suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".ply":
        bpy.ops.wm.ply_import(filepath=path)
    elif ext == ".blend":
        bpy.ops.wm.open_mainfile(filepath=path)
    else:
        raise ValueError(f"unsupported mesh extension: {ext}")


def audit_object(obj, poles_min_valence: int) -> dict:
    """bmesh topology audit for a single mesh object (mesh-checklist.md §6)."""
    bm = bmesh.new()
    try:
        bm.from_mesh(obj.data)
        bm.verts.ensure_lookup_table()
        bm.edges.ensure_lookup_table()
        bm.faces.ensure_lookup_table()
        tf = len(bm.faces)
        quads = sum(1 for f in bm.faces if len(f.verts) == 4)
        # flipped_faces: connectivity-based (count faces wound against their neighbours)
        flipped = _count_flipped_faces(bm)
        return {
            "object":              obj.name,
            "faces":               tf,
            "tris":                sum(1 for f in bm.faces if len(f.verts) == 3),
            "quads":               quads,
            "ngons":               sum(1 for f in bm.faces if len(f.verts) > 4),
            "pct_quads":           round(quads / max(tf, 1) * 100, 1),
            "non_manifold_edges":  sum(1 for e in bm.edges if not e.is_manifold and not e.is_boundary),
            "boundary_edges":      sum(1 for e in bm.edges if e.is_boundary),
            "wire_edges":          sum(1 for e in bm.edges if e.is_wire),
            "flipped_faces":       flipped,
            "high_valence_poles":  sum(1 for v in bm.verts if len(v.link_edges) >= poles_min_valence),
            "degenerate_faces":    sum(1 for f in bm.faces if f.calc_area() < 1e-8),
            "is_watertight":       all(e.is_manifold for e in bm.edges) and not any(e.is_boundary for e in bm.edges),
        }
    finally:
        bm.free()  # CRITICAL: always free; leaks cause OOM on batch jobs


def _count_flipped_faces(bm) -> int:
    """Count faces wound opposite to the majority of their manifold neighbours.

    Connectivity-based (not the centroid-dot heuristic, which false-positives on concave
    shapes). A face is flipped if, across its shared manifold edges, the winding direction
    is inconsistent with the adjacent face for the majority of its edges.
    """
    flipped = 0
    for f in bm.faces:
        disagree = 0
        shared = 0
        for e in f.edges:
            if not e.is_manifold:
                continue
            other = next((lf for lf in e.link_faces if lf is not f), None)
            if other is None:
                continue
            shared += 1
            # For consistent winding, the shared edge is traversed in OPPOSITE directions
            # by the two faces. Same direction => one of them is flipped.
            v_pair = (e.verts[0].index, e.verts[1].index)
            if _edge_dir_in_face(f, v_pair) == _edge_dir_in_face(other, v_pair):
                disagree += 1
        if shared > 0 and disagree > shared / 2:
            flipped += 1
    return flipped


def _edge_dir_in_face(face, v_pair) -> bool:
    """True if the face traverses edge (a,b) in the a->b direction."""
    idx = [v.index for v in face.verts]
    a, b = v_pair
    n = len(idx)
    for i in range(n):
        if idx[i] == a and idx[(i + 1) % n] == b:
            return True
        if idx[i] == b and idx[(i + 1) % n] == a:
            return False
    return True


def aggregate(objs: list[dict]) -> dict:
    """Roll per-object audits into suite-level totals + a gate verdict."""
    total = {k: 0 for k in ("faces", "tris", "quads", "ngons", "non_manifold_edges",
                            "boundary_edges", "wire_edges", "flipped_faces",
                            "high_valence_poles", "degenerate_faces")}
    for o in objs:
        for k in total:
            total[k] += o.get(k, 0)
    total["pct_quads"] = round(total["quads"] / max(total["faces"], 1) * 100, 1)
    # Gate verdict on the headline integrity fields (mesh-checklist.md §6 QUALITY_GATES)
    fail = (total["non_manifold_edges"] > 0 or total["flipped_faces"] > 0
            or total["degenerate_faces"] > 0)
    warn = total["high_valence_poles"] > 0 or total["ngons"] > 0
    total["overall"] = "FAIL" if fail else ("WARN" if warn else "PASS")
    return total


def main() -> None:
    args = parse_args()
    if not args.input:
        print(json.dumps({"error": "no --input given", "overall": "ERROR"}))
        return
    import_mesh(args.input)
    objs = [audit_object(o, args.poles_min_valence)
            for o in bpy.data.objects if o.type == "MESH"]
    if not objs:
        print(json.dumps({"error": "no mesh objects found", "overall": "ERROR"}))
        return
    report = {"file": args.input, "objects": objs, "totals": aggregate(objs)}
    report["overall"] = report["totals"]["overall"]
    if args.json:
        print(json.dumps(report, indent=2))
    else:
        t = report["totals"]
        print(f"[topology_audit] {pathlib.Path(args.input).name}  overall: {t['overall']}")
        print(f"  faces={t['faces']} quads={t['pct_quads']}% ngons={t['ngons']} "
              f"non_manifold_edges={t['non_manifold_edges']} flipped_faces={t['flipped_faces']} "
              f"degenerate_faces={t['degenerate_faces']} high_valence_poles={t['high_valence_poles']}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        # Surface the error but let Blender exit; --python-exit-code 1 makes the process fail.
        print(json.dumps({"error": str(e), "overall": "ERROR"}))
        raise
