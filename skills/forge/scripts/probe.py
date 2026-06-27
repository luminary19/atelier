"""
Forge probe — check 3D tool availability, detect project files, find prior renders.

Pure stdlib. Windows-first (use `python`, not `python3`).
No network. No third-party imports. Advisory: always exits 0.

Usage:
  python probe.py [--root DIR] [--json]

Outputs (human-readable by default):
  - Tool availability: blender, openscad, python, node, npx, magick, ffmpeg
  - Existing project files: .blend, .scad, .glb, .gltf, .usd, .usdc, .fbx, .stl, .obj
  - Prior renders: PNG/EXR files under typical render output directories
  - FORGE.md / ATELIER.md presence at root
"""

import sys
import io
import json
import shutil
import subprocess
from pathlib import Path

# UTF-8 stdout fix (Windows cp1252 default causes crashes on non-ASCII Blender output)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

TOOLS = {
    "blender":  {"cmd": ["blender", "--version"], "desc": "Headless 3D render + modeling"},
    "openscad": {"cmd": ["openscad.com", "--version"], "desc": "Parametric CAD (headless .com variant)"},
    "python":   {"cmd": ["python", "--version"], "desc": "System Python (scripts, probes)"},
    "node":     {"cmd": ["node", "--version"], "desc": "Node.js (gltf-transform, npx)"},
    "npx":      {"cmd": ["npx", "--version"], "desc": "npx runner (gltf-transform CLI)"},
    "magick":   {"cmd": ["magick", "--version"], "desc": "ImageMagick (poster resize/convert)"},
    "ffmpeg":   {"cmd": ["ffmpeg", "-version"], "desc": "FFmpeg (animation preview bake)"},
    # Advisory web/validate tools — absence => degrade (WebP fallback / Tier-1 validate), never block.
    "gltf_validator": {"cmd": ["gltf_validator", "--version"], "desc": "Khronos glTF spec validator (forge-validate Tier 2)"},
    "toktx":          {"cmd": ["toktx", "--version"], "desc": "KTX2/Basis texture compression (forge-optimize web)"},
}

# 3D source/asset extensions to detect
SOURCE_EXTS = {".blend", ".scad", ".fbx", ".obj", ".stl", ".3mf", ".step", ".stp"}
ASSET_EXTS  = {".glb", ".gltf", ".usd", ".usdc", ".usda", ".usdz", ".ply"}
IMAGE_EXTS  = {".png", ".exr", ".hdr"}

# Directories likely to hold render output
RENDER_DIRS = {"renders", "render", "output", "out", ".forge-build"}

# ---------------------------------------------------------------------------
# Tool checks
# ---------------------------------------------------------------------------

def check_tool(name: str, info: dict) -> dict:
    """Return availability and version for a single tool."""
    found = bool(shutil.which(info["cmd"][0]))
    version = ""
    if found:
        try:
            r = subprocess.run(
                info["cmd"],
                capture_output=True,
                text=True,
                timeout=5,
            )
            raw = (r.stdout or r.stderr or "").strip()
            version = raw.splitlines()[0] if raw else ""
        except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
            found = False
    return {
        "name": name,
        "found": found,
        "version": version,
        "desc": info["desc"],
    }


def check_all_tools() -> list:
    return [check_tool(name, info) for name, info in TOOLS.items()]

# ---------------------------------------------------------------------------
# File discovery
# ---------------------------------------------------------------------------

def find_files(root: Path, extensions: set, limit: int = 20) -> list:
    """Recursively find files with given extensions, skip .git."""
    results = []
    try:
        for p in root.rglob("*"):
            if ".git" in p.parts or ".forge-build" in p.parts:
                continue
            if p.suffix.lower() in extensions:
                try:
                    results.append(str(p.relative_to(root)))
                except ValueError:
                    results.append(str(p))
            if len(results) >= limit:
                break
    except (PermissionError, OSError):
        pass
    return results


def find_prior_renders(root: Path, limit: int = 15) -> list:
    """Find PNG/EXR files under render-output directories."""
    results = []
    try:
        for p in root.rglob("*"):
            if p.suffix.lower() not in IMAGE_EXTS:
                continue
            # Must be in a render-ish dir OR have "render"/"output"/"qa" in name
            parent_names = {part.lower() for part in p.parts}
            name_hints = {"render", "output", "qa", "preview", "forge"}
            if (parent_names & RENDER_DIRS) or any(h in p.stem.lower() for h in name_hints):
                try:
                    results.append(str(p.relative_to(root)))
                except ValueError:
                    results.append(str(p))
            if len(results) >= limit:
                break
    except (PermissionError, OSError):
        pass
    return results

