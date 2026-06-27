# forge-parametric / references / tolerances-fits.md
# ISO tolerances, fits, FDM clearances, GD&T, fillets, ribs, threads

## Contents
- §1. ISO 286-1 fit table
- §2. FDM print clearances by material
- §3. OpenSCAD ISO fit encoding
- §4. GD&T basics (ASME Y14.5 / ISO 1101)
- §5. Fillets, chamfers, draft angles — design rules
- §6. Ribs, bosses — injection molding rules
- §7. Thread clearances & tap drill diameters
- §8. Snap-fit cantilever beam
- §9. Parametric config → calc → geometry structure
- §10. Validation — geometry checks & tolerance coupon

---

## §1. ISO 286-1 fit table

*Values for nominal diameter range Ø10–18 mm. Verify against full ISO 286 tables for other ranges.*

| ISO Fit Code | Type | Min Clearance | Max Clearance | Typical Use |
|---|---|---|---|---|
| H7/f6 | Clearance | +0.020 mm | +0.054 mm | Easy running, small bearings |
| H7/g6 | Clearance | +0.007 mm | +0.041 mm | Sliding fit, precision bearings |
| H7/h6 | Clearance | 0.000 mm | +0.034 mm | Close sliding, spigot fits |
| H7/k6 | Transition | −0.009 mm | +0.025 mm | Location, dowels |
| H7/p6 | Interference | −0.026 mm | −0.001 mm | Light press fit, pins |
| H7/s6 | Interference | −0.048 mm | −0.023 mm | Heavy press fit, permanent |

**H7 hole:** lower deviation = 0; upper deviation = +IT7.
IT7 by nominal range: Ø6–10 mm → 0.015 mm; Ø10–18 mm → 0.018 mm; Ø18–30 mm → 0.021 mm.

**Shaft deviation by grade (g6 example, Ø6–10 mm):**
- Fundamental deviation (upper) = −0.005 mm
- Tolerance IT6 = 0.009 mm
- Lower deviation = −0.005 − 0.009 = −0.014 mm

GD&T stack additions on top of size tolerance:
```
+0.02–0.05 mm for flatness error
+0.05–0.10 mm for position error
+0.01–0.02 mm for cylindricity
```

---

## §2. FDM print clearances by material (per-side values, 0.4 mm nozzle, 0.2 mm layer)

| Fit Type | PLA | PETG | ABS | TPU |
|---|---|---|---|---|
| Press fit (permanent) | 0.00–0.05 mm | 0.05–0.10 mm | 0.05–0.10 mm | — |
| Snug / interference | 0.05–0.10 mm | 0.10–0.15 mm | 0.10–0.15 mm | — |
| Sliding fit | 0.15–0.20 mm | 0.20–0.25 mm | 0.20–0.25 mm | 0.30 mm |
| Loose rotation | 0.30–0.40 mm | 0.40–0.50 mm | 0.40–0.50 mm | 0.50 mm |
| Heat-set insert pocket | +0.20 mm | +0.25 mm | +0.20 mm | +0.30 mm |
| Snap-fit FDM | 0.50 mm nominal | — | — | — |
| Snap-fit SLA/SLS/MJF | 0.30 mm nominal | — | — | — |

**FDM hole undersizing:** Holes print 0.2–0.4 mm undersized in FDM (perimeter shrinkage).
Model bores 0.2–0.4 mm LARGER than nominal. For a 608 bearing (OD=22 mm), model bore as 22.3 mm.
Always print a two-piece tolerance coupon before full production run.

---

## §3. OpenSCAD ISO fit encoding

