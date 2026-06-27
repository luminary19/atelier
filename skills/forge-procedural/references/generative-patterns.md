# Generative Systems — L-systems, WFC, Scatter Rules

**Platform:** Blender 4.2 LTS headless · Native Windows 11 · PowerShell-first  
**All bpy code runs inside Blender's embedded Python (3.11 in Blender 4.2).**

## Contents
§1 L-system turtle script · §2 L-Py integration · §3 WFC solver · §4 Slope masking · §5 Seeded RNG · §6 Scatter rules · §7 WFC rules · §8 Gotchas · §9 Validation pointer

---

## §1. L-system: derive + turtle → mesh

```python
"""
forge_lsystem.py — headless stochastic L-system tree (Prusinkiewicz & Lindenmayer)
Usage: blender -b --factory-startup -P forge_lsystem.py -- --seed 42 --depth 5
       --angle 25.7 --out C:/renders/tree_s42_d5.png
"""
import bpy, bmesh, sys, math, random, io, os
from mathutils import Vector, Matrix

# UTF-8 stdout fix (Windows cp1252)
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

argv = sys.argv
args_start = argv.index("--") + 1 if "--" in argv else len(argv)
import argparse
p = argparse.ArgumentParser()
p.add_argument("--seed",  type=int,   default=0)
p.add_argument("--depth", type=int,   default=5)
p.add_argument("--angle", type=float, default=25.7)
p.add_argument("--out",   type=str,   default="C:/out/lsystem.png")
cfg = p.parse_args(argv[args_start:])

# ── Isolated RNG instance (NEVER use global random.seed()) ────────────────
rng = random.Random(cfg.seed)

# ── Grammar (stochastic plant — "Algorithmic Beauty of Plants" §1.7) ─────
AXIOM = "X"
RULES = {
    "X": [(0.5, "F+[[X]-X]-F[-FX]+X"), (0.5, "F[+X][-X]FX")],
    "F": [(1.0, "FF")],
}

def derive(s, rules, n, rng_inst):
    """Parallel string rewrite n times."""
    for _ in range(n):
        out = []
        for c in s:
            if c in rules:
                r = rng_inst.random(); cum = 0.0
                for prob, rep in rules[c]:
                    cum += prob
                    if r <= cum:
                        out.append(rep); break
            else:
                out.append(c)
        s = "".join(out)
    return s

# ── Turtle interpreter (bmesh edge skeleton + Skin modifier) ─────────────
# Emits one edge per branch segment, then skins it to solid renderable branches.
# Production upgrade: replace push_segment with bpy.data.curves (NURBS per branch)
# for smooth normals, per-branch taper via bevel_depth, and cleaner UV unwrapping.

def turtle_to_mesh(lstring, angle_deg, rng_inst):
    angle = math.radians(angle_deg)
    stack = []; mat = Matrix.Identity(4)
    seg_len = 1.0; seg_rad = 0.08

    merged_bm = bmesh.new()

    def push_segment(length, radius):
        # Emit a real edge per branch segment (base→tip). Loose verts alone fail
        # validate_lsystem_output (asserts len(mesh.edges) > 0) and render as an
        # invisible point cloud — a Skin modifier (added below) gives the edge skeleton
        # thickness. Production: build a bmesh cylinder per segment, or a NURBS curve
        # with bevel_depth for smooth normals + taper.
        tip = (mat @ Matrix.Translation((0, 0, length))).translation
        base = mat.translation.copy()
        v0 = merged_bm.verts.new(base)
        v1 = merged_bm.verts.new(tip)
        merged_bm.edges.new((v0, v1))

    for sym in lstring:
        if   sym == "F":
            push_segment(seg_len, seg_rad)
            mat = mat @ Matrix.Translation((0, 0, seg_len))
            seg_len *= 0.85; seg_rad *= 0.75
        elif sym == "+": mat = mat @ Matrix.Rotation( angle, 4, "Y")
        elif sym == "-": mat = mat @ Matrix.Rotation(-angle, 4, "Y")
        elif sym == "^": mat = mat @ Matrix.Rotation( angle, 4, "X")
        elif sym == "&": mat = mat @ Matrix.Rotation(-angle, 4, "X")
        elif sym == "\\": mat = mat @ Matrix.Rotation(angle, 4, "Z")
        elif sym == "/": mat = mat @ Matrix.Rotation(-angle, 4, "Z")
        elif sym == "[": stack.append((mat.copy(), seg_len, seg_rad))
        elif sym == "]": mat, seg_len, seg_rad = stack.pop()
        # X is no-op

    mesh_data = bpy.data.meshes.new("LSystemTree")
    merged_bm.to_mesh(mesh_data)
    merged_bm.free()
    obj = bpy.data.objects.new("LSystemTree", mesh_data)
    bpy.context.collection.objects.link(obj)

    # Skin the edge skeleton so it renders as solid branches (not an invisible wire).
    # The Skin modifier needs an MVertSkin layer; seed a uniform root radius.
    skin = obj.modifiers.new("Skin", "SKIN")
    skin_layer = mesh_data.skin_vertices[0] if mesh_data.skin_vertices else None
    if skin_layer is not None:
        for sv in skin_layer.data:
            sv.radius = (seg_rad, seg_rad)
    obj.modifiers.new("Subsurf", "SUBSURF").levels = 1   # smooth the skinned branches

    # Store parameters as custom properties (reproducibility metadata)
    import json
    obj["forge_lsystem_seed"]  = cfg.seed
    obj["forge_lsystem_depth"] = cfg.depth
    obj["forge_lsystem_axiom"] = AXIOM
    obj["forge_lsystem_rules"] = json.dumps(RULES)
    return obj

def main():
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.delete()

    lstring = derive(AXIOM, RULES, cfg.depth, rng)
    print(f"[Forge] L-string length after {cfg.depth} steps: {len(lstring)}")
    obj = turtle_to_mesh(lstring, cfg.angle, rng)

    # Camera
    bpy.ops.object.camera_add(location=(10, -10, 8))
    cam = bpy.context.object
    cam.rotation_euler = (math.radians(60), 0, math.radians(45))
    bpy.context.scene.camera = cam

    # Headless render — ALWAYS Cycles (EEVEE-Next unsupported headless on Windows)
    scene = bpy.context.scene
    scene.render.engine = "CYCLES"
    scene.cycles.samples = 32
    scene.render.image_settings.file_format = "PNG"
    os.makedirs(os.path.dirname(cfg.out), exist_ok=True)
    scene.render.filepath = cfg.out.replace("\\", "/")
    scene.render.resolution_x = 800; scene.render.resolution_y = 800
    bpy.ops.object.light_add(type='SUN', location=(5, 5, 10))
    bpy.ops.render.render(write_still=True)
    print(f"[Forge] Rendered → {cfg.out}")

main()
```

