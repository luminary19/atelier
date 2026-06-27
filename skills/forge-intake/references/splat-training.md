# Gaussian Splat Training Reference — forge-intake

## Contents
- §1. gsplat — install and headless training
- §2. Nerfstudio Splatfacto
- §3. PLY format — inspection and validation
- §4. Splat transforms (SRT-only rule)
- §5. Splat → mesh via SuGaR
- §6. QA renders (Open3D OffscreenRenderer)
- §7. Export formats and web delivery
- §8. Gotchas & fixes

---

## §1. gsplat — Install and Headless Training

**License:** Apache 2.0  
**Repo:** https://github.com/nerfstudio-project/gsplat  
**Version (dossier):** 1.5.3 (2025-07-04)

**Install (prebuilt wheels — fastest on Windows):**
```powershell
pip install ninja numpy jaxtyping rich
# PyTorch 2.0 + CUDA 11.8:
pip install gsplat --index-url https://docs.gsplat.studio/whl/pt20cu118
```

**Install (from source — requires MSVC):**
```powershell
# Activate MSVC 14.29 toolchain first
$env:DISTUTILS_USE_SDK = "1"
& "C:\Program Files\Microsoft Visual Studio\2022\BuildTools\VC\Auxiliary\Build\vcvars64.bat" `
    x64 -vcvars_ver=14.29
pip install git+https://github.com/nerfstudio-project/gsplat
```

**Input layout expected by `examples/simple_trainer.py`:**
```
dataset_dir/
  images/               <- undistorted images (colmap image_undistorter output)
  sparse/0/
    cameras.bin
    images.bin
    points3D.bin
```
This is exactly the COLMAP dense workspace layout after `image_undistorter`.

**Headless training:**
```powershell
# Production (30,000 steps, sh_degree 3 = full quality)
python examples/simple_trainer.py default `
    --data_dir "C:\project\scan01\dense" `
    --data_factor 1 `          # 1=full resolution; 2=half; 4=quarter
    --result_dir "C:\out\splat" `
    --disable_viewer `         # CRITICAL: suppresses viser web server
    --max_steps 30000 `
    --sh_degree 3 `            # 45 f_rest SH coefficients; 0=smallest file
    --strategy default         # or "mcmc" for MCMC densification

# Quick preview (7,000 steps)
python examples/simple_trainer.py default `
    --data_dir "C:\project\scan01\dense" `
    --result_dir "C:\out\splat_preview" `
    --disable_viewer `
    --max_steps 7000 `
    --sh_degree 0              # smallest for quick preview
```

**gsplat writes to:**
```
C:\out\splat\
  point_cloud\iteration_30000\point_cloud.ply   <- Gaussian PLY (main output)
  cfg_args                                      <- training config
  events.out.tfevents.*                         <- TensorBoard metrics (PSNR/SSIM)
```

**Export formats from gsplat:**
```python
from gsplat import export_splats

# After training, the results dict contains Gaussian parameters:
export_splats(results, "out.ply",             fmt="ply")            # standard, 600-900 MB
export_splats(results, "out.splat",           fmt="splat")          # legacy antimatter15
export_splats(results, "out.compressed.ply",  fmt="ply_compressed") # quantized, 50-150 MB
```

**MCMCStrategy vs DefaultStrategy:**
```
MCMCStrategy:   fewer but higher-quality Gaussians; more memory during training
DefaultStrategy: faster; default choice for iteration
```

**Scale regularization (Splatfacto):**
`use_scale_regularization=True` suppresses long "spike" artifacts at no quality cost — always enable.

---

## §2. Nerfstudio Splatfacto

**License:** Apache 2.0  
**Install:** `pip install nerfstudio` (includes gsplat backend)

```powershell
# Step 1: Process images (runs COLMAP internally)
ns-process-data images `
    --data "C:\images" `
    --output-dir "C:\dataset"

# Step 2: Train Splatfacto
ns-train splatfacto `
    --data "C:\dataset"

# Step 3: Export Gaussian PLY
ns-export gaussian-splat `
    --load-config "outputs\splatfacto\TIMESTAMP\config.yml" `
    --output-dir "exports\splat"
```

**Quality tuning flags:**
```powershell
ns-train splatfacto `
    --data "C:\dataset" `
    --pipeline.model.cull_alpha_thresh=0.005 `
    --pipeline.model.continue_cull_post_densification=False `
    --pipeline.model.use_scale_regularization=True
```

**Known Windows gotcha:**
`ns-export gaussian-splat` silently produces no output with `pymeshlab==2023.12.post2`.
Fix: `pip install pymeshlab==2023.12.post1` (the `.post2` wheel has a Windows filter-dispatch bug).

`torch.compile` is not supported on Windows — a RuntimeWarning appears but training still runs.

---

## §3. PLY Format — Inspection and Validation

Gaussian PLY vs mesh PLY: both use `.ply` extension. Identify by header inspection.

