# forge-parametric / references / build123d-cadquery.md
# build123d & CadQuery — Python B-rep CAD: install, API, export, validation

## Contents
- §1. Install (Windows, Python 3.12 venv)
- §2. OCP wheel matrix
- §3. build123d Builder Mode — core patterns
- §4. build123d Algebra Mode — parametric families
- §5. build123d Assemblies & Joints
- §6. build123d Export reference
- §7. CadQuery fluent API
- §8. Headless invocation (cq-cli, agentcad, tcv-screenshots)
- §9. Validation & QA
- §10. Gotcha → fix table

---

## §1. Install — Windows, Python 3.12 venv

```powershell
# Pin to Python 3.12 (3.13+ breaks VTK pin in cadquery)
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1

# MANDATORY: upgrade pip first (old pip fails on large OCP wheels)
python -m pip install --upgrade pip

# build123d — pulls cadquery-ocp 7.8.x wheels automatically
pip install build123d

# Type stubs (optional, for Pylance/mypy)
pip install cadquery-ocp-stubs

# CadQuery alongside (same OCP kernel, compatible)
pip install cadquery

# Headless CLI batch converter (CadQuery scripts only)
pip install cq-cli    # requires Python 3.11+

# Agent-grade runner with PNG render + metrics
pip install agentcad
pip install "agentcad[mcp]"   # adds MCP server

# Headless PNG via Playwright/Chromium
pip install tcv-screenshots && playwright install chromium
```

**Guard show() calls (prevents hanging headless):**
```python
import os
if os.environ.get("FORGE_HEADLESS", "1") != "1":
    from ocp_vscode import show
    show(part)
export_step(part, "out.step")
```

---

## §2. OCP wheel matrix (2026-06)

| cadquery-ocp | OCCT | Python | Windows wheel |
|---|---|---|---|
| 7.9.3.1.1 (latest) | 7.9.3 | 3.10–3.13 | win_amd64 ~45 MB |
| 7.8.1.1.post1 | 7.8.1 | 3.10–3.12 | win_amd64 |

build123d 0.10 pins `cadquery-ocp <7.9,>=7.8` — ships OCP 7.8.
Use `pip install git+https://github.com/gumyr/build123d` for dev branch with OCP 7.9.

---

## §3. build123d Builder Mode — core patterns

```python
from build123d import *

# --- Box with hole, chamfer, fillet ---
with BuildPart() as part:
    Box(80, 60, 10)
    Hole(radius=11)                         # through hole, diameter=22
    # Chamfer all top edges, fillet all vertical edges:
    chamfer(part.edges().group_by(Axis.Z)[-1], length=4)
    fillet(part.edges().filter_by(Axis.Z), radius=2)
solid = part.part

# --- Sketch → Extrude → Pocket ---
with BuildPart() as bracket:
    with BuildSketch(Plane.XY) as sk:
        Rectangle(80, 60)
        with Locations((0, 0)):
            Circle(11, mode=Mode.SUBTRACT)  # hole in sketch
        fillet(sk.vertices(), radius=5)     # round sketch corners
    extrude(amount=10)
    with BuildSketch(bracket.faces().sort_by(Axis.Z)[-1]):
        with GridLocations(60, 40, 2, 2):   # 2×2 hole pattern
            Circle(2)
    extrude(amount=-5, mode=Mode.SUBTRACT)  # pocket

# --- Sweep ---
with BuildPart() as handle:
    with BuildLine() as path:
        Spline((0,0,0), (5,3,10), (10,0,20), tangents=((1,0,0),(1,0,-1)))
    with BuildSketch(path.line @ 0):
        Circle(2)
    sweep()

# --- Loft (multi-section sweep) ---
with BuildPart() as lofted:
    with BuildSketch(Plane.XY):           Rectangle(10, 10)
    with BuildSketch(Plane.XY.offset(15)): Circle(6)
    with BuildSketch(Plane.XY.offset(30)): Rectangle(4, 4)
    loft()

# --- Shell (hollow) ---
with BuildPart() as box_shell:
    Box(30, 30, 30)
    opening = box_shell.faces().sort_by(Axis.Z)[-1]
    shell(openings=[opening], thickness=2)

# --- Edge/face selectors ---
part.edges().filter_by(Axis.Z)            # edges parallel to Z
part.edges().filter_by(GeomType.LINE)     # straight edges
part.faces().filter_by(Axis.Z)            # faces with Z-normal
part.faces().sort_by(Axis.Z)[-1]          # topmost face
part.edges().group_by(Axis.Z)[-1]         # all edges in top group
part.edges().filter_by(lambda e: e.is_interior)  # interior only
part.edges(Select.LAST)                   # last created topology
```

