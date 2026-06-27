# Forge Validate — Printability Reference
# Contents
- §1. Print-readiness invariants
- §2. Dimensional thresholds by process
- §3. Wall thickness check (trimesh)
- §4. Overhang check
- §5. Hollowing + drain holes (SLA)
- §6. Repair pipeline
- §7. Slicer pre-flight (OrcaSlicer, PrusaSlicer)

---

## §1. Print-Readiness Invariants

**Every mesh that reaches a slicer MUST satisfy:**

| Invariant | trimesh check | Why |
|-----------|---------------|-----|
| Closed, orientable, 2-manifold | `mesh.is_volume == True` | Open edges → wrong infill / missing walls |
| All normals pointing outward | `mesh.volume > 0` | Inverted normals → inside-out infill |
| No zero-area / zero-length elements | `mesh.euler_number == 2` | Slicer crash / NaN layer data |
| No self-intersections | Open3D `is_self_intersecting()` | Slicer generates garbage G-code |
| Positive volume | `mesh.volume > 0` | Degenerate solid |

**`mesh.is_volume` is the single authoritative go/no-go** for slicers.
`is_volume = is_watertight AND is_winding_consistent AND volume > 0`

---

## §2. Dimensional Thresholds by Process

| Parameter | FDM | SLA/DLP | SLS | DMLS/Metal |
|-----------|-----|---------|-----|-----------|
| Min wall (structural) | 1.2 mm (prefer 2.0) | 0.5 mm (prefer 0.8) | 0.7 mm | 0.5–1.0 mm |
| Min wall (decorative) | 0.8 mm | 0.2 mm | 0.3 mm | 0.4 mm |
| Min feature size | 0.8 mm | 0.2–0.3 mm | 0.6 mm | 0.3–0.5 mm |
| Min engraved detail | 0.6 mm wide, 2 mm deep | 0.15 mm recession | 0.1–0.35 mm | 0.1 mm |
| Overhang limit (no support) | 45° from vertical | 45° (tilt recommended) | No limit | 45° |
| Dimensional tolerance | ±0.2–0.5 mm | ±0.05–0.15 mm | ±0.15–0.3 mm | ±0.05–0.2 mm |

**FDM nozzle-aware wall rule:** wall thickness should be a multiple of extrusion width.
For 0.4 mm nozzle: walls at 0.4, 0.8, 1.2, 1.6, 2.0 mm. Odd values (1.0 mm) produce
partial-fill lines that reduce wall strength.

```python
def snap_to_nozzle_multiple(thickness_mm: float, nozzle_mm: float = 0.4) -> float:
    n = max(1, round(thickness_mm / nozzle_mm))
    return n * nozzle_mm
```

**Clearances / engineering fits (gap on diameter, positive = hole larger than shaft):**

| Fit type | FDM | SLA/DLP | SLS |
|----------|-----|---------|-----|
| Press (interference) | −0.1 to +0.1 mm | −0.1 to 0 mm | +0.05 to +0.15 mm |
| Transition | +0.1 to +0.2 mm | +0.05 to +0.15 mm | +0.15 to +0.25 mm |
| Sliding | +0.3 to +0.5 mm | +0.1 to +0.2 mm | +0.25 to +0.4 mm |
| Clearance (free) | +0.5 to +0.8 mm | +0.2 to +0.3 mm | +0.4 to +0.6 mm |

**FDM holes print undersized by 0.1–0.3 mm** — always oversize by 0.2 mm minimum
when mating with a fastener. Do NOT design press fits for structural loading — use
heat-pressed brass inserts (M3/M4) instead.

---

## §3. Wall Thickness Check (trimesh)

