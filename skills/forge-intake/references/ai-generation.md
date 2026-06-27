# AI Text/Image-to-3D Generation Reference — forge-intake

## Contents
- §1. Decision matrix — which tool to use
- §2. Meshy API (recommended cloud default)
- §3. Tripo H3 API (best topology control)
- §4. Rodin / Luma (alternatives)
- §5. Local inference — TripoSR
- §6. Local inference — Hunyuan3D 2.1
- §7. Best practices
- §8. Gotchas & fixes (Windows)

**Mesh cleanup, trimesh pre-flight, and QA checklist → `references/mesh-cleanup.md`**

---

## §1. Decision Matrix

| Scenario | Tool | Reason |
|---|---|---|
| Quick iteration, no GPU | **Meshy API** | Best REST API, test key, quad output, PBR, commercial license on Pro |
| Best topology for rigging/games | **Tripo H3 API** | `quad=true`, `smart_low_poly`, `face_limit`, `auto_size` meters |
| Multi-image → one model | **Rodin Gen-2.5** | `concat` mode (up to 5 reference images), bbox conditioning |
| Stylized / organic hero | **Meshy or Luma Genie** | Strongest aesthetic output for organic/stylized objects |
| Local GPU 6 GB VRAM, image only | **TripoSR (MIT)** | Simplest install if CUDA 11.8 matched |
| Local GPU 16–24 GB, full PBR | **Hunyuan3D 2.1** | Best local quality + PBR textures; Windows-fixable |

**Generate at MAX polycount, decimate afterwards.** Request `target_polycount=300000` from
Meshy; omit `face_limit` from Tripo on the first pass. Decimating from high-poly preserves
more detail for UV and texture quality.

---

## §2. Meshy API (Recommended Cloud Default)

**API base:** `https://api.meshy.ai/openapi/v2/`  
**Model:** Meshy-6 (current as of 2026-06)  
**Test key:** `msy_dummy_api_key_for_test_mode_12345678` (real response shapes, no credits)  
**Licensing:** Pro plan = full commercial. Free plan = CC BY 4.0.

**Pricing (approximate, 2026-06):**
- Pro $20/mo → 1,000 credits; ~$1 = 50 credits
- Text-to-3D Preview (Meshy-6): 20 credits; Refine (texture): 10 credits
- Image-to-3D: 20 credits (no texture) / 30 credits (with texture)
- Full textured asset ≈ 30 credits ≈ $0.60 on Pro

