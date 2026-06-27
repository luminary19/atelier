---
name: forge-topology
version: 1.0.0
description: >
  Forge suite — topology & edge-flow discipline. Audit, repair, and enforce mesh
  quality before any downstream work (subdivision, rigging, baking, export, booleans).
  Produces: JSON topology report, auto-repaired mesh, wireframe QA PNG, LOD chain
  GLBs, and boolean-cleaned geometry.
  Use whenever you need to: audit topology, fix non-manifold geometry, check or place
  poles, enforce quad flow, retopologize a high-poly mesh, generate an LOD chain,
  decimate for web/game budgets, run QuadriFlow or Voxel remesh, bake high-to-low
  normals, repair after a boolean operation, validate watertightness, apply a TRS or
  axis-swap to an existing mesh, serialize a quaternion for export, or bake handedness/
  up-axis conversion into the geometry before export.
  Defining the project-wide coordinate system, handedness, scale unit and pivot rules is
  **forge-standards**'s job — this skill OPERATES on a mesh, it does not set the standard.
  Also triggers on: "bad normals", "flipped faces", "ngon cleanup", "LOD0 LOD1 LOD2",
  "simplify mesh", "reduce polycount", "retopo", "manifold check", "gltfpack",
  "mesh is broken", "fix topology", "apply transforms to mesh", "bake axis swap into mesh",
  "quaternion order for export", "slerp", "serialize rotation".
  HEADLESS-ONLY: driven from code, output verified by reading a PNG. Part of the Forge suite.
triggers:
  - topology audit
  - non-manifold
  - edge flow
  - retopo
  - retopology
  - LOD chain
  - decimate
  - QuadriFlow
  - boolean cleanup
  - watertight
  - fix normals
  - pole valence
  - quad mesh
  - ngon
  - apply transforms to mesh
  - bake axis swap into mesh
  - quaternion slerp
  - serialize rotation for export
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
---

# forge-topology — Topology, Retopo, LOD, Boolean Cleanup & Transform Math

The mesh-quality gate. Every downstream skill (rigging, UV, bake, export, subdivision)
fails silently on broken topology. This skill audits, repairs, and enforces correctness
before the pipeline continues.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it
> carries the target engine, coordinate system (Y-up/Z-up), handedness, scale unit,
> poly budget, and output paths. All decisions in this skill are constrained by FORGE.md.
> When no FORGE.md is present, ask **forge-brief** to create one (Run = call the Skill
> tool with name `forge-brief`).
> If **ATELIER.md** is present, note the aesthetic world/signature — it can inform
> edge-flow density and silhouette-preservation targets during retopo/decimation.

---

> **Suite map**
>
> | Upstream | This skill | Downstream |
> |---|---|---|
> | **forge-model** (raw bpy mesh) | **forge-topology** (audit → repair → LOD → coords) | **forge-uv** (unwrap) |
> | **forge-parametric** (CAD/OpenSCAD output) | | **forge-texture** (bake H→L) |
> | **forge-procedural** (Geo-Nodes output) | | **forge-rig** (armature/skin) |
> | **forge-intake** (scans/AI output) | | **forge-export** (glTF/FBX/USD) |
> | | | **forge-validate** (final gate) |
>
> **forge-standards** is the canonical home for coordinate-system tables, handedness,
> pivots and poly budgets — read it when you need the full reference (Run = Skill tool
> `forge-standards`).
> **Web handoff (ordered):** **forge-export** (glTF/GLB) → **forge-optimize**
> (Draco/Meshopt/KTX2) → **atelier-webgl** (R3F/Three.js scene). forge-export owns
> engine-specific export settings; forge-optimize owns gltf-transform + KTX2 compression.

---

## Decide first — pick the tool and verify it is available

Before any execution, identify which tool the task requires and confirm it exists:

| Task | Primary tool | Fallback |
|---|---|---|
| Topology audit + repair on .blend/.glb/.fbx | Blender 4.5 LTS + bmesh | trimesh (triangle meshes only) |
| LOD chain from GLB for web | gltfpack CLI | gltf-transform CLI (Node.js) |
| Quad remesh / retopo | Blender QuadriFlow | Instant Meshes (batch mode) |
| Boolean CSG (programmatic) | manifold3d (pip) | Blender EXACT solver |
| Mesh repair without Blender | trimesh + PyMeshLab | Open3D |
| Coordinate / transform math | Blender bpy + mathutils | numpy + transforms3d (pip) |

