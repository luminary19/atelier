"""
forge-validate/scripts/validate.py
Forge suite mesh + GLB validation gate.

Usage:
    python validate.py --input model.glb [--budget-faces 100000] [--units m] [--json]

Pure stdlib for the structural checks; optional trimesh for mesh topology.
Degrades gracefully if trimesh is absent (GLB structural + size checks only).
Windows-first: use `python`, not `python3`.
Exit 0 = all checks ran (caller inspects JSON for PASS/FAIL/WARN per item).
"""

import sys
import io
import json
import struct
import argparse
import pathlib

# Windows stdout encoding fix — must be at module top
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ---------------------------------------------------------------------------
# Stdlib-only checks (always run)
# ---------------------------------------------------------------------------

def check_glb_header(path: pathlib.Path) -> dict:
    """Verify GLB magic bytes, version, and chunk structure. Pure stdlib."""
    if not path.exists():
        return {"check": "glb_header", "status": "FAIL", "detail": "file not found"}
    size_bytes = path.stat().st_size
    if size_bytes < 12:
        return {"check": "glb_header", "status": "FAIL", "detail": f"file too small: {size_bytes} bytes"}
    with open(path, "rb") as f:
        header = f.read(12)
    magic, version, total_len = struct.unpack_from("<4sII", header, 0)
    if magic != b"glTF":
        return {"check": "glb_header", "status": "FAIL", "detail": f"bad magic bytes: {magic!r}"}
    if version != 2:
        return {"check": "glb_header", "status": "WARN", "detail": f"unexpected GLB version: {version}"}
    return {
        "check":        "glb_header",
        "status":       "PASS",
        "size_bytes":   size_bytes,
        "size_mb":      round(size_bytes / 1_048_576, 2),
        "version":      version,
    }


def check_glb_size(path: pathlib.Path, warn_mb: float = 5.0, block_mb: float = 20.0) -> dict:
    """Check GLB file size against web delivery budgets."""
    size_mb = path.stat().st_size / 1_048_576
    if size_mb > block_mb:
        status = "WARN"
        detail = f"{size_mb:.1f} MB exceeds {block_mb} MB — run forge-optimize before web delivery"
    elif size_mb > warn_mb:
        status = "WARN"
        detail = f"{size_mb:.1f} MB exceeds recommended {warn_mb} MB web budget"
    else:
        status = "PASS"
        detail = f"{size_mb:.2f} MB"
    return {"check": "glb_size_budget", "status": status, "detail": detail, "size_mb": round(size_mb, 2)}


def check_poster_presence(path: pathlib.Path) -> dict:
    """Check that a poster WebP exists adjacent to the GLB (web delivery requirement)."""
    stem = path.stem
    # Handle common naming patterns: hero.glb → hero-poster.webp, slug-hero.glb → slug-hero-poster.webp
    candidates = [
        path.parent / f"{stem}-poster.webp",
        path.parent / f"{stem}.webp",
        path.parent / (stem.replace("-hero", "-hero-poster") + ".webp"),
    ]
    found = [str(c) for c in candidates if c.exists() and c.stat().st_size >= 1024]
    if found:
        return {"check": "poster_presence", "status": "PASS", "detail": found[0]}
    return {
        "check":  "poster_presence",
        "status": "WARN",
        "detail": f"no poster WebP found adjacent to {path.name}; poster is the no-WebGL fallback",
    }


# ---------------------------------------------------------------------------
# trimesh checks (run when trimesh is installed)
# ---------------------------------------------------------------------------

def _load_concatenated(path: pathlib.Path):
    """Load a mesh as a single concatenated Trimesh, or raise. Internal helper."""
    import trimesh
    loaded = trimesh.load(str(path), force="mesh")
    if isinstance(loaded, trimesh.Scene):
        geoms = list(loaded.geometry.values())
        if not geoms:
            raise ValueError("scene contains no geometry")
        return trimesh.util.concatenate(geoms)
    return loaded