```python
import numpy as np
import trimesh
from trimesh.sample import sample_surface

THRESHOLDS = {
    "fdm":  {"min_wall_mm": 1.2,  "min_feature_mm": 0.8,  "overhang_deg": 45.0},
    "sla":  {"min_wall_mm": 0.5,  "min_feature_mm": 0.2,  "overhang_deg": 45.0},
    "sls":  {"min_wall_mm": 0.7,  "min_feature_mm": 0.6,  "overhang_deg": 360.0},
    "dmls": {"min_wall_mm": 0.5,  "min_feature_mm": 0.3,  "overhang_deg": 45.0},
}

def check_wall_thickness(mesh: trimesh.Trimesh, min_thickness_mm: float, n_samples: int = 2000) -> dict:
    """
    Approximate wall thickness via inward ray-casting from surface samples.
    Install pyembree for 60x speedup: pip install pyembree
    """
    points, face_indices = sample_surface(mesh, count=n_samples)
    normals = mesh.face_normals[face_indices]
    origins = points - 1e-4 * normals   # slightly inside to avoid self-hit

    # Cast inward rays
    thicknesses = []
    for o, d in zip(origins, -normals):
        hits = mesh.ray.intersects_location(
            ray_origins=[o], ray_directions=[d], multiple_hits=False
        )[0]
        if len(hits) > 0:
            thicknesses.append(np.linalg.norm(hits[0] - o))
    thicknesses = np.array([t for t in thicknesses if np.isfinite(t)])

    if len(thicknesses) == 0:
        return {"error": "no thickness samples computed"}

    thin_frac = float(np.mean(thicknesses < min_thickness_mm))
    return {
        "min_measured_mm":  float(np.min(thicknesses)),
        "median_mm":        float(np.median(thicknesses)),
        "thin_sample_frac": thin_frac,
        "threshold_mm":     min_thickness_mm,
        "passes":           thin_frac < 0.05,  # allow up to 5% thin points (sharp edges)
    }
```

**Performance note:** `pip install pyembree` accelerates ray queries from ~10k/s to ~600k/s.
Without pyembree, reduce `n_samples` to 500 for reasonable speed.

---

## §4. Overhang Check

```python
def check_overhangs(mesh: trimesh.Trimesh, max_overhang_deg: float = 45.0, up_axis: int = 2) -> dict:
    """Count faces exceeding overhang threshold. up_axis=2 means Z is up (standard print orientation)."""
    normals = mesh.face_normals
    angles_deg = np.degrees(np.arccos(np.clip(-normals[:, up_axis], -1, 1)))
    overhang_mask = angles_deg > max_overhang_deg
    overhang_count = int(np.sum(overhang_mask))
    overhang_area = float(mesh.area_faces[overhang_mask].sum()) if overhang_count > 0 else 0.0
    return {
        "overhang_face_count": overhang_count,
        "overhang_area_mm2":   overhang_area,
        "threshold_deg":       max_overhang_deg,
        "passes":              overhang_count == 0,
    }
```

**SLS note:** `overhang_deg=360.0` (no overhang limit) — powder support eliminates support structures.

**Bridging limits:** FDM bridges ≤ 12–15 mm without support; SLA ≤ 5 mm (peel forces weaker).

---

## §5. Hollowing + Drain Holes (SLA)

**SLA shell requirements:**
- Minimum shell: 2.0–2.5 mm (thinner shells warp during post-cure UV)
- Minimum drain holes: 2 holes, ≥ 3 mm diameter
- Placement: one near build plate (lowest Z), one on opposite surface
- Allows IPA to flush trapped resin during cleaning

**Hollowing via manifold3d (MIT, guaranteed manifold output):**
```python
import numpy as np
import trimesh
from trimesh.boolean import difference as bool_diff

def hollow_mesh(mesh: trimesh.Trimesh, shell_thickness_mm: float = 2.5) -> trimesh.Trimesh:
    if not mesh.is_volume:
        raise ValueError("Hollow requires is_volume=True")
    center = mesh.center_mass
    scale_factor = 1.0 - (shell_thickness_mm * 2.0) / np.min(mesh.extents)
    if scale_factor <= 0.1:
        raise ValueError(f"Shell thickness {shell_thickness_mm}mm too large for this mesh")
    inner = mesh.copy()
    inner.apply_translation(-center)
    inner.apply_scale(scale_factor)
    inner.apply_translation(center)
    inner.invert()   # inner normals must point inward for correct boolean
    return bool_diff([mesh, inner], engine="manifold", check_volume=True)
```

**Drain hole placement gotcha:** always place at least one hole near the LOWEST point
relative to build plate. Hole on upward-facing surface = trapped resin = print failure
and hazardous IPA contamination.

---

## §6. Repair Pipeline

**Order matters — do not skip steps:**