**PLY type classifier (Python):**
```python
def classify_ply(path: str) -> str:
    """Return 'gaussian', 'mesh', 'pointcloud', or 'unknown'."""
    hdr = []
    with open(path, "rb") as f:
        for line in f:
            decoded = line.decode("ascii", errors="ignore").strip()
            hdr.append(decoded)
            if decoded == "end_header":
                break
    hdr_text = "\n".join(hdr)
    if "element face" in hdr_text:
        return "mesh"
    if any(k in hdr_text for k in ("scale_0", "rot_0", "opacity", "f_dc_0", "f_rest_0")):
        return "gaussian"
    return "pointcloud"
```

**Quick one-liner (check for Gaussian attributes in first 4KB):**
```python
with open(ply_path, "rb") as f:
    hdr = f.read(4096).decode("ascii", errors="ignore")
is_gaussian = "f_dc_0" in hdr or "scale_0" in hdr
```

**Gaussian PLY encodings (do NOT use raw values directly):**

| Attribute | Raw encoding | Decoded value |
|---|---|---|
| `opacity` | logit-encoded | `α = 1 / (1 + exp(-raw_opacity))` |
| `scale_0/1/2` | log-encoded | `s = exp(raw_scale)` |
| `f_dc_0/1/2` | SH degree-0 coefficient | `R = f_dc_0 * 0.28209 + 0.5` |
| `rot_0/1/2/3` | quaternion (wxyz) | normalized unit quaternion |
| `f_rest_*` | higher SH coefficients | depends on sh_degree |

Open3D `read_point_cloud` decodes opacity and scale automatically; `scale` in the returned
PointCloud is already linear.

**Load and inspect with Open3D:**
```python
import open3d as o3d
import numpy as np

def load_splat_o3d(path: str):
    """Load Gaussian PLY into Open3D tensor PointCloud; validates type."""
    gtype = o3d.io.read_file_geometry_type(path)
    assert gtype & o3d.io.CONTAINS_GAUSSIAN_SPLATS, f"Not a Gaussian splat: {path}"
    pcd = o3d.t.io.read_point_cloud(path)
    print(f"Loaded {pcd.point.positions.shape[0]:,} splats")
    print(f"Attributes: {list(pcd.point.keys())}")
    return pcd
```

---

## §4. Splat Transforms — SRT-Only Rule

**CRITICAL:** Gaussian splats must NOT be transformed with a 4×4 matrix (`pcd.transform()`).
This corrupts the per-splat orientation quaternions (`rot`) and higher SH coefficients (`f_rest`),
producing visual artifacts: colors shift wrong, splats appear un-rotated or distorted.

**Correct approach — SRT operations in order:**
```python
# Use pcd.scale(), pcd.rotate(), pcd.translate() separately
# These correctly update rot quaternions AND f_rest SH coefficients.

def scale_splat(pcd, factor: float):
    pcd.scale(float(factor), center=np.zeros(3))  # NOT .transform()

def rotate_splat(pcd, rx_deg=0.0, ry_deg=0.0, rz_deg=0.0):
    R = np.array(o3d.geometry.get_rotation_matrix_from_xyz(
        np.deg2rad([rx_deg, ry_deg, rz_deg])
    ))
    pcd.rotate(R, center=np.zeros(3))

def translate_splat(pcd, tx=0.0, ty=0.0, tz=0.0):
    pcd.translate(np.array([tx, ty, tz]))
```

---

## §5. Splat → Mesh via SuGaR

SuGaR (Surface-Aligned Gaussian Splatting, CVPR 2024) extracts a UV-unwrapped textured mesh
from a trained 3DGS model. This bridges the splat track to the mesh pipeline.

```powershell
# Prerequisites: pip install sugar  OR  clone https://github.com/Anttwo/SuGaR
# Requires: a vanilla 3DGS checkpoint (7k-step warmup)

# Step 1: 7k-step vanilla warmup (gsplat or original 3dgs)
python examples/simple_trainer.py default `
    --data_dir "C:\dataset" --result_dir "C:\out\vanilla" `
    --disable_viewer --max_steps 7000

# Step 2: Full SuGaR pipeline (regularize → extract → refine)
python train_full_pipeline.py `
    -s "C:\dataset" `
    -c "C:\out\vanilla\ckpts\ckpt_6999.pt" `
    -r "density" `        # regularization: 'density' or 'sdf'
    --high_poly True `    # high-poly mesh extraction
    --export_uv True      # UV-unwrapped textured mesh

# Output: C:\out\sugar\refined_mesh\*.obj  (textured, UV-unwrapped, riggable in Blender)
```

After SuGaR extraction, pass the `.obj` into the mesh cleanup track
(`forge_cleanup.py` or `Skill("forge-topology")`).

---

## §6. QA Renders (Open3D OffscreenRenderer)

**Requirements:** Real NVIDIA GPU + proper OpenGL driver on Windows.
Open3D OffscreenRenderer does NOT use OSMesa (Linux-only in Open3D builds).
On CI/cloud machines without GPU → cannot use this renderer on Windows.

```python
import open3d as o3d
import numpy as np

