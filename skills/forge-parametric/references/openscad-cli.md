# forge-parametric / references / openscad-cli.md
# OpenSCAD — headless CLI, language patterns, BOSL2, resolution, render verification

## Contents
- §1. Windows install & PATH
- §2. Key executables (always use `.com`, not `.exe`)
- §3. Headless CLI — canonical Forge invocations
- §4. OpenSCAD language — modules, functions, CSG
- §5. Special variables — resolution control
- §6. Customizer / JSON parameter sets
- §7. BOSL2 — rounding, attachment, threads, skin
- §8. Render-verification snippet
- §9. Performance rules
- §10. Visual failure diagnosis (after Read-ing the PNG)
- §11. Gotcha → fix table

---

## §1. Windows install & PATH

**Stable (2021.01) — winget:**
```powershell
winget install --id=OpenSCAD.OpenSCAD -e
# Installs to: C:\Program Files\OpenSCAD\
```

**Nightly (2025.xx — RECOMMENDED for Forge):** download 64-bit zip from
`https://files.openscad.org/` and extract to `C:\Tools\OpenSCAD-nightly\`.
Nightly adds: `--backend=Manifold` (8–30x faster than CGAL), multiple `-o` flags,
`--summary-file` JSON output, `--enable lazy-union`.

```powershell
# Session PATH (add to $PROFILE for persistence):
$env:PATH = "C:\Program Files\OpenSCAD;$env:PATH"
# Or for nightly:
$env:PATH = "C:\Tools\OpenSCAD-nightly;$env:PATH"
```

**BOSL2 install:**
```powershell
$lib = "$env:USERPROFILE\Documents\OpenSCAD\libraries"
New-Item -ItemType Directory -Force -Path $lib | Out-Null
git clone https://github.com/BelfrySCAD/BOSL2.git "$lib\BOSL2"
# OPENSCADPATH must point to PARENT of BOSL2 folder:
[System.Environment]::SetEnvironmentVariable("OPENSCADPATH", $lib, "User")
```

---

## §2. Key executables — ALWAYS `openscad.com`, not `openscad.exe`

| File | Purpose |
|---|---|
| `openscad.exe` | GUI binary; detaches from console — **never use from PS/cmd** |
| `openscad.com` | CLI wrapper; routes stdout/stderr to console. **Always use this.** |

**Verify install:**
```powershell
& "C:\Program Files\OpenSCAD\openscad.com" --version
# Output: OpenSCAD version 2021.01  (or 2025.xx for nightly)
```

**Library path check:**
```powershell
& "C:\Program Files\OpenSCAD\openscad.com" --info 2>&1 | Select-String "library"
```

---

## §3. Headless CLI — canonical Forge invocations

```powershell
# Minimal STL export (ASCII):
& "C:\Program Files\OpenSCAD\openscad.com" -o "out.stl" "model.scad"

# Binary STL (smaller — explicit flag needed):
& "C:\Program Files\OpenSCAD\openscad.com" --export-format binstl -o "out.stl" "model.scad"

# 3MF (preferred for modern slicers — preserves units, color, metadata):
& "C:\Program Files\OpenSCAD\openscad.com" -o "out.3mf" "model.scad"

# Nightly with Manifold backend (8-30x faster):
& "C:\Tools\OpenSCAD-nightly\openscad.com" --backend=Manifold -o "out.stl" "model.scad"

# PNG verification render — FAST preview (no CGAL; use for geometry check):
& "C:\Program Files\OpenSCAD\openscad.com" `
    -o "preview.png" `
    --imgsize=1920,1080 `
    --camera=0,0,0,55,0,25,200 `
    --projection=perspective `
    --colorscheme=Cornfield `
    --autocenter --viewall `
    "model.scad"

# PNG render — FULL geometry (CGAL/Manifold; use for final sign-off only):
& "C:\Program Files\OpenSCAD\openscad.com" `
    -o "render.png" --render `
    --imgsize=1920,1080 --camera=0,0,0,55,0,25,200 `
    --autocenter --viewall "model.scad"

# Override parameters at CLI (-D):
& "C:\Program Files\OpenSCAD\openscad.com" `
    -D "wall_thickness=2.5" -D "height=40" -o "out.stl" "model.scad"

# String parameter (double-double-quote in PowerShell):
& "C:\Program Files\OpenSCAD\openscad.com" `
    -D "material=""pla""" -o "out.stl" "model.scad"

# Use JSON customizer parameter set:
& "C:\Program Files\OpenSCAD\openscad.com" `
    -p "params.json" -P "large_variant" -o "out_large.stl" "model.scad"

# Geometry summary JSON (bounding box, volume, render time):
& "C:\Tools\OpenSCAD-nightly\openscad.com" `
    --render --summary all --summary-file summary.json -o out.stl model.scad
