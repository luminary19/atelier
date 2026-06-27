"""
forge-intake/scripts/meshy_gen.py
Headless Meshy text/image-to-3D generation driver for the Forge intake suite (Track D).

Drives the Meshy OpenAPI v2 REST endpoints, polls the task to completion, and downloads
the resulting GLB. Assembled from references/ai-generation.md §2 so the Meshy poll loop is a
pinned, re-runnable artifact instead of improvised prose each run.

Usage (PowerShell):
    $env:MESHY_API_KEY = "msy_..."   # test key: msy_dummy_api_key_for_test_mode_12345678
    python "$CLAUDE_CONFIG_DIR/skills/forge-intake/scripts/meshy_gen.py" \
        --mode text --prompt "Victorian armchair, aged oak" \
        --topology quad --polycount 300000 --out-dir "C:/project/ai_raw" [--json]

    python ".../meshy_gen.py" --mode image --image "C:/assets/chair_nobg.png" \
        --polycount 300000 --out-dir "C:/project/ai_raw"

Options:
    --mode {text,image}   text-to-3D (preview+refine) or image-to-3D (single task)
    --prompt STR          prompt (required for --mode text)
    --image PATH          reference image (required for --mode image); prefer rembg RGBA PNG
    --negative STR        negative prompt (text mode)
    --topology {quad,triangle}   default quad
    --polycount N         target_polycount; generate at MAX (300000) then decimate (default 300000)
    --no-pbr              disable PBR (NOT recommended — non-PBR bakes in studio lighting)
    --poll-seconds N      poll interval (default 5)
    --timeout N           overall timeout per task in seconds (default 1200)
    --out-dir DIR         output directory (created if absent; default "output")
    --json                emit a JSON summary to stdout instead of human-readable lines

Network: this is the ONLY Forge intake script that makes network calls (vendor API).
Requires `pip install requests`. Exits non-zero on failure (so the caller can branch).

Platform: Native Windows 11, PowerShell-first. Use `python`, not `python3`.
"""

import os
import sys
import io
import json
import time
import argparse
import pathlib

# UTF-8 stdout wrapper (Windows cp1252 default breaks non-ASCII console output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

API_BASE = "https://api.meshy.ai/openapi/v2"


def _require_requests():
    try:
        import requests  # noqa: F401
        return requests
    except ImportError:
        print("[meshy] ERROR: the 'requests' package is required. Run: pip install requests",
              file=sys.stderr)
        sys.exit(2)


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="forge-intake Meshy text/image-to-3D driver")
    p.add_argument("--mode", choices=["text", "image"], required=True)
    p.add_argument("--prompt", default="")
    p.add_argument("--image", default="")
    p.add_argument("--negative", default="low quality, asymmetry, noisy texture")
    p.add_argument("--topology", choices=["quad", "triangle"], default="quad")
    p.add_argument("--polycount", type=int, default=300000,
                   help="target_polycount; generate at MAX, decimate afterwards")
    p.add_argument("--no-pbr", action="store_true", default=False)
    p.add_argument("--poll-seconds", type=int, default=5)
    p.add_argument("--timeout", type=int, default=1200)
    p.add_argument("--out-dir", default="output")
    p.add_argument("--json", action="store_true", default=False)
    return p.parse_args()


def _headers() -> dict:
    key = os.environ.get("MESHY_API_KEY")
    if not key:
        print("[meshy] ERROR: MESHY_API_KEY is not set. "
              "Set it first: $env:MESHY_API_KEY = \"msy_...\" "
              "(test key: msy_dummy_api_key_for_test_mode_12345678)", file=sys.stderr)
        sys.exit(2)
    return {"Authorization": f"Bearer {key}"}


def _poll(requests, task_id: str, endpoint: str, poll_s: int, timeout: int) -> dict:
    headers = _headers()
    deadline = time.time() + timeout
    while time.time() < deadline:
        r = requests.get(f"{API_BASE}/{endpoint}/{task_id}", headers=headers)
        r.raise_for_status()
        task = r.json()
        status = task.get("status")
        if status == "SUCCEEDED":
            return task
        if status == "FAILED":
            raise RuntimeError(f"Task {task_id} FAILED: {task.get('task_error', {})}")
        print(f"  [{status}] {task.get('progress', 0)}%", flush=True)
        time.sleep(poll_s)
    raise TimeoutError(f"Task {task_id} timed out after {timeout}s "
                       "(Meshy queue time is 3-8 min typical, 15+ min at peak)")


