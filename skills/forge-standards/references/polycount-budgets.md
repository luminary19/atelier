# Polycount Budgets & LOD Ratios — forge-standards reference

## Contents
- §1. How to count (triangles, not polygons)
- §2. PC / Console budgets (AAA, current-gen 2025)
- §3. Mobile budgets (mid-range Android)
- §4. Web / AR / model-viewer budgets
- §5. Nanite (UE5) — what changes
- §6. LOD ratios and generation
- §7. bpy polycount query
- §8. Real-world scale reference objects

---

## §1. How to count (triangles, not polygons)

All budgets here are in **triangles** — the atomic unit the GPU rasterizes. One quad = ~2 triangles.
One n-gon of N sides = N-2 triangles. **Never quote polygon counts for budgets** — they're ambiguous
and misrepresent what hits the GPU.

Check in Blender:
```python
import bpy
obj = bpy.context.active_object
obj.data.calc_loop_triangles()
tri_count = len(obj.data.loop_triangles)
print(f"{obj.name}: {tri_count} triangles")
```

Or headlessly for all meshes in a .blend:
```python
for obj in bpy.data.objects:
    if obj.type == 'MESH':
        obj.data.calc_loop_triangles()
        print(f"{obj.name}: {len(obj.data.loop_triangles)} tris")
```

---

## §2. PC / Console budgets (AAA, current-gen 2025)

All values in triangles. Distances are approximate screen-coverage thresholds at a typical FOV.

| Asset class | LOD0 (≤10 m) | LOD1 (10–30 m) | LOD2 (30–60 m) | LOD3 (>60 m / imposter) | Notes |
|------------|-------------|----------------|----------------|------------------------|-------|
| Hero character (PC protagonist) | 50–100 k | 25–50 k | 10–25 k | 2–5 k | Face alone: 8–15 k; hair: card-based |
| Main NPC / companion | 20–60 k | 10–30 k | 5–15 k | 1–3 k | |
| Background NPC / crowd filler | 5–15 k | 2.5–7.5 k | 1–3 k | 500–1 k | Use imposters at crowd scale |
| Boss / hero enemy | 30–80 k | 15–40 k | 7.5–20 k | 2–5 k | |
| Weapon — FPS (in-hand) | 15–30 k | 7.5–15 k | 3–7.5 k | — | FPS weapons also get elevated TD |
| Weapon — TPS (small on screen) | 5–15 k | 2.5–7.5 k | 1–3 k | — | |
| Vehicle — hero / driveable | 30–80 k | 15–40 k | 7.5–20 k | 2–5 k | Interior: +20–50 k if enterable |
| Vehicle — background / traffic | 10–25 k | 5–12.5 k | 2.5–6 k | 500–2 k | |
| Hero prop (interactive / pickup) | 3–15 k | 1.5–7.5 k | 750–3 k | 100–500 | Chest, terminal, ornate lamp |
| Small prop (coin, can, cup) | 500–3 k | 250–1.5 k | 100–750 | 50–200 | |
| Environment — modular wall/floor | 500–3 k | 250–1.5 k | 100–500 | Billboard | Repeat instances multiply GPU cost |
| Environment — hero set-piece | 5–30 k | 2.5–15 k | 1–5 k | 500–2 k | |
| Foliage (tree LOD0) | 5–15 k | 2.5–7.5 k | 1–3 k | Billboard | Wind shader adds GPU cost |
| Creature — large (>4 m) | 20–50 k | 10–25 k | 5–12.5 k | 1–3 k | |
| Foliage — grass/flower (single) | 100–500 | 50–200 | Billboard | — | Use instancing; dense grass = GPU killer |

**Screen-fill rule:** If an asset fills >25% of the screen, it deserves its full LOD0 budget.
If it never appears larger than ~5% of screen, cut 80% of its LOD0 budget.

---

## §3. Mobile budgets (mid-range Android, Snapdragon 7-series ~2022)