**API note — targets `trimesh>=4.0`.** `remove_degenerate_faces()` / `remove_duplicate_faces()`
are removed in trimesh 4.x (raise `AttributeError`). Use `mesh.process(validate=True)`, which
removes duplicate + degenerate faces (`unique_faces() & nondegenerate_faces()`) and fixes
normals in one call.

```python
import trimesh, trimesh.repair as repair  # trimesh>=4.0

def repair_for_print(mesh: trimesh.Trimesh) -> trimesh.Trimesh:
    """Repair order: process → fix winding → fix normals → fill holes → drop loose verts."""
    mesh.process(validate=True)   # merge verts + remove duplicate/degenerate faces + fix normals
    repair.fix_winding(mesh)
    repair.fix_normals(mesh, multibody=True)
    repair.fill_holes(mesh)             # handles tri + quad holes only
    if hasattr(mesh, "remove_unreferenced_vertices"):
        mesh.remove_unreferenced_vertices()
    # If still not volume: escalate to PyMeshLab
    if not mesh.is_volume:
        raise ValueError("trimesh repair insufficient — use PyMeshLab meshing_close_holes")
    if mesh.volume < 0:
        mesh.invert()   # all normals were consistently inward
    return mesh
```

**Escalation to PyMeshLab (for complex non-convex holes):**
```python
import pymeshlab as pml

def repair_heavy(input_path: str, output_path: str, max_hole_size: int = 200):
    """Use when trimesh repair fails. Requires: pip install pymeshlab (GPL-3.0)."""
    ms = pml.MeshSet()
    ms.load_new_mesh(input_path)
    ms.meshing_remove_unreferenced_vertices()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()
    # Compatible shim for PercentageValue (name changed in 2022.2):
    PctVal = getattr(pml, "PercentageValue", None) or getattr(pml, "Percentage")
    ms.meshing_merge_close_vertices(threshold=PctVal(0.1))
    ms.meshing_repair_non_manifold_edges(method=0)
    ms.meshing_repair_non_manifold_vertices(vertdispratio=0)
    ms.meshing_close_holes(maxholesize=max_hole_size, selfintersection=True)
    ms.meshing_re_orient_faces_coherently()
    ms.save_current_mesh(output_path)
```

**Last-resort — alpha wrap (destroys fine detail):**
```python
ms.generate_alpha_wrap(
    alpha=pml.PercentageValue(0.3),
    offset=pml.PercentageValue(0.05)
)
ms.set_current_mesh(1)   # alpha wrap creates a new mesh layer
```

---

## §7. Slicer Pre-flight

**OrcaSlicer `--info` (no slicing — just model parsing):**
```powershell
$orca = "C:\Program Files\OrcaSlicer\orca-slicer.exe"
& $orca --info "model.3mf"
# Exit code 0 = slicer accepted the file; non-zero = file rejected
# Note: OrcaSlicer installer on Windows does NOT add to PATH — use full path
```

**PrusaSlicer console (stdout suppressed on GUI binary):**
```powershell
# prusa-slicer.exe suppresses stdout on Windows — use prusa-slicer-console.exe instead
$prusa = "C:\Program Files\Prusa3D\PrusaSlicer\prusa-slicer-console.exe"
& $prusa --export-stl --output "validated.stl" "input.stl"
```

**CuraEngine quick slice (discard G-code, check for errors):**
```powershell
$cura = "C:\Program Files\UltiMaker Cura 5.x\CuraEngine.exe"
& $cura slice -j "fdm_config.json" -l "model.stl" -o "$null"
# Exit 0 = sliced successfully; non-zero = mesh error
```

**3MF vs STL decision:**

| | STL | 3MF |
|--|-----|-----|
| Units | None embedded (assumed mm) | Millimeters explicit in spec |
| Color / multi-material | No | Yes (Materials Extension v1.2.1) |
| Multi-object | No | Yes |
| Metadata | No | Yes (Author, Description) |
| Slicer support | Universal | PrusaSlicer, OrcaSlicer, Bambu, Cura 5+ |

**Use 3MF when:** multi-material, multi-color, or embedded metadata needed.
**Use STL when:** maximum compatibility with older or unknown tooling.

**3MF via trimesh (requires `pip install trimesh[easy]` for lxml):**
```python
scene = trimesh.scene.scene.Scene(geometry={"model": mesh})
scene.export("output.3mf")   # lxml handles 3MF XML; trimesh[easy] pulls lxml
```
