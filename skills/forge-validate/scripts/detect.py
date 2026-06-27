"""
forge-validate/scripts/detect.py
Advisory regex-tier pre-pass for Forge 3D assets.

Usage:
    python detect.py --target <path|dir> [--json]

Flags missing poster, oversized GLB, EEVEE headless flag in scripts,
`//` Blender relative paths, missing `--` arg separator in Blender invocations,
and other common Forge gotchas.

Advisory only: exit 0 always.
Windows-first: use `python`, not `python3`.
"""

import sys
import io
import json
import argparse
import pathlib
import re

# Windows stdout encoding fix
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

# ---------------------------------------------------------------------------
# Check definitions: (id, level, pattern, message)
# level: BLOCK = must fix, WARN = review, NOTE = advisory
# ---------------------------------------------------------------------------

# Regex patterns applied to .py file contents
SCRIPT_PATTERNS = [
    (
        "EEVEE_HEADLESS",
        "BLOCK",
        re.compile(r"BLENDER_EEVEE(?:_NEXT)?", re.IGNORECASE),
        "EEVEE is unsupported headless on Windows — use BLENDER_WORKBENCH for QA, CYCLES (CPU) for shader passes",
    ),
    (
        "BLENDER_PATH_RELATIVE",
        "BLOCK",
        re.compile(r"""filepath\s*=\s*['"]//"""),
        "Relative `//` Blender path in filepath field — use absolute forward-slash path; `//` resolves relative to blend file (which may not exist in headless mode)",
    ),
    (
        "PYTHON3_CALL",
        "WARN",
        re.compile(r"\bpython3\b"),
        "`python3` not available on Windows by default — use `python` instead",
    ),
    (
        "MISSING_DASH_DASH_SEP",
        "WARN",
        # Per logical line: find `blender ... -P x.py` then assert NO `--` separator follows
        # on the same line. The previous DOTALL pattern false-fired on CORRECT invocations
        # because its char-class greedily ate the space before `--`, so the lookahead never
        # saw the separator. Scanning a single line ([^\n]) avoids that and skips the
        # backtick-continued PowerShell form (where `--` is on the next physical line — a
        # documented blind spot; that form is the canonical one in windows-headless.md).
        re.compile(r"blender\b[^\n]*?-P\s+\S+\.py(?![^\n]*?(?:\s|^)--(?:\s|$))", re.IGNORECASE),
        "Blender -P script invocation without `--` arg separator — script args after `--` only; without it Blender interprets them as blend filenames",
    ),
    (
        "HARDCODED_BACKSLASH_PATH",
        "WARN",
        re.compile(r'''(?:filepath|bpy\.ops\.\w+\.\w+\s*\(|load_new_mesh\s*\()\s*['"](\\[^\\])'''),
        "Backslash path literal passed to Blender/PyMeshLab — use forward slashes or pathlib.Path",
    ),
    (
        "MISSING_WRITE_STILL",
        "WARN",
        re.compile(r"bpy\.ops\.render\.render\s*\(\s*\)"),
        "bpy.ops.render.render() called without write_still=True — PNG will not be saved",
    ),
    (
        "RELATIVE_RENDER_FILEPATH",
        "WARN",
        # Flag any filepath that is NOT a drive-letter path (C:\ / C:/), a leading-slash
        # absolute path, or a `//` Blender-relative path (caught separately above). The
        # previous lookahead `(?![\w:/\\])` only fired on a leading non-word char (./ ../),
        # so a bare relative path like "out/render_" (starts with a word char) slipped through.
        re.compile(r"render\.filepath\s*=\s*['\"](?![A-Za-z]:[\\/])(?!//)(?![\\/])"),
        "render.filepath appears to be a relative path — use absolute path (relative paths break when no blend file is loaded)",
    ),
    (
        "BMesh_FREE_MISSING",
        "WARN",
        re.compile(r"bmesh\.new\(\)(?!.*bm\.free\(\))", re.DOTALL),
        "bmesh.new() without bm.free() detected — always free bmesh to avoid OOM on batch jobs",
    ),
    (
        "ENSURE_LOOKUP_TABLE_MISSING",
        "NOTE",
        re.compile(r"bmesh\.ops\.\w+\([^)]*\)\s*(?!\s*bm\.\w+\.ensure_lookup_table)"),
        "bmesh.ops call without ensure_lookup_table() after it — indices become stale after topology ops",
    ),
]

