---
name: forge-procedural
version: 1.0.0
description: >
  Forge suite — procedural geometry craft skill. Build mesh from code, not hand-modeling:
  Blender Geometry Nodes scripted via Python (scatter, greeble, curve-sweep, noise displacement),
  SDF/implicit surfaces (fogleman/sdf, marching cubes, dual contouring, gyroid/TPMS), and generative
  systems (L-system branching, Wave Function Collapse modular kit-bash). Use whenever the task is
  "generate geometry procedurally", "scatter objects on a surface", "grow a tree/plant/coral
  structure", "create a gyroid or lattice infill", "make a greeble detail pass", "build a modular
  tileset", "implicit surface", "SDF", "Geometry Nodes from Python", "parametric scatter", or
  "seeded reproducible geometry". Output is a headless-rendered PNG (Cycles CPU) for visual QA
  plus GLB/STL/OBJ for downstream use. HEADLESS-ONLY: driven from code, output verified by reading
  a PNG. Part of the Forge suite.
triggers:
  - geometry nodes python
  - scatter objects blender
  - l-system tree plant
  - sdf implicit surface
  - gyroid tpms lattice
  - greeble detail
  - wave function collapse
  - procedural geometry
  - seeded scatter
  - forge procedural
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# Forge — Procedural Geometry

Procedural geometry = mesh born from a function, not a modeler's hand. The same seed always produces
the same mesh; the same script, parametrized differently, produces infinite variation. Every output
is verified by rendering to PNG and reading the image.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries the
> render engine, coordinate system, poly budget, output paths, and any Atelier aesthetic link for
> this project. Write it via **`forge-brief`** before beginning. When **`ATELIER.md`** is also present,
> extract the world, aesthetic, signature moment, and primary OKLCH hue — these map directly to
> procedural parameters (scatter density, silhouette, branch angle, scatter scale).

---

> **Suite map:**
> - Entry / orchestration: **`forge`** (router) → **`forge-brief`** (writes FORGE.md) → **`forge-standards`** (units, budgets, naming)
> - Geometry peers: **`forge-model`** (polygon/bmesh modeling), **`forge-parametric`** (OpenSCAD/CadQuery code-CAD), **`forge-topology`** (retopo/LOD/booleans)
> - Downstream: **`forge-uv`** (unwrap), **`forge-material`** (PBR), **`forge-texture`** (bake), **`forge-light`** (rigs), **`forge-render`** (headless PNG)
> - Validation gate: **`forge-validate`** (manifold, watertight, normals, render QA) — run before any export
> - Export / web: **`forge-export`** → **`forge-optimize`** (Draco/Meshopt) → **`atelier-webgl`** handoff
> - Atelier seam: **`atelier-direction`** supplies aesthetic intent (density, silhouette, OKLCH hue) that maps to GN parameters
>
> **Run = call the Skill tool with the exact name. Writing "now run forge-validate" in prose runs nothing.**

---

## Decide first: tool + availability

Before writing any geometry code, answer two questions:

1. **Which generation method fits the task?**

| Task | Method | Why |
|------|--------|-----|
| Scatter objects on surface, greeble, sweep, deform | Geometry Nodes (bpy) | Native Blender, zero-cost instances, seeded, exports via `export_apply=True` |
| Organic blend, gyroid infill, smooth CSG, implicit form | SDF / fogleman/sdf + skimage | Pure Python, no build step, handles infinite-blend well |
| Sharp-corner CAD shapes from implicit (mechanical) | SDF + Dual Contouring (isomesh) | QEF vertex placement preserves hard edges |
| Plant / tree / coral / circuit — branching growth | L-system (pure bpy turtle interpreter) | No external deps; seeded; depth ≤ 6 interactive |
| Modular building / dungeon / circuit tile assembly | Wave Function Collapse (pure bpy) | Constraint-propagation; seeded retry loop |
| Complex L-system botany (reference quality) | L-Py (conda env) → OBJ → bpy import | Requires separate conda env; pipe via OBJ |

2. **Is the tool available?** Run the preflight from **`forge`**'s `scripts/probe.py`. For SDF work verify with an import probe in system Python: `python -c "import sdf, skimage, trimesh; print('sdf stack OK')"` (the package installs from the GitHub URL but its distribution/import name is `sdf` — `pip show fogleman/sdf` always reports "not found"; the pip-based variant is `pip show sdf scikit-image trimesh`). For Geometry Nodes, Blender 4.2 LTS or newer is required (`ng.interface.new_socket` API). **Do not begin until the tool is confirmed present.**

**Windows headless truths (non-negotiable):**
- Render engine: **Cycles** (CPU fallback) — EEVEE-Next is unsupported headless on Windows.
- Invocation: `blender -b scene.blend -P script.py -- <args>` — the `--` separator is mandatory.
- Blender path: always absolute forward-slash (e.g. `C:/Program Files/Blender Foundation/Blender/blender.exe`).
- `python` not `python3`; UTF-8 stdout wrapper at the top of every script.
- `os.makedirs(out_dir, exist_ok=True)` before any render or export — Blender will NOT create directories.

---

## The flow

