"""
forge-render/scripts/contact_sheet.py
Assembles a directory of PNG files into a single labelled contact-sheet PNG.

Usage (system Python, NOT Blender's embedded Python):
    python contact_sheet.py --input-dir DIR --output PATH [OPTIONS]

Options:
    --input-dir DIR      Directory containing PNG files to tile
    --output PATH        Output PNG path (created with parent dirs if needed)
    --cols N             Images per row (default: 4)
    --cell-w W           Cell width in pixels (default: 512; max recommended: 512)
    --cell-h H           Cell height in pixels (default: 512)
    --margin N           Gap between cells in pixels (default: 8)
    --max-per-sheet N    Max tiles per sheet (default: 36). More → split into
                         numbered sheets (sheet_01.png, sheet_02.png, …) so each
                         stays small enough for the Read tool to inspect.
    --json               Emit JSON summary to stdout instead of human-readable log
    --no-labels          Omit filename labels below each cell

Behaviour:
    - PNGs are sorted in natural/numeric order (turntable_001 < turntable_002 < turntable_010)
    - Pillow (PIL) is used if installed; degrades gracefully to a text manifest if absent
    - Missing/corrupt PNGs are shown as magenta placeholder cells, not as crashes
    - cell size is thumbnailed (not cropped) to preserve aspect ratio
    - optimize=True is set on save to keep output PNG size manageable

Platform: Windows 11 native (python, not python3; UTF-8 stdout wrapper at top).
"""

import sys
import io
import re
import math
import json
import pathlib
import argparse

# UTF-8 stdout wrapper (Windows cp1252 default)
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Argument parsing
# ─────────────────────────────────────────────────────────────────────────────

def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description="forge-render contact sheet assembler",
    )
    p.add_argument("--input-dir",  required=True, help="Directory of PNG files to tile")
    p.add_argument("--output",     required=True, help="Output PNG path")
    p.add_argument("--cols",       type=int, default=4,   help="Images per row (default: 4)")
    p.add_argument("--cell-w",     type=int, default=512, help="Cell width px (default: 512)")
    p.add_argument("--cell-h",     type=int, default=512, help="Cell height px (default: 512)")
    p.add_argument("--margin",     type=int, default=8,   help="Gap between cells px (default: 8)")
    p.add_argument("--max-per-sheet", type=int, default=36,
                   help="Max tiles per sheet; more splits into numbered sheets (default: 36)")
    p.add_argument("--json",       action="store_true",   help="Emit JSON summary to stdout")
    p.add_argument("--no-labels",  action="store_true",   help="Omit filename labels")
    return p.parse_args()


# ─────────────────────────────────────────────────────────────────────────────
# Sorting
# ─────────────────────────────────────────────────────────────────────────────