# GLB file checks (structural, no regex)
def check_glb_file(path: pathlib.Path) -> list[dict]:
    findings = []
    try:
        size_mb = path.stat().st_size / 1_048_576
        if size_mb > 20:
            findings.append({
                "file":  str(path),
                "id":    "GLB_OVERSIZE",
                "level": "BLOCK",
                "msg":   f"GLB is {size_mb:.1f} MB — run forge-optimize (Draco+Meshopt) before web delivery",
            })
        elif size_mb > 5:
            findings.append({
                "file":  str(path),
                "id":    "GLB_LARGE",
                "level": "WARN",
                "msg":   f"GLB is {size_mb:.1f} MB — consider forge-optimize for web delivery",
            })

        # Check for poster
        stem = path.stem
        poster_candidates = [
            path.parent / f"{stem}-poster.webp",
            path.parent / f"{stem}.webp",
            path.parent / (stem.replace("-hero", "-hero-poster") + ".webp"),
        ]
        has_poster = any(c.exists() and c.stat().st_size >= 1024 for c in poster_candidates)
        if not has_poster:
            findings.append({
                "file":  str(path),
                "id":    "MISSING_POSTER",
                "level": "WARN",
                "msg":   f"No poster WebP found adjacent to {path.name} — poster is the reduced-motion/no-WebGL fallback for web delivery",
            })
    except Exception as e:
        findings.append({"file": str(path), "id": "GLB_CHECK_ERROR", "level": "NOTE", "msg": str(e)})
    return findings


def check_script_file(path: pathlib.Path) -> list[dict]:
    findings = []
    try:
        content = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        return [{"file": str(path), "id": "READ_ERROR", "level": "NOTE", "msg": str(e)}]

    for check_id, level, pattern, msg in SCRIPT_PATTERNS:
        if pattern.search(content):
            findings.append({
                "file":  str(path),
                "id":    check_id,
                "level": level,
                "msg":   msg,
            })
    return findings


def collect_files(target: pathlib.Path) -> tuple[list[pathlib.Path], list[pathlib.Path]]:
    """Return (glb_files, script_files) from a path or directory."""
    glbs, scripts = [], []
    if target.is_file():
        ext = target.suffix.lower()
        if ext in (".glb", ".gltf"):
            glbs.append(target)
        elif ext == ".py":
            scripts.append(target)
    elif target.is_dir():
        for p in target.rglob("*"):
            if not p.is_file():
                continue
            ext = p.suffix.lower()
            if ext in (".glb", ".gltf"):
                glbs.append(p)
            elif ext == ".py":
                scripts.append(p)
    return glbs, scripts


def main():
    ap = argparse.ArgumentParser(description="Forge advisory pre-pass detector.")
    ap.add_argument("--target", required=True, help="File or directory to scan")
    ap.add_argument("--json", action="store_true", help="Output JSON to stdout")
    args = ap.parse_args()

    target = pathlib.Path(args.target)
    if not target.exists():
        result = {"error": f"target not found: {target}", "findings": [], "summary": {}}
        if args.json:
            print(json.dumps(result))
        else:
            print(f"[detect] ERROR: target not found: {target}")
        sys.exit(0)

    glbs, scripts = collect_files(target)
    findings = []
    for p in glbs:
        findings.extend(check_glb_file(p))
    for p in scripts:
        findings.extend(check_script_file(p))

    counts = {"BLOCK": 0, "WARN": 0, "NOTE": 0}
    for f in findings:
        counts[f.get("level", "NOTE")] = counts.get(f.get("level", "NOTE"), 0) + 1

    report = {
        "target":   str(target),
        "scanned":  {"glb": len(glbs), "scripts": len(scripts)},
        "findings": findings,
        "summary":  counts,
    }

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print(f"[detect] scanned {len(glbs)} GLB(s), {len(scripts)} script(s) — "
              f"BLOCK:{counts['BLOCK']} WARN:{counts['WARN']} NOTE:{counts['NOTE']}")
        for f in findings:
            icon = {"BLOCK": "BLOCK", "WARN": "WARN ", "NOTE": "NOTE "}.get(f["level"], "     ")
            rel = pathlib.Path(f["file"]).name
            print(f"  [{icon}] {rel}: [{f['id']}] {f['msg']}")
        if not findings:
            print("  [OK  ] No issues detected.")

    # Advisory: always exit 0
    sys.exit(0)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(json.dumps({"error": str(e), "findings": [], "summary": {}}))
        sys.exit(0)
