# COLMAP Pipeline Reference — forge-intake

## Contents
- §1. Install (Windows)
- §2. Sparse reconstruction (SfM)
- §3. Dense reconstruction (MVS)
- §4. Meshing and texturing
- §5. Scale recovery
- §6. One-shot automatic reconstructor
- §7. Quality checks
- §8. Gotchas & fixes

---

## §1. Install (Windows)

**Pre-built binary (recommended):**
Download the latest `COLMAP-<ver>-windows-cuda.zip` from
https://github.com/colmap/colmap/releases — unzip to `C:\COLMAP\`. Run via `COLMAP.bat` which
sets bundled DLL paths automatically.

**IMPORTANT:** Always call `COLMAP.bat`, never `colmap.exe` directly.
`colmap.exe` without the wrapper causes DLL-not-found failures on Windows.

```powershell
# Verify install
& "C:\COLMAP\COLMAP.bat" -h
```

**CUDA requirement:**
- `patch_match_stereo` (dense) requires NVIDIA CUDA GPU.
- Feature extraction/matching has `--FeatureExtraction.use_gpu 1` (GPU) or `0` (CPU).
- CPU-only dense is prohibitively slow (hours for 100 images at HIGH quality); use Meshroom
  or skip to Poisson-from-sparse if no CUDA.

**Meshroom alternative (CPU-capable):**
```powershell
# Set PYTHONPATH before calling meshroom_batch
$env:PYTHONPATH = "C:\Meshroom-2025.1.0"
python "C:\Meshroom-2025.1.0\bin\meshroom_batch" `
    --input "C:\images" `
    --output "C:\out" `
    --pipeline photogrammetry
```

---

## §2. Sparse Reconstruction (SfM)

```powershell
$COLMAP = "C:\COLMAP\COLMAP.bat"
$DS     = "C:\project\scan01"       # dataset root

# ── Feature extraction ──────────────────────────────────────────────
# ALIKED features work better than SIFT for low-texture surfaces and repetitive patterns.
& $COLMAP feature_extractor `
    --database_path "$DS\database.db" `
    --image_path "$DS\images" `
    --FeatureExtraction.use_gpu 1 `
    --ImageReader.camera_model SIMPLE_RADIAL
    # Add: --ImageReader.camera_params "focal,0,cx,cy" if focal length is known

# ── Feature matching ────────────────────────────────────────────────
# exhaustive_matcher: best quality, O(n²) — use for <1000 images
# vocab_tree_matcher: O(n log n) — required for >1000 images
& $COLMAP exhaustive_matcher `
    --database_path "$DS\database.db" `
    --FeatureMatching.use_gpu 1

# ── Sparse mapping (incremental SfM) ───────────────────────────────
# Incremental is most robust. Global is faster but requires accurate focal priors.
New-Item -ItemType Directory -Force "$DS\sparse"
& $COLMAP mapper `
    --database_path "$DS\database.db" `
    --image_path "$DS\images" `
    --output_path "$DS\sparse"
    # Result: $DS\sparse\0\ with cameras.bin, images.bin, points3D.bin

# ── Check registration quality ─────────────────────────────────────
& $COLMAP model_analyzer --path "$DS\sparse\0"
# Healthy: mean_reprojection_error < 1.0 px, >90% images registered
# Bad: <70% registered → re-run with vocab_tree_matcher or more overlap
```

**Registration ratio check (Python):**
```python
import pathlib

def check_registration(sparse_dir: str, image_dir: str) -> float:
    """Return fraction of images successfully registered."""
    images_txt = pathlib.Path(sparse_dir) / "images.txt"
    registered = sum(
        1 for l in images_txt.read_text().splitlines()
        if l and not l.startswith("#") and not l.startswith(" ")
    ) // 2  # images.txt: 2 lines per image (pose + points2D)
    total = (
        len(list(pathlib.Path(image_dir).glob("*.jpg"))) +
        len(list(pathlib.Path(image_dir).glob("*.png")))
    )
    ratio = registered / max(total, 1)
    print(f"Registration: {registered}/{total} ({ratio:.1%})")
    return ratio
```

---

## §3. Dense Reconstruction (MVS)

Requires CUDA GPU. Outputs a fused point cloud (`.ply`).

```powershell
$COLMAP = "C:\COLMAP\COLMAP.bat"
$DS     = "C:\project\scan01"

# ── Undistort images into dense workspace ──────────────────────────
New-Item -ItemType Directory -Force "$DS\dense"
& $COLMAP image_undistorter `
    --image_path "$DS\images" `
    --input_path "$DS\sparse\0" `
    --output_path "$DS\dense" `
    --output_type COLMAP `
    --max_image_size 2000    # limit image size to prevent OOM in patch_match_stereo

