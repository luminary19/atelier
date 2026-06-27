# Toolchain Install Reference — forge-intake

Quick install pointers for every tool used in the intake pipeline.
All paths are native Windows 11. No WSL. PowerShell-first.

---

## COLMAP

**Requirement:** NVIDIA GPU + CUDA ≥11.x for dense reconstruction (`patch_match_stereo`)
**Download:** https://github.com/colmap/colmap/releases
→ `COLMAP-<ver>-windows-cuda.zip` (pre-built)
**Install:** Unzip to `C:\COLMAP\`. No installer needed. Portable.
**Always call via:** `C:\COLMAP\COLMAP.bat` (sets bundled DLL paths; `colmap.exe` directly = DLL errors)

```powershell
& "C:\COLMAP\COLMAP.bat" -h    # verify
```

**CPU-only machines:** Feature extraction/matching work with `--FeatureExtraction.use_gpu 0`,
but dense reconstruction (`patch_match_stereo`) is CUDA-only. CPU fallback: use Meshroom or
skip dense → use Poisson reconstruction directly from the sparse point cloud.

---

## Meshroom (CPU-capable alternative)

**Requirement:** None for CPU MVS (slow); CUDA for faster processing
**Download:** https://github.com/alicevision/Meshroom/releases
→ `Meshroom-2025.1.0-win64.zip` — all-in-one, portable
**Install:** Unzip to `C:\Meshroom-2025.1.0\`. No installer.

```powershell
# Set PYTHONPATH before calling meshroom_batch
$env:PYTHONPATH = "C:\Meshroom-2025.1.0"
python "C:\Meshroom-2025.1.0\bin\meshroom_batch" `
    --input "C:\images" --output "C:\out" --pipeline photogrammetry
```

---

## Blender 4.x (headless)

**Download:** https://www.blender.org/download/
→ Windows Portable `.zip` — no installer; portable
**Install:** Unzip to `C:\Program Files\Blender Foundation\Blender 4.4\`
(or any path; update `$blender` variable in scripts accordingly)

```powershell
# Test headless
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
& $blender -b --version
```

**Headless render engine:** Use **Cycles** for headless renders on Windows.
EEVEE Next is UNSUPPORTED headless on Windows — always use `bpy.context.scene.render.engine = 'CYCLES'`.

---

## FFmpeg (video → frames)

**Download:** https://ffmpeg.org/download.html → Windows Builds (BtbN/Gyan.dev)
→ `ffmpeg-release-essentials.zip`
**Install:** Unzip to `C:\ffmpeg\`; add `C:\ffmpeg\bin` to PATH (System → Advanced → Environment Variables)

```powershell
# Test
ffmpeg -version

# Extract 1 frame/sec from video
ffmpeg -i "C:\captures\walk.mp4" -vf fps=1 -q:v 2 "C:\images\frame_%04d.jpg"
```

---

## Python environment (gsplat / nerfstudio / TripoSR / Hunyuan3D)

These tools need a dedicated Python environment with PyTorch + matching CUDA.
**Critical:** Only ONE CUDA Toolkit version system-wide. Mixing versions causes compile failures.

```powershell
# Check current PyTorch CUDA target
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"

# Recommended: PyTorch 2.1+ with CUDA 12.x (prebuilt from pytorch.org)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121
```

**gsplat (prebuilt wheels — fastest):**
```powershell
pip install ninja numpy jaxtyping rich
pip install gsplat --index-url https://docs.gsplat.studio/whl/pt20cu118
```

**Nerfstudio (includes gsplat backend):**
```powershell
pip install nerfstudio
# Confirm ns-export works:
pip install pymeshlab==2023.12.post1    # NOT post2 — Windows silent-failure bug
```

**PyMeshLab:**
```powershell
pip install pymeshlab    # prebuilt wheels for Windows Python 3.10-3.12
```

**trimesh:**
```powershell
pip install "trimesh[easy]"
```

**Open3D (splat rendering):**
```powershell
pip install open3d
# Requires real GPU + OpenGL driver for OffscreenRenderer on Windows
```

**TripoSR:**
```powershell
git clone https://github.com/VAST-AI-Research/TripoSR
cd TripoSR
pip install -r requirements.txt
# torchmcubes compiles CUDA kernels at install time — requires matching CUDA Toolkit
```

**Hunyuan3D 2.1 (Windows):**
```powershell
# Use the Windows-tested fork
git clone https://github.com/lzz19980125/Hunyuan3D-2.1-Windows
cd Hunyuan3D-2.1-Windows
# Remove deepspeed from requirements.txt (not needed for inference)
(Get-Content requirements.txt) | Where-Object { $_ -notmatch "deepspeed" } | Set-Content requirements.txt
pip install -r requirements.txt
```

**CUDA Toolkit (system-level):**
- Download: https://developer.nvidia.com/cuda-downloads
- Install only ONE version at a time. Set path explicitly:
  ```powershell
  $env:CUDA_HOME = "C:\Program Files\NVIDIA GPU Computing Toolkit\CUDA\v12.6"
  ```
- Check: `nvcc --version` + `python -c "import torch; print(torch.version.cuda)"`
  → these must match at major version level (e.g., both 12.x).

---

## Meshy API

**No local install needed.** Pure REST.
```powershell
pip install requests    # stdlib requests for the poll loop; optional sseclient for SSE
pip install sseclient   # optional — for event-driven polling
```

Set API key:
```powershell
$env:MESHY_API_KEY = "msy_..."
# Test key (no credits consumed): msy_dummy_api_key_for_test_mode_12345678
```

---

## Tripo API

```powershell
pip install tripo3d
$env:TRIPO_API_KEY = "..."
```

---

## rembg (background removal for reference images)

```powershell
pip install rembg[gpu]    # GPU-accelerated; or rembg for CPU-only
```

---

## Summary table

| Tool | Install method | Path / command | GPU required? |
|---|---|---|---|
| COLMAP | Unzip portable | `C:\COLMAP\COLMAP.bat` | For dense only |
| Meshroom | Unzip portable | `python bin/meshroom_batch` | For faster MVS |
| Blender 4.x | Unzip portable | `blender.exe -b` | No (CPU Cycles) |
| FFmpeg | Unzip + PATH | `ffmpeg` | No |
| gsplat | `pip install gsplat` | via `python examples/...` | Yes (CUDA) |
| nerfstudio | `pip install nerfstudio` | `ns-train`, `ns-export` | Yes (CUDA) |
| PyMeshLab | `pip install pymeshlab` | via Python | No |
| trimesh | `pip install "trimesh[easy]"` | via Python | No |
| Open3D | `pip install open3d` | via Python | For OffscreenRenderer |
| TripoSR | Clone + `pip install -r` | `python run.py` | Yes (6 GB VRAM) |
| Hunyuan3D 2.1 | Clone Windows fork | `python api_server.py` | Yes (6–24 GB) |
| Meshy API | `pip install requests` | REST API | No |
| Tripo API | `pip install tripo3d` | Python SDK | No |
| rembg | `pip install rembg[gpu]` | via Python | Optional (GPU faster) |
