# Forge — Polycount Budgets, Texel Density, LOD Ratios & Asset Standards

## Contents
- §1. Polycount budgets by asset class and target
- §2. Texel density tiers
- §3. LOD ratios and chain generation
- §4. UV utilization and channel conventions
- §5. Draw-call and file-size ceilings (web)
- §6. FORGE_STANDARDS.json schema
- §7. Git LFS setup for binary assets

---

## §1. Polycount budgets

All values in **triangles** (the GPU primitive). Polygons ≈ tris ÷ 2 for quad meshes.

### PC / Console — current-gen AAA (UE5 / Unity 2025)

| Asset class | LOD0 (0–10 m) | LOD1 (10–30 m) | LOD2 (30–60 m) | LOD3 (>60 m / imposter) |
|---|---|---|---|---|
| Hero character (PC protagonist) | 50K–100K | 25K–50K | 10K–25K | 2K–5K |
| Main NPC / companion | 20K–60K | 10K–30K | 5K–15K | 1K–3K |
| Background NPC / crowd filler | 5K–15K | 2.5K–7.5K | 1K–3K | 500–1K |
| Boss / hero enemy | 30K–80K | 15K–40K | 7.5K–20K | 2K–5K |
| Weapon — FPS (in-hand) | 15K–30K | 7.5K–15K | 3K–7.5K | — |
| Weapon — TPS (small on screen) | 5K–15K | 2.5K–7.5K | 1K–3K | — |
| Vehicle — hero / driveable | 30K–80K | 15K–40K | 7.5K–20K | 2K–5K |
| Vehicle — background | 10K–25K | 5K–12.5K | 2.5K–6K | 500–2K |
| Hero prop (interactive / pickup) | 3K–15K | 1.5K–7.5K | 750–3K | 100–500 |
| Small prop (coin, can) | 500–3K | 250–1.5K | 100–750 | 50–200 |
| Environment — modular wall/floor | 500–3K | 250–1.5K | 100–500 | Billboard |
| Environment — hero set-piece | 5K–30K | 2.5K–15K | 1K–5K | 500–2K |
| Foliage (tree LOD0) | 5K–15K | 2.5K–7.5K | 1K–3K | Billboard |
| Creature — large (4 m+) | 20K–50K | 10K–25K | 5K–12.5K | 1K–3K |

**Nanite note (UE5):** With Nanite on, tri count is virtualised — budget by VRAM and
shadow-casting draw calls instead. Non-Nanite assets (transparent, masked, skeletal) still
need manual LODs.

### Mobile — mid-range Android (Snapdragon 7-series, ~2022 baseline)

| Asset class | LOD0 | LOD1 | LOD2 |
|---|---|---|---|
| Hero character | 3K–8K | 1.5K–4K | 500–1.5K |
| NPC | 1K–4K | 500–2K | 200–800 |
| Hero prop | 500–2K | 250–1K | 100–400 |
| Small prop | 100–500 | 50–250 | 20–100 |
| Environment element | 200–1.5K | 100–750 | 50–300 |
| **Scene total budget** | 50K–150K | — | — |

iOS devices support roughly 2× the triangle budget of equivalent-tier Android.

### Web / WebGL / WebAR (three.js, model-viewer, R3F, Babylon.js)

| Asset class | Triangle limit | GLB file limit |
|---|---|---|
| Any single asset | ≤ 50,000 tri | ≤ 4 MB incl. textures |
| Hero / complex object | 20K–50K | — |
| Environment / background | 5K–15K | — |
| Full scene budget | ≤ 150,000 tri | ≤ 12 MB total |

DRACO compression reduces GLB geometry by 60–80%. KTX2 textures compress VRAM 4–8×.

### 3D print / CAD

| Constraint | Value |
|---|---|
| Minimum wall thickness (PLA, non-load) | 1.5 mm |
| Minimum wall thickness (PLA, structural) | 3.0 mm |
| Maximum overhang without supports | 45° from vertical |
| Manifold | Required (zero open edges, zero internal faces) |
| Triangle count | No budget; slicer handles it |

---

## §2. Texel density tiers

Formula: `Texel Density (px/m) = Texture Resolution (px) / Object Dimension (m)`

Example: 1 m × 1 m surface + 1024 × 1024 texture → 1024 px/m.

| Tier | px/m | Texture for 1 m² surface | Use case |
|---|---|---|---|
| Hero FPS / face / key close-up | 2048 | 2048×2048 | Weapon, main character face, hero prop |
| Standard PC / console foreground | 1024 | 1024×1024 | Standard prop, mid NPC |
| Mid-range environment | 512 | 512×512 (or 1024 tiled) | Background props, modular pieces |
| Background / distant | 256 | 256×256 or tiled atlas | Far geometry |
| Mobile foreground | 512 | 512×512 | Mid-range Android |
| Mobile background | 128–256 | Use tiled materials | |
| Web / WebAR / R3F hero | 512–1024 | 1024×1024 max to stay in GLB budget | |
| Crytek/CryEngine baseline | 512 | Green in Crytek debug view | |