def check_with_trimesh(path: pathlib.Path, budget_faces: int, units: str,
                       repair_preview: bool = False) -> list[dict]:
    """Run full mesh topology checks using trimesh. Returns list of result dicts.

    Measure first, repair second: the gate reports the asset's RAW state (is_watertight,
    winding, volume, broken_faces) on the untouched mesh so it never silently masks the
    defect it exists to catch. When repair_preview=True, an advisory pass on a COPY reports
    whether the mesh would become watertight after process()/fix_normals()/fill_holes().
    """
    try:
        import trimesh
        import trimesh.repair as repair
        import numpy as np
    except ImportError:
        return [{"check": "trimesh_available", "status": "WARN",
                 "detail": "trimesh not installed — install with: pip install trimesh[easy]  (full checks skipped)"}]

    results = []

    # Load mesh
    try:
        mesh = _load_concatenated(path)
    except Exception as e:
        return [{"check": "mesh_load", "status": "FAIL", "detail": str(e)}]

    results.append({"check": "mesh_load", "status": "PASS",
                    "detail": f"{len(mesh.faces)} faces, {len(mesh.vertices)} verts"})

    # NaN / Inf check (on raw input — corrupt geometry makes everything else unreliable)
    has_nan = not np.isfinite(mesh.vertices).all()
    results.append({
        "check":  "finite_vertices",
        "status": "FAIL" if has_nan else "PASS",
        "detail": "NaN/Inf vertices found" if has_nan else "all vertices finite",
    })
    if has_nan:
        return results  # further checks unreliable on corrupt geometry

    # --- RAW verdict (NO mutation) — this is what the gate grades --------------
    # Only merge duplicate verts (process without validate=True does NOT remove faces or
    # fix normals) so multi-body GLBs load with shared verts but topology stays untouched.
    raw_watertight = bool(mesh.is_watertight)
    raw_winding = bool(mesh.is_winding_consistent)
    raw_volume = bool(mesh.is_volume)
    raw_broken = len(repair.broken_faces(mesh))
    raw_degenerate = int((~mesh.nondegenerate_faces()).sum())
    raw_euler = int(mesh.euler_number)
    try:
        body_count = len(mesh.split(only_watertight=False))
    except Exception:
        body_count = None  # mesh.split needs networkx (trimesh[easy]); degrade, don't error

    results.append({"check": "is_watertight", "status": "PASS" if raw_watertight else "FAIL",
                    "detail": f"{raw_watertight} (raw — measured before any repair)"})
    results.append({"check": "is_winding_consistent", "status": "PASS" if raw_winding else "FAIL",
                    "detail": f"{raw_winding} (raw)"})
    results.append({"check": "is_volume", "status": "PASS" if raw_volume else "WARN",
                    "detail": f"{raw_volume} (raw)"})

    # Volume sign (inward normals). trimesh defines is_volume as watertight AND
    # winding-consistent AND volume > 0, so an inverted-but-closed mesh has is_volume=False
    # purely from the sign. Surface that explicit, actionable case even when raw_volume is
    # False — only skip when the mesh is open/non-manifold (volume meaningless there).
    if raw_watertight and raw_winding:
        vol = mesh.volume
        vol_ok = vol > 0
        results.append({"check": "volume_positive", "status": "PASS" if vol_ok else "FAIL",
                        "detail": f"volume = {vol:.4f}" + ("" if vol_ok else " (negative = normals inward, run mesh.invert())")})

    # Euler number (genus-0 simple solid = 2)
    results.append({"check": "euler_number", "status": "PASS" if raw_euler == 2 else "WARN",
                    "detail": f"euler = {raw_euler} (expected 2 for simple solid)"})

    # Broken faces (raw)
    results.append({"check": "broken_faces", "status": "PASS" if raw_broken == 0 else "FAIL",
                    "detail": f"{raw_broken} broken faces (raw)"})

    # Degenerate faces (raw count — informational; reported, not silently removed)
    results.append({"check": "degenerate_faces", "status": "PASS" if raw_degenerate == 0 else "WARN",
                    "detail": f"{raw_degenerate} degenerate faces (raw)"})

    # Optional advisory repair preview on a COPY — never mutates the graded mesh
    if repair_preview and not raw_watertight:
        try:
            preview = mesh.copy()
            preview.process(validate=True)            # 4.x: unique_faces & nondegenerate + fix_normals
            repair.fix_normals(preview, multibody=True)
            preview.fill_holes()
            results.append({
                "check":  "repairable",
                "status": "PASS" if preview.is_watertight else "WARN",
                "detail": ("would be watertight after process()/fix_normals()/fill_holes()"
                           if preview.is_watertight
                           else "still not watertight after light repair — escalate to PyMeshLab (see mesh-repair.md)"),
            })
        except Exception as e:
            results.append({"check": "repairable", "status": "WARN", "detail": f"repair preview failed: {e}"})

    # Body count (None when networkx unavailable — informational, not a gate failure)
    if body_count is None:
        results.append({"check": "body_count", "status": "WARN",
                        "detail": "body split needs networkx (pip install trimesh[easy])"})
    else:
        results.append({"check": "body_count", "status": "PASS" if body_count == 1 else "WARN",
                        "detail": f"{body_count} body(ies)"})

    # Polycount budget
    face_count = len(mesh.faces)
    over_budget = face_count > budget_faces
    results.append({
        "check":  "polycount_budget",
        "status": "WARN" if over_budget else "PASS",
        "detail": f"{face_count} faces vs budget {budget_faces}",
        "faces":  face_count,
        "budget": budget_faces,
    })

    # Scale / units check (bounding box sanity)
    dims = mesh.bounds[1] - mesh.bounds[0]
    max_dim = float(np.max(dims))
    if units == "mm":
        # For print: object should be between 1mm and 1000mm
        scale_ok = 1.0 <= max_dim <= 1000.0
        scale_detail = f"max dim = {max_dim:.2f} mm (expected 1–1000 mm for print)"
    else:
        # For web/glTF: object should be between 0.001m and 100m
        scale_ok = 0.001 <= max_dim <= 100.0
        scale_detail = f"max dim = {max_dim:.3f} m (expected 0.001–100 m for web/glTF)"
    results.append({"check": "scale_units", "status": "PASS" if scale_ok else "WARN", "detail": scale_detail})

    # Surface area and volume summary (informational)
    results.append({"check": "surface_area", "status": "PASS",
                    "detail": f"{mesh.area:.4f} {units}^2"})
    if raw_volume:
        results.append({"check": "volume_measurement", "status": "PASS",
                        "detail": f"{mesh.volume:.4f} {units}^3"})

    return results


