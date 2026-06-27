# forge-parametric / references / freecad-headless.md
# FreeCAD headless scripting — FreeCADCmd, STEP I/O, PartDesign, validation

## Contents
- §1. When to use FreeCAD vs CadQuery
- §2. Executables & install
- §3. Headless invocation patterns
- §4. sys.path bootstrap (external Python only)
- §5. Document lifecycle
- §6. Part workbench — direct BRep geometry
- §7. STEP and IGES import/export
- §8. Mesh-to-solid conversion
- §9. PartDesign — Body, Pad, Pocket
- §10. Parametric modification (setDatum)
- §11. Validation
- §12. PowerShell driver wrapper
- §13. Gotcha → fix table

---

## §1. When to use FreeCAD vs CadQuery

| Use FreeCAD | Use CadQuery / build123d |
|---|---|
| Vendor STEP/IGES import with colors/metadata | Pure programmatic code-first workflow |
| Existing FCStd files / parametric history | pip-installable, venv-compatible |
| TechDraw 2D drawings (with GUI caveat) | Python 3.12+ |
| FEM analysis setup (CalculiX, Elmer) | CI/CD without large binary install (~100 MB pip) |
| Assemblies with constraint solver | Quick parametric families |
| Mesh-to-solid sewing (STL → STEP) | Assembly with typed joints (build123d) |

**Decision rule for Forge:** Default to CadQuery/build123d for code-first geometry.
Switch to FreeCAD for vendor STEP imports, FCStd round-trips, TechDraw, or FEM.

---

## §2. Executables & install (FreeCAD 1.1.1, 2026-04-14)

| Executable | Default path (per-user install) | Purpose |
|---|---|---|
| `FreeCAD.exe` | `%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin\FreeCAD.exe` | Full GUI |
| `FreeCADCmd.exe` | `%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin\FreeCADCmd.exe` | Headless Python; exits after script |
| `python.exe` | `%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin\python.exe` | Bundled CPython 3.11 |

All-users install path (admin): `C:\Program Files\FreeCAD 1.1\bin\`

**Silent install:**
```powershell
$installer = "$env:TEMP\FreeCAD_1.1.1-Windows-x86_64-py311-installer.exe"
Invoke-WebRequest `
    -Uri "https://github.com/FreeCAD/FreeCAD/releases/download/1.1.1/FreeCAD_1.1.1-Windows-x86_64-py311-installer.exe" `
    -OutFile $installer
& $installer /S
```

**PATH setup (PowerShell session):**
```powershell
$env:PATH = "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin;$env:PATH"
```

**Critical version note:** FreeCAD bundles CPython 3.11 — it is NOT compatible with
system Python 3.12+. Always use `FreeCADCmd.exe` or the bundled `bin\python.exe`.

---

## §3. Headless invocation patterns

```powershell
# RECOMMENDED: script file via FreeCADCmd (auto-initializes all modules)
FreeCADCmd.exe "C:\forge\scripts\make_bracket.py"

# Inline one-liner (quick test):
FreeCADCmd.exe "import Part; print(Part.makeBox(10,5,15).Volume)"

# Pass extra Python paths:
FreeCADCmd.exe -P "C:\forge\lib" "C:\forge\scripts\make_bracket.py"
```

**ALWAYS use `FreeCADCmd.exe` for non-trivial work** — it auto-sets `sys.path`
to `bin\` and `bin\Mod\`, initializes workbench `Init.py` files, and exits with
a non-zero code on Python exceptions (enabling CI integration).

---

## §4. sys.path bootstrap (external Python only — skip when using FreeCADCmd)

Use only when driving FreeCAD from a different Python process (e.g., a Blender bridge):

```python
# forge_freecad_bootstrap.py
import sys, os

FC_BIN = os.environ.get(
    "FREECAD_BIN",
    os.path.expandvars(r"%LOCALAPPDATA%\Programs\FreeCAD 1.1\bin")
)
FC_MOD = os.path.join(FC_BIN, "Mod")

if FC_BIN not in sys.path: sys.path.insert(0, FC_BIN)
if FC_MOD not in sys.path: sys.path.insert(1, FC_MOD)