**PowerShell invocation:**
```powershell
& "C:\Program Files\Blender Foundation\Blender\blender.exe" `
    -b --factory-startup `
    -P "C:\Forge\forge_lsystem.py" `
    -- --seed 42 --depth 5 --out "C:/renders/tree_s42_d5.png"
```

**L-system depth limits:**
- Depth ≤ 5: fast, good for interactive preview
- Depth ≤ 7: batch-only (string can reach 10k+ symbols)
- Depth ≥ 8: very slow mesh creation; profile first

---

## §2. L-Py integration (conda env → OBJ → bpy import)

L-Py requires compiled Boost::Python (conda only) — cannot run inside Blender's Python.

```python
# conda activate lpy_env && python lpy_export.py
from openalea.lpy import Lsystem
from openalea.plantgl.all import ObjExporter
LSYSTEM_CODE = "Axiom: A\nderivation length: 6\nproduction:\nA --> F[+A][-A]FA\nF --> FF\nendlsystem"
ls = Lsystem(); ls.setCode(LSYSTEM_CODE, {"ANGLE": 25.7, "STEP": 1.0})
scene = ls.sceneInterpretation(ls.derive())
ObjExporter().save(scene, "C:/Forge/tree_output.obj")
```

In Blender headless script: `bpy.ops.wm.obj_import(filepath="C:/Forge/tree_output.obj")`

**Do NOT** import `openalea` inside Blender's Python — always pipe via OBJ/PLY.

---

## §3. Wave Function Collapse: solver + placer

Module objects in a Blender collection carry a `"wfc_connectors"` custom property:
JSON list of 6 connector labels (one per face: +X,-X,+Y,-Y,+Z,-Z).
Tiles are compatible when connectors match across the shared face; `"any"` is a wildcard.

```python
"""
forge_wfc.py — Usage: blender -b --factory-startup -P forge_wfc.py -- --seed 7 --grid 5 5 3
"""
import bpy, sys, random, json, io, os, math
from mathutils import Vector