# ---------------------------------------------------------------------------
# UV overlap heuristic (trimesh, optional)
# ---------------------------------------------------------------------------

def check_uv_basic(path: pathlib.Path, allow_udim: bool = False) -> list[dict]:
    """UV presence, range, texel-density CV and flipped-UV winding (trimesh).

    NOTE: this does NOT compute full UV-island overlap (intersection); the range check is a
    tiling/UDIM signal only. Set allow_udim=True (FORGE.md UDIM target) to downgrade the
    out-of-[0,1] range finding from WARN to INFO so intentional UDIM tiling is not flagged.
    """
    try:
        import trimesh
        import numpy as np
    except ImportError:
        return []

    try:
        mesh = trimesh.load(str(path), force="mesh")
        if isinstance(mesh, trimesh.Scene):
            mesh = trimesh.util.concatenate(list(mesh.geometry.values()))
    except Exception:
        return []

    results = []

    # UV presence
    has_uv = hasattr(mesh.visual, "uv") and getattr(mesh.visual, "uv", None) is not None
    results.append({"check": "uv_present", "status": "PASS" if has_uv else "WARN",
                    "detail": "UV coordinates present" if has_uv else "no UV data found in mesh"})

    if has_uv:
        uv = np.asarray(mesh.visual.uv)
        # Check UV range (should be 0–1 for each island; outside = tiling or error).
        # UDIM tiling is intentional — downgrade to INFO when the project allows it.
        out_of_range = int(np.sum((uv < 0) | (uv > 1)))
        if out_of_range > 0:
            range_status = "INFO" if allow_udim else "WARN"
            range_note = "UDIM tiling (allowed)" if allow_udim else "tiling or unwrap error"
        else:
            range_status, range_note = "PASS", "all within [0,1]"
        results.append({
            "check":  "uv_range",
            "status": range_status,
            "detail": f"{out_of_range} UV coords outside [0,1] ({range_note})",
        })

        # Texel-density coefficient of variation (mesh-checklist.md §5). CV < 0.5 = even
        # texel density; higher = uneven (some islands far higher resolution than others).
        try:
            face_uvs = uv[mesh.faces]                          # (N, 3, 2)
            v0 = face_uvs[:, 1] - face_uvs[:, 0]
            v1 = face_uvs[:, 2] - face_uvs[:, 0]
            uv_areas = np.abs(v0[:, 0] * v1[:, 1] - v0[:, 1] * v1[:, 0]) * 0.5
            face_areas = mesh.area_faces
            mask = face_areas > 1e-10
            density = np.sqrt(uv_areas[mask] / face_areas[mask])
            if len(density) > 0 and float(np.mean(density)) > 0:
                cv = float(np.std(density) / np.mean(density))
                results.append({
                    "check":  "uv_texel_cv",
                    "status": "WARN" if cv > 0.5 else "PASS",
                    "detail": f"texel-density CV = {cv:.3f} (WARN > 0.5 — uneven texel density)",
                })
        except Exception:
            pass  # informational only; never block on texel-density math

        # Flipped-UV winding via signed UV-triangle area (mesh-checklist.md §5
        # count_flipped_uvs). Negative signed area = mirrored island = flipped winding.
        try:
            face_uvs = uv[mesh.faces]
            a = face_uvs[:, 0]; b = face_uvs[:, 1]; c = face_uvs[:, 2]
            signed = (b[:, 0] - a[:, 0]) * (c[:, 1] - a[:, 1]) - (b[:, 1] - a[:, 1]) * (c[:, 0] - a[:, 0])
            flipped = int(np.sum(signed < 0))
            results.append({
                "check":  "uv_flipped_faces",
                "status": "WARN" if flipped > 0 else "PASS",
                "detail": f"{flipped} faces with flipped UV winding (mirrored checker; fix bmesh.ops.reverse_uvs)",
            })
        except Exception:
            pass

    return results


