# -*- coding: utf-8 -*-
"""
atelier detect - a native, regex-tier static checker for Atelier's own design tells.

Strictly Atelier: this mechanizes the checklist in
  atelier-perf-a11y/references/anti-slop-preflight.md
plus the numeric thresholds from atelier-foundations / atelier-typography. It is NOT a port of any
third-party tool. Pure standard library, no deps, Windows-first (use `python`, not `python3`).

WHAT IT IS: a fast static pass over source text (CSS / HTML / JSX / TSX / Vue / Svelte / Astro). It
catches what is visible in source. WHAT IT IS NOT: a DOM / layout / computed-style / contrast analyzer
- it cannot see rendered geometry or resolved colors. Treat it as a cheap first net that complements
(never replaces) the LLM anti-slop review and atelier-review's live, pixel-computed checks.

Findings carry a five-bucket category and a severity:
  category : a11y | layout | drift | cliche | subjective   (the buckets from the dive)
  severity : block  -> real defect (a11y/layout); fails CI under --strict
             warn   -> probable issue / strong AI tell; advisory
             suggest-> low-confidence nudge / matter of taste; advisory

Usage (Windows: `python`, not `python3`):
  python detect.py [paths...]                 # scan files/dirs (default: cwd)
  python detect.py src/ --json                # machine-readable
  python detect.py src/ --category cliche      # only one bucket
  python detect.py src/ --severity warn        # warn + block only (drop suggest)
  python detect.py src/ --quiet                # print nothing if clean (for the hook)
  python detect.py src/ --strict               # exit 2 if any BLOCK finding (for CI)

Exit codes: 0 = no blocking findings (default always 0 unless --strict); 2 = --strict and a block finding.
"""

import argparse
import io
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

WEB_EXT = {".html", ".htm", ".css", ".scss", ".sass", ".less",
           ".jsx", ".tsx", ".js", ".ts", ".vue", ".svelte", ".astro", ".md", ".mdx"}
MARKUP_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro"}
STYLE_EXT = {".css", ".scss", ".sass", ".less", ".vue", ".svelte", ".astro"}
COMPONENT_EXT = {".jsx", ".tsx", ".vue", ".svelte"}
COPY_EXT = {".html", ".htm", ".jsx", ".tsx", ".vue", ".svelte", ".astro", ".md", ".mdx"}
IGNORE_DIRS = {"node_modules", ".git", "dist", "build", ".next", ".astro", ".svelte-kit",
               ".nuxt", "out", "vendor", "coverage", ".cache", "__pycache__", ".vercel"}
MAX_BYTES = 600_000  # skip very large / generated files

CATEGORIES = ("a11y", "layout", "drift", "cliche", "subjective")
SEV_RANK = {"block": 0, "warn": 1, "suggest": 2}


@dataclass(frozen=True)
class Finding:
    rule: str
    category: str
    severity: str
    file: str
    line: int
    snippet: str
    message: str


# --- line-regex rules: (id, category, severity, ext-set, compiled-regex, message, optional value-test) ---
# value-test, if given, receives the match and returns True to keep the finding (for numeric thresholds).

def _font_too_small(m: "re.Match") -> bool:
    try:
        return int(m.group(1)) < 12
    except (ValueError, IndexError):
        return False

def _zindex_high(m: "re.Match") -> bool:
    try:
        return int(m.group(1)) >= 999
    except (ValueError, IndexError):
        return False

def _tabindex_positive(m: "re.Match") -> bool:
    try:
        return int(m.group(1)) > 0
    except (ValueError, IndexError):
        return False

def _border_thick(m: "re.Match") -> bool:
    try:
        return int(m.group(1)) >= 3  # 1-2px full borders are fine; a 3px+ one-sided border is the accent-stripe tell
    except (ValueError, IndexError):
        return False


