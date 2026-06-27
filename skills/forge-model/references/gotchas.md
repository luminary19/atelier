# forge-model — Gotchas, Failure Modes & Windows Pitfalls

## Contents
- §G1. bpy.ops.mesh poll() fails headless (RuntimeError)
- §G2. use_auto_smooth removed in Blender 4.1 (AttributeError)
- §G3. SmoothByAngle must be last in stack
- §G4. WeightedNormal + SmoothByAngle wrong order (shading seam)
- §G5. Exit code 0 on Python exception (silent failure)
- §G6. EEVEE headless: black image on Windows
- §G7. Absolute vs // paths in render output
- §G8. Boolean solver failure on non-manifold mesh
- §G9. bmesh lookup table stale after topology change
- §G10. to_mesh_clear() memory leak in loops
- §G11. Array modifier FIT_CURVE: requires curve object
- §G12. Mirror merge_threshold too large
- §G13. Windows path separator in smooth_by_angle operator
- §G14. subprocess argument splitting (merged flags)
- §G15. Argument order changes behavior
- §G16. bpy.data references stale after depsgraph re-eval
- §G17. bm.free() omitted → C-level memory leak

---

## §G1. bpy.ops.mesh poll() fails headless

**Symptom:**
```
RuntimeError: Operator bpy.ops.mesh.extrude_region_move.poll() failed, context is incorrect
RuntimeError: Operator bpy.ops.mesh.loopcut.poll() failed, context is incorrect
```

**Cause:** `bpy.ops.mesh.*` operators check for Edit Mode context (active 3D viewport, object in
edit mode). In headless scripts this context is absent.

**Fix:** Use `bmesh.ops.*` instead — it has zero context dependency:
```python
# WRONG (headless)
bpy.ops.mesh.extrude_region_move(...)

# CORRECT (headless)
ret = bmesh.ops.extrude_face_region(bm, geom=faces)
```

**If you must use bpy.ops.mesh.* (last resort):**
```python
bpy.context.view_layer.objects.active = obj
obj.select_set(True)
bpy.ops.object.mode_set(mode='EDIT')
# ... bpy.ops.mesh calls ...
bpy.ops.object.mode_set(mode='OBJECT')
```

**Safe `bpy.ops.object.*` that DO work headless** (after setting active object):
- `bpy.ops.object.modifier_apply(modifier=name)`
- `bpy.ops.object.modifier_move_to_index(modifier=name, index=n)`
- `bpy.ops.object.shade_smooth()`

---

## §G2. use_auto_smooth Removed in Blender 4.1 (AttributeError)

**Symptom:**
```
AttributeError: 'Mesh' object has no attribute 'use_auto_smooth'
```

**Cause:** Blender 4.1 removed `mesh.use_auto_smooth` and `mesh.auto_smooth_angle`.
The replacement is the "Smooth by Angle" Geometry Nodes modifier.

**Fix:** Use `_add_smooth_by_angle()` from `references/modifier-stack.md §4`.

**Compatibility wrapper:**
```python
import bpy, math

def set_auto_smooth(obj, angle_degrees=30.0):
    if bpy.app.version < (4, 1, 0):
        obj.data.use_auto_smooth = True
        obj.data.auto_smooth_angle = math.radians(angle_degrees)
    else:
        _add_smooth_by_angle(obj, angle_degrees)  # from modifier-stack.md
```

**Version matrix:**
| Blender | Smooth method |
|---|---|
| < 4.1 | `mesh.use_auto_smooth = True` + `mesh.auto_smooth_angle` |
| 4.1+ | Smooth by Angle GN modifier (must be LAST in stack) |

---

## §G3. SmoothByAngle Must Be Last in Stack

**Symptom:** Wrong shading on parts of the mesh that should be smooth, or hard edges where none
were intended.

**Cause:** Smooth by Angle was added via the UI right-click menu (or modifier_add_node_group op)
when other modifiers were present, and landed at a middle position in the stack instead of last.

**Detect:**
```python
last_mod = obj.modifiers[-1] if obj.modifiers else None
if last_mod and last_mod.type != 'NODES':
    print(f"WARNING: last modifier '{last_mod.name}' type={last_mod.type} — not SmoothByAngle")
```

**Fix:** Explicitly move it after adding:
```python
bpy.context.view_layer.objects.active = obj
bpy.ops.object.modifier_move_to_index(
    modifier=smooth_mod.name,
    index=len(obj.modifiers) - 1,
)
```

---

## §G4. WeightedNormal + SmoothByAngle Wrong Order (Shading Seam)

**Symptom:** Flat faces on a beveled hard-surface mesh show a visible shading seam near the bevel.
The large flat face's normal doesn't dominate as expected.