```openscad
// Tolerance lookup — shaft deviation for H7 hole basis, Ø6–10 mm range.
// Returns [lower_dev, upper_dev] in mm (relative to nominal shaft diameter).
function iso_fit_shaft_6_10(code) =
    code == "f6" ? [-0.010, -0.022] :   // easy running
    code == "g6" ? [-0.005, -0.014] :   // sliding clearance
    code == "h6" ? [ 0.000, -0.009] :   // close sliding
    code == "k6" ? [+0.001, +0.010] :   // transition location
    code == "p6" ? [+0.010, +0.019] :   // light press
    code == "s6" ? [+0.023, +0.032] :   // heavy press/shrink
    [0, 0];

// H7 hole: lower=0, upper=+IT7=0.015 for Ø6-10mm
H7_lower = 0.000;
H7_upper = 0.015;

// Usage: light press fit, Ø8 nominal
nominal  = 8;
fit      = "p6";
dev      = iso_fit_shaft_6_10(fit);
// Model at nominal shaft (minimum material condition):
shaft_d  = nominal + dev[0];   // 8.010 for p6
hole_d   = nominal + H7_lower; // 8.000 (bore at MMC)
interference_mmc = (nominal + dev[1]) - hole_d;
echo("Interference at MMC:", interference_mmc, "mm");

cylinder(d=shaft_d, h=20, $fn=64);

// Nominal bore in housing (with epsilon for CSG clearance):
eps = 0.001;
difference() {
    cube([30, 30, 20]);
    translate([15, 15, -eps])
        cylinder(d=hole_d, h=20+2*eps, $fn=64);
}
```

---

## §4. GD&T basics (ASME Y14.5 / ISO 1101)

**The 5 GD&T categories:**

| Category | Symbols | Notes |
|---|---|---|
| **Form** | Flatness, Straightness, Circularity, Cylindricity | No datum required |
| **Orientation** | Parallelism, Perpendicularity, Angularity | Datum required |
| **Location** | Position (most used), Concentricity, Symmetry | Datums required |
| **Profile** | Profile of Surface/Line | Complex curve control |
| **Runout** | Circular Runout, Total Runout | Datum axis required |

**Feature Control Frame reading:** `[Symbol | Tolerance | Datum A | Datum B]`
Example: `[⊕ | Ø0.05 | A | B]` = position within Ø0.05 mm zone relative to datums A and B.

**Practical impact on CAD clearances:**
- Flatness error budget: add +0.02–0.05 mm to mating face clearance.
- Position error budget: add +0.05–0.10 mm to hole-pattern clearance.
- Cylindricity budget: add +0.01–0.02 mm to bore diameter.

---

## §5. Fillets, chamfers, draft angles — design rules

```openscad
wall_t = 3.0;   // [mm] nominal wall thickness

// FILLET rules:
// Internal corners (stress risers): ALWAYS fillet, min r = 0.25 × wall_t
// External corners (cosmetic): chamfer preferred (cheaper to machine)
// Boss/rib base: fillet r = 0.25–0.50 × wall_t
internal_min_fillet = wall_t * 0.25;   // 0.75 mm for 3mm wall

// DRAFT ANGLE table (injection molding):
// Smooth surface:       0.5°–1° minimum
// Light texture:        1°–2°
// Deep texture/grain:   3°–5°
// Rib sidewalls:        0.5°–0.75° per side
// Boss OD:              0.5° minimum
draft_smooth  = 1.0;   // [degrees]
draft_texture = 3.0;   // [degrees]

// Tapered wall for injection molding ejection:
module drafted_wall(h, w, draft_deg=1.0) {
    taper = h * tan(draft_deg);
    linear_extrude(height=h, scale=[(w - taper) / w, 1])
        square([w, 50]);
}

// CHAMFER vs FILLET selection:
// Internal: fillet (stress relief)
// External: chamfer (machineable, no radius to mis-match)
// Printability: chamfer on overhangs avoids supports
```

**Rule summary:**
- Internal corners: fillet ≥ 0.25 × wall_t (stress risers → fatigue failure)
- All vertical features: draft ≥ 0.5° per side
- Increase draft by 1° per 25 mm of feature height

---

## §6. Ribs, bosses — injection molding rules