**Text-to-3D (Python, headless):**
```python
# Requires: pip install requests
# Env: $env:MESHY_API_KEY = "msy_..."

import os, time, requests, pathlib

API_BASE = "https://api.meshy.ai/openapi/v2"
HEADERS  = {"Authorization": f"Bearer {os.environ['MESHY_API_KEY']}"}
POLL_S   = 5
TIMEOUT  = 1200   # 20 minutes; queue time varies


def _poll(task_id: str, endpoint: str) -> dict:
    deadline = time.time() + TIMEOUT
    while time.time() < deadline:
        r = requests.get(f"{API_BASE}/{endpoint}/{task_id}", headers=HEADERS)
        r.raise_for_status()
        task = r.json()
        status = task["status"]
        if status == "SUCCEEDED":
            return task
        if status == "FAILED":
            raise RuntimeError(f"Task {task_id} FAILED: {task.get('task_error', {})}")
        print(f"  [{status}] {task.get('progress', 0)}%", flush=True)
        time.sleep(POLL_S)
    raise TimeoutError(f"Task {task_id} timed out after {TIMEOUT}s")


def text_to_3d(
    prompt: str,
    negative_prompt: str = "low quality, asymmetry, noisy texture",
    topology: str = "quad",
    target_polycount: int = 300000,  # generate at max, decimate afterwards
    enable_pbr: bool = True,
    should_remesh: bool = True,
    out_dir: str = "output",
) -> pathlib.Path:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    # Stage 1: Preview (geometry)
    r = requests.post(f"{API_BASE}/text-to-3d", headers=HEADERS, json={
        "mode": "preview",
        "prompt": prompt,
        "negative_prompt": negative_prompt,
        "ai_model": "meshy-6",
        "topology": topology,
        "target_polycount": target_polycount,
        "should_remesh": should_remesh,
    })
    r.raise_for_status()
    preview_id = r.json()["result"]
    print(f"[Meshy] Preview task: {preview_id}")
    _poll(preview_id, "text-to-3d")

    # Stage 2: Refine (texture + PBR)
    r = requests.post(f"{API_BASE}/text-to-3d", headers=HEADERS, json={
        "mode": "refine",
        "preview_task_id": preview_id,
        "enable_pbr": enable_pbr,
    })
    r.raise_for_status()
    refine_id = r.json()["result"]
    print(f"[Meshy] Refine task: {refine_id}")
    refine_task = _poll(refine_id, "text-to-3d")

    glb_url  = refine_task["model_urls"]["glb"]
    glb_path = out / f"{preview_id}.glb"
    glb_path.write_bytes(requests.get(glb_url).content)
    print(f"[Meshy] Saved: {glb_path}")
    return glb_path


def image_to_3d(
    image_path: str,
    topology: str = "quad",
    target_polycount: int = 300000,
    enable_pbr: bool = True,
    remove_lighting: bool = True,   # strip baked shadows from input image
    out_dir: str = "output",
) -> pathlib.Path:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    with open(image_path, "rb") as f:
        r = requests.post(
            f"{API_BASE}/image-to-3d",
            headers=HEADERS,
            files={"image_file": f},
            data={
                "topology": topology,
                "target_polycount": str(target_polycount),
                "enable_pbr": str(enable_pbr).lower(),
                "remove_lighting": str(remove_lighting).lower(),
                "ai_model": "meshy-6",
                "should_remesh": "true",
            },
        )
    r.raise_for_status()
    task_id = r.json()["result"]
    task = _poll(task_id, "image-to-3d")
    glb_path = out / f"{task_id}.glb"
    glb_path.write_bytes(requests.get(task["model_urls"]["glb"]).content)
    print(f"[Meshy] Saved: {glb_path}")
    return glb_path
```

**SSE stream endpoint (avoids fixed poll interval):**
```python
import sseclient, requests

response = requests.get(
    f"{API_BASE}/text-to-3d/{task_id}/stream",
    headers=HEADERS, stream=True
)
for event in sseclient.SSEClient(response).events():
    if event.data == "SUCCEEDED":
        break
```

---

## §3. Tripo H3 API (Best Topology Control)

**Python SDK:** `pip install tripo3d`  
**Models:** H3 (`v3.1-20260211`), H2, P1  
**Licensing:** Free = CC BY 4.0; Pro+ = commercial. `quad=true` forces FBX output.

**Strengths:** `quad=true` (clean quad topology), `smart_low_poly` (hand-crafted loops),
`auto_size=True` (outputs in real-world meters — most reliable scale), `generate_parts`
(segmented editable parts), `face_limit` up to 150,000 recommended for quads.

```python
# Requires: pip install tripo3d
# Env: $env:TRIPO_API_KEY = "..."

import asyncio, pathlib
from tripo3d import TripoClient


async def image_to_3d_quad(
    image_path: str,
    out_dir: str = "output",
    face_limit: int = 150000,
    smart_low_poly: bool = False,
) -> pathlib.Path:
    out = pathlib.Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    async with TripoClient() as client:
        task_id = await client.image_to_model(
            image=image_path,
            model_version="v3.1-20260211",
            texture=True,
            pbr=True,
            quad=True,              # quad-dominant mesh; forces FBX
            face_limit=face_limit,
            smart_low_poly=smart_low_poly,
            auto_size=True,         # scale to real-world meters
            texture_quality="standard",  # "standard" | "detailed" | "extreme"
        )
        print(f"[Tripo] Task: {task_id}")
        result_paths = await client.wait_for_task(task_id, download_dir=str(out))

    for file_type, file_path in result_paths.items():
        print(f"[Tripo] {file_type}: {file_path}")
    # quad=True forces FBX output
    fbx_path = next(
        (pathlib.Path(p) for t, p in result_paths.items() if t == "fbx"), None
    )
    return fbx_path or pathlib.Path(list(result_paths.values())[0])


if __name__ == "__main__":
    asyncio.run(image_to_3d_quad("input.png"))
```