---

## §4. build123d Algebra Mode — parametric families

```python
from build123d import *

# Algebra mode: +=ADD, -=SUBTRACT, *=INTERSECT
box  = Part() + Box(80, 60, 10)
hole = Cylinder(11, 10)
box -= hole

# Chamfer + fillet in algebra mode (last, after all booleans):
box = chamfer(box.edges().group_by(Axis.Z)[-1], length=4)
box = fillet(box.edges().filter_by(Axis.Z), radius=2)

# Placement operators: Plane * Pos * Shape
box_placed = Plane.XZ * Pos(X=50) * Box(10, 10, 10)

# Parametric family as a function:
def mounting_plate(width: float, height: float, thickness: float,
                   hole_diam: float, hole_margin: float) -> Part:
    plate = Part() + Box(width, height, thickness)
    with Locations(*[
        (x, y, 0)
        for x in [-width/2 + hole_margin, width/2 - hole_margin]
        for y in [-height/2 + hole_margin, height/2 - hole_margin]
    ]):
        plate -= Cylinder(hole_diam/2, thickness)
    plate = fillet(plate.edges().filter_by(Axis.Z), hole_margin * 0.3)
    # Validate early:
    assert plate.is_valid, f"plate ({width}x{height}) is invalid"
    assert plate.volume > 0, f"plate volume is zero"
    return plate

# Generate family of variants:
for w in [60, 80, 100]:
    part = mounting_plate(w, 40, 4, 5, 8)
    export_step(part, f"plate_w{w}.step")
    export_stl(part,  f"plate_w{w}.stl", tolerance=1e-3, angular_tolerance=0.1)
```

---

## §5. build123d Assemblies & Joints

```python
import copy
from build123d import *

# Build pipe with joint definitions at ends:
with BuildPart() as pipe_builder:
    with BuildLine() as path:
        TangentArc((0,0,0), (200,0,100), tangent=(1,0,0))
    with BuildSketch(Plane(origin=path @ 0, z_dir=path % 0)):
        Circle(10)
    sweep()
    RigidJoint("inlet",  joint_location=-path.location_at(0))
    RigidJoint("outlet", joint_location= path.location_at(1))

# Build flange with joint:
with BuildPart() as flange:
    Cylinder(25, 10)
    Cylinder(10, 20, mode=Mode.SUBTRACT)
    RigidJoint("pipe", joint_location=Location(Plane.XY.offset(-5)))
    flange.part.label = "flange"

# Connect parts via joints:
flange_in  = copy.copy(flange.part)
flange_out = copy.copy(flange.part)
pipe_builder.part.joints["inlet"].connect_to(flange_in.joints["pipe"])
pipe_builder.part.joints["outlet"].connect_to(flange_out.joints["pipe"])

# Assemble compound:
pipe_builder.part.label = "pipe"
assembly = Compound(
    label="pipe_assembly",
    children=[pipe_builder.part, flange_in, flange_out]
)

# Joint types:
# RigidJoint      → fixed
# RevoluteJoint   → hinge (angular_range param)
# LinearJoint     → slider
# CylindricalJoint → screw
# BallJoint       → gimbal (3 angles)

# RevoluteJoint example (hinge, 0–120 degrees):
RevoluteJoint("hinge", to_part=lid,
              axis=Axis((0,60,50),(1,0,0)), angular_range=(0,120))
lid.joints["hinge"].connect_to(box.joints["hinge_mount"], angle=45)

# Shallow copy for repeated instances (100x faster than deepcopy in STEP export):
screw = import_step("m3_screw.step")
locs  = HexLocations(6, 5, 5).local_locations
screws = [copy.copy(screw).locate(loc) for loc in locs]
screw_assy = Compound(children=screws)
export_step(screw_assy, "screw_pattern.step")
```

---

## §6. build123d Export reference