**Run the preflight check first** (invoke `forge`'s `scripts/probe.py` to confirm tool
availability, or run the PowerShell one-liner below):

```powershell
# Verify Blender is reachable — adjust path if installed elsewhere
$b = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
& $b --version | Select-Object -First 1
```

If Blender is missing, fall back to the pure-Python tier (trimesh / manifold3d / Open3D)
for the subset of tasks they can handle. Document the fallback in a comment.

**Run = call the Skill tool with the exact name. Writing "next: forge-uv" in prose
runs nothing.**

---

## The flow

**1. Read FORGE.md** — extract: target engine, coordinate system, poly budget, output paths.
   If absent, call Skill(`forge-brief`) before continuing.

**2. Preflight** — verify tool availability (Blender exe path, gltfpack/gltf-transform on
   PATH, manifold3d installed). Fail loudly if the required tool is missing; do not silently
   downgrade without logging the fallback.

**3. Classify the task** — pick exactly one lane from the table below:

   | Lane | Trigger | Reference |
   |---|---|---|
   | A — Audit + repair | Non-manifold edges, bad normals, ngons, high-valence poles | `references/topo-audit-repair.md` |
   | B — Retopo + LOD | Sculpt/scan/CAD needs retopologized mesh or LOD chain | `references/retopo-lod.md` |
   | C — Boolean cleanup | Post-boolean debris, coplanar artifacts, union/difference CSG | `references/boolean-csg.md` |
   | D — Transform / coordinate math | Axis swap, handedness, TRS apply, quaternion serialization | `references/transform-math.md` |
   | E — Mesh-processing lib | trimesh / Open3D / PyMeshLab repair, decimate, validate | `references/mesh-libs.md` |

   **Read the relevant reference file** before executing. Each file contains
   copy-paste-ready code, parameter tables, and gotcha→fix tables.

**4. Execute headlessly** — emit a `.py` script or PowerShell invocation; run it via Bash
   or PowerShell. The mandatory Blender invocation pattern:

   ```
   blender -b scene.blend -P script.py -- --input C:/path/mesh.glb --output C:/path/out.json
   ```

   The `--` separator is **non-negotiable**. Without it, Blender tries to parse your script
   args as blend filenames and fails silently. Use absolute forward-slash paths in all Python
   filepath strings inside Blender scripts.

**5. Validate** — after every repair or LOD generation, run the quality-gate check:
   read the JSON audit report and confirm all thresholds pass (>90% quads, 0
   non-manifold edges, 0 flipped normals, 0 degenerate faces for subdivision/deform
   meshes; see `references/topo-audit-repair.md §Quality gates`).

**6. Render wireframe PNG** — use Blender Workbench engine to render a wireframe
   overlay, then call `Read` on the PNG to visually confirm: continuous loops at
   joints, even density, no stray edges, poles in flat zones.

**7. Hand off** — once topology is clean:
   - UV work → Skill(`forge-uv`)
   - Baking → Skill(`forge-texture`)
   - Rigging → Skill(`forge-rig`)
   - Export → Skill(`forge-export`)
   - Web delivery → Skill(`forge-export`) → Skill(`forge-optimize`) → Skill(`atelier-webgl`)
   - Final gate → Skill(`forge-validate`)

---

## Operating principles

- **Verify before trusting.** Run `topo_audit.py` before and after every repair or
  boolean. Read back the JSON report; do not assume the operation succeeded.
- **Always free bmesh.** Wrap every `bm = bmesh.new()` in `try/finally: bm.free()`.
  Leaking bmesh objects causes OOM on batch jobs — this is the #1 headless crash.
- **Cascade LOD decimation, never re-decimate from source.** Each LOD is generated
  from the previous LOD using step ratios. From-source decimation produces visual
  discontinuities at LOD transitions.
- **Coordinate math is typed.** Scale swizzles have no sign flip; location swizzles do.
  Quaternion component order differs between Blender (w,x,y,z) and glTF/Unity/Unreal
  (x,y,z,w). Confusing them is silent and produces wrong geometry in the target engine.
- **Booleans require watertight inputs and produce broken topology.** Always validate
  manifold status before a boolean and run audit + repair immediately after. Use the
  Blender `EXACT` solver (not `MANIFOLD` — bug #140590 in Blender 4.5, coplanar faces).
