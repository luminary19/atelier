# forge-light — Lighting Presets & Aesthetic Mapping
# Map ATELIER.md world/aesthetic to lighting parameters

## Contents
- §1. Aesthetic → lighting parameter mapping
- §2. Named preset quick-reference
- §3. Lighting mood vocabulary

---

## §1. Aesthetic → lighting parameter mapping

When `ATELIER.md` is present, its `world` or `aesthetic` field drives lighting choices.

| Atelier aesthetic / world | Rig | Key energy | fill_ratio | rim_ratio | HDRI strength | Color temp K | Notes |
|---|---|---|---|---|---|---|---|
| `award-grade / editorial` | Three-point | 1500–2000 W | 0.15–0.20 | 0.80–1.0 | 0.4–0.6 | 5500–6500 | Hard shadows, strong rim for drama |
| `production / commercial` | Three-point | 800–1200 W | 0.35 | 0.60 | 0.8–1.0 | 5500 | Classic packshot ratios |
| `e-commerce / bright` | Three-point | 600–1000 W | 0.50–0.60 | 0.30 | 1.2–1.5 | 5000–5500 | High-key, minimal shadow |
| `luxury / jewellery` | Three-point + kicker | 2000–3000 W | 0.25 | 0.70 | 0.6–0.8 | 4500–5500 | Tight key, 4K HDRI, caustics 512+ samples |
| `industrial / matte` | IBL only | — | — | — | 1.0 | — | Diffuse read; no specular distractions |
| `dark / moody` | Three-point | 1000–1500 W | 0.10–0.15 | 0.90 | 0.3–0.4 | 4000–5000 | Low fill, heavy rim for contrast |
| `warm / lifestyle` | Three-point | 800 W | 0.40 | 0.50 | 1.0 | 3200–4500 | Warm key + fill color temps |
| `cool / tech` | Three-point + IBL | 1000 W | 0.30 | 0.65 | 0.8 | 6500–8000 | Cooler keys, minimal color cast |
| `neutral / catalog` | IBL + kicker | — | — | — | 0.8–1.0 | 5500 | Turntable rig (see turntable-catalog.md) |

---

## §2. Named preset quick-reference

### "Studio Classic" — packshot standard

```
Rig:             Three-point area lights
Key:             1000 W, 5500K, SQUARE, radius×1.5, 45° left, 30° elev
Fill:            350 W, 5700K, SQUARE×1.8, opposite, 20° elev
Rim:             600 W, pure white, SQUARE×0.8, behind, 60° elev
HDRI:            studio_small_09 @ 2K, strength 0.8 (fill only, hide_background=True)
Shadow catcher:  yes, transparent bg
Color mgmt:      AgX, look "None", exposure 0.0
Samples:         256, OPENIMAGEDENOISE
```

### "Hero Shot" — editorial product

```
Rig:             Three-point, dramatic ratios
Key:             2000 W, 6000K, RECTANGLE (3:1), tight softbox
Fill:            200 W, 5800K, large panel (fill_ratio=0.10)
Rim:             1600 W, white-blue (0.8,0.9,1.0), narrow DISK (rim_ratio=0.80)
HDRI:            none (or minimal 0.3 strength for bounce fill)
Shadow catcher:  yes
Color mgmt:      AgX, look "High Contrast", exposure -0.3
Samples:         512+
```

### "Jewelry Close-Up"

```
Rig:             Three-point + two kickers
Key:             3000 W, 4500K, DISK, radius×0.6 (tight for facet definition)
Fill:            600 W, 4500K, large RECTANGLE (fill_ratio=0.20)
Rim:             2400 W, pure white (rim_ratio=0.80)
Kicker 1:        1500 W, top, small DISK
Kicker 2:        1500 W, side, small DISK
HDRI:            4K–8K HDRI for gem caustics
Shadow catcher:  yes, transparent bg
Color mgmt:      AgX, look "None", exposure 0.5
Samples:         1024, OPENIMAGEDENOISE
```

### "E-commerce White Background"

```
Rig:             High-key three-point
Key:             800 W, 5200K, large RECTANGLE (fill_ratio=0.55)
Fill:            440 W, 5400K, large RECTANGLE
Rim:             240 W (rim_ratio=0.30) — subtle
Background:      Cyclorama, pure white (1,1,1), fully rough
Color mgmt:      AgX, look "None", exposure 0.3
Samples:         128–256 (fast; diffuse product)
```

### "Material QA Turntable"

```
Rig:             IBL + kicker (catalog rig)
HDRI:            studio_small_09 @ 2K, strength 0.8
Kicker:          500 W, tight DISK at 45° front-right
Color mgmt:      AgX, look "None", exposure 0.0
Samples:         128 (QA iteration speed), OPENIMAGEDENOISE
Animation:       72 frames, 24fps, 5°/frame
```

---

## §3. Lighting mood vocabulary

| Term | Meaning | Control |
|---|---|---|
| High-key | Bright, minimal shadows, fill-dominant | fill_ratio > 0.50, high HDRI strength |
| Low-key | Dark, strong shadows, key-dominant | fill_ratio < 0.15, low HDRI strength |
| Hard light | Crisp shadows, small source relative to subject | Small area size (size_m / radius ratio < 0.5) |
| Soft light | Diffuse shadows, large source relative to subject | Large area size (ratio > 2.0) |
| Rim / edge light | Bright outline of subject, separation from background | High rim_ratio (0.7+), narrow size |
| Kicker | Small accent light for specular pop | Small DISK or SQUARE, high energy, tight aim |
| Wrap | Light wraps around subject, fills shadows from many angles | HDRI IBL dominant, large fill panel |
| Specular peak | Bright specular highlight spot | Small source, high energy, precise aim |
| Color contrast | Warm key / cool fill (or inverse) | Different `color_temp_k` for key vs fill |

### Dynamic range guide

| Fill ratio | Shadow EV ratio | Style |
|---|---|---|
| 0.50 | ~1 EV | Flat/commercial (high-key) |
| 0.35 | ~1.5 EV | Packshot standard |
| 0.25 | ~2 EV | Moderate contrast |
| 0.15 | ~2.7 EV | Dramatic product |
| 0.08 | ~3.6 EV | Dark/editorial |
| 0.03 | ~5 EV | Very dark/noir |