$s = Get-Content summary.json | ConvertFrom-Json
Write-Host "Volume: $($s.geometry.volume) mm3; BBox: $($s.geometry.'bounding-box')"

# Batch — design family from PowerShell:
@(10, 20, 30, 40, 50) | ForEach-Object {
    & "C:\Program Files\OpenSCAD\openscad.com" `
        -o "tube_L$_.stl" -D "length=$_" --backend=Manifold tube.scad
}

# Render STL to PNG (wrap in temp .scad — OpenSCAD cannot import STL as direct input to CLI):
$tmp = [System.IO.Path]::GetTempFileName() + ".scad"
"import(""C:/abs/path/part.stl"");" | Set-Content $tmp
& "C:\Program Files\OpenSCAD\openscad.com" -o preview.png --autocenter --viewall $tmp
Remove-Item $tmp
```

**Camera formats:**
- Gimbal: `--camera=tx,ty,tz,rx,ry,rz,distance` — `55,0,25` rotation gives pleasing 3/4 view
- Vector: `--camera=ex,ey,ez,cx,cy,cz`

**Three-view verification:**
```powershell
$cameras = @{ iso="0,0,0,55,0,25,150"; top="0,0,0,90,0,0,150"; front="0,0,0,0,0,0,150" }
$cameras.GetEnumerator() | ForEach-Object {
    $view = $_.Key; $cam = $_.Value
    $png = "verify_${view}.png"
    & "C:\Tools\OpenSCAD-nightly\openscad.com" `
        -o $png --imgsize=800,600 --camera=$cam --autocenter --viewall model.scad 2>&1
    $sz = (Get-Item $png -ErrorAction SilentlyContinue).Length
    if ($sz -lt 10240) { Write-Error "Blank render for $view view ($sz bytes)" }
    else { Write-Host "$view OK: $sz bytes" }
}
```

---

## §4. OpenSCAD language — modules, functions, CSG

```openscad
// ── FUNCTION: returns a value ─────────────────────────────────────────────────
function chamfer_offset(r, angle=45) = r / tan(angle);
function linspace(start, stop, n) =
    [for (i = [0 : n-1]) start + i * (stop - start) / (n - 1)];

// ── MODULE: performs geometry, no return ──────────────────────────────────────
module rounded_box(size=[10,10,10], r=1, $fn=32) {
    x = size[0]; y = size[1]; z = size[2];
    hull() {
        for (dx = [-1, 1], dy = [-1, 1], dz = [-1, 1])
            translate([dx*(x/2-r), dy*(y/2-r), dz*(z/2-r)])
                sphere(r=r, $fn=$fn);
    }
}
rounded_box([30, 20, 15], r=2);

// ── CSG OPERATIONS ────────────────────────────────────────────────────────────
union()        { cube([20,20,5]); cylinder(h=30,r=5,center=true,$fn=32); }
difference()   { cube([30,30,10]); translate([15,15,-1]) cylinder(h=12,r=5,$fn=32); }
intersection() { cube([20,20,20],center=true); sphere(r=14,$fn=48); }

// Hull for rounded box transition:
hull() {
    translate([0,  0, 0]) sphere(r=3,$fn=16);
    translate([30, 0, 0]) sphere(r=3,$fn=16);
    translate([15,20, 0]) sphere(r=3,$fn=16);
}

// ── CUTTING TOOL OVERSHOOT (mandatory) ────────────────────────────────────────
// Zero-thickness faces cause CGAL degenerate errors and Manifold silent failure.
epsilon = 0.01;
difference() {
    cube([20, 20, 10]);
    translate([10, 10, -epsilon])
        cylinder(h = 10 + 2*epsilon, r=3, $fn=32);
}

// ── TRANSFORMS ────────────────────────────────────────────────────────────────
translate([x, y, z]) child();
rotate([rx, ry, rz]) child();           // ZYX Euler, degrees
rotate(a=45, v=[1,1,0]) child();        // axis-angle
scale([sx, sy, sz]) child();
mirror([1, 0, 0]) child();

// ── LINEAR EXTRUDE ────────────────────────────────────────────────────────────
linear_extrude(height=20, center=false, convexity=10, twist=90, scale=[1.5,1], slices=20) {
    circle(r=10, $fn=6);
}

// ── ROTATE EXTRUDE ────────────────────────────────────────────────────────────
rotate_extrude(angle=270, convexity=4, $fn=64) {
    translate([15, 0]) square([5, 3]);
}