1. **Read FORGE.md** (if present) → extract render engine, coordinate system, poly budget, output paths, Atelier aesthetic link. If absent, invoke Skill(`forge-brief`) first.

2. **Decide: method + availability gate** (see table above). Confirm Blender version ≥ 4.2 for GN work; confirm SDF stack installed for implicit work. Log the decision.

3. **Design parameters** — derive the key numbers from FORGE.md + brief: density (scatter), depth + angle (L-system), period + resolution (gyroid), grid dimensions (WFC), SDF blend radius `k`. Map aesthetic intent (silhouette, density, scale) to numeric inputs.

4. **Write the generation script** — one `.py` file per generation method. Use the canonical boilerplate:
   - GN: `create_gn_modifier()` idempotent pattern; `ng.interface.new_socket()` (Blender 4.0+ API).
   - SDF: `fogleman/sdf` or `skimage.measure.marching_cubes`; always clip infinite SDFs to a finite box; use `sparse=False` for non-uniform scale ops.
   - L-system: separate `derive()` + `turtle_to_mesh()` functions; `random.Random(seed)` (never global `random.seed()`).
   - WFC: `solve_wfc()` with 10-attempt retry loop; `wfc_connectors` JSON on each module object.
   - All scripts: `argparse` after `--` separator; `--seed INT`; `--out PATH`; UTF-8 stdout wrapper.
   - Full script reference: **`references/gn-patterns.md`**, **`references/sdf-patterns.md`**, **`references/generative-patterns.md`**.

5. **In-script validation** — before rendering, call the appropriate validator:
   - GN: `validate_gn_output(obj, mod_name)` → checks vertex/face count > 0.
   - SDF: `validate_sdf_mesh(path)` → watertight, Euler=2, no degenerate faces.
   - L-system: `validate_lsystem_output(obj)` → min verts, non-degenerate bounding box.
   - Full validator snippets: **`references/validation-qa.md`**.

6. **Render to PNG (headless Cycles)** — set `scene.render.engine = 'CYCLES'`; `scene.cycles.samples = 64`; place camera + sun light; call `bpy.ops.render.render(write_still=True)`. Output path: `FORGE.md → Output paths` (default `.forge-build/out/<slug>_procedural.png`). Use absolute forward-slash path.

7. **Read the PNG** — call `Read(png_path)`. Visually inspect:
   - All black → camera not set as `scene.camera`, or output path directory missing.
   - All grey → no lighting; add `bpy.ops.object.light_add(type='SUN')`.
   - Point cloud / degenerate mesh → instances not realized (add `GeometryNodeRealizeInstances`) or SDF bounding box too tight.
   - Fix and re-render until the image shows the intended geometry.

8. **Export** — once the render passes:
   - GN mesh: `bpy.ops.export_scene.gltf(filepath=path, export_apply=True)` (applies modifier, realizes instances).
   - SDF mesh: `trimesh_mesh.export('out.glb')` (trimesh writes correct normals).
   - L-system / WFC: select placed objects, `export_scene.gltf(use_selection=True, export_apply=True)`.

9. **Gate: invoke Skill(`forge-validate`)** — manifold, watertight, normals, poly budget, render QA. Resolve any CRITICAL or HIGH issues before passing downstream.

10. **Hand off** — if this is a web asset: Skill(`forge-export`) → Skill(`forge-optimize`) → Skill(`atelier-webgl`).

---

## References (deep detail — load on demand)

Read these files when the corresponding method is chosen; do NOT load all upfront:

| File | When to read |
|------|-------------|
| **`references/gn-patterns.md`** | Geometry Nodes via Python: node identifiers, interface API, scatter/greeble/sweep full scripts, gotcha table |
| **`references/sdf-patterns.md`** | SDF/implicit: fogleman/sdf, skimage MC, dual contouring, TPMS/gyroid, smin variants, resolution table, gotcha table |
| **`references/generative-patterns.md`** | L-systems, WFC, seeded RNG rules, Poisson vs Random scatter, bpy gotchas |
| **`references/validation-qa.md`** | In-script validators (GN, SDF, L-system, WFC), render-verify snippet, PowerShell QA shell |

---

## Operating principles

- **Decide before writing.** Pick the generation method and verify availability before a single line of geometry code is written. Guessing and pivoting mid-script wastes context and time.
- **Seed everything explicitly.** Every `FunctionNodeRandomValue`, `DistributePointsOnFaces`, `random.Random`, and `np.random.default_rng` call must receive a controlled seed derived from a single `--seed` CLI argument. Same seed = same mesh, every run.
- **Idempotent scripts.** Remove existing node groups and modifiers by name before recreating them (`obj.modifiers.get(name)` → remove if exists; `bpy.data.node_groups.get(name)` → remove if exists). Scripts that run twice must not accumulate `.001` suffixes.
- **Verify with eyes, not just file size.** `Read` the rendered PNG and inspect it visually. A 50 KB file is not a pass; a non-black image showing the expected silhouette is.
- **Never realize instances early.** Unrealized instances are free in Cycles. Realize only at export (`export_apply=True`) or when downstream ops require real mesh data. Realizing 100k instances at runtime is 100× the memory.