import sys, io
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

argv = sys.argv; args_start = argv.index("--") + 1 if "--" in argv else len(argv)
import argparse
p = argparse.ArgumentParser()
p.add_argument("--seed", type=int, default=0); p.add_argument("--grid", type=int, nargs=3, default=[4,4,2])
p.add_argument("--cell", type=float, default=2.0); p.add_argument("--source-collection", default="WFCModules")
p.add_argument("--out", type=str, default="C:/out/wfc_result.png")
cfg = p.parse_args(argv[args_start:])

DIRECTIONS_6 = [(+1,0,0),(-1,0,0),(0,+1,0),(0,-1,0),(0,0,+1),(0,0,-1)]
OPPOSITE = {i: (i+1 if i%2==0 else i-1) for i in range(6)}

def load_modules(col_name):
    col = bpy.data.collections.get(col_name)
    if col is None: raise RuntimeError(f"Collection '{col_name}' not found")
    return [{"obj": obj, "connectors": json.loads(obj.get("wfc_connectors","[]"))
             if isinstance(obj.get("wfc_connectors"), str) else list(obj.get("wfc_connectors",[]))}
            for obj in col.objects if obj.get("wfc_connectors") is not None]

def compatible(ma, di, mb):
    ca=ma["connectors"][di]; cb=mb["connectors"][OPPOSITE[di]]
    return ca==cb or ca=="any" or cb=="any"

def solve_wfc(grid_shape, modules, rng):
    gx,gy,gz = grid_shape
    wave=[[[set(range(len(modules))) for _ in range(gz)] for _ in range(gy)] for _ in range(gx)]
    collapsed=[[[False]*gz for _ in range(gy)] for _ in range(gx)]
    result=[[[None]*gz for _ in range(gy)] for _ in range(gx)]
    def collapse(x,y,z):
        poss=list(wave[x][y][z])
        if not poss: return False
        w=[modules[i]["obj"].get("wfc_weight",1.0) for i in poss]
        ch=rng.choices(poss,weights=w,k=1)[0]
        wave[x][y][z]={ch}; collapsed[x][y][z]=True; result[x][y][z]=ch; return True
    def propagate(sx,sy,sz):
        stack=[(sx,sy,sz)]
        while stack:
            cx,cy,cz=stack.pop()
            for di,(dx,dy,dz) in enumerate(DIRECTIONS_6):
                nx,ny,nz=cx+dx,cy+dy,cz+dz
                if not(0<=nx<gx and 0<=ny<gy and 0<=nz<gz): continue
                before=len(wave[nx][ny][nz])
                wave[nx][ny][nz]={m for m in wave[nx][ny][nz]
                    if any(compatible(modules[cm],di,modules[m]) for cm in wave[cx][cy][cz])}
                if not wave[nx][ny][nz]: return False
                if len(wave[nx][ny][nz])<before: stack.append((nx,ny,nz))
        return True
    for _ in range(gx*gy*gz):
        min_e=float("inf"); cands=[]
        for x in range(gx):
            for y in range(gy):
                for z in range(gz):
                    if not collapsed[x][y][z]:
                        e=len(wave[x][y][z])
                        if e<min_e: min_e=e; cands=[(x,y,z)]
                        elif e==min_e: cands.append((x,y,z))
        if not cands: break
        cx,cy,cz=rng.choice(cands)
        if not collapse(cx,cy,cz) or not propagate(cx,cy,cz): return None
    return result