```python
from build123d import *
shape = Box(10, 10, 10)

# STEP: B-rep, lossless, for CAD interchange / CAM / CNC
export_step(shape, "out.step",
            unit=Unit.MM,
            write_pcurves=True,                     # False → 30% smaller (for mesh consumers)
            precision_mode=PrecisionMode.AVERAGE)

# STL: mesh for 3D printing
export_stl(shape, "out.stl",
           tolerance=1e-3,                          # linear deflection mm
           angular_tolerance=0.1,                   # radians
           ascii_format=False)                      # binary is smaller

# glTF (text JSON):
export_gltf(shape, "out.gltf", binary=False, linear_deflection=1e-3, angular_deflection=0.1)
# Binary glTF (GLB — for web delivery):
export_gltf(shape, "out.glb", binary=True)

# 3MF:
export_3mf(shape, "out.3mf")

# SVG 2D projection:
export_svg(shape, "out.svg")

# DXF for laser cutting / CNC:
export_dxf(shape, "out.dxf")
```

**Mesh export tolerances by use case:**

| Use case | `tolerance` | `angular_tolerance` |
|---|---|---|
| FDM (nozzle ≥ 0.4 mm) | 0.1 mm | 0.2 rad |
| Resin (fine detail) | 0.01 mm | 0.05 rad |
| Web viewer (small file) | 0.5 mm | 0.5 rad |
| Engineering review | 0.001 mm | 0.05 rad |
| Default (safe start) | 0.001 mm | 0.1 rad |

---

## §7. CadQuery fluent API

```python
import cadquery as cq

# Box with holes and fillets:
result = (
    cq.Workplane("XY")
    .box(80, 60, 10)
    .faces(">Z").workplane()
    .hole(22)
    .faces(">Z").workplane()
    .rect(80-12, 60-12, forConstruction=True)
    .vertices()
    .cboreHole(2.4, 4.4, 2.1)
    .edges("|Z").fillet(2.0)
)

# String selector reference:
# ">X" most +X face   "<X" most -X face   "|Z" edges parallel to Z
# "#Z" faces perp to Z   ">Z[2]" second-to-last face by Z

# Loft:
loft = (cq.Workplane("XY").rect(10,10).workplane(offset=20).circle(5).loft())

# Sweep:
path = cq.Workplane("XZ").spline([(0,0,0),(5,3,10),(10,0,20)])
sweep = cq.Workplane("XY").circle(2).sweep(path)

# Shell (hollow):
shell = cq.Workplane("XY").box(20,20,20).faces(">Z").shell(-2)

# Boolean operators (CadQuery 2.7+):
c1 = cq.Workplane().cylinder(20, 10)
c2 = cq.Workplane().box(15, 15, 30)
union = c1 + c2;  diff = c2 - c1;  inter = c1 * c2

# Export:
cq.exporters.export(result, "model.step")   # STEP
result.export("model.stl")                  # STL
result.val().exportStl("model.stl", tolerance=0.001, angularTolerance=0.1, parallel=True)
# glTF — assembly only:
assy = cq.Assembly(name="assy")
assy.add(result, name="part")
assy.export("model.glb")    # binary GLB

# .stp extension FAILS silently — always use .step or pass explicit type:
result.export("model.stp", "STEP")   # explicit type needed
```

---

## §8. Headless invocation (cq-cli, agentcad, tcv-screenshots)

```powershell
# cq-cli: CadQuery scripts only
cq-cli --codec step --infile model.py --outfile model.step
cq-cli --codec stl  --infile model.py --outfile model.stl `
       --outputopts "linearDeflection:0.01;angularDeflection:0.05"
cq-cli --codec gltf --infile model.py --outfile model.gltf
# Multiple outputs:
cq-cli --codec "step;stl" --infile model.py --outfile "model.step;model.stl"

# agentcad: build123d + CadQuery, with PNG render:
agentcad run model.py --output v1
agentcad run model.py --output v1 --render iso,front,top,right
agentcad run model.py --output v1 --export stl,glb
agentcad measure  output.step   # dimensional report (JSON)
agentcad inspect  output.step   # topology / validity (JSON)
agentcad diff 1 2               # version diff

