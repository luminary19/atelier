# forge-render — Contact Sheet Assembly Reference

## Contents
- §overview. What the contact sheet is and why it matters
- §layout. Canonical layout spec
- §usage. CLI usage for contact_sheet.py
- §pillow. Pillow-based assembly (full pattern)
- §fallback. Graceful degradation (no Pillow)
- §qa-checklist. Visual inspection checklist per cell type
- §size-rules. Size discipline (PNG must be Read-friendly)

---

## §overview. What the contact sheet is and why it matters

The contact sheet is the **single PNG the model reads** to assess an asset's quality in one
visual pass. It tiles: turntable frames + 6-view ortho + diagnostic variants (wireframe,
matcap, normal, UV checker) into a dark-background labelled grid.

The model calls `Read` on this one file. Reading 24 separate PNGs one-by-one is slower and
loses the spatial comparison that a contact sheet enables. The contact sheet is the
render-QA loop's "film strip" — one look, full context.

**Contract:**
- Input: a directory of PNG files, sorted by natural name order
- Output: a single PNG tiled at a fixed cell size, labelled, dark background
- Max cell size: 512×512 px — larger cells bloat the PNG past Read tool usability
- If Pillow is absent: emit a plain-text manifest of all PNG paths instead of crashing

---

## §layout. Canonical layout spec

**Recommended column order:**
```
Row 0+: Turntable frames   (turntable_000_000deg.png, turntable_001_030deg.png, ...)
Row N:  6-view ortho       (6view_front.png, 6view_back.png, 6view_right.png, 6view_left.png, 6view_top.png, 6view_bottom.png)
Row N+1: Diagnostics       (wireframe_030deg.png, matcap_030deg.png, normals_030deg.png, uv_checker_030deg.png)
```

**Cell settings (defaults in contact_sheet.py):**
```python
COLS       = 4        # images per row; increase to 6 for wide sheets
CELL_W     = 512      # px per cell, width
CELL_H     = 512      # px per cell, height
MARGIN     = 8        # gap between cells (px)
LABEL_H    = 22       # label bar height below each image (px)
BG_COLOR   = (30, 30, 30)    # dark grey — max contrast for both light + dark geometry
LABEL_BG   = (50, 50, 50)    # slightly lighter for label bar
LABEL_COLOR = (220, 220, 220) # near-white label text
```

**Total dimensions:**
```python
W = COLS * CELL_W + (COLS + 1) * MARGIN
H = ROWS * (CELL_H + LABEL_H) + (ROWS + 1) * MARGIN
```

---

## §usage. CLI usage for contact_sheet.py

```powershell
# Assemble all PNGs in a directory into a contact sheet
python "$env:CLAUDE_CONFIG_DIR\skills\forge-render\scripts\contact_sheet.py" `
    --input-dir "C:\forge\out\qa" `
    --output    "C:\forge\out\qa_contact_sheet.png" `
    --cols 4 `
    --cell-w 512 `
    --cell-h 512

# --json: output a JSON summary of tiles assembled
python ".../contact_sheet.py" `
    --input-dir "C:\forge\out\qa" --output "C:\forge\out\sheet.png" --json
```

**Staging pattern (multiple input directories):**
```powershell
# Gather all diagnostic PNGs from sub-dirs into a staging folder, then sheet
$staging = "C:\forge\out\_staging"
New-Item -ItemType Directory -Force $staging | Out-Null
Get-ChildItem -Path "C:\forge\out\turntable","C:\forge\out\6view","C:\forge\out\diag" `
    -Filter "*.png" | Copy-Item -Destination $staging
python ".../contact_sheet.py" --input-dir $staging --output "C:\forge\out\qa_sheet.png" --cols 6
```

---

## §pillow. Pillow-based assembly (full pattern)

The full assembly pattern used by `scripts/contact_sheet.py`:

```python
import sys, io, re, math, pathlib, argparse, json

# UTF-8 stdout wrapper
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

def natural_sort_key(s):
    """Sort: turntable_001 < turntable_002 < turntable_010 (not lexicographic)."""
    return [int(t) if t.isdigit() else t.lower()
            for t in re.split(r"(\d+)", str(s))]