def place_modules(result, modules, cell_size):
    gx=len(result); gy=len(result[0]); gz=len(result[0][0])
    placed=[]
    for x in range(gx):
        for y in range(gy):
            for z in range(gz):
                idx=result[x][y][z]
                if idx is None: continue
                o=bpy.data.objects.new(f"WFC_{x}_{y}_{z}", modules[idx]["obj"].data)
                o.location=Vector((x*cell_size,y*cell_size,z*cell_size))
                bpy.context.collection.objects.link(o); placed.append(o)
    return placed

def main():
    bpy.ops.object.select_all(action="SELECT"); bpy.ops.object.delete()
    modules = load_modules(cfg.source_collection)
    if not modules: raise RuntimeError("No valid WFC modules (missing wfc_connectors property)")
    # Retry loop: WFC fails ~15-30% without backtracking
    result = None
    for attempt in range(10):
        result = solve_wfc(tuple(cfg.grid), modules, random.Random(cfg.seed + attempt))
        if result is not None: print(f"[WFC] Solved attempt {attempt+1}"); break
    if result is None: raise RuntimeError("WFC failed after 10 attempts — audit connector rules")
    placed = place_modules(result, modules, cfg.cell)
    print(f"[WFC] Placed {len(placed)} modules")
    cx = cfg.grid[0]*cfg.cell*1.5
    bpy.ops.object.camera_add(location=(cx,-cx,cfg.grid[2]*cfg.cell*2))
    bpy.context.object.rotation_euler=(math.radians(55),0,math.radians(45))
    bpy.context.scene.camera=bpy.context.object
    scene=bpy.context.scene; scene.render.engine="CYCLES"; scene.cycles.samples=32
    os.makedirs(os.path.dirname(cfg.out),exist_ok=True)
    scene.render.filepath=cfg.out.replace("\\","/"); scene.render.image_settings.file_format="PNG"
    bpy.ops.object.light_add(type='SUN',location=(5,5,10))
    bpy.ops.render.render(write_still=True); print(f"[Forge] WFC render → {cfg.out}")

main()
```

---

## §4. Slope masking for scatter (GN snippet)

Add after `DistributePointsOnFaces` to cull steep-slope regions:

```python
# Normal → dot(Z-axis) → MapRange → DeleteGeometry (removes steep faces)
normal_node = ng.nodes.new("GeometryNodeInputNormal")
z_axis = ng.nodes.new("FunctionNodeInputVector"); z_axis.vector = (0.0, 0.0, 1.0)
dot = ng.nodes.new("ShaderNodeVectorMath"); dot.operation = 'DOT_PRODUCT'
ng.links.new(normal_node.outputs["Normal"], dot.inputs[0])
ng.links.new(z_axis.outputs["Vector"],      dot.inputs[1])
mr = ng.nodes.new("ShaderNodeMapRange")
mr.inputs["From Min"].default_value = 0.3   # cosine threshold: 0.3 = ~72° slope
mr.inputs["From Max"].default_value = 1.0
ng.links.new(dot.outputs["Value"], mr.inputs["Value"])
delete = ng.nodes.new("GeometryNodeDeleteGeometry")
delete.domain = 'POINT'; delete.mode = 'ALL'
# Wire: distribute.Points → delete.Geometry; mr.Result → delete.Selection
```

---

## §5. Seeded RNG rules (canonical patterns)

```python
# CORRECT: isolated instance, seed-stable, concurrency-safe
rng = random.Random(master_seed)              # stdlib, portable
rng_np = np.random.default_rng(master_seed)  # numpy

# WRONG: global state, order-sensitive
random.seed(master_seed)         # global → breaks with parallel scripts
np.random.seed(master_seed)      # global → same issue