# ── Depth map estimation (CUDA) ────────────────────────────────────
& $COLMAP patch_match_stereo `
    --workspace_path "$DS\dense" `
    --workspace_format COLMAP `
    --PatchMatchStereo.geom_consistency true
    # OOM fix: add --PatchMatchStereo.max_image_size 1000
    #          or --PatchMatchStereo.window_radius 3

# ── Fuse depth maps into dense point cloud ─────────────────────────
& $COLMAP stereo_fusion `
    --workspace_path "$DS\dense" `
    --workspace_format COLMAP `
    --input_type geometric `
    --output_path "$DS\dense\fused.ply"
```

---

## §4. Meshing and Texturing

```powershell
$COLMAP = "C:\COLMAP\COLMAP.bat"
$DS     = "C:\project\scan01"

# ── Poisson mesher (watertight — good for closed objects) ──────────
# Use Poisson for props, objects, buildings with closed surfaces.
# Use Delaunay for open terrain, walls, unclosed scenes.
& $COLMAP poisson_mesher `
    --input_path "$DS\dense\fused.ply" `
    --output_path "$DS\dense\meshed-poisson.ply"

# ── Decimate (25% of faces as first pass) ──────────────────────────
& $COLMAP mesh_simplifier `
    --input_path "$DS\dense\meshed-poisson.ply" `
    --output_path "$DS\dense\meshed-simplified.ply" `
    --MeshSimplification.target_face_ratio 0.25
# Repeat with 0.1 if further reduction needed

# ── Texture atlas generation ───────────────────────────────────────
# Produces a textured/ folder with .obj + atlas PNGs
& $COLMAP mesh_texturer `
    --workspace_path "$DS\dense" `
    --input_path "$DS\dense\meshed-simplified.ply" `
    --output_path "$DS\dense\textured"
```

**PyMeshLab cleanup pipeline (after COLMAP meshing):**
```python
# Run after COLMAP meshing to remove floaters, repair topology, decimate
# pip install pymeshlab
import pymeshlab as pml

def clean_photogrammetry_mesh(
    input_path: str,
    output_path: str,
    target_face_count: int = 500_000,
    min_component_pct: float = 5.0,
    min_component_faces: int = 500,
) -> None:
    ms = pml.MeshSet()
    ms.load_new_mesh(input_path)

    ms.meshing_remove_unreferenced_vertices()
    ms.meshing_remove_duplicate_vertices()
    ms.meshing_remove_duplicate_faces()
    ms.meshing_remove_null_faces()

    # Remove floaters: components smaller than 5% of bounding-box diagonal
    ms.meshing_remove_connected_component_by_diameter(
        mincomponentdiag=pml.Percentage(min_component_pct)
    )
    ms.meshing_remove_connected_component_by_face_number(
        mincomponentsize=min_component_faces
    )

    ms.meshing_repair_non_manifold_edges(method=0)     # 0=remove faces
    ms.meshing_repair_non_manifold_vertices(vertdispratio=0)
    ms.meshing_remove_t_vertices(method=0, threshold=40, repeat=True)
    ms.meshing_merge_close_vertices(threshold=pml.Percentage(0.1))

    current = ms.current_mesh().face_number()
    if current > target_face_count:
        ms.meshing_decimation_quadric_edge_collapse(
            targetfacenum=target_face_count,
            preservenormal=True,
            preservetopology=True,
        )

    ms.compute_normal_per_vertex()
    ms.save_current_mesh(output_path)
    final = ms.current_mesh()
    print(f"Cleaned: {final.vertex_number():,} verts, {final.face_number():,} faces → {output_path}")
```

**Poly-count budgets:**

| Use case | Triangle target |
|---|---|
| Web AR / VR | < 30K tris |
| Realtime game prop | 5K – 50K tris |
| Hero game prop | 50K – 100K tris |
| Cinematic / film | 100K – 500K tris |
| Normal bake source | 300K – 1M tris |

---

## §5. Scale Recovery

COLMAP uses arbitrary units. Outputs have NO real-world scale unless explicitly aligned.

**Option 1: GPS-tagged images (model_aligner):**
```powershell
# ref_images.txt format: "image_name.jpg lat lon alt" (one per line)
& "C:\COLMAP\COLMAP.bat" model_aligner `
    --input_path "C:\project\sparse\0" `
    --output_path "C:\project\sparse_aligned" `
    --ref_images_path "C:\project\gps_ref.txt" `
    --ref_is_gps 1 `
    --alignment_type ecef `
    --robust_alignment 1 `
    --robust_alignment_max_error 3.0 `
    --transform_path "C:\project\transform.txt"
# Note: model_aligner only aligns the SPARSE model.
# Propagate the transform manually to dense PLY / mesh if needed.
```

