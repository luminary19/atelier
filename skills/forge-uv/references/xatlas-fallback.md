# forge-uv — xatlas Fallback Reference (no Blender)

# Contents
- §1. When this fallback applies
- §2. xatlas unwrap recipe (pure Python)
- §3. Writing the UVs back out
- §4. Headless checker QA without Blender
- §5. Caveats — what xatlas does NOT give you

---

## §1. When this fallback applies

The decide-first gate degrades to xatlas **only** when Blender is absent AND the task is the
"clean non-overlapping UVs for baking" path. xatlas (an Python binding over Thekla/xatlas, the
same library Godot and many engines use for lightmap UVs) generates a non-overlapping atlas
headlessly with zero Blender dependency.

**xatlas covers:** generating a valid, non-overlapping bake/lightmap UV channel for an arbitrary
triangle mesh, headless, on a box with no Blender install.

**xatlas does NOT cover:** manual/artistic seam placement, texel-density normalization to a target
px/m, UDIM tile layout, the `io_mesh_uv_layout` reference PNG, or `CONCAVE` packing density. Those
remain Blender-only (the gate stops and reports if they are required).

Install: `pip install xatlas` (also needs `pip install trimesh numpy` for I/O and QA).

---

## §2. xatlas unwrap recipe (pure Python)

xatlas works on a triangle mesh. Load with trimesh, parametrize, then carry the new UVs back.
`xatlas.parametrize` **re-indexes** vertices (a vertex on a UV seam is split), so it returns a
vertex remap you MUST apply to positions and faces.

```python
"""
xatlas_unwrap.py — headless UV unwrap WITHOUT Blender (bake-channel fallback).
Pure Python: xatlas + trimesh + numpy. Windows: use `python`, not `python3`.
Usage:
    python xatlas_unwrap.py --in mesh.obj --out mesh_uv.obj
"""
import sys, io, argparse
if sys.stdout.encoding and sys.stdout.encoding.lower() != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import numpy as np
import trimesh
import xatlas


def unwrap_with_xatlas(in_path: str, out_path: str):
    mesh = trimesh.load(in_path, force="mesh")
    if mesh.is_empty or len(mesh.faces) == 0:
        print(f"[ERROR] {in_path}: no faces to unwrap")
        sys.exit(1)

    # parametrize returns: vmapping (per-output-vert -> source vert index),
    #                      indices (new face index array, shape (F, 3)),
    #                      uvs (per-output-vert UV, shape (V, 2), already in 0-1, non-overlapping)
    vmapping, indices, uvs = xatlas.parametrize(mesh.vertices, mesh.faces)

    # Rebuild the mesh on the new (seam-split) vertex set.
    new_vertices = mesh.vertices[vmapping]
    new_mesh = trimesh.Trimesh(vertices=new_vertices, faces=indices, process=False)
    # Attach UVs as a TextureVisuals so OBJ export carries vt coords.
    new_mesh.visual = trimesh.visual.TextureVisuals(uv=uvs)

    new_mesh.export(out_path)
    print(f"[INFO] xatlas unwrap: {len(mesh.faces)} faces -> {len(indices)} faces, "
          f"{len(uvs)} UV verts, written {out_path}")
    print("[INFO] xatlas guarantees a non-overlapping atlas (bake channel ready). "
          "Seam/TD/UDIM control NOT available — Blender required for those.")
    return new_mesh


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="in_path", required=True)
    ap.add_argument("--out", dest="out_path", required=True)
    args = ap.parse_args()
    unwrap_with_xatlas(args.in_path, args.out_path)


if __name__ == "__main__":
    main()
```

**Tuning (optional):** for finer control use the `xatlas.Atlas` object and pass
`ChartOptions` / `PackOptions` (e.g. `pack_options.padding`, `pack_options.resolution`,
`chart_options.max_cost`) before `atlas.generate(...)`. The one-shot `parametrize()` above uses
library defaults, which are sufficient for a baking channel.

---

## §3. Writing the UVs back out

- **OBJ**: `new_mesh.export("mesh_uv.obj")` writes `vt` UV coordinates directly (above).
- **GLB**: `new_mesh.export("mesh_uv.glb")` carries `TEXCOORD_0` for the web/`forge-export` path.
- **Round-trip into Blender later**: if Blender becomes available, import the xatlas OBJ/GLB and
  the atlas UVs come in as the active UV layer — you can then refine seams or normalize TD there.

xatlas UVs are already inside the 0–1 tile and non-overlapping, so the overlap gate
(`detect_overlaps_bmesh`, seams-packing §8, when Blender is present) passes by construction.

---

## §4. Headless checker QA without Blender

The Cycles checker render (validation.md §2) needs Blender. Without it, do the visual QA with the
pure-Python depth/checker render from **forge-topology `references/mesh-libs.md §7`** (trimesh ray
casting + PIL — no GPU, no display). Render the unwrapped mesh, `Read` the PNG, and check the same
criteria from validation.md §6 (uniform cell size, square cells, no overlap bright spots). It is a
coarser image than a Cycles checker, but it confirms the atlas is sane headless.

```python
# Re-uses forge-topology's render_depth_png (mesh-libs.md §7) for a no-Blender QA image.
# from mesh_libs import render_depth_png
# render_depth_png("mesh_uv.obj", "C:/forge-build/out/uv_xatlas_qa.png")
# then: Read("C:/forge-build/out/uv_xatlas_qa.png")
```

---

## §5. Caveats — what xatlas does NOT give you

| Capability | xatlas | Action if required |
|------------|--------|--------------------|
| Non-overlapping bake/lightmap UVs | YES | use this fallback |
| Artistic / hidden-edge seam placement | NO (auto seams only) | requires Blender |
| Texel-density normalization to target px/m | NO | requires Blender (texel-density.md §4) |
| UDIM tile layout | NO | requires Blender (udim.md) |
| `io_mesh_uv_layout` reference PNG | NO | requires Blender; or use §4 checker QA |
| `CONCAVE` high-density packing | NO (rectangular charts) | requires Blender pack_islands |

**Rule:** take the xatlas fallback for the bake-channel case and **say so in a comment**
(e.g. `# xatlas fallback — no Blender; seam/TD/UDIM control unavailable`). If the brief needs
seam craft, TD normalization, or UDIMs, stop and report that Blender is required — do not pretend
xatlas delivered them.