```openscad
wall_t = 3.0;   // nominal wall thickness [mm]

// RIB RULES:
rib_thickness   = wall_t * 0.50;   // 50% of wall — prevents sink marks
rib_height_max  = wall_t * 3.0;    // max 3× wall height
rib_spacing     = wall_t * 2.5;    // min 2.5× wall between ribs
rib_base_fillet = wall_t * 0.25;   // fillet at rib-wall junction
rib_draft       = 0.5;             // degrees per side, minimum

// BOSS RULES:
boss_screw_d    = 5.0;             // e.g. M3 self-tapping
boss_od         = boss_screw_d * 2.0;   // 2× screw OD
boss_wall       = wall_t * 0.60;        // 60% of nominal wall MAX
boss_height_max = boss_od * 3.0;        // max 3× boss OD
boss_base_fillet = wall_t * 0.25;      // base fillet
```

**Check rib tip thickness (must be ≥ 0.8 mm FDM, ≥ 0.5 mm injection molding):**
```python
# In a Python validation script:
import math
rib_base_t = 1.5; rib_height = 9.0; draft_deg = 0.75
tip_t = rib_base_t - 2 * rib_height * math.tan(math.radians(draft_deg))
assert tip_t >= 0.8, f"Rib tip {tip_t:.2f} mm — too thin; reduce height or draft"
```

---

## §7. Thread clearances & tap drill diameters

**Through-hole clearances for bolts (ISO 273):**

| Bolt | Close (H12) | Medium | Free |
|---|---|---|---|
| M3  | Ø3.2 mm | Ø3.4 mm | Ø3.6 mm |
| M4  | Ø4.3 mm | Ø4.5 mm | Ø4.8 mm |
| M5  | Ø5.3 mm | Ø5.5 mm | Ø5.8 mm |
| M6  | Ø6.4 mm | Ø6.6 mm | Ø7.0 mm |
| M8  | Ø8.4 mm | Ø9.0 mm | Ø10.0 mm |
| M10 | Ø10.5 mm | Ø11.0 mm | Ø12.0 mm |

**Tap drill diameter:** nominal_d − pitch
- M3 × 0.5: Ø2.5 mm tap drill
- M4 × 0.7: Ø3.3 mm tap drill
- M5 × 0.8: Ø4.2 mm tap drill
- M6 × 1.0: Ø5.0 mm tap drill
- M8 × 1.25: Ø6.75 mm tap drill
- M10 × 1.5: Ø8.5 mm tap drill

**Boss pilot hole for self-tapping (plastic):**
- M3 self-tap in ABS/PC/POM: Ø2.5 mm
- M4 self-tap in ABS/PC/POM: Ø3.3 mm
- M3 self-tap in soft PE/PP: Ø2.7 mm

**BOSL2 threaded rod (real threads, functional FDM):**
```openscad
include <BOSL2/std.scad>
include <BOSL2/threading.scad>

// ISO M6 × 1.0 mm pitch, 20 mm long:
threaded_rod(d=6, pitch=1.0, l=20, blunt=true, $fn=32);

// M6 nut pocket (internal thread):
difference() {
    cuboid([15, 15, 8]);
    threaded_rod(d=6, pitch=1.0, l=10, internal=true, $fn=32, anchor=TOP);
}
```

**Cosmetic thread (preferred for render/preview):**
```openscad
module cosmetic_thread(d, pitch, length, fn=64) {
    cylinder(d=d, h=length, $fn=fn);
}
```

---

## §8. Snap-fit cantilever beam