// ── SCOPE / VARIABLE RULES ────────────────────────────────────────────────────
// Variables are SINGLE-ASSIGNMENT per scope. Last assignment at parse time WINS.
// Use let() or functions for computed intermediates, never re-assign inside loops.
// CORRECT:
values = [for (i = [0:5]) i * 2];
// WRONG (count never increments):
// for (i=[0:5]) { count = count + 1; }
```

---

## §5. Special variables — resolution control

```openscad
// $fn=0 (default): OpenSCAD uses $fa and $fs together.
// $fn>0: override — use exactly this many facets.
$fn = 0;   // adaptive (default)
$fa = 4;   // min angle per fragment (4° → max 90 sides)
$fs = 0.5; // min fragment size (0.5mm)

// Preview vs. final:
$fn = $preview ? 16 : 64;  // $preview=true only in F5 interactive
// For headless: $preview is always false even with --preview flag.
// Use a custom variable for headless quality toggle:
quality_mode = "draft";  // override with -D quality_mode=\"final\"
$fn = (quality_mode == "final") ? 128 : 32;
```

| Context | Setting | Rationale |
|---|---|---|
| Dev / preview | `$fn=0; $fa=6; $fs=1` | Fast, ~60 sides max |
| Final FDM | `$fn=0; $fa=2; $fs=0.4` | Matches 0.4mm nozzle |
| SLA / fine detail | `$fn=0; $fa=1; $fs=0.1` | SLA resolves 0.05mm |
| Explicit round | `$fn=32` / `$fn=128` | Per-object override |

**Do NOT use global `$fn=128`** — every loop iteration recomputes at high res, exploding CSG tree size.

---

## §6. Customizer / JSON parameter sets

```openscad
/* [Dimensions] */
outer_d = 30;    // [10:100]
wall_t  = 2.5;   // [0.5:0.5:10]
height  = 40;    // [5:200]
/* [Options] */
has_flange = true;
flange_style = "round"; // [round, square, hex]
/* [Hidden] */
_fn = 64;
```

```json
// params.json
{
  "parameterSets": {
    "small": { "outer_d": "20", "wall_t": "1.5", "height": "25" },
    "large": { "outer_d": "50", "wall_t": "3",   "height": "80" }
  },
  "fileFormatVersion": "1"
}
```

```powershell
@("small", "large") | ForEach-Object {
    & "C:\Program Files\OpenSCAD\openscad.com" -p params.json -P $_ -o "tube_$_.stl" params.scad
}
```

**Gotcha:** `-D var=val` CANNOT override a value already set by `-p/-P`. To work around, declare a
proxy variable in the `.scad`: `_cpart = cpart;` then pass `-D _cpart=2`.

---

## §7. BOSL2 — rounding, attachment, threads, skin

```openscad
include <BOSL2/std.scad>  // ALWAYS include, not use — BOSL2 needs special vars at parse time

// ── ROUNDING ─────────────────────────────────────────────────────────────────
cuboid([60, 40, 20], rounding=3);                          // all edges
cuboid([60, 40, 20], rounding=3, edges=TOP, chamfer=2, chamfer_edges=BOTTOM);

// Fillet bottom, roundover top:
diff()
    cuboid([50, 60, 70], rounding=-10, edges=BOT)
        edge_profile(TOP) mask2d_roundover(r=10);

// ── ATTACHMENT ────────────────────────────────────────────────────────────────
cuboid([40, 40, 20]) {
    attach(TOP)           cyl(h=15, d=10, $fn=32);
    attach(RIGHT, BOTTOM) cuboid([10, 10, 5]);
}

// ── DIFF / TAG PATTERN ────────────────────────────────────────────────────────
diff()
    cuboid([50, 50, 30]) {
        tag("remove") cuboid([30, 10, 35], rounding=2, edges=Z);
        tag("remove") attach(FRONT) cyl(h=15, d=12, $fn=32);
    }

// ── THREADS ──────────────────────────────────────────────────────────────────
include <BOSL2/threading.scad>
// M6 threaded rod, 20mm long:
threaded_rod(d=6, pitch=1, l=20, blunt=true, $fn=32);
// M6 nut pocket (internal thread):
difference() {
    cuboid([15, 15, 8]);
    threaded_rod(d=6, pitch=1, l=10, internal=true, $fn=32, anchor=TOP);
}

// ── PATH_SWEEP ────────────────────────────────────────────────────────────────
path = concat(arc(r=20, angle=[0,90]), [[20+i, 20, i/2] for i=[0:10]]);
path_sweep(circle(r=3, $fn=16), path3d(path));