**Blender headless check (pure bpy — no add-on required):**
```python
import bpy, bmesh, math

def calc_texel_density(obj, texture_res=1024):
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    uv_layer = bm.loops.layers.uv.active
    if not uv_layer:
        bm.free(); return None
    total_uv_area = 0.0
    total_world_area = 0.0
    for face in bm.faces:
        uvs = [loop[uv_layer].uv for loop in face.loops]
        if len(uvs) < 3:
            continue
        uv_area = abs(sum(
            (uvs[i].x * uvs[(i+1) % len(uvs)].y -
             uvs[(i+1) % len(uvs)].x * uvs[i].y)
            for i in range(len(uvs))
        ) / 2.0)
        total_uv_area += uv_area
        total_world_area += face.calc_area()
    bm.free()
    if total_world_area == 0:
        return None
    texels_covered = total_uv_area * (texture_res ** 2)
    return math.sqrt(texels_covered / total_world_area)

for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        td = calc_texel_density(obj, 1024)
        if td:
            print(f"{obj.name}: {td:.1f} px/m")
```

---

## §3. LOD ratios and chain generation

Standard LOD reduction ratios (Decimate modifier):

| LOD level | Ratio | Use |
|---|---|---|
| LOD0 | 1.0 (original) | 0–10 m camera distance |
| LOD1 | 0.5 (50%) | 10–30 m |
| LOD2 | 0.2 (20%) | 30–60 m |
| LOD3 | 0.05 (5%) | > 60 m / imposter |

**Always decimate from LOD0, not from previous LOD** — cascading reduces quality and
accumulates UV seam drift.

Headless LOD chain script stub:
```python
# blender -b scene.blend -P forge_lod.py -- --ratios 1.0 0.5 0.2 0.05
import bpy, sys, argparse

def generate_lod(base_obj, ratios):
    lod_coll = bpy.data.collections.new(f"{base_obj.name}_LODs")
    bpy.context.scene.collection.children.link(lod_coll)
    lod0 = base_obj.copy(); lod0.data = base_obj.data.copy()
    lod_objs = [lod0]
    for i, ratio in enumerate(ratios[1:], start=1):
        dup = lod_objs[0].copy(); dup.data = lod_objs[0].data.copy()
        dup.name = f"{base_obj.name}_LOD{i}"
        dup.data.name = dup.name
        lod_coll.objects.link(dup)
        mod = dup.modifiers.new("Decimate_LOD", 'DECIMATE')
        mod.ratio = ratio
        mod.use_symmetry = True
        mod.delimit = {'SEAM'}
        bpy.context.view_layer.objects.active = dup
        bpy.ops.object.modifier_apply(modifier="Decimate_LOD")
        lod_objs.append(dup)

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
ap = argparse.ArgumentParser()
ap.add_argument("--ratios", nargs="+", type=float, default=[1.0, 0.5, 0.2, 0.05])
args = ap.parse_args(argv)
for obj in bpy.context.selected_objects:
    if obj.type == 'MESH':
        generate_lod(obj, args.ratios)
```

---

## §4. UV utilization and channel conventions

**UV Channel 1 (index 0) — Primary texture map:**
- Utilization target: ≥ 85% (hero); ≥ 75% (environment props)
- No overlapping islands (unless intentionally mirrored — document it)
- All islands in 0–1 UV space
- Island padding: ≥ 2 px at target texture resolution; 4 px on 2048² maps
- Seams in low-visibility areas (inside geometry, along natural material breaks)

**UV Channel 2 (index 1) — Lightmap:**
- Named `LightmapUV` in Blender (UE5 auto-detects by name)
- Zero overlapping islands — hard requirement; overlap = bake artifact
- Padding: 2–4% of texture resolution (margin 0.02 in Blender Lightmap Pack)
- All islands in 0–1 space; no mirrored/stacked islands

**Texture suffix table (PBR pipeline):**

| Suffix | Map | Color space |
|---|---|---|
| `_BC` or `_D` | Base Color / Diffuse / Albedo | sRGB |
| `_N` | Normal (tangent-space) | Linear / Non-Color |
| `_ORM` | Packed: AO(R) Roughness(G) Metallic(B) | Linear / Non-Color |
| `_R` | Roughness (standalone) | Linear |
| `_M` or `_MT` | Metallic (standalone) | Linear |
| `_AO` | Ambient Occlusion | Linear |
| `_E` or `_EM` | Emissive | sRGB or Linear |
| `_H` | Height / Displacement | Linear |
| `_O` or `_A` | Opacity / Alpha | Linear |