# Offset per sub-system to prevent correlation between channels:
# scatter Seed = master_seed
# rotation Seed = master_seed + 1
# scale Seed = master_seed + 2
# instance-index Seed = master_seed + 3
# Each FunctionNodeRandomValue in GN also needs its own Seed input.

# Store seed as CLI arg AND as custom property on the output object:
obj["forge_seed"] = args.seed
```

---

## §6. Scattering rules / Poisson vs Random

| Rule | Detail |
|------|--------|
| Default to Poisson Disk | `distribute_method = 'POISSON'` prevents clumping. ~2–4× slower to compute, done once. |
| Greeble: use Random | Dense detail doesn't need separation; `'RANDOM'` at high density looks correct. |
| Never realize early | Instances are free in Cycles (shared BVH). Realize only at export (`export_apply=True`) or when baking normals/AO. 100k realized instances = 100× memory. |
| Instance count limits (Blender 4.2, viewport) | Solid viewport: ~50k; Cycles rendered viewport: ~150k; Headless render: millions (GPU BVH) |
| Slope masking | Dot product of face normal with (0,0,1) → Delete Geometry where dot < threshold (see §4) |
| Viewport LOD | Use `GeometryNodeMeshToPoints` + 10–25% of real density for interactive preview |

---

## §7. WFC rules / connector design

| Rule | Detail |
|------|--------|
| Connector symmetry mandatory | If module A has "wall" on +X, every compatible module must have "wall" on -X. Asymmetric connectors → unsolvable contradictions. |
| Retry loop | Pure WFC (no backtracking) fails 15–30% on complex rule sets. Run with `seed + attempt` for up to 10 attempts. |
| Pre-validate coverage | For each module × each direction, verify at least one other module is compatible. Otherwise some cells are always unsolvable. |
| Cell size ↔ module bounding box | Must match exactly. Apply all transforms on modules (`bpy.ops.object.transform_apply()`) before registering connectors. |
| Weight heavy tiles | `obj["wfc_weight"] = 1.0` for common tiles, `0.3` for rare. Pass to `rng.choices(weights=...)`. |
| Contradiction recovery | If `result is None`, increment seed and retry. If 10 retries all fail, the rule set has isolated connector labels — audit with the pre-validate step. |

---

## §8. Gotchas — bpy + Windows

| Symptom | Cause | Fix |
|---------|-------|-----|
| `AttributeError: 'NoneType' ...scene` | `bpy.context` invalid at module level | Wrap all bpy calls in `main()` |
| Script 10× slower creating many objects | `bpy.ops` in a loop | Use `bpy.data.meshes.new()` + bmesh directly |
| `RuntimeError: modifier_apply.poll()` | Object not active/selected | `bpy.context.view_layer.objects.active = obj; obj.select_set(True)` |
| `AttributeError: 'NodeTree' has no 'inputs'` | Pre-4.0 API | `nt.interface.new_socket(...)` |
| RAM grows monotonically in bmesh loop | bmesh not freed | `try/finally: bm.free()` after `bm.to_mesh()` |
| WFC `None` cells | Contradiction, no backtracking | Retry loop with `random.Random(seed + attempt)` |
| `FileNotFoundError` on existing path | Backslash escape | Use `"C:/renders/out"` or `r"C:\renders\out"` |
| L-Py import fails inside Blender Python | Needs conda Boost::Python | Run L-Py in separate conda env; export OBJ; import via `bpy.ops.wm.obj_import` |
| CPU 10–15% with high instance count | GN evaluation single-threaded | Launch multiple Blender processes in parallel |
| No render output, no error | Output dir missing | `os.makedirs(os.path.dirname(path), exist_ok=True)` before render |
| `ModuleNotFoundError` in Blender | System Python ≠ Blender Python | `& "C:\blender-4.2\4.2\python\bin\python.exe" -m pip install X` |

---

## §9. Validation

Full validator snippets (L-system, WFC, scatter, render, SDF, PowerShell QA shell) are in
**`validation-qa.md`** — read that file when running QA checks.