| Asset class | LOD0 | LOD1 | LOD2 | Notes |
|------------|------|------|------|-------|
| Hero character | 3–8 k | 1.5–4 k | 500–1.5 k | iOS: ~2× these limits (A15+) |
| NPC | 1–4 k | 500–2 k | 200–800 | |
| Hero prop | 500–2 k | 250–1 k | 100–400 | |
| Small prop | 100–500 | 50–250 | 20–100 | |
| Environment element | 200–1.5 k | 100–750 | 50–300 | |
| **Scene triangle budget (all on-screen)** | 50–150 k total | — | — | Profile on real device — non-negotiable |

**Mobile draw-call ceiling:** ≤ 150 draw calls per frame on mid-range Android. Batching is mandatory.
**Mobile texture memory ceiling:** ≤ 512 MB VRAM total. One 2048² RGBA8 = 16 MB uncompressed.

---

## §4. Web / AR / model-viewer budgets

| Asset class | Triangle limit | GLB file limit | Notes |
|------------|---------------|---------------|-------|
| Any single asset | ≤ 50 k | ≤ 4 MB incl. textures | 50 k proven at 60 fps on 3-year-old mid-range Android |
| Hero / complex object | 20–50 k | — | Draco compression reduces GLB by 60–80% |
| Environment / background | 5–15 k | — | |
| Entire scene (all assets on screen) | ≤ 150 k | ≤ 12 MB | Test on mid-range Android; flagships support ~2× |
| WebAR (model-viewer / Quick Look) | ≤ 50 k | ≤ 4 MB | USDZ for iOS; GLB for Android |

**Web draw-call ceiling:** ≤ 50 draw calls per frame for smooth 60 fps on mid-range Android Chrome.
Use `KHR_mesh_quantization` (baked into Draco) and `EXT_meshopt_compression` for maximum GLB reduction.
Tool: `npx @gltf-transform/cli optimize --draco --meshopt input.glb output.glb`

---

## §5. Nanite (UE5.0+) — what changes

With Nanite enabled on a Static Mesh, the traditional LOD0 triangle budget no longer applies directly.
Nanite virtualizes the mesh and renders only visible micropolygons at adaptive detail. However:

- Nanite does **not** eliminate memory concerns: each mesh still costs VRAM.
- Nanite does **not** cover transparent, masked, or **skeletal** meshes — those still need manual LODs.
- **What matters in Nanite scenes:** draw-call count (persistent objects) and shadow-casting light count.
  Budget by texture VRAM and shadow lights, not triangles.
- **Rule of thumb:** if Nanite is enabled for a static mesh, skip LOD1/LOD2 generation. Keep LOD3
  (imposter billboard) for distant instanced foliage or crowd fillers that still need imposters.
- **Fallback:** always author LOD0 at "correct" quality anyway — Nanite uses it as the source.

---

## §6. LOD ratios and generation

### Default ratios

```
LOD0 = 1.0   (full detail — the authored mesh)
LOD1 = 0.5   (50% of LOD0 triangles)
LOD2 = 0.2   (20% of LOD0 triangles)
LOD3 = 0.05  (5% of LOD0 triangles — near-imposter)
```

Always decimate from **LOD0** for each subsequent LOD, not cascading from the previous LOD.
Cascading amplifies Decimate artifacts at each step.

### Headless LOD generation (bpy Decimate modifier)