LINE_RULES = [
    # --- cliche (AI tells from anti-slop-preflight.md) ---
    ("gradient-text", "cliche", "warn", None,
     re.compile(r"(?:-webkit-)?background-clip:\s*text|-webkit-text-fill-color:\s*transparent", re.I),
     "Gradient text (background-clip:text) - decorative AI tell. Use one solid color; emphasis via weight/size.", None),
    ("cream-token-name", "cliche", "warn", STYLE_EXT,
     re.compile(r"--(?:paper|cream|sand|sandstone|bone|linen|parchment|wheat|biscuit|ivory|flour|oat|eggshell)\b", re.I),
     "Cream/sand/paper token name - the warm-neutral AI default. Name tokens by role (--bg/--surface) and pick the body bg deliberately.", None),
    ("pure-black-white", "cliche", "warn", STYLE_EXT,
     re.compile(r"(?<![\w-])(?:color|background|background-color|fill)\s*:\s*[^;]*(#000(?:000)?\b|#fff(?:fff)?\b|rgb\(\s*0\s*,\s*0\s*,\s*0\s*\)|rgb\(\s*255\s*,\s*255\s*,\s*255\s*\))", re.I),
     "Pure #000 / #fff as text or surface - causes halation and reads cheap. Use tinted ink/off-white tokens.", None),
    ("bounce-elastic-easing", "cliche", "warn", STYLE_EXT | {".js", ".ts", ".jsx", ".tsx"},
     re.compile(r"\b(?:elastic|bounce)\b|(?:back|elastic|bounce)\.(?:in|out|inOut)\b|cubic-bezier\(\s*[\d.]+\s*,\s*-0?\.[1-9]", re.I),
     "Bounce/elastic easing - reads gimmicky. Atelier default is ease-out (exponential), no overshoot.", None),
    ("side-stripe", "cliche", "warn", STYLE_EXT,
     re.compile(r"border-(?:left|right|inline-start|inline-end):\s*(\d+)px\s+solid", re.I),
     "Side-stripe accent border (thick one-sided colored border) - the AI 'make it pop' reflex. Use a full border, a background tint, a leading icon/number, or nothing.", _border_thick),
    ("buzzword-copy", "cliche", "suggest", COPY_EXT,
     re.compile(r"\b(?:seamless|robust|elevate|empower|unlock|supercharge|leverage|delve|revolutionary|game-?changing|effortless|cutting-edge|next-level|world-class)\b", re.I),
     "Marketing buzzword (AI/template tell) - say the specific benefit instead (see atelier-copy voice-and-tone).", None),
    # --- a11y (real defects) ---
    ("positive-tabindex", "a11y", "block", MARKUP_EXT,
     re.compile(r"tabindex\s*=\s*[\"']?\s*([1-9]\d*)", re.I),
     "Positive tabindex breaks natural focus order (WCAG 2.4.3). Use 0 or -1 and order in the DOM.", _tabindex_positive),
    ("div-onclick", "a11y", "warn", COMPONENT_EXT,
     re.compile(r"<(?:div|span)\b[^>]*\bonClick\b", re.I),
     "Click handler on a non-interactive element - not keyboard-reachable. Use <button>, or add role+tabIndex+key handler.", None),
    ("tiny-font", "a11y", "warn", STYLE_EXT,
     re.compile(r"font-size:\s*(\d{1,2})px", re.I),
     "Body font below 12px is hard to read. Use >=16px body; reserve small sizes for true labels only.", _font_too_small),
    # --- layout ---
    ("magic-zindex", "layout", "warn", STYLE_EXT,
     re.compile(r"z-index:\s*(\d{3,})", re.I),
     "Magic z-index (>=999) - use a named scale (dropdown<sticky<modal<toast<tooltip), not 999/9999.", _zindex_high),
    ("viewport-height-unit", "layout", "suggest", STYLE_EXT,
     re.compile(r":\s*100vh\b", re.I),
     "100vh overflows under mobile browser chrome. Prefer 100dvh (with a 100vh fallback).", None),
    ("justified-text", "subjective", "suggest", STYLE_EXT,
     re.compile(r"text-align:\s*justify", re.I),
     "Justified text creates uneven 'rivers' on the web without hyphenation. Prefer text-align:start.", None),
]


def iter_files(paths: list[str]) -> list[Path]:
    found: list[Path] = []
    for raw in paths:
        p = Path(raw)
        if p.is_file():
            if p.suffix.lower() in WEB_EXT:
                found.append(p)
            continue
        if p.is_dir():
            for sub in p.rglob("*"):
                if sub.is_file() and sub.suffix.lower() in WEB_EXT:
                    if any(part in IGNORE_DIRS for part in sub.parts):
                        continue
                    if sub.name.endswith((".min.css", ".min.js")):
                        continue
                    found.append(sub)
    return found