// ── SKIN ──────────────────────────────────────────────────────────────────────
skin([
    path3d(square([20,10], center=true), 0),
    path3d(square([15, 8], center=true), 10),
    path3d(circle(r=5, $fn=32),          20),
    path3d(circle(r=3, $fn=32),          30),
], slices=3);
```

**BOSL2 gotcha:** ALWAYS `include <BOSL2/std.scad>`, never `use <BOSL2/std.scad>`.
Using `use` drops special variables (`$anchor_override` etc.) from scope, producing empty geometry.

---

## §8. Render-verification snippet (PowerShell function)

```powershell
function Invoke-OpenSCADVerify {
    param(
        [string]$ScadFile,
        [string]$PngOut   = "verify.png",
        [string]$OpenSCAD = "C:\Program Files\OpenSCAD\openscad.com"
    )
    $result = & $OpenSCAD `
        -o $PngOut --imgsize=800,600 `
        --autocenter --viewall --colorscheme=Cornfield `
        --camera=0,0,0,55,0,25,150 `
        $ScadFile 2>&1
    if ($LASTEXITCODE -ne 0) {
        Write-Error "OpenSCAD exited $LASTEXITCODE: $result"; return $false
    }
    $size = (Get-Item $PngOut -ErrorAction SilentlyContinue).Length
    if (-not $size -or $size -lt 10240) {
        Write-Error "PNG too small ($size bytes) — blank render. Check geometry."; return $false
    }
    Write-Host "OK: $PngOut ($size bytes)"
    return $true
}
Invoke-OpenSCADVerify -ScadFile "model.scad" -PngOut "verify.png"
```

After running: call `Read("C:/abs/path/verify.png")` to visually inspect the output.

---

## §9. Performance rules

1. **Use `--preview` (no `--render`)** for PNG verification — skips full CSG evaluation.
2. **Use Manifold backend** (nightly): `--backend=Manifold`.
3. **Minimize `minkowski()`** — it is O(V_a × V_b). Keep `$fn ≤ 16` for the kernel shape.
   Use BOSL2 `cuboid(..., rounding=R)` instead.
4. **`render()` to cache expensive sub-trees:**
   ```openscad
   module expensive_base() { render(convexity=4) difference() { /* CSG */ } }
   ```
5. Enable `--enable lazy-union` (nightly experimental) for further speedup.

---

## §10. Visual failure diagnosis (after Read-ing the PNG)

Once the verify PNG passes the > 10 KB size check and you `Read` it, map what you see to a cause
and fix. (The blank-PNG / CGAL cases also appear in §11; this table reads the *rendered geometry*.)

| What you see | Cause | Fix |
|-------------|-------|-----|
| Part missing / empty frame | CGAL degenerate from a coplanar or zero-thickness face | Add 0.01 mm epsilon overshoot to every cutter (§4) — extend past both faces |
| Hole didn't cut through | Cutter not extended past both faces (flush with surface) | Extend the cutter by `2*eps` (start at `-eps`, height `+2*eps`) |
| Surface facets too coarse | `$fn`/`$fs` too low for this object's size | Bump the per-object `$fn` (or lower `$fs`); never a global `$fn=128` (§5) |
| Everything one flat color | Expected — Cornfield preview has no materials | None for QA; use `--render` (+ `--colorscheme`) only for final sign-off |
| Z-fighting flicker on coincident faces | Two faces exactly coplanar (cutter flush with wall) | Add epsilon overshoot so the cut surface clears the wall (§4) |
| Part tiny / off-center despite `--viewall` | Camera distance too large, or a stray far-away vertex inflating the bbox | Reduce `--camera` distance; check for a rogue `translate` placing geometry far off-origin |
| BOSL2 shape empty | Used `use <BOSL2/std.scad>` instead of `include` (drops special vars) | `include <BOSL2/std.scad>` — never `use` (§7) |
| Chamfers/roundovers missing | `minkowski`/profile applied before a `difference()` consumed them | Apply rounding last; use `cuboid(rounding=R)` / `edge_profile()` (§7) |

---

## §11. Gotcha → fix table

| Symptom | Cause | Fix |
|---|---|---|
| No console output, process hangs | Called `openscad.exe` not `openscad.com` | Always `openscad.com` in PS/cmd |
| Blank PNG (~5–15 KB) | Camera not aimed at geometry, or missing `--autocenter --viewall` | Add `--autocenter --viewall` |
| Variable re-assignment has no effect | OpenSCAD is single-assignment per scope | Use list comprehensions or functions |
| `CGAL error` / empty STL | Zero-thickness walls, coplanar faces | Add epsilon overshoot (0.01 mm) to all cutters |
| `minkowski()` hangs | O(V²) cost with high-`$fn` kernel | Keep kernel `$fn ≤ 16`; use Manifold backend |
| BOSL2 `include` path not found | `OPENSCADPATH` points wrong directory | Set `OPENSCADPATH` to parent of `BOSL2/` folder |
| String `-D` parameter parse error | PowerShell strips quotes | Double-double-quote: `-D "material=""pla"""` |
| `$preview` false in headless | `$preview` only true in F5 interactive | Use custom quality variable + `-D quality_mode=...` |
| Complex model slow in 2021.01 | No CLI Manifold support | Use nightly 2025.xx with `--backend=Manifold` |