import FreeCAD as App   # aliased as App in FreeCAD macros
import Part
import Sketcher
import PartDesign        # requires FC_MOD in sys.path
```

**Critical:** `FreeCAD.pyd` is in `bin\`, workbenches in `bin\Mod\`. Both must be
on `sys.path` when using external interpreter. Never use `import PartDesignGui` —
it crashes silently in headless mode (see §13 gotcha 3).

---

## §5. Document lifecycle

```python
# run via: FreeCADCmd.exe forge_doc_lifecycle.py
import FreeCAD as App

doc = App.newDocument("ForgeDoc")
# ... do work ...
doc.recompute()                           # MANDATORY after every structural change
doc.saveAs(r"C:\forge\output\part.FCStd")
doc2 = App.openDocument(r"C:\forge\input\part.FCStd")
App.closeDocument("ForgeDoc")
```

---

## §6. Part workbench — direct BRep geometry

```python
# run via: FreeCADCmd.exe
import FreeCAD as App
import Part
from FreeCAD import Base

# Primitives:
box    = Part.makeBox(100, 50, 30)         # length, width, height (mm)
cyl    = Part.makeCylinder(15, 80)         # radius, height
sphere = Part.makeSphere(25)
cone   = Part.makeCone(10, 20, 40)         # r1, r2, height
torus  = Part.makeTorus(40, 10)            # major r, minor r

# Boolean operations:
union = box.fuse(cyl)
diff  = box.cut(cyl)
inter = box.common(cyl)

# Transforms:
box.translate(Base.Vector(10, 0, 0))
box.rotate(Base.Vector(0,0,0), Base.Vector(0,0,1), 45)  # origin, axis, degrees

# Add to document (required for Import.export):
doc = App.newDocument("Parts")
feat = doc.addObject("Part::Feature", "MyBox")
feat.Shape = box
doc.recompute()

# Fillets/chamfers on Part shapes:
edge_idx = 0    # 0-based index from shape.Edges
fillet_shape = box.makeFillet(2.0, [box.Edges[edge_idx]])
chamfer_shape = box.makeChamfer(1.0, [box.Edges[edge_idx]])
```

---

## §7. STEP and IGES import/export

| Module | Import | Export | Colors | Headless |
|---|---|---|---|---|
| `Part` (shape method) | `shape.read("f.stp")` | `shape.exportStep("f.stp")` | No | Yes |
| `Import` | `Import.open("f.stp")` | `Import.export([objs],"f.stp")` | Yes | Yes |
| `ImportGui` | — | `ImportGui.export(...)` | Yes (best) | **NO** — GUI only |

```python
# run via: FreeCADCmd.exe
import FreeCAD as App
import Part
import Import

# Method A: shape-level (geometry only, no colors):
shape = Part.Shape()
shape.read(r"C:\forge\input\vendor.stp")
shape.exportStep(r"C:\forge\output\clean.stp")
shape.exportStl(r"C:\forge\output\clean.stl")

# Method B: Import module (preserves document structure and colors):
Import.open(r"C:\forge\input\assembly.stp")
doc = App.ActiveDocument
doc.recompute()
objs = doc.Objects
Import.export(objs, r"C:\forge\output\assembly_out.stp")

# STEP round-trip (geometry only):
s1 = Part.Shape(); s1.read("in.stp")
s1.exportStep("out.stp")
s2 = Part.Shape(); s2.read("out.stp")
delta = abs(s1.Volume - s2.Volume) / max(s1.Volume, 1e-9)
print("Round-trip delta:", delta, "PASS" if delta < 0.001 else "FAIL")
```

---

## §8. Mesh-to-solid conversion (STL → watertight STEP)

```python
# run via: FreeCADCmd.exe
import FreeCAD as App
import Mesh, Part, Import, MeshPart

doc = App.newDocument("MeshConv")
Mesh.insert(r"C:\forge\input\scan.stl", doc.Name)
doc.recompute()
mesh = doc.getObject("scan").Mesh   # name = stl filename stem

# Mesh → Shape:
shape = Part.Shape()
shape.makeShapeFromMesh(mesh.Topology, 0.10)  # tolerance=0.10mm