**Pricing (2026-06, credits, $1=100 credits):**
- Image-to-3D H3 with texture: 30 credits = $0.30
- `quad=true`: +5 credits; `smart_low_poly`: +10 credits; `geometry_quality=detailed`: +20 credits

---

## §4. Rodin and Luma (Alternatives)

**Rodin Gen-2.5 (Hyper3D):** unique `concat` mode accepts up to 5 reference images → one model.
`mesh_mode: "Quad"`, `tier: "HighPack"` for 4K textures.
```python
# API: https://hyperhuman.deemos.com/api/v2/rodin
import requests, os
r = requests.post("https://hyperhuman.deemos.com/api/v2/rodin",
    headers={"Authorization": f"Bearer {os.environ['RODIN_API_KEY']}"},
    json={"prompt": "Victorian armchair", "images": [],
          "mesh_mode": "Quad", "tier": "Regular", "geometry_file_format": "glb"})
task_id = r.json()["uuid"]
```

**Luma AI Genie 3D:** best for stylized/organic heroes. 400-char prompt limit. No quad output.
```python
# Model: genie-3d (2025-08-05). Produces mesh + 6 ortho reference renders.
import requests, os
r = requests.post("https://api.lumalabs.ai/dream-machine/v1/generations",
    headers={"Authorization": f"Bearer {os.environ['LUMA_API_KEY']}"},
    json={"model": "genie-3d", "prompt": "Victorian armchair, oak wood"})
```

---

## §5. Local Inference — TripoSR

**License:** MIT — full commercial use  
**Repo:** https://github.com/VAST-AI-Research/TripoSR  
**Input:** single image → 3D mesh (no text-to-3D)  
**VRAM:** ~6 GB  
**Speed:** <0.5s on A100; ~3–8s on RTX 3090

**Install and run (Windows, CUDA 11.8):**
```powershell
# One-time setup
git clone https://github.com/VAST-AI-Research/TripoSR
cd TripoSR
pip install -r requirements.txt    # torchmcubes compiles at install time

# Run headless → GLB output with UV-baked texture
python run.py examples\chair.png `
    --output-dir "C:\out\triposr" `
    --bake-texture `
    --texture-resolution 1024

# Multiple images
python run.py img1.png img2.png --output-dir "C:\out\triposr"
```

**Limitations:**
- Image-only (no text input)
- Without `--bake-texture`: outputs vertex colors only (no UV map). Always pass `--bake-texture`.
- Single dense triangle mesh (~200K+ tris) → must be cleaned and retopologized before delivery
- No PBR outputs

---

## §6. Local Inference — Hunyuan3D 2.1

**Repo:** https://github.com/tencent-hunyuan/hunyuan3d-2.1 (2025-06-13)  
**License:** Tencent Open Source License (non-commercial base weights; check LICENSE for details)  
**Architecture:** DiT flow-matching (shape) + PBR texture synthesis (paint)  
**VRAM:**
- 24 GB+: standard model `v2-1`
- 16 GB: standard with `low_vram_mode=True`
- 6 GB: mini model `v2-mini` with `low_vram_mode=True`

**Windows-specific setup (critical):**
```powershell
# Use the Windows-tested fork:
git clone https://github.com/lzz19980125/Hunyuan3D-2.1-Windows

# Remove deepspeed from requirements.txt (not needed for inference)
# (Get-Content requirements.txt) -notmatch "deepspeed" | Set-Content requirements.txt

# Install (CUDA 12.4 required for custom_rasterizer C++ extensions)
pip install -r requirements.txt

# Verify CUDA
python -c "import torch; print(torch.cuda.is_available(), torch.version.cuda)"
```

**Headless shape generation (Python):**
```python
import sys, pathlib
sys.path.insert(0, './hy3dshape')

from hy3dshape.pipelines import Hunyuan3DDiTFlowMatchingPipeline


def generate_shape(
    image_path: str,
    out_path: str = "output_raw.glb",
    model_variant: str = "hunyuan3d-dit-v2-mini",  # "v2-mini" (6GB) or "v2-1" (16GB+)
    num_steps: int = 50,           # 20=fast, 50=balanced, 100=high quality
    guidance_scale: float = 5.0,
    octree_resolution: int = 256,  # 256=fast, 384=default, 512=high detail
    low_vram: bool = True,
) -> pathlib.Path:
    pipe = Hunyuan3DDiTFlowMatchingPipeline.from_pretrained(
        "tencent/Hunyuan3D-2.1",
        subfolder=model_variant,
        low_vram_mode=low_vram,
    )
    mesh = pipe(
        image=image_path,
        num_inference_steps=num_steps,
        guidance_scale=guidance_scale,
        octree_resolution=octree_resolution,
    )[0]
    out = pathlib.Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    mesh.export(str(out))
    print(f"[Hunyuan3D] Raw mesh: {out}")
    return out
