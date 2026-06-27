"""
forge-render/scripts/preflight.py
Checks tool availability before attempting headless rendering.
Pure stdlib — no third-party packages, no network calls.

Usage:
    python preflight.py [--tools blender,python] [--json]

Exits 0 if all checked tools are found.
Exits 1 if any required tool is missing.
"""

import sys
import io
import json
import shutil
import subprocess
import argparse

# UTF-8 stdout wrapper (Windows cp1252 fix)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


KNOWN_TOOLS = {
    "blender": {
        "cmd":   ["blender", "--version"],
        "desc":  "Blender headless renderer",
        "url":   "https://www.blender.org/download/",
    },
    "python": {
        "cmd":   ["python", "--version"],
        "desc":  "System Python (for contact_sheet.py)",
        "url":   "https://www.python.org/downloads/windows/",
    },
    "pillow": {
        "cmd":   ["python", "-c", "import PIL; print(PIL.__version__)"],
        "desc":  "Pillow (contact sheet assembly)",
        "url":   "https://pypi.org/project/Pillow/ — install: pip install Pillow",
    },
}


def check_tool(name: str) -> dict:
    """Check a single tool. Returns a result dict."""
    spec = KNOWN_TOOLS.get(name)
    if spec is None:
        return {"tool": name, "found": False, "version": "", "error": "unknown tool"}

    # shutil.which for a quick PATH check first (avoids subprocess overhead when missing)
    exe = spec["cmd"][0]
    if not shutil.which(exe):
        return {
            "tool":    name,
            "found":   False,
            "version": "",
            "error":   f"'{exe}' not on PATH",
            "url":     spec.get("url", ""),
        }

    # subprocess for version string
    try:
        result = subprocess.run(
            spec["cmd"],
            capture_output=True,
            text=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
        )
        combined = (result.stdout or result.stderr or "").strip()
        first_line = combined.splitlines()[0] if combined else ""
        found = (result.returncode == 0) or bool(first_line)
        return {"tool": name, "found": found, "version": first_line, "error": ""}
    except FileNotFoundError:
        return {"tool": name, "found": False, "version": "", "error": "not found"}
    except subprocess.TimeoutExpired:
        return {"tool": name, "found": False, "version": "", "error": "timeout"}
    except Exception as exc:
        return {"tool": name, "found": False, "version": "", "error": str(exc)}


def find_blender_path() -> str:
    """
    Try to find the blender.exe absolute path using multiple strategies.
    Returns the path string only if it points at a real file, else ''.
    """
    import pathlib

    # 1. shutil.which (PATH-based)
    found = shutil.which("blender") or shutil.which("blender.exe")
    if found and pathlib.Path(found).is_file():
        return found

    # 2. Glob common Windows install roots for Blender*/blender.exe (newest first).
    #    Versioned install dirs sort lexicographically — reverse() picks the latest.
    install_roots = (
        "C:/Program Files/Blender Foundation",
        "C:/Program Files (x86)/Blender Foundation",
        "C:/Tools",
    )
    for root in install_roots:
        try:
            matches = sorted(pathlib.Path(root).glob("Blender*/blender.exe"), reverse=True)
            if matches and matches[0].is_file():
                return str(matches[0])
        except OSError:
            pass

    # 3. Fallback: deep search under the same roots (catches non-standard nesting).
    for root in install_roots:
        root_p = pathlib.Path(root)
        if root_p.is_dir():
            try:
                exes = sorted(root_p.rglob("blender.exe"), reverse=True)
                if exes and exes[0].is_file():
                    return str(exes[0])
            except OSError:
                pass

    return ""


def main() -> None:
    p = argparse.ArgumentParser(description="forge-render preflight check")
    p.add_argument("--tools",  default="blender,python",
                   help="Comma-separated tools to check (default: blender,python)")
    p.add_argument("--json",   action="store_true", help="Emit JSON output")
    args = p.parse_args()

    requested = [t.strip().lower() for t in args.tools.split(",") if t.strip()]
    results   = [check_tool(name) for name in requested]
    missing   = [r["tool"] for r in results if not r["found"]]

    # Attempt to locate blender.exe absolute path for caller convenience
    blender_path = find_blender_path() if "blender" in requested else ""

    output = {
        "results":      results,
        "missing":      missing,
        "all_found":    len(missing) == 0,
        "blender_path": blender_path,
    }

    if args.json:
        print(json.dumps(output, indent=2))
    else:
        print("## forge-render preflight")
        for r in results:
            status = "OK  " if r["found"] else "MISS"
            ver    = r["version"][:60] if r["version"] else "(no version string)"
            print(f"  [{status}] {r['tool']:12s}  {ver}")
            if not r["found"] and r.get("url"):
                print(f"           Install: {r['url']}")
        if blender_path:
            print(f"\n  blender path: {blender_path}")
        if missing:
            print(f"\n  MISSING: {', '.join(missing)}")
            sys.exit(1)
        else:
            print("\n  All tools present.")

    if missing:
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        print(f"[forge-render] preflight error: {exc}", file=sys.stderr)
        sys.exit(1)
