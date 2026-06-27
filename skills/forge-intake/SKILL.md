---
name: forge-intake
version: 1.0.0
description: >
  Forge suite — physical-world and AI-world 3D intake. Converts real-world photo sequences
  into production-ready meshes or Gaussian splats (photogrammetry via COLMAP/Meshroom/
  RealityScan), trains and exports Gaussian-splat / NeRF scenes (gsplat, Nerfstudio
  Splatfacto), and turns AI-generated raw geometry into clean, game-ready assets
  (Meshy/Tripo/TripoSR/Hunyuan3D → retopology + UV unwrap + texture rebake → GLB/FBX).
  Use whenever you need to: process a photo scan, run photogrammetry, reconstruct a 3D
  scene from images, train a Gaussian splat, convert a .ply splat file, generate 3D from
  a text prompt or reference image, clean up a raw AI-generated or scanned mesh, retopologise
  a dense scan, rebake textures off a raw scan, fix non-manifold geometry on raw capture, or
  make a raw scan/AI mesh game-ready. This is the INTAKE gate for raw scan/AI geometry only —
  for retopo/decimation/LOD of an EXISTING clean mesh use forge-topology; for PBR baking on a
  clean mesh use forge-texture. Produces validated GLB/FBX/PLY ready for downstream Forge skills.
  HEADLESS-FIRST: mesh tracks are driven from code and verified by reading a render PNG; splat
  tracks are verified by PSNR/SSIM (Open3D offscreen render needs a real GPU/OpenGL) and produce
  .ply/.sog; cloud AI tracks call vendor APIs over the network. Part of the Forge suite.
triggers:
  - photogrammetry
  - photo scan
  - gaussian splat
  - nerf
  - 3dgs
  - colmap
  - gsplat
  - nerfstudio
  - splatfacto
  - text to 3d
  - image to 3d
  - ai generated mesh
  - meshy
  - tripo
  - triposr
  - hunyuan3d
  - retopo ai mesh
  - retopologize scan
  - rebake scan textures
  - ai mesh cleanup
  - scan cleanup
  - scan intake
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge Intake — Photogrammetry · Gaussian Splat · AI-to-3D

The entry gate for real-world and AI-world geometry. Raw scans, splat captures, and AI-generated
meshes are rarely production-ready: scale is arbitrary, topology is chaotic, normals are broken,
UVs are missing, and textures bake in studio lighting. This skill drives every stage of intake —
from capture to validated, forge-clean GLB — without touching a GUI.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the target engine, coordinate system, poly budget, texel density, and verified output paths
> for this project. Write your output paths back into FORGE.md when this skill exits successfully.

---

> **Forge suite — related skills (bold = most likely cross-skill calls from here):**
>
> Upstream — **`forge-brief`** establishes the asset brief and writes FORGE.md.
> **`forge-standards`** holds the canonical poly budgets, texel density, scale rules, and
> coordinate-system conventions that intake must satisfy.
>
> Downstream (mesh path) — **`forge-topology`** for manual retopo and edge-flow cleanup beyond
> what Quadriflow produces. **`forge-uv`** for advanced UDIM unwrap, seam planning, and
> distortion checks. **`forge-texture`** for full PBR baking (AO, curvature, displacement) from
> the high-res scan source to the clean low-res target. **`forge-material`** to wire the baked
> maps into a Principled BSDF / glTF PBR material. **`forge-render`** for the turntable
> contact-sheet QA render after cleanup. **`forge-export`** for final GLB/FBX/USD packaging.
> **`forge-validate`** is the mandatory gate before any asset leaves this pipeline.
>
> Downstream (splat path) — **`atelier-webgl`** embeds `.compressed.ply` / `.sog` files in a
> Three.js / R3F scene. Invoke = `Skill("atelier-webgl")`.
>
> **Scope boundary:** this skill is the INTAKE gate for RAW scan / AI / splat geometry only.
> For retopo, decimation, or LOD of an EXISTING clean mesh use **`forge-topology`**; for PBR
> baking (AO/curvature/normal) on a clean mesh use **`forge-texture`**; for the watertight/
> non-manifold gate use **`forge-validate`**. Intake owns retopo/rebake/cleanup only when the
> input is unprocessed scan or AI-generated raw geometry.
>
> **Run = call the Skill tool with its exact name. Writing "now run forge-validate" in prose
> runs nothing.**

---

## Decide first: which intake track?

Before touching any data, identify the track and verify its toolchain is available.