**Cause (Blender tracker issue #121620):** WeightedNormal placed ABOVE SmoothByAngle produces
broken shading. The UI change workaround adds SmoothByAngle after WeightedNormal, but if
SmoothByAngle ends up above WeightedNormal (e.g., from a reorder or script error), the bug
manifests.

**Fix:** Enforce the order with `modifier_move_to_index`:
```python
# Find indices
mods = list(obj.modifiers)
names = [m.name for m in mods]

wn_idx   = next((i for i,m in enumerate(mods) if m.type == 'WEIGHTED_NORMAL'), -1)
sba_idx  = next((i for i,m in enumerate(mods) if m.type == 'NODES' and
                 'Smooth' in m.name), -1)

if wn_idx > sba_idx and sba_idx >= 0:
    # SmoothByAngle is above WeightedNormal — fix it
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.modifier_move_to_index(
        modifier=mods[sba_idx].name,
        index=len(mods) - 1,
    )
```

**Correct order assertion:**
```
WeightedNormal appears before SmoothByAngle in obj.modifiers list order.
SmoothByAngle is at index len(obj.modifiers)-1.
```

---

## §G5. Exit Code 0 on Python Exception (Silent Failure)

**Symptom:** PowerShell reports `$LASTEXITCODE = 0` even though the Blender script threw an
exception. CI passes, geometry is wrong or missing.

**Cause:** Blender exits 0 by default regardless of Python exceptions.

**Fix (two-part):**
1. Add `--python-exit-code 1` to the PowerShell invocation:
   ```powershell
   & $BLENDER_EXE --background --factory-startup --python-exit-code 1 --python script.py ...
   ```
2. Wrap `main()` in the script with an explicit `sys.exit(1)`:
   ```python
   try:
       main()
   except Exception:
       import traceback
       traceback.print_exc()
       sys.exit(1)
   ```

**Detection:** Also check for a sentinel string in stdout:
```powershell
$output = & $BLENDER_EXE ... 2>&1
if ($output -notmatch "FORGE_MODEL_PASS") {
    throw "Script did not reach success sentinel"
}
```

---

## §G6. EEVEE Headless: Black Image on Windows

**Symptom:** EEVEE render produces a black PNG or crashes without a useful error.

**Cause:** EEVEE Next (Blender 4.2+) uses Vulkan/OpenGL and requires a display adapter or GPU
context. Windows machines without a GPU, or running in a headless shell without display, may
have no valid context for EEVEE.

**Fix:** Use Cycles with CPU for all Forge headless renders:
```python
scene.render.engine = 'CYCLES'
scene.cycles.device = 'CPU'    # explicit: --factory-startup defaults to CPU, but be explicit
```

**Detection:**
```python
if not os.path.exists(args.output):
    # No file = crash
    raise RuntimeError("Render failed — no output file (possible EEVEE GPU crash)")
size = os.path.getsize(args.output)
if size < 1000:
    # 0 or very small = black frame
    raise RuntimeError(f"Render output suspiciously small ({size} bytes) — try Cycles CPU")
```

---

## §G7. Absolute vs // Paths in Render Output

**Symptom:** Render output goes to Blender's installation directory, or `//` is treated literally.

**Cause:** `//` is Blender's relative-to-.blend-file prefix. In headless scripts without a saved
.blend file, `//` is undefined or resolves to the Blender executable directory.

**Fix:** Always use `os.path.abspath()`:
```python
import os
out_path = os.path.abspath(args.output)
os.makedirs(os.path.dirname(out_path), exist_ok=True)
scene.render.filepath = out_path
```

**Windows path discipline:**
- PowerShell invocation: `"C:\absolute\path\out.png"` (backslash OK in PowerShell)
- Inside Blender Python: use forward slashes `"C:/absolute/path/out.png"` OR `os.path.abspath()`
- `Path(...).resolve()` from pathlib also works inside Blender's bundled Python

---

## §G8. Boolean Solver Failure on Non-Manifold Mesh

**Symptom:** Boolean modifier result is empty, topology is wrong, or Blender logs "no intersection".

**Cause:** `solver='EXACT'` requires the cutter mesh to be manifold (every edge has exactly
2 faces). Interior faces, duplicate vertices, or open boundaries cause failure.

**Detect:**
```python
import bmesh as bm_mod
def is_manifold(obj):
    bm = bm_mod.new()
    bm.from_mesh(obj.data)
    result = all(len(e.link_faces) == 2 for e in bm.edges)
    bm.free()
    return result

if not is_manifold(cutter):
    raise ValueError(f"Cutter '{cutter.name}' is not manifold — Boolean will fail")
```

**Fix:**
1. Set `bool_mod.solver = 'EXACT'` + `bool_mod.use_hole_tolerant = True`.
2. Ensure cutter has no internal faces: open in edit mode, delete face interior.
3. Remove duplicate vertices: `bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.0001)`.
4. Fill holes: `bmesh.ops.edgeloop_fill(bm, edges=[...])` for open boundary loops.

---

## §G9–§G17. Quick-Reference Table

| # | Symptom | Fix |
|---|---|---|
| G9 | `IndexError` on `bm.verts[n]` after extrude/subdivide | Call `bm.verts/edges/faces.ensure_lookup_table()` after every topology-changing op |
| G10 | RAM grows in batch loops using evaluated meshes | Wrap `obj_eval.to_mesh()` in `try/finally obj_eval.to_mesh_clear()` |
| G11 | Array count=1 with `FIT_CURVE` | Set `array.fit_type='FIT_CURVE'` AND `array.curve=obj` together |
| G12 | Wrong vertices merged at mirror plane | `mirror.merge_threshold = 0.001` (1mm); old .blend files may have 0.01 |
| G13 | `modifier_add_node_group` returns CANCELLED on Windows | Use raw string `r"geometry_nodes\smooth_by_angle.blend\NodeTree\Smooth by Angle"`; or use `libraries.load()` path (preferred) |
| G14 | `unknown argument, loading as file: --python script.py` | Each flag must be a separate list element in `subprocess.run([...])` |
| G15 | `--render-output` has no effect | `--render-output` must precede `--render-frame` (Blender processes left-to-right); `--` separator must precede custom args |
| G16 | Crash after depsgraph update using stored reference | Never cache `bpy_struct` across state changes; re-fetch from `bpy.data` by name |
| G17 | RAM grows during batch bmesh work | Every `bmesh.new()` paired with `bm.free()` in `try/finally` |