def render_splat_offscreen(ply_path: str, output_png: str, width=1280, height=720) -> bool:
    """Render Gaussian PLY to PNG. Returns False if image appears black (failed load)."""
    gtype = o3d.io.read_file_geometry_type(ply_path)
    if not (gtype & o3d.io.CONTAINS_GAUSSIAN_SPLATS):
        print(f"ERROR: {ply_path} is not a Gaussian splat PLY")
        return False

    pcd = o3d.t.io.read_point_cloud(ply_path)
    renderer = o3d.visualization.rendering.OffscreenRenderer(width, height)
    renderer.scene.set_background([0.1, 0.1, 0.1, 1.0])

    mat = o3d.visualization.rendering.MaterialRecord()
    mat.shader = "gaussianSplat"
    # Enable only for Mip-Splatting trained scenes:
    # mat.gaussian_splat_antialias = True

    renderer.scene.add_geometry("splat", pcd, mat)
    bb = renderer.scene.bounding_box
    c = bb.get_center()
    ext = np.linalg.norm(bb.get_max_bound() - bb.get_min_bound())
    eye = c + np.array([0.0, -ext * 0.3, ext * 0.5])
    renderer.setup_camera(60.0, c.tolist(), eye.tolist(), [0.0, -1.0, 0.0])

    img_arr = np.asarray(renderer.render_to_image())
    mean_brightness = img_arr.mean()
    o3d.io.write_image(output_png, renderer.render_to_image())

    if mean_brightness < 5.0:
        print(f"WARNING: render is nearly black (brightness={mean_brightness:.1f})")
        return False
    print(f"QA render OK: {output_png} (brightness={mean_brightness:.1f})")
    return True
```

**Quality metrics (PSNR / SSIM) — standalone check:**
```python
import torch
from torchmetrics.image import PeakSignalNoiseRatio, StructuralSimilarityIndexMeasure

psnr_fn = PeakSignalNoiseRatio(data_range=1.0)
ssim_fn = StructuralSimilarityIndexMeasure(data_range=1.0)
# rendered, ground_truth: float32 tensors (1, 3, H, W) in [0,1]
psnr = psnr_fn(rendered, ground_truth)
ssim = ssim_fn(rendered, ground_truth)
print(f"PSNR: {psnr:.2f} dB  SSIM: {ssim:.4f}")
# Target: PSNR > 25 dB, SSIM > 0.85 for good reconstruction.
# MipNeRF-360 garden reference: PSNR ≈ 27.4, SSIM ≈ 0.87 with vanilla 3DGS.
```

---

## §7. Export Formats and Web Delivery

| Format | File size (3M splats) | Notes |
|---|---|---|
| `.ply` (standard) | 600–900 MB | Full quality; source of truth |
| `.splat` (antimatter15 legacy) | ~200 MB | Legacy format; fewer viewers |
| `.compressed.ply` (SuperSplat) | 50–150 MB | Quantized; SuperSplat and Three.js compatible |
| `.sog` (ZIP + webp textures) | 10–30 MB | Best web runtime format; PlayCanvas SuperSplat |

**SuperSplat conversion (web UI, no local server):** https://superspl.at

**Web delivery recommendation:** `.sog` for production; `.compressed.ply` for Three.js.
For `@playcanvas/supersplat-viewer` embedding: see **`atelier-webgl`** skill.

**sh_degree and file size tradeoff:**
- `sh_degree=0` → `f_dc` only (RGB per splat); smallest file; no view-dependent color
- `sh_degree=3` → 45 `f_rest` coefficients; full view-dependent effects; largest file
- For web delivery, `sh_degree=1` is often a good balance

---

## §8. Gotchas & Fixes

| Problem | Symptom | Fix |
|---|---|---|
| `--disable_viewer` missing | gsplat starts viser server; hangs on headless | Always add `--disable_viewer` |
| PLY loaded wrong in Blender | Millions of unshaded points | Use graphdeco-inria Blender add-on or Open3D — not standard Blender import |
| SRT transform ignored | Colors shift, geometry distorted after transform | Use `pcd.scale()`, `pcd.rotate()`, `pcd.translate()` — NOT `pcd.transform(matrix)` |
| `ns-export` produces nothing | No output, no error | `pip install pymeshlab==2023.12.post1` (not post2) |
| gsplat source build fails | `cl.exe` CUDA build error | Set `$env:DISTUTILS_USE_SDK = "1"`, run `vcvars64.bat x64 -vcvars_ver=14.29` |
| Open3D OffscreenRenderer black | No GPU or no OpenGL | Requires real GPU + driver on Windows; no OSMesa fallback |
| Raw opacity values wrong | Opacity looks inverted | Decode: `alpha = 1 / (1 + exp(-raw_opacity))` — Open3D does this automatically |
| `torch.compile` warning | RuntimeWarning during training | Non-fatal on Windows; training still completes; ignore |