# Sew to close gaps (tolerance 0.10 for clean CAD, 0.5–2.0 for scan data):
try:
    sewn = shape.sewShape(0.10)
    if sewn: shape = sewn
except Exception as e:
    App.Console.PrintWarning(f"Sew failed: {e}\n")

# Attempt solid:
solid = Part.Solid(shape)
solid_obj = doc.addObject("Part::Feature", "Solid")
solid_obj.Shape = solid
doc.recompute()

# Export STEP:
Import.export([solid_obj], r"C:\forge\output\scan_solid.stp")

# Shape → Mesh (forward direction):
mesh_out = MeshPart.meshFromShape(
    Shape=solid_obj.Shape,
    LinearDeflection=0.1,    # mm
    AngularDeflection=0.523, # ~30 degrees
    Relative=False, Segments=True
)
Mesh.export([solid_obj], r"C:\forge\output\solid.stl")
```

---

## §9. PartDesign — Body, Pad, Pocket

```python
# run via: FreeCADCmd.exe   (do NOT import PartDesignGui — crashes headlessly)
import FreeCAD as App
import Part, Sketcher

doc = App.newDocument("BracketDoc")

# Create Body:
body = doc.addObject("PartDesign::Body", "Body")

# Pad sketch:
pad_sketch = doc.addObject("Sketcher::SketchObject", "PadSketch")
body.addObject(pad_sketch)   # MUST add to body BEFORE the feature that uses it

# Draw closed rectangle on XY plane (indices are 0-based):
pad_sketch.addGeometry(Part.LineSegment(App.Vector(0,  0, 0), App.Vector(60,  0, 0)), False)
pad_sketch.addGeometry(Part.LineSegment(App.Vector(60, 0, 0), App.Vector(60, 40, 0)), False)
pad_sketch.addGeometry(Part.LineSegment(App.Vector(60,40, 0), App.Vector(0,  40, 0)), False)
pad_sketch.addGeometry(Part.LineSegment(App.Vector(0, 40, 0), App.Vector(0,   0, 0)), False)
for i in range(3):
    pad_sketch.addConstraint(Sketcher.Constraint("Coincident", i, 2, i+1, 1))
pad_sketch.addConstraint(Sketcher.Constraint("Coincident", 3, 2, 0, 1))

# Pad:
pad = doc.addObject("PartDesign::Pad", "Pad")
body.addObject(pad)
pad.Profile = pad_sketch
pad.Length  = 20.0
pad.Midplane = False; pad.Reversed = False
doc.recompute()

# Pocket sketch on top face (Z=20 plane):
pkt_sketch = doc.addObject("Sketcher::SketchObject", "PocketSketch")
body.addObject(pkt_sketch)
pkt_sketch.Placement = App.Placement(App.Vector(0,0,20), App.Rotation(App.Vector(0,0,1),0))
pkt_sketch.addGeometry(Part.Circle(App.Vector(30,20,0), App.Vector(0,0,1), 12.0), False)
pkt_sketch.addConstraint(Sketcher.Constraint("Radius", 0, 12.0))

pkt = doc.addObject("PartDesign::Pocket", "Pocket")
body.addObject(pkt)
pkt.Profile = pkt_sketch; pkt.Length = 15.0
doc.recompute()

# Export:
import Import
Import.export([body], r"C:\forge\output\bracket.stp")
doc.saveAs(r"C:\forge\output\bracket.FCStd")
```

---

## §10. Parametric modification (setDatum)

```python
# run via: FreeCADCmd.exe
import FreeCAD as App

doc = App.openDocument(r"C:\forge\output\bracket.FCStd")
sketch = doc.getObject("PadSketch")

# Inspect constraints:
for i, c in enumerate(sketch.Constraints):
    print(i, c.Type, c.Value)

# Change a constraint dimension (0-based index):
sketch.setDatum(4, App.Units.Quantity("80 mm"))
doc.recompute()

import Import
Import.export([doc.getObject("Body")], r"C:\forge\output\bracket_v2.stp")
```

---

## §11. Validation

```python
# forge_validate.py — run via FreeCADCmd.exe
import FreeCAD as App
import Part