```openscad
// Material: PETG, max strain ~3%
beam_l    = 12.0;  // [mm] cantilever length
beam_t    = 1.5;   // [mm] beam thickness at base
taper_tip = 0.8;   // [mm] tip thickness
hook_h    = 1.0;   // [mm] hook protrusion = snap interference depth
beam_w    = 6.0;   // [mm] width

// Max strain check: PETG 3%, ABS 2%, PLA 1.5%
max_strain  = 0.03;    // PETG
// Max deflection: δ = ε × L² / (1.5 × t)
max_deflect = max_strain * beam_l * beam_l / (1.5 * beam_t);
echo("Max deflection:", max_deflect, "mm (hook_h must be <=", max_deflect, ")");
assert(hook_h <= max_deflect, "Hook exceeds max material deflection — reduce hook_h or lengthen beam");

module snap_beam() {
    linear_extrude(height=beam_w)
        polygon([
            [0, 0], [beam_t, 0],
            [taper_tip, beam_l],
            [taper_tip + hook_h, beam_l],
            [taper_tip + hook_h, beam_l + hook_h * 0.7],
            [0, beam_l + hook_h * 0.7]
        ]);
}
rotate([90, 0, 0]) snap_beam();
```

---

## §9. Parametric config → calc → geometry structure

```openscad
// ============================================================
// CONFIG — all user-facing params at top, with units in comments
// ============================================================
/* [Dimensions] */
outer_d      = 30;   // [mm] nominal outer diameter  [10:100]
wall_t       = 2.5;  // [mm] wall thickness          [0.5:0.5:10]
height       = 40;   // [mm] total height            [5:200]
/* [Options] */
has_flange   = true;
flange_style = "round";  // [round, square, hex]
/* [Hidden] */
_fn  = 64;    // render quality
_eps = 0.01;  // boolean overshoot epsilon [mm]

// ============================================================
// CALC — derived from config, used everywhere below
// ============================================================
inner_d = outer_d - 2 * wall_t;
assert(inner_d > 0, str("wall_t too thick: inner_d=", inner_d));
base_r  = outer_d * 0.25;   // base fillet radius

// ============================================================
// GEOMETRY — modules only use CALC values
// ============================================================
module main_body() {
    difference() {
        cylinder(d=outer_d, h=height, $fn=_fn);
        translate([0, 0, wall_t])
            cylinder(d=inner_d, h=height, $fn=_fn);
    }
}

main_body();
```

---

## §10. Validation — geometry checks & tolerance coupon

**OpenSCAD geometry summary (nightly):**
```powershell
& "C:\Tools\OpenSCAD-nightly\openscad.com" `
    --render --summary all --summary-file summary.json `
    --backend=Manifold -o out.stl model.scad
$s = Get-Content summary.json | ConvertFrom-Json
$vol = $s.geometry.volume
if ($vol -lt 100) { Write-Error "Volume too small: $vol mm3" }
$bb = $s.geometry."bounding-box"
Write-Host "BBox min: $($bb.min)  max: $($bb.max)"
```

**build123d inline validation:**
```python
from build123d import *
part = ...    # your part
assert part.is_valid,  "Solid is topologically invalid"
assert part.volume > 0, f"Volume is zero: {part.volume}"
bb = part.bounding_box()
assert bb.size.X > 0 and bb.size.Y > 0 and bb.size.Z > 0
```

**Tolerance coupon (always print before production):**
```openscad
// tolerance_coupon.scad — calibrate printer clearances for a material
wall = 3;
test_diams = [4.8, 5.0, 5.2, 5.4, 5.6];   // 5 mm nominal, 5 variants

for (i = [0:len(test_diams)-1]) {
    translate([i * 20, 0, 0])
    difference() {
        cylinder(d=wall*2 + test_diams[i], h=wall*2, $fn=32);
        cylinder(d=test_diams[i],          h=wall*2 + 1, $fn=32);
    }
}
```
```powershell
& "C:\Tools\OpenSCAD-nightly\openscad.com" `
    --backend=Manifold -o tolerance_coupon.stl tolerance_coupon.scad
```
Print, measure actual bore with calipers, compute compensation = (nominal − actual).
Apply to `fdm_bore_comp` in subsequent models for that material/printer combination.