| Track | Input | Primary toolchain | Output |
|---|---|---|---|
| **A. Photogrammetry → mesh** | ≥80 photos of object/scene | COLMAP → PyMeshLab → Blender | Cleaned `.glb` / `.obj` |
| **B. Gaussian splat training** | Same photos OR video frames | COLMAP sparse → gsplat / Nerfstudio | `.ply` / `.compressed.ply` / `.sog` |
| **C. Splat conversion / cleanup** | Existing `.ply` / `.splat` | Open3D, SuperSplat | Validated splat PLY |
| **D. AI text/image-to-3D (cloud)** | Text prompt or reference image | Meshy API or Tripo H3 API | Raw `.glb` |
| **E. AI local inference** | Reference image | TripoSR / Hunyuan3D 2.1 | Raw `.glb` |
| **F. Mesh cleanup / rebake** | Raw `.glb` / `.obj` / `.fbx` | trimesh → Blender headless | Game-ready `.glb` |

**Tool availability check (run before every track):**

```powershell
# Quick availability probe — PowerShell
$tools = @{
  blender   = "blender"
  python    = "python"
  colmap    = "COLMAP"       # or full path to COLMAP.bat
  ffmpeg    = "ffmpeg"
}
foreach ($name in $tools.Keys) {
  $found = $null -ne (Get-Command $tools[$name] -ErrorAction SilentlyContinue)
  Write-Host "[$( if ($found) {'OK  '} else {'MISS'} )] $name"
}
```

If a required tool is missing, state the install path from **`references/toolchain-install.md`**
and ask the user before proceeding. Never assume a tool is present on a fresh machine.

---

## The flow

### 0. Read FORGE.md, confirm track, verify tools

Read `FORGE.md` if present. Confirm the intake track from the table above. Run the tool
availability check. Record the chosen track and confirmed tool paths in FORGE.md.

### 1. Pre-process inputs

**Photos/video (tracks A and B):**
- Extract frames from video with FFmpeg if needed: `ffmpeg -i video.mp4 -vf fps=1 -q:v 2 frames\%04d.jpg`
  (1–2 fps for slow walks; up to 4 fps for fast orbits)
- Target: 80–200 images for a prop, 400+ for a complex scene. ≥80% frame overlap.
- Avoid: direct sunlight (specular hotspots fail SfM), featureless surfaces (spray texture).

**AI reference image (tracks D and E):**
- Remove background first: `rembg` (Python) produces a clean RGBA PNG with no background noise
  bleeding into the mesh surface.
- Prefer even, diffuse lighting in the reference — avoid hard shadows (they bake into albedo).
- Capture note log in FORGE.md: image count, lighting conditions, known problem areas.

### 2. Sparse reconstruction (tracks A and B) or AI generation (tracks D and E)

**Tracks A/B — COLMAP sparse reconstruction:**
Full command reference: **`references/colmap-pipeline.md`**

One-shot automatic (fastest path):
```powershell
& "C:\COLMAP\COLMAP.bat" automatic_reconstructor `
    --workspace_path "C:\project\scan01" `
    --image_path "C:\project\scan01\images" `
    --quality HIGH `
    --data_type INDIVIDUAL `
    --feature ALIKED `
    --mapper INCREMENTAL `
    --mesher POISSON
```

Verify registration ratio after sparse mapping — target >90% images registered, mean reprojection
error <1.0 px. If <70% registered, re-run with `vocab_tree_matcher` or increase overlap.

Scale is arbitrary after COLMAP. Fix with `model_aligner` (GPS) or manual two-point measurement
before exporting. Full alignment commands: **`references/colmap-pipeline.md §Scale recovery`**.

**Track D — Cloud AI generation (Meshy default):**
Full API reference: **`references/ai-generation.md`**

```powershell
$env:MESHY_API_KEY = "msy_..."   # or test key: msy_dummy_api_key_for_test_mode_12345678
$meshy = "$env:CLAUDE_CONFIG_DIR\skills\forge-intake\scripts\meshy_gen.py"
python "$meshy" --mode text --prompt "Victorian armchair, aged oak" `
    --topology quad --polycount 300000 --out-dir "C:\project\ai_raw" --json
```

`scripts/meshy_gen.py` ships with this skill (the only intake script that touches the network):
it posts to the Meshy OpenAPI v2 endpoint, runs the preview→refine poll loop, and downloads the
GLB. Generate at MAX polycount (`300000`); decimate afterwards — this preserves more detail for
UV packing and texture quality during generation. (For image-to-3D: `--mode image --image
input_nobg.png`. For Tripo, follow `references/ai-generation.md §3`.)