**Option 2: Two known points (Python + Open3D):**
```python
# For GUI point selection — requires a display. Use in a non-headless session.
import open3d as o3d, numpy as np

pcd = o3d.io.read_point_cloud(r"C:\project\dense\fused.ply")
print("Click exactly 2 known-distance points, then close the window.")
vis = o3d.visualization.VisualizerWithEditing()
vis.create_window()
vis.add_geometry(pcd)
vis.run()
vis.destroy_window()
picked = vis.get_picked_points()
assert len(picked) == 2, "Must pick exactly 2 points"

pts = np.asarray(pcd.points)
model_dist = np.linalg.norm(pts[picked[0]] - pts[picked[1]])
real_dist = float(input("Enter real-world distance in meters: "))
scale_factor = real_dist / model_dist
print(f"Scale factor: {scale_factor:.6f}")

pcd_scaled = pcd.scale(scale_factor, center=pcd.get_center())
o3d.io.write_point_cloud(r"C:\project\dense\fused_scaled.ply", pcd_scaled)
```

**Option 3: Known camera baseline (calibrated stereo rig):**
Use `rig_bundle_adjuster` — see COLMAP docs for full setup.

---

## §6. One-Shot Automatic Reconstructor

Fastest path for standard captures:

```powershell
& "C:\COLMAP\COLMAP.bat" automatic_reconstructor `
    --workspace_path "C:\project\scan01" `
    --image_path "C:\project\scan01\images" `
    --quality HIGH `         # MEDIUM / HIGH / EXTREME
    --data_type INDIVIDUAL ` # INDIVIDUAL (all cameras) or VIDEO (frame sequence)
    --feature ALIKED `       # SIFT (default) or ALIKED (better for difficult textures)
    --mapper INCREMENTAL `   # INCREMENTAL or GLOBAL
    --mesher POISSON         # POISSON or DELAUNAY
```

For final delivery only, use `--quality EXTREME` (much slower). `HIGH` is the right default
for iteration.

---

## §7. Quality Checks

**Sparse model statistics:**
```powershell
& "C:\COLMAP\COLMAP.bat" model_analyzer --path "C:\project\sparse\0"
# Healthy output:
#   Cameras:              N
#   Images:               M  (registered)
#   Points:               P
#   Observations:         O
#   Mean track length:    T  (>3 is good)
#   Mean reprojection error: E px  (<1.0 is good)
```

**PyMeshLab QA:**
```python
import pymeshlab as pml

def qa_mesh(path: str) -> dict:
    ms = pml.MeshSet()
    ms.load_new_mesh(path)
    m = ms.current_mesh()
    return {
        "vertices": m.vertex_number(),
        "faces":    m.face_number(),
        "is_watertight": m.is_watertight(),
        "has_non_manifold_edges": m.has_non_manifold_edges(),
    }
```

---

## §8. Gotchas & Fixes

| Problem | Symptom | Fix |
|---|---|---|
| `colmap.exe` DLL errors | `The code execution cannot proceed` | Use `COLMAP.bat` instead of `colmap.exe` |
| `patch_match_stereo` fails | `CUDA not found` | Requires NVIDIA GPU + CUDA toolkit ≥11.x |
| `patch_match_stereo` OOM | Hang / crash | `--PatchMatchStereo.max_image_size 1000` or `--window_radius 3` |
| <70% images registered | Poor reconstruction | More overlap; try `vocab_tree_matcher`; better lighting |
| Meshroom `ModuleNotFoundError` | `No module named meshroom` | `$env:PYTHONPATH = "C:\Meshroom-2025.1.0"` |
| Scale is arbitrary | Model is 1000x too big | `model_aligner` with GPS or manual two-point scale factor |
| ALIKED not available | Unknown feature extractor | ALIKED requires COLMAP ≥3.9; older versions use SIFT only |
| Blender Quadriflow hangs | Hang on >2M tri input | Pre-decimate with PyMeshLab to <1M tris before Blender |

**Capture best practices:**
- Overlap: ≥80% between adjacent frames
- Lighting: overcast/diffuse; avoid hard directional sun
- Featureless surfaces (white walls, matte plastic): apply texture spray or fiducial markers
- Video → frames: `ffmpeg -i input.mp4 -vf fps=1 -q:v 2 "C:\images\frame_%04d.jpg"` (1–2 fps for slow walk, up to 4 for fast orbit)
- Poisson mesher = watertight (good for objects); Delaunay = open surface (terrain, walls)
- `target_face_ratio 0.25` for first simplification pass; repeat with 0.1 if needed