def make_contact_sheet(
    input_dir: str,
    output_path: str,
    n_cols: int   = 4,
    cell_w: int   = 512,
    cell_h: int   = 512,
    margin: int   = 8,
    label_h: int  = 22,
) -> dict:
    from PIL import Image, ImageDraw, ImageFont

    pngs = sorted(pathlib.Path(input_dir).glob("*.png"), key=natural_sort_key)
    if not pngs:
        raise FileNotFoundError(f"No PNG files in: {input_dir}")

    n_rows    = math.ceil(len(pngs) / n_cols)
    total_w   = n_cols * cell_w + (n_cols + 1) * margin
    total_h   = n_rows * (cell_h + label_h) + (n_rows + 1) * margin
    BG        = (30, 30, 30)
    LABEL_BG  = (50, 50, 50)
    LABEL_FG  = (220, 220, 220)

    sheet = Image.new("RGB", (total_w, total_h), BG)
    draw  = ImageDraw.Draw(sheet)

    # Font: try Windows monospace, fall back to PIL default
    try:    font = ImageFont.truetype("C:/Windows/Fonts/consola.ttf", 13)
    except Exception: font = ImageFont.load_default()

    for idx, png_path in enumerate(pngs):
        col = idx % n_cols
        row = idx // n_cols
        x   = margin + col * (cell_w + margin)
        y   = margin + row * (cell_h + label_h + margin)

        # Paste thumbnail (center in cell)
        try:
            img = Image.open(png_path).convert("RGB")
            img.thumbnail((cell_w, cell_h), Image.LANCZOS)
            px  = x + (cell_w - img.width)  // 2
            py  = y + (cell_h - img.height) // 2
            sheet.paste(img, (px, py))
        except Exception as e:
            # Magenta error placeholder
            draw.rectangle([x, y, x + cell_w, y + cell_h], fill=(120, 0, 80))
            draw.text((x + 4, y + 4), f"ERR\n{png_path.name[:30]}", font=font, fill=(255,255,255))

        # Label bar below cell
        ly = y + cell_h
        draw.rectangle([x, ly, x + cell_w, ly + label_h], fill=LABEL_BG)
        draw.text((x + 3, ly + 3), png_path.stem[:38], font=font, fill=LABEL_FG)

    out = pathlib.Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(str(out), "PNG", optimize=True)
    summary = {
        "path":   str(out),
        "tiles":  len(pngs),
        "cols":   n_cols,
        "rows":   n_rows,
        "size":   f"{total_w}×{total_h}",
        "names":  [p.name for p in pngs],
    }
    print(f"[forge-render] contact sheet → {out}  ({total_w}×{total_h}px, {len(pngs)} images)")
    return summary
```

---

## §fallback. Graceful degradation (no Pillow)

When Pillow is not installed, `contact_sheet.py` emits a plain-text manifest listing all
PNG paths so the model can still Read them individually:

```python
def make_manifest(input_dir: str, output_path: str) -> dict:
    """Fallback when Pillow is absent: write a text file listing all PNGs."""
    pngs  = sorted(pathlib.Path(input_dir).glob("*.png"), key=natural_sort_key)
    lines = [str(p.resolve()) for p in pngs]
    out   = pathlib.Path(output_path).with_suffix(".txt")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines), encoding="utf-8")
    summary = {"manifest": str(out), "tiles": len(pngs), "names": [p.name for p in pngs]}
    print(f"[forge-render] Pillow not installed — wrote manifest: {out} ({len(pngs)} PNGs)")
    return summary
```

---

## §qa-checklist. Visual inspection checklist per cell type

Use this when the model reads the contact sheet PNG:

**Turntable cells (turntable_*):**
- [ ] Silhouette consistent across all N angles (no sudden pop/crease at any step)
- [ ] Scale appears correct vs brief dimensions
- [ ] No floating geometry (disconnected pieces orbit at wrong speed/position)
- [ ] No unexpected holes in the mesh visible from any angle

**6-view cells (6view_*):**
- [ ] Proportions match brief from all 6 axes
- [ ] No unexpected asymmetry (left ≠ right when symmetry expected)
- [ ] Top/bottom orthographic views show correct footprint

**Wireframe cells (wireframe_*):**
- [ ] Edge density uniform — no dense pole clusters (>6 edges at vertex)
- [ ] No stray floating edges or isolated vertices (appear as disconnected dots)
- [ ] N-gons (irregular polygons) flagged if SDS-bound surface
- [ ] No T-junctions (open edges that don't connect to another face)

**Matcap cells (matcap_*):**
- [ ] Smooth shading gradient across surfaces → correct normals
- [ ] Black patches → inverted normals (run `bmesh.ops.recalc_face_normals`)
- [ ] No sharp creases where smooth should flow → missing smooth/auto-smooth

**Normal RGB cells (normals_*):**
- [ ] Smooth colour gradient across surface → normals consistent
- [ ] Abrupt red-to-cyan reversal → flipped normal on adjacent faces
- [ ] Uniform colour on flat surfaces → correct

**UV checker cells (uv_checker_*):**
- [ ] Checker squares uniform in screen size across surface → even texel density
- [ ] Distorted/elongated squares → UV stretching (>2:1 ratio → re-unwrap)
- [ ] Very small squares → over-scaled UV (wasted texel resolution)
- [ ] Seams at unexpected locations → UV island placement error

---

## §size-rules. Size discipline (PNG must be Read-friendly)

| Rule | Reason |
|---|---|
| Cell size ≤ 512×512 px | Larger cells bloat PNG past Read tool usability (>10 MB) |
| Use `img.thumbnail()` not `img.resize()` | `thumbnail()` preserves aspect ratio; `resize()` distorts portrait images |
| `optimize=True` on `sheet.save()` | Reduces PNG size ~15–30% with no quality loss |
| Max 36 images per sheet (ENFORCED) | `contact_sheet.py --max-per-sheet` (default 36) auto-splits >36 tiles into numbered sheets (`<stem>_01.png`, `<stem>_02.png`, …); `Read` each |
| Label stems ≤ 38 chars | Longer labels overflow the label bar at 13pt monospace |