**Track E — Local AI generation:**
Full local inference guide: **`references/ai-generation.md §Local inference`**

Check CUDA availability first: `python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"`
CUDA mismatch is the most common Windows failure — see **`references/ai-generation.md §Gotchas`**.

### 3. Dense reconstruction and meshing (track A) OR splat training (track B)

**Track A — Dense reconstruction → mesh:**
Full commands: **`references/colmap-pipeline.md §Dense reconstruction`**

```powershell
# Dense depth estimation (requires CUDA)
& "C:\COLMAP\COLMAP.bat" patch_match_stereo `
    --workspace_path "C:\project\scan01\dense" `
    --workspace_format COLMAP `
    --PatchMatchStereo.geom_consistency true
# Fuse + Poisson mesh
& "C:\COLMAP\COLMAP.bat" stereo_fusion ...
& "C:\COLMAP\COLMAP.bat" poisson_mesher ...
```

No CUDA GPU? Use `--PatchMatchStereo.max_image_size 1000` to reduce OOM, or use Meshroom CPU
MVS (hours, not minutes). COLMAP.bat vs colmap.exe: always use the `.bat` — it sets DLL paths.

**Track B — Gaussian splat training:**
Full training commands: **`references/splat-training.md`**

```powershell
# gsplat headless training (--disable_viewer is CRITICAL for headless)
python examples/simple_trainer.py default `
    --data_dir "C:\project\scan01\dense" `
    --result_dir "C:\project\scan01\splat_out" `
    --disable_viewer `
    --max_steps 30000 `
    --sh_degree 3 `
    --strategy default
```

`--disable_viewer` suppresses the viser web server — mandatory for headless operation.
30,000 steps = production; 7,000 steps = fast preview. MCMCStrategy produces fewer but
higher-quality Gaussians.

### 4. Mesh cleanup and retopology (tracks A, D, E, F)

Full cleanup reference: **`references/mesh-cleanup.md`**

**Step 4a — trimesh pre-flight (always run before Blender):**
A non-watertight mesh with disconnected islands crashes Blender's remesh modifiers.

```powershell
python -c "
import trimesh, json, sys
m = trimesh.load(sys.argv[1], force='mesh')
print(json.dumps({'watertight': m.is_watertight, 'bodies': m.body_count,
'faces': len(m.faces), 'extents': m.extents.tolist()}))
" "input_raw.glb"
```

If `watertight: false` or `body_count > 1` → run trimesh repair before Blender.

**Step 4b — Blender headless cleanup (retopo + UV + rebake):**

```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$cleanup = "$env:CLAUDE_CONFIG_DIR\skills\forge-intake\scripts\cleanup.py"
& $blender -b --factory-startup --python-exit-code 1 `
    -P "$cleanup" `
    -- "input_raw.glb" "output_clean.glb" 2048 20000 --seed 0