# ---------------------------------------------------------------------------
# Render-QA PNG verification (skill-authoring-meta §6.1)
# ---------------------------------------------------------------------------

def verify_render(path: pathlib.Path, min_bytes: int = 1024) -> dict:
    """Confirm a render PNG exists and is plausibly sized (< 1 KB == silent-failure image).

    A failed Cycles/Workbench render on Windows commonly writes a 0-byte or tiny black PNG
    while Blender still exits 0 — never Read such a file and report PASS.
    """
    if not path.exists():
        return {"check": "render_png", "status": "FAIL", "ok": False,
                "size_bytes": 0, "detail": f"output PNG does not exist: {path}"}
    size = path.stat().st_size
    if size < min_bytes:
        return {"check": "render_png", "status": "FAIL", "ok": False, "size_bytes": size,
                "detail": f"PNG suspiciously small: {size} bytes (< {min_bytes}) — render failed "
                          f"silently (EEVEE-on-Windows or missing write_still=True)"}
    return {"check": "render_png", "status": "PASS", "ok": True, "size_bytes": size,
            "detail": f"{size} bytes — safe to Read", "path": str(path.resolve())}


# ---------------------------------------------------------------------------
# Printability sub-pass (--print) — emits the `printability` block the Tier-3
# reviewer reads (printability.md §3–§5). trimesh-gated; degrades to WARN.
# ---------------------------------------------------------------------------

PRINT_THRESHOLDS = {
    "fdm":  {"min_wall_mm": 1.2, "overhang_deg": 45.0},
    "sla":  {"min_wall_mm": 0.5, "overhang_deg": 45.0},
    "sls":  {"min_wall_mm": 0.7, "overhang_deg": 360.0},
    "dmls": {"min_wall_mm": 0.5, "overhang_deg": 45.0},
}


