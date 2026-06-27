# SDF / Implicit Surface Modeling — Reference

**Stack:** fogleman/sdf · scikit-image marching_cubes · isomesh (dual contouring) · PyMCubes · trimesh · microgen  
**Platform:** Native Windows 11, Python (system Python — not Blender's bundled Python)

## Contents
- §1. Install (PowerShell)
- §2. SDF primitive library (numpy)
- §3. CSG operations (sharp)
- §4. Smooth blending — smin variants
- §5. fogleman/sdf — full workflow examples
- §6. skimage marching cubes (low-level)
- §7. Dual Contouring with isomesh (sharp features)
- §8. TPMS / Gyroid via microgen
- §9. Trimesh watertight check & repair
- §10. Resolution vs cost table
- §11. Meshing method selection table
- §12. Gotcha → fix table

---

## §1. Install (PowerShell)

```powershell
# Minimal Forge SDF stack (no build step required)
pip install "git+https://github.com/fogleman/sdf.git"
pip install scikit-image trimesh[easy] meshio[all] PyMCubes numpy

# For TPMS/gyroid generation
pip install microgen pyvista

# For Dual Contouring (sharp-feature preservation)
pip install isomesh

# After install: verify (the SKILL.md decide-first gate uses the one-line stack probe)
python -c "import sdf, skimage, trimesh; print('sdf stack OK')"
# Or check each individually:
python -c "from sdf import sphere; print('sdf OK')"
python -c "from skimage import measure; print('skimage OK')"
python -c "import trimesh; print('trimesh OK')"
# NOTE: the distribution/import name is `sdf` — `pip show fogleman/sdf` ALWAYS reports
# "not found" (that's a GitHub repo slug, not a PyPI name). pip variant: pip show sdf scikit-image trimesh
```

---

## §2. SDF primitive library (numpy — copy-paste ready)

```python
import numpy as np

def _length(p):
    """Euclidean norm along last axis. p: (N,3) → (N,)."""
    return np.linalg.norm(p, axis=-1)

def sdf_sphere(p, center=np.zeros(3), radius=1.0):
    return _length(p - center) - radius

def sdf_box(p, half_extents=np.ones(3)):
    """Exact box SDF with rounded exterior for smooth CSG."""
    q = np.abs(p) - half_extents
    return _length(np.maximum(q, 0.0)) + np.minimum(np.max(q, axis=-1), 0.0)

def sdf_torus(p, r_major=1.0, r_minor=0.25):
    q = np.stack([_length(p[:, :2]) - r_major, p[:, 2]], axis=-1)
    return _length(q) - r_minor

def sdf_capsule(p, a=np.array([0,-1,0]), b=np.array([0,1,0]), r=0.5):
    pa = p - a; ba = b - a
    h = np.clip(np.dot(pa, ba) / np.dot(ba, ba), 0.0, 1.0).reshape(-1, 1)
    return _length(pa - ba * h) - r

def sdf_gyroid(p, period=1.0, t=0.0):
    """Gyroid TPMS. NOT a true SDF (|∇f| ≠ 1). Clip to a box before meshing."""
    q = (2.0 * np.pi / period) * p
    val = (np.sin(q[:, 0]) * np.cos(q[:, 1])
         + np.sin(q[:, 1]) * np.cos(q[:, 2])
         + np.sin(q[:, 2]) * np.cos(q[:, 0]))
    return val - t

def sdf_schwarz_p(p, period=1.0, t=0.0):
    q = (2.0 * np.pi / period) * p
    return np.cos(q[:, 0]) + np.cos(q[:, 1]) + np.cos(q[:, 2]) - t

def sdf_schwarz_d(p, period=1.0, t=0.0):
    """Schwarz Diamond TPMS."""
    q = (np.pi / period) * p
    return (np.cos(q[:,0])*np.cos(q[:,1])*np.cos(q[:,2])
          - np.sin(q[:,0])*np.sin(q[:,1])*np.sin(q[:,2])) - t
```

---

## §3. CSG operations (sharp)

```python
def csg_union(a, b):        return np.minimum(a, b)
def csg_intersection(a, b): return np.maximum(a, b)
def csg_difference(a, b):   return np.maximum(a, -b)
```

---

## §4. Smooth blending — smin variants

`k` is the blend radius in **world units** (same scale as geometry). A sphere of radius 1 uses `k ≈ 0.1–0.3`.

```python
def smin_quadratic(a, b, k=0.1):
    """C1 continuous. Rigid (no global distortion). Best general-purpose choice."""
    k_norm = k * 4.0
    h = np.maximum(k_norm - np.abs(a - b), 0.0) / k_norm
    return np.minimum(a, b) - h * h * k_norm * (1.0 / 4.0)

def smin_cubic(a, b, k=0.1):
    """C2 continuous — smoother second derivative. Use for aesthetic blends."""
    k_norm = k * 6.0
    h = np.maximum(k_norm - np.abs(a - b), 0.0) / k_norm
    return np.minimum(a, b) - h * h * h * k_norm * (1.0 / 6.0)

def smin_exponential(a, b, k=0.1):
    """Associative (order-independent for 3+ shapes). Causes global distortion. k > 0 required."""
    r = np.exp2(-a / k) + np.exp2(-b / k)
    return -k * np.log2(r)

def smooth_union(a, b, k=0.0):
    return csg_union(a, b) if k == 0.0 else smin_quadratic(a, b, k)

# Selection guide:
# k = 0                → hard CSG (no blend)
# quadratic, k small  → tight weld
# cubic, k medium     → aesthetic smoothing
# exponential         → ONLY when blending 3+ shapes simultaneously (metaballs)
```

---

## §5. fogleman/sdf — workflow examples

```python
from sdf import *

# --- Example 1: Classic CSG demo ---
def make_csg_demo(path='csg_demo.stl'):
    f = sphere(1) & box(1.5)              # intersection
    c = cylinder(0.5)
    f -= c.orient(X) | c.orient(Y) | c.orient(Z)  # subtract 3 cylinders
    f.save(path)                           # auto-meshes with marching cubes

# --- Example 2: Smooth blob ---
def make_blob(path='blob.stl'):
    a = sphere(0.5).translate((0.6, 0, 0))
    b = sphere(0.5).translate((-0.6, 0, 0))
    f = union(a, b, k=0.3)                # 0.3 world-unit blend
    f.save(path, step=0.02)               # explicit voxel size in world units

# --- Example 3: Gyroid infill clipped to box ---
# CRITICAL: clip infinite SDFs before saving — bounds estimation hangs otherwise
def make_gyroid_infill(path='gyroid.stl'):
    @sdf3
    def gyroid(period=1.0, t=0.0):
        def f(p):
            q = (2.0 * np.pi / period) * p
            return (np.sin(q[:,0])*np.cos(q[:,1])
                  + np.sin(q[:,1])*np.cos(q[:,2])
                  + np.sin(q[:,2])*np.cos(q[:,0])) - t
        return f
    g = gyroid(period=0.5, t=0.1) & box(3)
    g.save(path, step=0.025, sparse=True)

# --- Resolution control ---
SAMPLES = {'draft': 2**20, 'normal': 2**22, 'high': 2**24, 'final': 2**26}
def save_quality(shape, path, quality='normal'):
    shape.save(path, samples=SAMPLES[quality], sparse=True)

# --- Non-uniform scale: MUST use sparse=False ---
# f = sphere(1).scale((1, 2, 3))        # inexact SDF — breaks sparse batch-skipping
# f.save('ellipsoid.stl', sparse=False) # correct but slower

# --- Export to GLB instead of STL (normals fix) ---
import trimesh, numpy as np
def export_glb(shape, path='out.glb', samples=2**22):
    pts = shape.generate(samples=samples)        # (N,3) unindexed triangle vertices
    verts_u, idx = np.unique(pts.reshape(-1, 3), axis=0, return_inverse=True)
    faces = idx.reshape(-1, 3)
    mesh = trimesh.Trimesh(vertices=verts_u, faces=faces)
    mesh.export(path)                            # trimesh writes correct normals
```

---

## §6. skimage marching cubes (low-level)

```python
import numpy as np
from skimage import measure
import trimesh

def sdf_to_mesh_skimage(sdf_func, bounds, resolution=64):
    """
    Evaluate sdf_func on a grid, run Lewiner marching cubes, return trimesh.Trimesh.
    sdf_func: callable(p: ndarray (N,3)) -> ndarray (N,)
    bounds:   ((xmin,ymin,zmin), (xmax,ymax,zmax))
    resolution: voxels per axis (64=draft, 128=normal, 256=high)
    """
    (x0,y0,z0),(x1,y1,z1) = bounds
    xs = np.linspace(x0, x1, resolution)
    ys = np.linspace(y0, y1, resolution)
    zs = np.linspace(z0, z1, resolution)
    XX,YY,ZZ = np.meshgrid(xs, ys, zs, indexing='ij')
    pts = np.stack([XX.ravel(), YY.ravel(), ZZ.ravel()], axis=-1)
    vals = sdf_func(pts).reshape(resolution, resolution, resolution)

    spacing = ((x1-x0)/resolution, (y1-y0)/resolution, (z1-z0)/resolution)
    verts, faces, normals, _ = measure.marching_cubes(
        vals, level=0, spacing=spacing,
        allow_degenerate=False, method='lewiner'
    )
    verts += np.array([x0, y0, z0])           # translate to world space
    return trimesh.Trimesh(vertices=verts, faces=faces, vertex_normals=normals)

# Watertight rule: add 10-15% padding around the surface
# so the isosurface never clips the bounding box edge.
```

---

## §7. Dual Contouring with isomesh (sharp features)

```python
import isomesh, trimesh, numpy as np

def wrap_sdf(sdf):
    """Wrap numpy SDF for isomesh: returns (distances, gradients|None)."""
    def f(pts): return sdf(pts), None   # None → isomesh uses finite differences
    return f

def mesh_sharp_sdf(sdf_func, bbox=(-1,-1,-1,1,1,1), min_depth=4, max_depth=7):
    verts, faces = isomesh.extract(
        wrap_sdf(sdf_func),
        bbox_min=bbox[:3], bbox_max=bbox[3:],
        min_depth=min_depth, max_depth=max_depth,
        adaptive=True, angle_threshold=30.0, iso_value=0.0
    )
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    # DC can produce T-junctions; repair after extraction
    trimesh.repair.fix_winding(mesh)
    trimesh.repair.fill_holes(mesh)
    return mesh

# Use when: mechanical shapes with hard 90° edges (box interiors, grooves, brackets)
# Use skimage MC when: organic smooth shapes (creatures, blobs, organic architecture)
```

---

## §8. TPMS / Gyroid via microgen

```python
from microgen import Tpms
from microgen.shape import surface_functions

# Gyroid sheet (hollow surface — typical infill look)
geo = Tpms(
    surface_function=surface_functions.gyroid,
    density=0.30,     # relative density [0,1]; controls wall thickness
    resolution=30,    # voxels per unit cell (≥20 for FDM-printable)
)
shape = geo.generate_surface_mesh(type_part="sheet")
shape.save("gyroid_sheet.stl")   # PyVista PolyData

# Schwarz-P skeletal, tiled 3×3×3
geo2 = Tpms(
    surface_function=surface_functions.schwarz_p,
    offset=0.3, repeat_cell=3, resolution=20,
)
shape2 = geo2.generate_surface_mesh(type_part="skeletal")
shape2.save("schwarz_p_skeletal.stl")

# Available surface_functions: gyroid, schwarz_p, schwarz_d, neovius, iwp,
#   fischer_koch_s, p_w_hybrid, f_rd_w, f_rd_s, ...
```

**Cell size rules:**
- FDM printing: period ≥ 3mm
- SLA/SLS printing: period ≥ 0.5mm
- `resolution = period_in_voxels × 20` (e.g. 10mm cell at 0.5mm → resolution ≥ 20)
- Density 0.20–0.35 for mechanical infill. Below 0.15, sheet becomes disconnected at low resolution.

---

## §9. Trimesh watertight check & repair

```python
import trimesh

def load_and_repair(path):
    mesh = trimesh.load_mesh(path)
    print(f"Loaded: {len(mesh.vertices)} verts, {len(mesh.faces)} faces")
    print(f"Watertight before: {mesh.is_watertight}")
    if not mesh.is_watertight:
        trimesh.repair.fix_winding(mesh)
        trimesh.repair.fix_normals(mesh)
        trimesh.repair.fill_holes(mesh)
        print(f"Watertight after:  {mesh.is_watertight}")
    return mesh

def export_all_formats(mesh, stem='output'):
    mesh.export(f'{stem}.stl')   # 3D printing
    mesh.export(f'{stem}.glb')   # web/Blender (trimesh writes normals)
    mesh.export(f'{stem}.obj')   # widest compatibility

# meshio CLI conversion (use python -m on Windows PATH issues):
# python -m meshio convert output.stl output.glb
```

---

## §10. Resolution vs cost table

| Use case | step / voxels | Approx verts | Time (Python) |
|----------|---------------|-------------|---------------|
| Draft / iteration | step=0.1 or 32³ | 5k–50k | < 1 s |
| Normal | step=0.03 or 128³ | 100k–500k | 5–30 s |
| High quality | step=0.01 or 256³ | 500k–2M | 1–5 min |
| Ultra / research | step=0.005 or 512³ | 2M–10M | 10–60 min |

Always develop at draft; export at normal/high. Add `sparse=True` (fogleman/sdf) for large scenes. O(N³) in voxel count.

---

## §11. Meshing method selection table

| Condition | Method | Why |
|-----------|--------|-----|
| Smooth organic shapes | skimage Lewiner MC | Faster, cleaner normals |
| Mechanical parts, sharp edges | Dual Contouring (isomesh) | QEF preserves corners |
| TPMS/gyroid infill | microgen | Correct density control, ready for print |
| Fastest iteration | fogleman/sdf (multi-threaded MC) | Auto bounds, sparse skip |
| Neural SDF / noisy field | sdftoolbox SurfaceNets | Better than MC for noisy inputs |
| Guaranteed watertight for FEA | trimesh manifold3d | Watertight by construction |

---

## §12. Gotcha → fix table

| Symptom | Cause | Fix |
|---------|-------|-----|
| Script hangs at `f.save()` for gyroid | Infinite SDF, bounds estimation loops | Clip first: `gyroid(period=0.5) & box(3)` |
| Mesh has holes/missing patches after `scale((1,2,3))` | Non-uniform scale = inexact SDF, `sparse=True` skips batches incorrectly | `f.save(path, sparse=False)` |
| Mesh appears mirrored on old skimage | ZYX vertex order (pre-0.19) | `verts = verts[:, ::-1]` (only if on old version) |
| `pip install PyMCubes` fails with numpy error | PyMCubes 0.1.6 requires numpy ≥ 2.0, Python ≥ 3.9 | `pip install "pymcubes==0.1.4"` for Python 3.8 |
| `meshio` CLI not found in PowerShell | Scripts not on PATH | `python -m meshio convert input.stl output.glb` |
| fogleman/sdf GLB has wrong normals | meshio doesn't write normals by default | Use trimesh for final export (see §5 export_glb) |
| `mesh.is_watertight == False` after DC | T-junctions from isomesh | `trimesh.repair.fix_winding(mesh); fill_holes(mesh)` |
| libfive build takes 4+ hours on Windows | Windows Defender scans every file write | Temporarily disable real-time protection during vcpkg install |
| Multiple smin blend zones wrong geometry | Quadratic smin is not associative for 3+ shapes | Use `smin_exponential` for multi-body blends |
| Gyroid `|∇f| ≠ 1` causes shell/dilate errors | TPMS is not a true SDF | Use mesh-to-sdf (`pip install mesh-to-sdf`) after meshing to get true SDF |