```python
# forge_lod.py — run via: blender -b scene.blend -P forge_lod.py -- --ratios 1.0 0.5 0.2 0.05
import bpy, sys, argparse, io

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_lod_chain(base_obj, ratios):
    """Creates LOD0..LODn from base_obj using Decimate modifier."""
    coll = bpy.data.collections.new(f"{base_obj.name}_LODs")
    bpy.context.scene.collection.children.link(coll)

    lod_objects = []
    for i, ratio in enumerate(ratios):
        lod_name = f"{base_obj.name}_LOD{i}"

        if i == 0:
            new_obj = base_obj.copy()
            new_obj.data = base_obj.data.copy()
        else:
            # Always decimate from LOD0, not from previous LOD
            new_obj = lod_objects[0].copy()
            new_obj.data = lod_objects[0].data.copy()

        new_obj.name      = lod_name
        new_obj.data.name = lod_name
        coll.objects.link(new_obj)

        if ratio < 1.0:
            mod = new_obj.modifiers.new("Decimate_LOD", 'DECIMATE')
            mod.ratio         = ratio
            mod.use_symmetry  = True    # preserve silhouette on symmetric meshes
            mod.delimit       = {'SEAM'}  # lock UV seam boundaries
            with bpy.context.temp_override(active_object=new_obj):
                bpy.ops.object.modifier_apply(modifier="Decimate_LOD")

        new_obj.data.calc_loop_triangles()
        tri_count = len(new_obj.data.loop_triangles)
        print(f"  {lod_name}: {tri_count:,} triangles  (ratio={ratio})")
        lod_objects.append(new_obj)

    return lod_objects

if __name__ == "__main__":
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    ap = argparse.ArgumentParser()
    ap.add_argument("--ratios", nargs="+", type=float, default=[1.0, 0.5, 0.2, 0.05])
    args = ap.parse_args(argv)

    for obj in bpy.context.selected_objects:
        if obj.type == 'MESH':
            print(f"Generating LOD chain: {obj.name}")
            generate_lod_chain(obj, args.ratios)
```

**PowerShell invocation:**
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
& $blender -b "C:\project\source\SM_Chair_Wood\SM_Chair_Wood_v01.blend" `
    -P "C:\project\tools\forge_lod.py" `
    -- --ratios 1.0 0.5 0.2 0.05
```

---

## §7. bpy polycount query

```python
# polycount_report.py — run headless to report triangle counts for all meshes
import bpy, sys, io, json

if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
import argparse
ap = argparse.ArgumentParser()
ap.add_argument("--json", action="store_true")
ap.add_argument("--max-tris", type=int, default=0, help="Flag meshes exceeding this limit")
args = ap.parse_args(argv)

results = []
for obj in bpy.data.objects:
    if obj.type != 'MESH':
        continue
    obj.data.calc_loop_triangles()
    tris = len(obj.data.loop_triangles)
    verts = len(obj.data.vertices)
    over  = args.max_tris > 0 and tris > args.max_tris
    results.append({"name": obj.name, "triangles": tris, "vertices": verts, "over_budget": over})

if args.json:
    print(json.dumps(results, indent=2))
else:
    print(f"{'Object':<40} {'Tris':>8} {'Verts':>8} {'Status'}")
    print("-" * 65)
    for r in sorted(results, key=lambda x: x['triangles'], reverse=True):
        flag = " *** OVER BUDGET ***" if r["over_budget"] else ""
        print(f"{r['name']:<40} {r['triangles']:>8,} {r['vertices']:>8,}{flag}")
    total = sum(r['triangles'] for r in results)
    print(f"\nTotal triangles: {total:,}")
```

---

## §8. Real-world scale reference objects

Use these as a render-verify sanity check. Drop the reference silhouette into the scene and render:

| Object | Width × Height × Depth | Notes |
|--------|------------------------|-------|
| Standing adult human | 0.5 × 1.80 × 0.25 m | Center of mass ~0.9 m; use as the universal reference |
| Standard interior door | 0.91 × 2.03 × 0.04 m | US standard; EU often 0.875–1.0 m wide |
| Seated chair | 0.50 × 0.90 × 0.55 m | Seat height ~0.45 m |
| Pickup truck | 5.50 × 1.80 × 2.00 m | Length × height × width |
| Standard brick | 0.22 × 0.065 × 0.106 m | US standard |
| Oil drum / barrel (55-gal) | 0.58 × 0.88 × 0.58 m | Diameter × height |
| Dining table | 1.52 × 0.75 × 0.91 m | Standard 4-person US |
| Bedroom door knob height | ~0.96 m above floor | Good detail reference |
| Vehicle wheel (midsize sedan) | 0.65 × 0.19 m | Diameter × width |

**Render-verify workflow:**
1. Load `render_rig.blend` — a minimal scene with a fixed camera and a 1.8 m human silhouette mesh.
2. Import exported asset at world origin (assumes correct pivot at base-center).
3. Render to PNG with Cycles (4 samples is enough for scale check).
4. `Read` the PNG — compare asset scale visually against the 1.8 m silhouette.
5. A seated chair seat top should reach ~0.45 m = 25% of the human silhouette height.