def check_printability(path: pathlib.Path, process: str, n_samples: int = 800) -> list[dict]:
    """Printability checks for a print-target mesh. Emits volume_mm3, thin_sample_frac,
    overhang_face_count, drain_hole_count, body_count — the exact fields the reviewer
    checklist names. Process-aware thresholds from printability.md §2."""
    try:
        import trimesh
        import numpy as np
    except ImportError:
        return [{"check": "printability", "status": "WARN",
                 "detail": "trimesh not installed — printability checks skipped (install: pip install trimesh[easy])"}]

    th = PRINT_THRESHOLDS.get(process, PRINT_THRESHOLDS["fdm"])
    results = []
    try:
        mesh = _load_concatenated(path)
    except Exception as e:
        return [{"check": "printability", "status": "FAIL", "detail": f"load failed: {e}"}]

    is_vol = bool(mesh.is_volume)
    results.append({"check": "print_is_volume", "status": "PASS" if is_vol else "FAIL",
                    "detail": f"is_volume = {is_vol} (must be True for slicing)"})
    vol_mm3 = float(mesh.volume) if is_vol else 0.0
    results.append({"check": "print_volume_mm3", "status": "PASS" if vol_mm3 > 0 else "FAIL",
                    "detail": f"volume_mm3 = {vol_mm3:.2f}", "volume_mm3": round(vol_mm3, 4)})

    # Body count (multi-body raises WARN; needs networkx)
    try:
        body_count = len(mesh.split(only_watertight=False))
        results.append({"check": "print_body_count", "status": "PASS" if body_count == 1 else "WARN",
                        "detail": f"body_count = {body_count} (1 preferred)", "body_count": body_count})
    except Exception:
        results.append({"check": "print_body_count", "status": "WARN",
                        "detail": "body split needs networkx (pip install trimesh[easy])", "body_count": None})

    # Wall thickness via inward ray-casting from surface samples (printability.md §3)
    try:
        points, face_idx = trimesh.sample.sample_surface(mesh, count=n_samples)
        normals = mesh.face_normals[face_idx]
        origins = points - 1e-4 * normals
        thick = []
        for o, d in zip(origins, -normals):
            hits = mesh.ray.intersects_location(
                ray_origins=[o], ray_directions=[d], multiple_hits=False)[0]
            if len(hits) > 0:
                thick.append(float(np.linalg.norm(hits[0] - o)))
        thick = np.array([t for t in thick if np.isfinite(t)])
        if len(thick) > 0:
            thin_frac = float(np.mean(thick < th["min_wall_mm"]))
            results.append({
                "check":  "print_wall_thickness",
                "status": "PASS" if thin_frac < 0.05 else "WARN",
                "detail": f"thin_sample_frac = {thin_frac:.3f} (<0.05 ok); min_wall {th['min_wall_mm']}mm; "
                          f"min measured {float(np.min(thick)):.3f}mm",
                "thin_sample_frac": round(thin_frac, 4),
            })
        else:
            results.append({"check": "print_wall_thickness", "status": "WARN",
                            "detail": "no thickness samples computed (ray engine needs rtree; pyembree for speed)",
                            "thin_sample_frac": None})
    except Exception as e:
        results.append({"check": "print_wall_thickness", "status": "WARN",
                        "detail": f"wall-thickness ray-cast skipped: {e} "
                                  f"(needs a ray engine: pip install rtree, or pyembree for 60x speed)",
                        "thin_sample_frac": None})

    # Overhang faces (printability.md §4) — Z-up print orientation
    try:
        fn = mesh.face_normals
        angles = np.degrees(np.arccos(np.clip(-fn[:, 2], -1, 1)))
        overhang_count = int(np.sum(angles > th["overhang_deg"]))
        # SLS (overhang_deg 360) never flags — powder support eliminates supports
        results.append({
            "check":  "print_overhang",
            "status": "PASS" if overhang_count == 0 else "WARN",
            "detail": f"overhang_face_count = {overhang_count} (> {th['overhang_deg']} deg from vertical)",
            "overhang_face_count": overhang_count,
        })
    except Exception as e:
        results.append({"check": "print_overhang", "status": "WARN",
                        "detail": f"overhang check skipped: {e}", "overhang_face_count": None})

    # SLA drain holes: a hollow shell shows as >1 body OR genus > 0. We cannot reliably
    # detect drilled holes from triangle soup, so surface the requirement explicitly.
    if process == "sla":
        results.append({
            "check":  "print_drain_holes",
            "status": "WARN",
            "detail": "SLA: confirm >= 2 drain holes (diameter >= 3mm), one near the lowest Z — "
                      "trapped resin = failed print (see printability.md §5)",
            "drain_hole_count": None,
        })

    return results


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(description="Forge mesh + GLB validation gate.")
    ap.add_argument("--input", help="Path to .glb / .stl / .obj / .ply")
    ap.add_argument("--budget-faces", type=int, default=100_000,
                    help="Polycount WARN threshold (default: 100000)")
    ap.add_argument("--units", choices=["m", "mm", "cm"], default="m",
                    help="Expected unit system (m for web/glTF, mm for print)")
    ap.add_argument("--web", action="store_true",
                    help="Enable web-delivery checks (poster presence, GLB size budget)")
    ap.add_argument("--print", dest="print_mode", action="store_true",
                    help="Run the printability sub-pass (wall thickness, overhang, drain holes)")
    ap.add_argument("--process", choices=["fdm", "sla", "sls", "dmls"], default="fdm",
                    help="Print process for --print thresholds (default: fdm)")
    ap.add_argument("--udim", action="store_true",
                    help="Treat out-of-[0,1] UVs as intentional UDIM tiling (downgrade to INFO)")
    ap.add_argument("--repair-preview", action="store_true",
                    help="Advisory: on a COPY, report whether a failing mesh WOULD become watertight "
                         "after light repair. Default is measure-only (the gate never mutates what it grades).")
    ap.add_argument("--verify-png", metavar="PATH",
                    help="Verify a render PNG exists and is >= 1KB (skill-authoring-meta §6.1); "
                         "use before Read-ing a contact sheet. Can run standalone.")
    ap.add_argument("--json", action="store_true", help="Output JSON report to stdout")
    args = ap.parse_args()

    # Standalone PNG verification mode (no mesh input required)
    if args.verify_png:
        vr = verify_render(pathlib.Path(args.verify_png))
        report = {"file": args.verify_png, "overall": vr["status"], "checks": [vr],
                  "summary": {"pass": int(vr["status"] == "PASS"), "warn": 0,
                              "fail": int(vr["status"] == "FAIL")}}
        if args.json:
            print(json.dumps(report, indent=2))
        else:
            icon = {"PASS": "OK  ", "FAIL": "FAIL"}.get(vr["status"], "    ")
            print(f"[forge-validate] verify-png  [{icon}] {vr['detail']}")
        sys.exit(0)

    if not args.input:
        ap.error("one of --input or --verify-png is required")

    path = pathlib.Path(args.input)
    results = []

    # Structural GLB checks (always, stdlib only)
    if path.suffix.lower() in (".glb", ".gltf"):
        results.append(check_glb_header(path))
        if args.web:
            results.append(check_glb_size(path))
            results.append(check_poster_presence(path))

    # Mesh topology checks (trimesh if available)
    if path.suffix.lower() in (".glb", ".gltf", ".stl", ".obj", ".ply", ".off"):
        results.extend(check_with_trimesh(path, args.budget_faces, args.units,
                                          repair_preview=args.repair_preview))
        results.extend(check_uv_basic(path, allow_udim=args.udim))

    # Printability sub-pass (print-target assets)
    if args.print_mode and path.suffix.lower() in (".glb", ".gltf", ".stl", ".obj", ".ply", ".off"):
        results.extend(check_printability(path, args.process))

    # Summarise (INFO is advisory — does not affect the gate verdict)
    statuses = [r["status"] for r in results]
    overall = "FAIL" if "FAIL" in statuses else ("WARN" if "WARN" in statuses else "PASS")

    report = {
        "file":    str(path),
        "overall": overall,
        "checks":  results,
        "summary": {
            "pass":  statuses.count("PASS"),
            "warn":  statuses.count("WARN"),
            "fail":  statuses.count("FAIL"),
            "info":  statuses.count("INFO"),
        },
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"[forge-validate] {path.name}  overall: {overall}")
        for r in results:
            icon = {"PASS": "OK  ", "WARN": "WARN", "FAIL": "FAIL", "INFO": "INFO"}.get(r["status"], "    ")
            print(f"  [{icon}] {r['check']:35s} {r.get('detail', '')}")

    # Exit 0 always (advisory pattern — caller inspects JSON)
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e), "overall": "ERROR"}))
        sys.exit(0)  # advisory: always exit 0
