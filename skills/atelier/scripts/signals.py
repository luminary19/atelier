# -*- coding: utf-8 -*-
"""
atelier signals - project-state probe for the /atelier router's recommender.

Pure standard library. No third-party deps, no network beyond localhost dev-server
port probes. Windows-first (use `python`, not `python3`).

Usage:
  python signals.py [--root DIR] [--json]

Emits the facts the /atelier skill reasons over to recommend the next 2-3 steps:
whether ATELIER.md exists, the detected stack, git-changed web files, and whether a
dev server is up. It RECOMMENDS NOTHING itself - the skill decides; this only gathers
facts. Fail-safe: any probe that errors degrades to a null/empty value, never a crash.
"""

import argparse
import io
import json
import socket
import subprocess
import sys
from pathlib import Path

# Force UTF-8 stdout on Windows (cp1252 default) so summaries never crash on a glyph.
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WEB_EXT = {".html", ".htm", ".css", ".scss", ".jsx", ".tsx", ".js", ".ts",
           ".vue", ".svelte", ".astro", ".mdx"}
# Common dev-server ports: Next/CRA(3000-1), Astro(4321), Vite(5173-4), Vite preview(4173),
# generic(8080/8000/5000), Hugo(1313).
DEV_PORTS = [3000, 3001, 4321, 5173, 5174, 4173, 8080, 8000, 5000, 1313]


def find_root(start: Path) -> Path:
    """Walk up to the nearest .git or package.json; fall back to the start dir."""
    cur = start.resolve()
    for p in [cur, *cur.parents]:
        if (p / ".git").exists() or (p / "package.json").exists():
            return p
    return cur


def git_changed_web_files(root: Path) -> list[str] | None:
    """git status --porcelain, filtered to web files. None if not a repo / git missing."""
    try:
        out = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(root), capture_output=True, text=True, timeout=5,
        )
        if out.returncode != 0:
            return None
        files: list[str] = []
        for line in out.stdout.splitlines():
            path = line[3:].strip()              # porcelain v1: 2 status chars + space + path
            if " -> " in path:                   # renames: "old -> new"
                path = path.split(" -> ")[-1]
            path = path.strip().strip('"')
            if path and Path(path).suffix.lower() in WEB_EXT:
                files.append(path)
        return files
    except Exception:
        return None


def port_open(port: int) -> bool:
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.15)
            return s.connect_ex(("127.0.0.1", port)) == 0
    except Exception:
        return False


def detect_stack(root: Path) -> dict:
    stack = {"hasPackageJson": False, "framework": None, "tailwind": False}
    pkg = root / "package.json"
    if not pkg.exists():
        return stack
    stack["hasPackageJson"] = True
    try:
        data = json.loads(pkg.read_text(encoding="utf-8"))
        deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
        stack["tailwind"] = "tailwindcss" in deps
        for fw in ("next", "nuxt", "@sveltejs/kit", "astro", "@remix-run/react",
                   "vue", "react", "svelte"):
            if fw in deps:
                stack["framework"] = fw
                break
    except Exception:
        pass
    return stack


def gather(root: Path) -> dict:
    atelier_md = root / "ATELIER.md"
    changed = git_changed_web_files(root)
    ports = [p for p in DEV_PORTS if port_open(p)]
    return {
        "root": str(root),
        "memory": {
            "hasAtelierMd": atelier_md.exists(),
            "path": str(atelier_md) if atelier_md.exists() else None,
        },
        "stack": detect_stack(root),
        "git": {
            "isRepo": (root / ".git").exists(),
            "changedWebFiles": changed or [],
            "changedCount": len(changed) if changed else 0,
        },
        "devServer": {"running": bool(ports), "ports": ports},
    }


def format_human(sig: dict) -> str:
    m, g, d, st = sig["memory"], sig["git"], sig["devServer"], sig["stack"]
    fw = st["framework"] or ("vanilla / static" if not st["hasPackageJson"] else "unknown")
    lines = [
        "## atelier signals",
        f"root         : {sig['root']}",
        f"ATELIER.md   : {'present' if m['hasAtelierMd'] else 'MISSING (offer /atelier init on substantial work)'}",
        f"stack        : {fw}{' + tailwind' if st['tailwind'] else ''}",
        f"git          : {'repo' if g['isRepo'] else 'not a repo'}, {g['changedCount']} changed web file(s)",
    ]
    if g["changedWebFiles"]:
        lines.append("  changed    : " + ", ".join(g["changedWebFiles"][:12])
                     + (" …" if g["changedCount"] > 12 else ""))
    lines.append(
        "dev server   : " + (f"running on {', '.join(map(str, d['ports']))}"
                             if d["running"] else "not detected")
    )
    lines.append("\n(facts only — the /atelier skill reasons over these to recommend next steps)")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description="atelier project-state signals (facts for the router)")
    ap.add_argument("--root", default=".", help="Project dir to probe (default: cwd)")
    ap.add_argument("--json", action="store_true", help="Emit JSON instead of a human summary")
    args = ap.parse_args()

    sig = gather(find_root(Path(args.root)))
    print(json.dumps(sig, indent=2) if args.json else format_human(sig))


if __name__ == "__main__":
    main()