# args after --: <input> <output> <bake_res> <target_tris> [--seed N] [--scale 0.01 for Meshy cm]
```

`scripts/cleanup.py` ships with this skill — a pinned, idempotent Quadriflow+unwrap+bake
pipeline (import-by-ext → scale fix → transform_apply → voxel remesh → Quadriflow with a fixed
`--seed` → smart_project UV → selected-to-active Cycles diffuse bake → Y-up GLB). The fixed seed
makes reruns reproducible; the output is overwritten in place. The `--` separator before script
args is MANDATORY; `--python-exit-code 1` makes Python exceptions fail the process;
`--factory-startup` removes startup-file nondeterminism. Full operation notes:
**`references/mesh-cleanup.md §3`**.

**Step 4c — re-verify the OUTPUT (not just the input):**
Retopo is the most failure-prone intake step, so re-run the trimesh pre-flight (Step 4a) on
`output_clean.glb`. A Quadriflow that collapsed, holed, or exploded is only caught by checking
the result — a clean input report says nothing about the output.

**Scale check — always:**
Meshy exports in centimeters (100× scale) → pass `--scale 0.01` to cleanup.py. TripoSR normalizes
to [-1,1] cube. Forge standard: 1 Blender unit = 1 meter. cleanup.py prints post-scale extents;
confirm `max(extents) < 10` for props.

For advanced retopology beyond Quadriflow → `Skill("forge-topology")`.
For full UDIM/seam UV planning → `Skill("forge-uv")`.
For high-quality PBR baking (AO, curvature, displacement) → `Skill("forge-texture")`.

### 5. Splat QA render (track B and C)

Full splat validation reference: **`references/splat-training.md §Validation`**

```python
# Render splat to PNG via Open3D OffscreenRenderer (requires real GPU + OpenGL on Windows)
# See references/splat-training.md §6 for the full render_splat_offscreen() script
```

Target quality metrics: PSNR >25 dB, SSIM >0.85. Check with gsplat's TensorBoard logs or
use `torchmetrics` for standalone evaluation.

**No-GPU degradation branch (CPU / headless box):** Open3D's `OffscreenRenderer` needs a real
GPU + OpenGL driver on Windows and has **no OSMesa fallback** (`references/splat-training.md §6`,
`references/toolchain-install.md`) — on a CPU/headless machine it returns a black PNG. If no GPU
is available, do NOT report that black frame as a render failure:
- QA the splat structurally instead — load the `.ply` with the Open3D/numpy classifier
  (`references/splat-training.md §3`) and report splat count + bounding box + a NaN/Inf guard.
- Defer the visual QA to `Skill("atelier-webgl")` (in-browser splat viewer).
- Mirror the same CPU-fallback discipline already used for COLMAP dense (Meshroom CPU MVS).
The operating principle "black frames mean a failed render" applies only when a GPU was present.

Splat format for web delivery:
- `.ply` (standard, 600–900 MB / 3M splats) → compress to `.compressed.ply` or `.sog`
- `.compressed.ply` ≈ 50–150 MB (quantized) → SuperSplat compatible
- `.sog` ≈ 10–30 MB (ZIP + webp textures) → best web runtime format
- Splat-to-mesh via SuGaR: full pipeline in **`references/splat-training.md §SuGaR`**

**For web embedding of splats:** a trained splat is a heavy (50–150 MB), AT-invisible canvas
asset, so build the fallback FIRST per the FORGE_PLAN §F.5 contract: render a static poster
(`.webp`) as the no-WebGL / reduced-motion fallback BEFORE the handoff, then
`Skill("atelier-webgl")` to embed the `.compressed.ply` / `.sog`, then run the web-runtime gate
`Skill("atelier-perf-a11y")` (CWV/LCP/CLS/INP + a DOM alt-text description for the canvas). Do
NOT route splats through `forge-optimize` — it is GLB-only; intake already owns splat compression
in this step.

### 6. Validate and hand off

Run `Skill("forge-validate")` — the mandatory exit gate. It checks:
watertight, normals, scale, UV overlap, polycount vs budget, glTF-Validator.

Then `Skill("forge-render")` — render a 4-angle turntable contact sheet. Read each PNG with
the `Read` tool to visually confirm: no exploded geometry, no inverted normals, texture has
no baked-in lighting direction.

If the asset (mesh track) is destined for web:
- `Skill("forge-export")` → GLB with correct Y-up, metallic-roughness PBR
- `Skill("forge-optimize")` → Draco + Meshopt + KTX2 compression + a static `.webp` poster
  (the no-WebGL / reduced-motion fallback — built FIRST, per FORGE_PLAN §F.5)
- `Skill("atelier-webgl")` → Three.js / R3F scene integration (receives the GLB + poster)
- `Skill("atelier-perf-a11y")` → the web-runtime gate (CWV/LCP/CLS/INP + DOM alt-text for the
  canvas). Forge keeps its own asset gate (forge-validate) but DEFERS the web-runtime gate here.

---

## Operating principles

- **Track first, tool second.** Identify the intake track and confirm tool availability before
  touching any data. Missing a CUDA GPU changes the entire dense-reconstruction strategy.
- **Verify the output, not the input.** Every generated or cleaned mesh must pass trimesh
  pre-flight on the OUTPUT and the forge-validate gate before being passed downstream. Read the
  output PNG — black frames mean a failed render, EXCEPT when a no-GPU box makes Open3D's
  OffscreenRenderer return black (then QA the splat structurally; see step 5).
- **Scale is always wrong until proven right.** Photogrammetry scale is arbitrary (COLMAP units).
  AI generators disagree on what "1 unit" means. Fix scale in Blender before any bake or export.
  Forge standard: 1 unit = 1 meter; `max(extents) < 10` for props.
- **Generate at max, decimate to budget.** For AI generators: request maximum polycount and
  decimate afterwards. The UV packing and texture generation quality degrade if you generate
  sparse from the start.
- **The `--` separator is non-negotiable.** Every `blender -b -P script.py -- args` invocation
  requires the `--` before script arguments. Missing it silently passes args to Blender itself,
  not to the Python script.