```

**REST API server (preferred for headless Forge — avoids Gradio double-slash bug):**
```powershell
python api_server.py --host 127.0.0.1 --port 8080
$imgB64 = [Convert]::ToBase64String([IO.File]::ReadAllBytes("C:\assets\input.png"))
Invoke-RestMethod -Uri "http://127.0.0.1:8080/generate" -Method Post `
    -ContentType "application/json" `
    -Body (@{ image = $imgB64 } | ConvertTo-Json) -OutFile "output.glb"
```

**Notes:** Text-to-3D requires a text-to-image step first — Hunyuan3D doesn't accept raw text.
Model cache: `~/.cache/hy3dgen/` — ~25 GB first download.

---

## §7. Best Practices

**Reference images:**
- Remove background with `rembg` before sending to any generator:
  ```python
  from rembg import remove
  from PIL import Image
  img_nobg = remove(Image.open("input.jpg"))
  img_nobg.save("input_nobg.png")  # RGBA PNG
  ```
- Diffuse/even lighting only. Hard directional shadows bake into albedo permanently.
- Use image-to-3D over text-to-3D when possible — image provides a concrete silhouette.
  Text-to-3D has high variance; expect 3–5 regenerations for acceptable geometry.

**Scale (Forge standard: 1 unit = 1 meter):**
- Meshy: outputs in centimeters by default (100× scale). Apply 0.01 in Blender.
- Tripo `auto_size=True`: outputs meters. Most reliable.
- TripoSR / Hunyuan3D: normalized to [-1,1] cube. Must rescale to real dimensions.
- Check: `max(extents) < 10` for props; `max(extents) < 2` for characters.

**PBR always:** Always enable PBR (`enable_pbr=true` on Meshy, `pbr=True` on Tripo).
Non-PBR diffuse textures bake in studio lighting and won't integrate with scene lighting.

---

## §8. Gotchas & Fixes (Windows)

| Problem | Symptom | Fix |
|---|---|---|
| CUDA version mismatch | `torchmcubes` / `custom_rasterizer` fails to compile | Match system CUDA Toolkit to PyTorch CUDA; set `$env:CUDA_HOME`; use only one CUDA version |
| Baked-in lighting | Texture has permanent bright/dark sides | `remove_lighting=True` (Meshy) or `enable_image_autofix=True` (Tripo); prevention > cure |
| Non-manifold / shell mesh | Blender boolean fails; print slicers report hollow | trimesh auto-repair then Blender: Recalculate Normals → 3D Print Toolbox → Solidify modifier |
| Wrong scale on import | 100× or 0.01× extents | Apply 0.01 scale for Meshy GLB; use Tripo `auto_size`; always `transform_apply(scale=True)` before remesh |
| Hunyuan3D Gradio double-slash | `http://127.0.0.1:8080//` network error | Use `api_server.py` endpoint instead; or fix `gr.mount_gradio_app(app, demo, path="")` |
| TripoSR: no UVs | UV Editor empty after import; bake produces black image | Always run TripoSR with `--bake-texture --texture-resolution 1024`; or treat output as hi-res bake source |
| SF3D build fails | C++ MSVC compile error | Install VS 2022 full C++ workload; CUDA Toolkit 12.4.1 or earlier; or use `YanWenKun/StableFast3D-WinPortable` |
| Meshy poll timeout | Preview never reaches SUCCEEDED | Queue time: 3–8 min typical; 15+ min peak. Use 1200s timeout + SSE stream endpoint |
| Quadriflow hangs | Blender hangs on >2M tri input | Pre-decimate with PyMeshLab to <1M tris before loading into Blender |
| `--` separator missing | Script args silently ignored by Blender | The `--` between `-P script.py` and script args is MANDATORY in all `blender -b` invocations |