def validate_shape(shape, name="shape"):
    if shape.isNull():
        App.Console.PrintError(f"{name}: shape is NULL\n"); return False
    check = shape.check(True)   # list of (shape, severity, description) — empty = valid
    if check:
        for item in check:
            App.Console.PrintWarning(f"  {item}\n")
    vol  = shape.Volume; area = shape.Area
    App.Console.PrintMessage(f"{name}: Vol={vol:.3f} mm3, Area={area:.3f} mm2\n")
    if vol <= 0:
        App.Console.PrintError(f"{name}: non-positive volume\n"); return False
    for i, shell in enumerate(shape.Shells):
        if not shell.isClosed():
            App.Console.PrintWarning(f"{name}: shell {i} is OPEN\n"); return False
    App.Console.PrintMessage(f"{name}: VALID\n"); return True

doc = App.openDocument(r"C:\forge\output\bracket.FCStd")
doc.recompute()
validate_shape(doc.getObject("Body").Shape, "bracket")

# Sketch constraint DOF check:
dof = sketch.solve()
# 0 = fully constrained; >0 = under-constrained; -1 = redundant; -2 = conflicting
if dof != 0:
    App.Console.PrintError(f"Sketch DOF={dof}. Redundant: {sketch.RedundantConstraints}\n")
```

---

## §12. PowerShell driver wrapper

```powershell
# forge_run.ps1
param(
    [string]$Script,
    [string]$FreeCadBin = "$env:LOCALAPPDATA\Programs\FreeCAD 1.1\bin"
)
$fc = Join-Path $FreeCadBin "FreeCADCmd.exe"
if (-not (Test-Path $fc)) { throw "FreeCADCmd not found at: $fc" }
$proc = Start-Process -FilePath $fc -ArgumentList "`"$Script`"" -NoNewWindow -Wait -PassThru
if ($proc.ExitCode -ne 0) { throw "FreeCADCmd exited $($proc.ExitCode)" }
Write-Host "FreeCADCmd OK."
```

---

## §13. Gotcha → fix table

| Symptom | Cause | Fix |
|---|---|---|
| Script shows "Zen of Python", code never runs | Script named after stdlib module (`test.py`, `math.py`) | Rename: `forge_bracket.py`, `step_roundtrip.py` |
| `PartDesign::Body` loads as `GeoFeature` | PartDesign module not initialized before `openDocument` | Use `FreeCADCmd.exe` (auto-inits); if external Python, import `PartDesign` first |
| Silent crash after `import PartDesignGui` | GUI module requires Coin3D/pivy scenegraph; not available headless | Never import `*Gui` modules in Forge scripts |
| `ImportError: DLL load failed` importing `FreeCAD.pyd` | Python version mismatch (FreeCAD ships 3.11; system may be 3.12+) | Use `FreeCADCmd.exe` or the bundled `bin\python.exe` |
| `ImportGui.export()` raises `ModuleNotFoundError` | `ImportGui` is GUI-only | Use `Import.export([objs], path)` for headless |
| Placements lost on STEP export | Pre-1.0 behavior or incomplete object reconstruction | Use FreeCAD 1.0+; wrap in `App::Part` container |
| Feature tree breaks after sketch edit | Topological Naming Problem (pre-1.0) | Use FreeCAD 1.0+ (TNP mitigation enabled by default) |
| `print()` output lost on crash | Python stdout buffering | Use `App.Console.PrintMessage("...\n")` — unbuffered |
| TechDraw SVG/PDF is empty in headless | TechDraw requires GUI viewport to render | Use `FreeCAD.exe --console` with display, or use a separate 2D tool |
| Path backslash causes wrong escape | `\f`, `\n` in non-raw Python strings | Always use raw strings `r"..."` or forward slashes `"C:/..."` |
| `doc.recompute()` deadlocks | Circular expression (model → spreadsheet → model) | Spreadsheet drives model only; never model → spreadsheet |
| FEM / CalculiX solver fails headless | Solver execution is external to FreeCAD | Run solver binary separately; FreeCADCmd just writes the `.inp` file |