def natural_sort_key(s):
    """Natural/numeric sort: turntable_001 < turntable_002 < turntable_010."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", str(s))]


# ─────────────────────────────────────────────────────────────────────────────
# Contact sheet assembly (requires Pillow)
# ─────────────────────────────────────────────────────────────────────────────

def make_contact_sheet(
    pngs: list,
    output_path: str,
    n_cols: int   = 4,
    cell_w: int   = 512,
    cell_h: int   = 512,
    margin: int   = 8,
    show_labels: bool = True,
) -> dict:
    """
    Assemble pngs into a contact sheet using Pillow.
    Returns a summary dict.
    """
    from PIL import Image, ImageDraw, ImageFont  # noqa: PLC0415

    LABEL_H   = 22 if show_labels else 0
    BG        = (30, 30, 30)
    LABEL_BG  = (50, 50, 50)
    LABEL_FG  = (220, 220, 220)
    ERR_BG    = (120, 0, 80)   # magenta for missing/corrupt files

    n_rows  = math.ceil(len(pngs) / n_cols)
    total_w = n_cols * cell_w + (n_cols + 1) * margin
    total_h = n_rows * (cell_h + LABEL_H) + (n_rows + 1) * margin

    sheet = Image.new("RGB", (total_w, total_h), BG)
    draw  = ImageDraw.Draw(sheet)

    # Font: prefer Windows Consolas; degrade to PIL built-in
    try:
        font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
    except Exception:
        font = ImageFont.load_default()

    for idx, png_path in enumerate(pngs):
        col = idx % n_cols
        row = idx // n_cols
        x   = margin + col * (cell_w + margin)
        y   = margin + row * (cell_h + LABEL_H + margin)

        # Paste thumbnail (centered in cell, preserving aspect ratio)
        try:
            img = Image.open(png_path).convert("RGB")
            img.thumbnail((cell_w, cell_h), Image.LANCZOS)
            paste_x = x + (cell_w - img.width)  // 2
            paste_y = y + (cell_h - img.height) // 2
            sheet.paste(img, (paste_x, paste_y))
        except Exception as exc:
            # Magenta error placeholder — do not crash the whole sheet
            draw.rectangle([x, y, x + cell_w, y + cell_h], fill=ERR_BG)
            err_msg = f"ERR: {pathlib.Path(png_path).name[:28]}\n{str(exc)[:40]}"
            draw.text((x + 4, y + 4), err_msg, font=font, fill=(255, 200, 200))

        # Label bar below cell
        if show_labels:
            ly = y + cell_h
            draw.rectangle([x, ly, x + cell_w, ly + LABEL_H], fill=LABEL_BG)
            label = pathlib.Path(png_path).stem[:38]
            draw.text((x + 3, ly + 3), label, font=font, fill=LABEL_FG)

    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out), "PNG", optimize=True)

    summary = {
        "path":    str(out),
        "tiles":   len(pngs),
        "cols":    n_cols,
        "rows":    n_rows,
        "size_px": f"{total_w}x{total_h}",
        "names":   [pathlib.Path(p).name for p in pngs],
    }
    print(f"[forge-render] contact sheet → {out}  ({total_w}×{total_h}px, {len(pngs)} images)")
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Fallback: plain-text manifest (Pillow not installed)
# ─────────────────────────────────────────────────────────────────────────────

def make_manifest(pngs: list, output_path: str) -> dict:
    """
    Fallback when Pillow is absent.
    Writes a UTF-8 text file listing resolved PNG paths, one per line.
    """
    lines = [str(pathlib.Path(p).resolve()) for p in pngs]
    out   = pathlib.Path(output_path).with_suffix(".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    summary = {
        "manifest": str(out),
        "tiles":    len(pngs),
        "note":     "Pillow not installed; install with: pip install Pillow",
        "names":    [pathlib.Path(p).name for p in pngs],
    }
    print(f"[forge-render] Pillow not installed — manifest written: {out} ({len(pngs)} PNGs)")
    print("[forge-render] Install Pillow: pip install Pillow")
    return summary


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main() -> None:
    args = parse_args()

    # Collect PNGs in natural sort order
    input_dir = pathlib.Path(args.input_dir)
    if not input_dir.is_dir():
        print(f"[forge-render] ERROR: --input-dir not found: {input_dir}", file=sys.stderr)
        sys.exit(1)

    pngs = sorted(input_dir.glob("*.png"), key=natural_sort_key)
    if not pngs:
        print(f"[forge-render] WARNING: No PNG files found in: {input_dir}", file=sys.stderr)
        summary = {"path": args.output, "tiles": 0, "names": []}
        if args.json:
            print(json.dumps(summary, indent=2))
        sys.exit(0)

    png_strs = [str(p) for p in pngs]
    max_per  = max(1, args.max_per_sheet)

    # Attempt Pillow assembly; fall back to manifest
    try:
        import PIL  # noqa: F401
        if len(png_strs) <= max_per:
            summary = make_contact_sheet(
                pngs=png_strs,
                output_path=args.output,
                n_cols=args.cols,
                cell_w=args.cell_w,
                cell_h=args.cell_h,
                margin=args.margin,
                show_labels=not args.no_labels,
            )
        else:
            # Enforced cap: split into numbered sheets so each stays Read-friendly.
            out_base = pathlib.Path(args.output)
            stem, suffix = out_base.stem, (out_base.suffix or ".png")
            chunks = [png_strs[i:i + max_per] for i in range(0, len(png_strs), max_per)]
            sheets = []
            print(f"[forge-render] {len(png_strs)} images > {max_per} cap — "
                  f"split into {len(chunks)} sheets")
            for n, chunk in enumerate(chunks, start=1):
                sheet_path = str(out_base.with_name(f"{stem}_{n:02d}{suffix}"))
                s = make_contact_sheet(
                    pngs=chunk,
                    output_path=sheet_path,
                    n_cols=args.cols,
                    cell_w=args.cell_w,
                    cell_h=args.cell_h,
                    margin=args.margin,
                    show_labels=not args.no_labels,
                )
                sheets.append(s)
            summary = {
                "sheets":   [s["path"] for s in sheets],
                "n_sheets": len(sheets),
                "tiles":    len(png_strs),
                "max_per_sheet": max_per,
                "per_sheet": sheets,
            }
    except ImportError:
        summary = make_manifest(png_strs, args.output)

    # Validate output(s) exist and are non-trivially small
    out_paths = summary.get("sheets") or [summary.get("path", args.output)]
    for op in out_paths:
        out_path = pathlib.Path(op)
        if out_path.exists():
            size_kb = round(out_path.stat().st_size / 1024, 1)
            if size_kb < 1:
                print(f"[forge-render] WARN: output suspiciously small: {size_kb} KB → {out_path}",
                      file=sys.stderr)
            else:
                print(f"[forge-render] Output: {out_path}  ({size_kb} KB)")
        else:
            # manifest .txt case
            manifest_path = pathlib.Path(summary.get("manifest", ""))
            if manifest_path.exists():
                print(f"[forge-render] Manifest: {manifest_path}")

    if args.json:
        print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    try:
        main()
    except SystemExit:
        raise
    except Exception as exc:
        # Advisory: never crash hard so the QA pipeline can continue
        print(f"[forge-render] contact_sheet.py error: {exc}", file=sys.stderr)
        import traceback; traceback.print_exc(file=sys.stderr)
        sys.exit(0)   # exit 0 so pipeline does not halt on a sheet-assembly failure