# tcv-screenshots: headless PNG via Playwright:
python -m tcv_screenshots -f model.py -o ./renders
```

---

## §8b. Render verification (after agentcad/tcv-screenshots)

The §9 asserts (`is_valid`, `volume > 0`) are the programmatic gate and MUST pass before
rendering. Then verify the render exactly like the OpenSCAD path: size-check the PNG, `Read` it,
and diagnose against the visual-failure table.

```powershell
# agentcad writes <output>_<view>.png; size-check before Read (blank/transparent ~ a few KB):
agentcad run model.py --output iso --render iso,front,top,right
Get-ChildItem iso_*.png | ForEach-Object {
    if ($_.Length -lt 10240) { throw "[Forge QA] blank render: $($_.Name) ($($_.Length) bytes)" }
    Write-Host "OK: $($_.Name) ($($_.Length) bytes)"
}
```

Then visually inspect, e.g. `Read("C:/forge-build/out/iso_iso.png")`.

**Visual failure diagnosis table** — after `Read(png_path)`, common failure modes:

| What you see | Cause | Fix |
|-------------|-------|-----|
| Blank / transparent | Camera not framing part, or `part.volume == 0` (boolean produced nothing) | Re-run §9 asserts; offset cutter by 0.001 mm (see §10); let agentcad auto-frame |
| Only edges / wireframe | Wireframe-only export flag | Drop the wireframe/edges-only render flag; render shaded |
| Wrong scale (tiny or huge in frame) | Unit mismatch (`Unit.MM` vs scene/import unit) | Export with explicit `unit=Unit.MM`; confirm import unit on round-trip |
| Missing fillets / chamfers | `fillet()`/`chamfer()` applied before a boolean (got consumed) | Apply fillets/chamfers LAST, after all booleans (see §3/§4) |
| `fillet()` errored, part rendered sharp | Radius too large or non-manifold edge | Reduce radius; fillet a subset of edges; use chamfer (see §10) |
| Faceted curves in render | Mesh deflection too coarse for preview | Tighten `linear_deflection`/`angular_deflection` on `export_gltf`/`export_stl` (§6 table) |

---

## §9. Validation & QA

```python
from build123d import *

part = Box(10, 10, 10)

# Validity (OCCT internal check):
assert part.is_valid, "Solid is topologically invalid"

# Volume (must be > 0):
assert part.volume > 0, f"Volume is zero or negative: {part.volume}"

# Bounding box:
bb = part.bounding_box()
assert bb.size.X > 0 and bb.size.Y > 0 and bb.size.Z > 0

# Face/edge count (regression check):
print(f"Faces: {len(part.faces())}, Edges: {len(part.edges())}")

# STEP round-trip validation (Windows-safe temp path — never POSIX /tmp):
import os, tempfile
rt = os.path.join(tempfile.gettempdir(), "forge_roundtrip.step")  # or "C:/forge-build/out/_roundtrip.step"
export_step(part, rt)
reimported = import_step(rt)
delta = abs(part.volume - reimported.volume) / part.volume
assert delta < 1e-6, f"Volume drift: {delta*100:.4f}%"
```

**agentcad topology inspect:**
```powershell
agentcad inspect model.step
# JSON: {shells, free_edges, validity, face_count, edge_count}
agentcad measure model.step
# JSON: {volume, surface_area, bounding_box, min_wall_thickness, ...}
```

---

## §10. Gotcha → fix table

| Symptom | Cause | Fix |
|---|---|---|
| `pip install cadquery` fails on Python 3.13 | VTK wheel not available for 3.13 | Use Python 3.12: `py -3.12 -m venv .venv` |
| `import cadquery` in conda fails | Conda OCP version conflicts with pip | Never mix conda + pip OCP; use pure pip venv |
| `.stp` extension exports nothing | CadQuery only auto-detects `.step` | Use `.step` or pass `"STEP"` as explicit type |
| `part.volume` is 0 after boolean | Near-coincident faces, self-intersection | Offset cutter by 0.001 mm; use `fuzzy_tol=0.001` on export |
| `fillet()` raises `Standard_Failure` | Non-manifold edge or radius too large | Reduce radius; fillet before some cuts; use chamfer instead |
| `show()` hangs headless | OCP viewer not connected | Set `FORGE_HEADLESS=1` and guard `show()` import |
| `cq-cli --codec step` KeyError | cqcodecs plugin not found | Use `uv tool install cq-cli`; invoke from install dir |