# ---------------------------------------------------------------------------
# Memory file checks
# ---------------------------------------------------------------------------

def check_memory(root: Path) -> dict:
    forge_md = (root / "FORGE.md").exists()
    atelier_md = (root / "ATELIER.md").exists()
    result = {"forge_md": forge_md, "atelier_md": atelier_md}
    if forge_md:
        try:
            text = (root / "FORGE.md").read_text(encoding="utf-8", errors="replace")
            # Extract key fields for quick display
            import re
            engine_m = re.search(r"##\s*Target\s*\n.*?engine:\s*(.+)", text)
            render_m = re.search(r"##\s*Render\s*\n.*?engine:\s*(.+)", text)
            result["forge_target_engine"] = engine_m.group(1).strip() if engine_m else ""
            result["forge_render_engine"] = render_m.group(1).strip() if render_m else ""
        except (OSError, AttributeError):
            pass
    if atelier_md:
        try:
            text = (root / "ATELIER.md").read_text(encoding="utf-8", errors="replace")
            import re
            interact_m = re.search(r"##\s*Interactivity\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL)
            world_m = re.search(r"\*\*World:\*\*\s*(.+)", text)
            result["atelier_interactivity"] = interact_m.group(1).strip()[:80] if interact_m else ""
            result["atelier_world"] = world_m.group(1).strip() if world_m else ""
        except (OSError, AttributeError):
            pass
    return result

# ---------------------------------------------------------------------------
# Gather all signals
# ---------------------------------------------------------------------------

def gather(root: Path) -> dict:
    return {
        "root": str(root),
        "tools": check_all_tools(),
        "source_files": find_files(root, SOURCE_EXTS),
        "asset_files": find_files(root, ASSET_EXTS),
        "prior_renders": find_prior_renders(root),
        "memory": check_memory(root),
    }

# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------

def _status(found: bool) -> str:
    return "OK  " if found else "MISS"


def print_human(sig: dict) -> None:
    print("## forge probe")
    print(f"   root: {sig['root']}")
    print()

    # Memory files
    mem = sig["memory"]
    forge_status = "found" if mem["forge_md"] else "ABSENT (run /forge init)"
    atelier_status = "found" if mem["atelier_md"] else "absent"
    print(f"   FORGE.md   : {forge_status}")
    if mem.get("forge_target_engine"):
        print(f"     target   : {mem['forge_target_engine']}")
    if mem.get("forge_render_engine"):
        print(f"     render   : {mem['forge_render_engine']}")
    print(f"   ATELIER.md : {atelier_status}")
    if mem.get("atelier_interactivity"):
        print(f"     interact : {mem['atelier_interactivity'][:60]}")
    if mem.get("atelier_world"):
        print(f"     world    : {mem['atelier_world']}")
    print()

    # Tools
    print("   tools:")
    for t in sig["tools"]:
        ver = f"  ({t['version'][:60]})" if t["version"] else ""
        print(f"     [{_status(t['found'])}] {t['name']:<12}{ver}")
    print()

    # 3D files
    sf = sig["source_files"]
    af = sig["asset_files"]
    pr = sig["prior_renders"]

    def _list(label: str, items: list, cap: int = 5) -> None:
        if not items:
            print(f"   {label:<16}: none found")
        else:
            shown = items[:cap]
            rest = len(items) - cap
            print(f"   {label:<16}: {len(items)} found")
            for f in shown:
                print(f"       {f}")
            if rest > 0:
                print(f"       … and {rest} more")

    _list("source files", sf)
    _list("asset files", af)
    _list("prior renders", pr)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(
        description="Forge probe — check 3D tool availability and project state."
    )
    ap.add_argument(
        "--root",
        default=".",
        help="Project root directory to probe (default: current directory)",
    )
    ap.add_argument(
        "--json",
        action="store_true",
        help="Output JSON instead of human-readable text",
    )
    args = ap.parse_args()

    root = Path(args.root).resolve()
    try:
        sig = gather(root)
    except Exception as exc:
        if args.json:
            print(json.dumps({"error": str(exc)}, indent=2))
        else:
            print(f"probe error: {exc}")
        sys.exit(0)  # advisory: never block

    if args.json:
        print(json.dumps(sig, indent=2))
    else:
        print_human(sig)


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        # Advisory: never crash; always exit 0
        print(f"probe warning: {exc}")
        sys.exit(0)