def text_to_3d(requests, args, out: pathlib.Path) -> dict:
    headers = _headers()
    # Stage 1: Preview (geometry)
    r = requests.post(f"{API_BASE}/text-to-3d", headers=headers, json={
        "mode": "preview",
        "prompt": args.prompt,
        "negative_prompt": args.negative,
        "ai_model": "meshy-6",
        "topology": args.topology,
        "target_polycount": args.polycount,
        "should_remesh": True,
    })
    r.raise_for_status()
    preview_id = r.json()["result"]
    print(f"[meshy] preview task: {preview_id}")
    _poll(requests, preview_id, "text-to-3d", args.poll_seconds, args.timeout)

    # Stage 2: Refine (texture + PBR)
    r = requests.post(f"{API_BASE}/text-to-3d", headers=headers, json={
        "mode": "refine",
        "preview_task_id": preview_id,
        "enable_pbr": not args.no_pbr,
    })
    r.raise_for_status()
    refine_id = r.json()["result"]
    print(f"[meshy] refine task: {refine_id}")
    task = _poll(requests, refine_id, "text-to-3d", args.poll_seconds, args.timeout)

    glb_url = task["model_urls"]["glb"]
    glb_path = out / f"{preview_id}.glb"
    glb_path.write_bytes(requests.get(glb_url).content)
    return {"task_id": refine_id, "preview_id": preview_id, "glb": str(glb_path)}


def image_to_3d(requests, args, out: pathlib.Path) -> dict:
    headers = _headers()
    img = pathlib.Path(args.image)
    if not img.exists():
        raise FileNotFoundError(f"reference image not found: {args.image}")
    with open(img, "rb") as f:
        r = requests.post(
            f"{API_BASE}/image-to-3d",
            headers=headers,
            files={"image_file": f},
            data={
                "topology": args.topology,
                "target_polycount": str(args.polycount),
                "enable_pbr": str(not args.no_pbr).lower(),
                "remove_lighting": "true",   # strip baked shadows from the input image
                "ai_model": "meshy-6",
                "should_remesh": "true",
            },
        )
    r.raise_for_status()
    task_id = r.json()["result"]
    print(f"[meshy] image-to-3d task: {task_id}")
    task = _poll(requests, task_id, "image-to-3d", args.poll_seconds, args.timeout)
    glb_path = out / f"{task_id}.glb"
    glb_path.write_bytes(requests.get(task["model_urls"]["glb"]).content)
    return {"task_id": task_id, "glb": str(glb_path)}


def main() -> None:
    args = parse_args()
    if args.mode == "text" and not args.prompt:
        print("[meshy] ERROR: --prompt is required for --mode text", file=sys.stderr)
        sys.exit(2)
    if args.mode == "image" and not args.image:
        print("[meshy] ERROR: --image is required for --mode image", file=sys.stderr)
        sys.exit(2)

    requests = _require_requests()
    out = pathlib.Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)

    result = text_to_3d(requests, args, out) if args.mode == "text" else image_to_3d(requests, args, out)

    glb = pathlib.Path(result["glb"])
    size_kb = round(glb.stat().st_size / 1024, 1) if glb.exists() else 0
    result["size_kb"] = size_kb
    result["ok"] = size_kb > 1

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        status = "OK" if result["ok"] else "WARN (tiny)"
        print(f"[meshy] saved [{status}]: {result['glb']} ({size_kb} KB)")
        print("[meshy] NEXT: run scripts/cleanup.py to retopo/UV/rebake, then forge-validate. "
              "Meshy exports in centimeters (100x scale) — cleanup.py applies the 0.01 scale fix.")

    if not result["ok"]:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[meshy] FATAL: {exc}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        sys.exit(1)