def scan_file(path: Path) -> list[Finding]:
    try:
        if path.stat().st_size > MAX_BYTES:
            return []
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return []

    ext = path.suffix.lower()
    fp = str(path)
    out: list[Finding] = []
    lines = text.splitlines()

    # line-regex rules
    for rid, cat, sev, exts, rx, msg, test in LINE_RULES:
        if exts is not None and ext not in exts:
            continue
        for i, line in enumerate(lines, 1):
            if rid == "pure-black-white" and any(
                k in line.lower() for k in ("shadow", "color-mix", "gradient")
            ):
                continue  # #000/#fff inside a shadow, color-mix(), or gradient stop is not a flat surface
            for m in rx.finditer(line):
                if test is not None and not test(m):
                    continue
                out.append(Finding(rid, cat, sev, fp, i, line.strip()[:160], msg))
                break  # one finding per line per rule is enough

    # special: <img> without alt (tag may span lines)
    if ext in MARKUP_EXT:
        for m in re.finditer(r"<img\b[^>]*?>", text, re.I | re.S):
            tag = m.group(0)
            if not re.search(r"\balt\s*=", tag, re.I):
                line_no = text.count("\n", 0, m.start()) + 1
                out.append(Finding("img-no-alt", "a11y", "block", fp, line_no,
                                   tag.strip()[:160],
                                   "<img> without alt (WCAG 1.1.1). Add real alt, or alt=\"\" if purely decorative."))

    # special: outline:none with no :focus-visible anywhere in the file
    if ext in STYLE_EXT:
        mo = re.search(r"outline:\s*(?:none|0)\b", text, re.I)
        if mo and not re.search(r":focus-visible", text, re.I):
            line_no = text.count("\n", 0, mo.start()) + 1
            out.append(Finding("outline-none-no-focus", "a11y", "block", fp, line_no,
                               text[mo.start():mo.start() + 60].splitlines()[0].strip(),
                               "outline removed with no :focus-visible ring in this file (WCAG 2.4.7). Add a visible focus style."))

    # special: glassmorphism by default (many backdrop-blur surfaces)
    if ext in STYLE_EXT:
        blur_hits = [i for i, ln in enumerate(lines, 1)
                     if re.search(r"backdrop-filter:\s*[^;]*blur\(", ln, re.I)]
        if len(blur_hits) > 3:
            out.append(Finding("glassmorphism-default", "cliche", "warn", fp, blur_hits[0],
                               f"{len(blur_hits)} backdrop-blur surfaces",
                               "Glassmorphism used widely (>3 surfaces) reads as default. Make glass a rare, purposeful moment."))

    # special: !important overuse (drift)
    if ext in STYLE_EXT:
        bang = [i for i, ln in enumerate(lines, 1) if "!important" in ln.lower()]
        if len(bang) > 5:
            out.append(Finding("important-overuse", "drift", "suggest", fp, bang[0],
                               f"{len(bang)} !important declarations",
                               "Heavy !important use signals specificity drift. Lean on the token/layer system instead."))

    # special: em-dash overuse in content/copy (AI cadence tell)
    if ext in {".md", ".mdx", ".html", ".htm"}:
        if text.count("—") > 6:
            first = next((i for i, ln in enumerate(lines, 1) if "—" in ln), 1)
            out.append(Finding("em-dash-overuse", "cliche", "suggest", fp, first,
                               f"{text.count(chr(0x2014))} em-dashes",
                               "Heavy em-dash use is an AI cadence tell in prose. Vary sentence structure (see atelier-copy)."))

    # special: hardcoded hex colors in component files (possible token drift)
    if ext in COMPONENT_EXT:
        hexes = [i for i, ln in enumerate(lines, 1) if re.search(r"#[0-9a-fA-F]{3,8}\b", ln)]
        if len(hexes) > 12:
            out.append(Finding("hardcoded-color-drift", "drift", "suggest", fp, hexes[0],
                               f"{len(hexes)} hardcoded hex colors",
                               "Many raw hex colors in a component - likely token drift. Reference atelier-foundations semantic tokens."))

    return out


def main() -> None:
    ap = argparse.ArgumentParser(description="atelier detect - native regex-tier design-tell checker")
    ap.add_argument("paths", nargs="*", default=["."], help="files/dirs to scan (default: cwd)")
    ap.add_argument("--json", action="store_true", help="machine-readable JSON output")
    ap.add_argument("--category", choices=CATEGORIES, help="only this bucket")
    ap.add_argument("--severity", choices=("block", "warn", "suggest"), default="suggest",
                    help="minimum severity to report (default: suggest = everything)")
    ap.add_argument("--quiet", action="store_true", help="print nothing when clean (for the hook)")
    ap.add_argument("--strict", action="store_true", help="exit 2 if any BLOCK finding (for CI)")
    args = ap.parse_args()

    files = iter_files(args.paths or ["."])
    findings: list[Finding] = []
    for f in files:
        findings.extend(scan_file(f))

    min_rank = SEV_RANK[args.severity]
    findings = [f for f in findings if SEV_RANK[f.severity] <= min_rank]
    if args.category:
        findings = [f for f in findings if f.category == args.category]
    findings.sort(key=lambda f: (SEV_RANK[f.severity], f.category, f.file, f.line))

    has_block = any(f.severity == "block" for f in findings)

    if args.json:
        print(json.dumps({
            "scanned": len(files),
            "count": len(findings),
            "blocking": sum(1 for f in findings if f.severity == "block"),
            "findings": [asdict(f) for f in findings],
        }, indent=2, ensure_ascii=False))
    elif not (args.quiet and not findings):
        if not findings:
            print(f"atelier detect: clean ({len(files)} files scanned, regex-tier).")
        else:
            by_sev: dict[str, list[Finding]] = {"block": [], "warn": [], "suggest": []}
            for f in findings:
                by_sev[f.severity].append(f)
            print(f"## atelier detect - {len(findings)} finding(s) across {len(files)} files (regex-tier; "
                  f"verify visual tells in-browser via atelier-review)")
            label = {"block": "BLOCK (real defects)", "warn": "WARN (probable / strong tell)",
                     "suggest": "SUGGEST (low-confidence / taste)"}
            for sev in ("block", "warn", "suggest"):
                group = by_sev[sev]
                if not group:
                    continue
                print(f"\n### {label[sev]} - {len(group)}")
                for f in group:
                    rel = f.file
                    print(f"- [{f.category}/{f.rule}] {rel}:{f.line}\n    {f.message}\n    > {f.snippet}")

    sys.exit(2 if (args.strict and has_block) else 0)


if __name__ == "__main__":
    main()