ORM packing rationale: G channel gets the most bit precision under BC1/BC3 compression
(6 bits vs 5 for R/B). Roughness has the most perceptually-critical gradients → Green.
One ORM texture replaces three maps, saving ~4 MB per 2048² material at BC1.

---

## §5. Draw-call and file-size ceilings (web)

| Metric | Target | Hard limit |
|---|---|---|
| Draw calls per frame | < 100 | ≤ 300 (performance degrades severely above) |
| GLB hero asset | ≤ 2 MB (ideal) | ≤ 5 MB |
| GLB full scene | ≤ 8 MB | ≤ 12 MB |
| Static poster (WebP) | ≤ 150 KB | ≤ 300 KB |
| HDRI / environment | ≤ 512 KB | ≤ 2 MB |
| Texture per map (KTX2) | ≤ 256 KB | ≤ 1 MB |

Use instancing (`InstancedMesh` / `BatchedMesh` in Three.js) for repeated objects — each
unique draw call reduces from N to 1 per object type.

---

## §6. FORGE_STANDARDS.json schema

Write this at the project root for machine-readable validation. The `forge-validate` skill
reads this file. The top-level `"seed"` is the machine-readable mirror of FORGE.md's
`## Determinism` block — `forge-render` and `forge-validate` read it so render-compare runs
against a stable baseline (FORGE_PLAN §A: "idempotent rebuilds; seeded randomness").

> This schema is also maintained canonically by **`forge-standards`**
> (`forge-standards/references/forge-standards-schema.md`). When that copy is updated, keep the
> `"seed"` / `"cycles_animated_seed"` keys in sync there too — `forge-standards` writes the file
> other skills ingest.

```json
{
  "version": "1.0",
  "project": "<project-name>",
  "engine": "unreal5 | unity | godot | threejs | print | render-only",
  "seed": 0,
  "cycles_animated_seed": false,
  "profiles": {
    "console": {
      "max_tris_lod0": 50000,
      "max_tris_lod1": 25000,
      "max_tris_lod2": 12500,
      "max_tris_lod3": 3000,
      "required_lod_count": 3,
      "texel_density_px_m": 1024,
      "texel_density_hero_px_m": 2048,
      "max_texture_res": 4096,
      "min_uv_utilization": 0.80,
      "lm_uv_margin": 0.02,
      "lod_ratios": [1.0, 0.5, 0.2, 0.05],
      "collision_prefix": "UCX_",
      "pivot_rule": "bottom_center_except_hinged_rotated",
      "scale_unit": "meters_applied_fbx_scale_all"
    },
    "web": {
      "max_tris_lod0": 50000,
      "required_lod_count": 0,
      "texel_density_px_m": 1024,
      "max_texture_res": 2048,
      "min_uv_utilization": 0.75,
      "max_draw_calls": 100,
      "max_glb_bytes": 5242880,
      "scale_unit": "meters",
      "pivot_rule": "center_of_object"
    },
    "mobile": {
      "max_tris_lod0": 8000,
      "required_lod_count": 2,
      "texel_density_px_m": 512,
      "max_texture_res": 1024,
      "min_uv_utilization": 0.75,
      "scale_unit": "meters"
    }
  }
}
```

---

## §7. Git LFS setup for binary assets

Without Git LFS, `.blend`, `.fbx`, `.png` commits bloat the repo immediately.

Add to `.gitattributes` at project root:
```gitattributes
*.blend filter=lfs diff=lfs merge=lfs -text
*.fbx   filter=lfs diff=lfs merge=lfs -text
*.glb   filter=lfs diff=lfs merge=lfs -text
*.gltf  filter=lfs diff=lfs merge=lfs -text
*.png   filter=lfs diff=lfs merge=lfs -text
*.tga   filter=lfs diff=lfs merge=lfs -text
*.exr   filter=lfs diff=lfs merge=lfs -text
*.hdr   filter=lfs diff=lfs merge=lfs -text
*.psd   filter=lfs diff=lfs merge=lfs -text
*.stl   filter=lfs diff=lfs merge=lfs -text
*.3mf   filter=lfs diff=lfs merge=lfs -text
```

Migrate existing commits: `git lfs migrate import --include="*.blend,*.fbx,*.png" --everything`

**Forge standard path depth rule:** Keep folder depth ≤ 4 levels; asset names ≤ 40 characters;
full path from project root ≤ 150 characters. Windows MAX_PATH = 260 — exceeding it causes
silent Blender export failures and Python `FileNotFoundError`.

Enable long paths via PowerShell (run as Administrator):
```powershell
Set-ItemProperty -Path "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" `
    -Name "LongPathsEnabled" -Value 1 -Type DWord
```
