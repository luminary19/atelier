# forge-data — Budgets & Standards Reference

Authoritative polycount and texel-density tables, naming conventions, pivot placement rules,
scale discipline, and LOD ratios. The decision authority for these values is **forge-standards**;
this file is the queryable copy.

## Contents
- §1. Polycount budgets — PC / Console (AAA)
- §2. Polycount budgets — Mobile
- §3. Polycount budgets — WebAR / WebGL
- §4. Texel density tiers
- §5. Naming conventions (cross-engine)
- §6. Texture suffixes (PBR)
- §7. Pivot placement rules
- §8. Scale discipline (Blender → engines)
- §9. LOD ratios and UV conventions

---

## §1. Polycount budgets — PC / Console (AAA, current-gen 2025)

All values in **triangles**. `Poly ≈ Tri ÷ 2` for quads.

| Asset class | LOD0 (0–10 m) | LOD1 (10–30 m) | LOD2 (30–60 m) | LOD3 (>60 m / imposter) |
|------------|--------------|----------------|----------------|------------------------|
| Hero character (PC protagonist) | 50,000–100,000 | 25,000–50,000 | 10,000–25,000 | 2,000–5,000 |
| Main NPC / companion | 20,000–60,000 | 10,000–30,000 | 5,000–15,000 | 1,000–3,000 |
| Background NPC / crowd | 5,000–15,000 | 2,500–7,500 | 1,000–3,000 | 500–1,000 |
| Boss / hero enemy | 30,000–80,000 | 15,000–40,000 | 7,500–20,000 | 2,000–5,000 |
| Weapon — FPS (in-hand) | 15,000–30,000 | 7,500–15,000 | 3,000–7,500 | — |
| Weapon — TPS | 5,000–15,000 | 2,500–7,500 | 1,000–3,000 | — |
| Vehicle — hero / driveable | 30,000–80,000 | 15,000–40,000 | 7,500–20,000 | 2,000–5,000 |
| Vehicle — background | 10,000–25,000 | 5,000–12,500 | 2,500–6,000 | 500–2,000 |
| Hero prop (interactive / pickup) | 3,000–15,000 | 1,500–7,500 | 750–3,000 | 100–500 |
| Small prop (coin, can) | 500–3,000 | 250–1,500 | 100–750 | 50–200 |
| Environment — modular wall/floor | 500–3,000 | 250–1,500 | 100–500 | Billboard |
| Environment — hero set-piece | 5,000–30,000 | 2,500–15,000 | 1,000–5,000 | 500–2,000 |
| Foliage (tree LOD0) | 5,000–15,000 | 2,500–7,500 | 1,000–3,000 | Billboard |
| Creature — large (4 m+) | 20,000–50,000 | 10,000–25,000 | 5,000–12,500 | 1,000–3,000 |

**Nanite note:** With UE5 Nanite enabled, LOD0 triangle budget does not apply directly — Nanite
virtualizes the mesh. Budget by texture VRAM and shadow-casting draw calls instead. Non-Nanite
(transparent, masked, skeletal) assets still need manual LODs.

---

## §2. Polycount budgets — Mobile

Mid-range Android (Snapdragon 7-series, ~2022). iOS allows ~2× these limits.

| Asset class | LOD0 | LOD1 | LOD2 |
|------------|------|------|------|
| Hero character | 3,000–8,000 | 1,500–4,000 | 500–1,500 |
| NPC | 1,000–4,000 | 500–2,000 | 200–800 |
| Hero prop | 500–2,000 | 250–1,000 | 100–400 |
| Small prop | 100–500 | 50–250 | 20–100 |
| Environment element | 200–1,500 | 100–750 | 50–300 |
| Scene total (all on-screen) | 50,000–150,000 | — | — |

---

## §3. Polycount budgets — WebAR / WebGL

Khronos 3D Commerce v1.0 + 2025 practitioner consensus.

| Asset class | Triangle limit | GLB file limit | Notes |
|------------|---------------|---------------|-------|
| Any single asset | ≤ 50,000 | ≤ 4 MB incl. textures | 50K proven on 3-year-old Android at 60 fps |
| Hero / complex object | 20,000–50,000 | — | Draco reduces GLB by 60–80% |
| Environment / background | 5,000–15,000 | — | |
| Entire scene budget (desktop, 60 fps) | ≤ 500,000 | — | Draw calls dominate; fix those first |
| Entire scene budget (mobile, 60 fps) | ≤ 150,000–200,000 | — | < 50 draw calls |
| Decorative / background prop | ≤ 5,000 | ≤ 500 KB | |
| Single-item 3D catalogue (mobile AR) | ≤ 50,000 | ≤ 3 MB | |

**Draw calls dominate over triangles on mobile.** 500 K tris / 20 draw calls > 100 K tris / 200
draw calls in real device testing.

---

## §4. Texel density tiers

Formula: `TD (px/m) = Texture Resolution (px) / Surface Dimension (m)`

| Target / Asset tier | px/m | Texture for 1 m² surface | Notes |
|---------------------|------|--------------------------|-------|
| Hero FPS weapon, main char face, key props | 2048 | 2048×2048 | Maximum quality tier |
| Standard PC / console foreground prop | 1024 | 1024×1024 for 1 m² | Default AAA |
| Mid-range environment props | 512 | 512×512 or 1024 tiled | |
| Background / distant | 256 | 256×256, tiled atlas | |
| Mobile foreground | 512 | 512×512 | |
| Mobile background | 128–256 | Use tiled materials | |
| WebAR / WebGL | 512–1024 | Keep total GLB ≤ 4 MB | |
| CryEngine AAA baseline | 512 | 512 px/m = green in debug | |

**VRAM formula (uncompressed):**
`vram_bytes = width × height × 4 × 1.333  // ×4 for RGBA, ×1.333 for mip chain`
4096×4096 ≈ 89.5 MB VRAM. KTX2 ETC1S reduces to ~11 MB at same resolution.

---

## §5. Naming conventions (cross-engine consensus)

**Pattern:** `[TypePrefix]_[AssetName]_[Descriptor]_[VariantOrNumber]`
No spaces. No Unicode. PascalCase asset names. Numbers zero-padded (`_01`).

| Prefix | Asset type | Example |
|--------|-----------|---------|
| `SM_` | Static Mesh | `SM_Barrel_Oak_01` |
| `SK_` | Skeletal Mesh | `SK_Hero_Male_A` |
| `T_` | Texture (generic) | `T_Barrel_Oak_BC` |
| `M_` | Material master | `M_Wood_Planks` |
| `MI_` | Material Instance | `MI_Wood_Planks_Dark` |
| `MF_` | Material Function | `MF_Triplanar_Blend` |
| `MPC_` | Material Parameter Collection | `MPC_GlobalFX` |
| `BP_` | Blueprint / prefab | `BP_Door_Sliding` |
| `AM_` | Animation Montage | `AM_Attack_Slash_01` |
| `AS_` | Animation Sequence | `AS_Walk_Forward` |
| `NS_` | Niagara System | `NS_Fire_Ember` |
| `HDR_` | HDRI / environment map | `HDR_Studio_Neutral` |

**LOD suffixes on meshes:** `SM_Barrel_Oak_LOD0` … `SM_Barrel_Oak_LOD3`
**UE5 collision prefixes:** `UCX_` (convex), `UBX_` (box), `USP_` (sphere), `UCP_` (capsule)

**Blender Studio (film / animation pipeline):**
`GEO-hero_male-body`, `RIG-hero_male`, `WGT-`, `HLP-`, `LGT-`, `TMP-`
Node groups: `GN-` (Geometry Nodes), `SH-` (Shader), `CM-` (Compositing)

---

## §6. Texture suffixes (PBR)

| Suffix | Channel / Map | Color space |
|--------|--------------|-------------|
| `_BC` or `_D` | Base Color / Diffuse / Albedo | sRGB |
| `_N` | Normal map (tangent-space) | Linear / Non-Color |
| `_ORM` | Packed AO(R) Roughness(G) Metallic(B) | Linear / Non-Color |
| `_R` | Roughness (standalone) | Linear |
| `_M` / `_MT` | Metallic (standalone) | Linear |
| `_AO` | Ambient Occlusion (standalone) | Linear |
| `_E` / `_EM` | Emissive | sRGB or Linear |
| `_H` | Height / Displacement | Linear |
| `_O` / `_A` | Opacity / Alpha | Linear |
| `_UI` | UI-only texture | sRGB |

**ORM packing rationale:** R=AO, G=Roughness, B=Metallic. Green gets the most bit precision
under BC1/BC3 compression (6 bits vs 5 for R/B), and roughness has the most perceptually-critical
gradients. One ORM replaces three maps, saving ~4 MB per 2048² at BC1.

---

## §7. Pivot placement rules

| Object class | Pivot placement | Rationale |
|-------------|----------------|-----------|
| Ground-resting props (chair, barrel, crate) | Bottom-center of bounding box | Sits on floor at Y=0 without offset |
| Architectural (wall, floor tile) | Bottom-left corner OR world origin | Modular snap-to-grid |
| Doors, hinged lids, drawers | Hinge point (edge of rotating face) | Correct rotation axis |
| Wheels, fans, rotating machinery | Axle center | Animation axis correct |
| Weapons FPS | Grip / attachment point | Matches character rig socket |
| Character / skeletal mesh | Floor level, centered on root bone XY | Root motion correct |
| Ceiling-mounted (pendant light) | Top mounting point | Attaches to ceiling |

---

## §8. Scale discipline (Blender → engines)

| Engine | 1 unit = | Import correction needed |
|--------|---------|------------------------|
| Unreal Engine 5 | 1 cm | Blender default 1 m → 100× mismatch; use `FBX_SCALE_ALL` |
| Unity | 1 m | Blender 1 m = Unity 1 m — apply transforms only |
| Godot 4 | 1 m | Same as Unity |
| glTF / USD | 1 m | Standard; use Blender metric at 1 m scale |

**Real-world reference sizes:**
- Interior door: ~0.9 m wide × 2.1 m tall
- Seated chair: seat height ~0.45 m, total ~0.9 m
- Standing human: 1.75–1.85 m
- Pickup truck: ~5.5 m L × 2.0 m W × 1.8 m H
- Standard brick: ~0.22 m × 0.065 m × 0.106 m

**WIP versioning rule:** `_v01` on source `.blend` files only — strip on export. Runtime names
must be stable (engine GUIDs and redirectors break on renames).

---

## §9. LOD ratios and UV conventions

**Default LOD Decimate ratios:** `[1.0, 0.5, 0.2, 0.05]` (LOD0–LOD3).
Always duplicate from LOD0, not from the previous LOD — cascading artifacts accumulate.

**UV Channel 1 (index 0) — Primary texture map:**
- UV utilization: ≥ 85% for hero assets; ≥ 75% for environment props
- No overlapping islands (unless intentionally mirrored — document it)
- All islands within 0–1 UV space
- Seams in low-visibility areas
- Island padding: ≥ 2 px at target resolution (e.g. 4 px on 2048² map)

**UV Channel 2 (index 1) — Lightmap:**
- Named `LightmapUV` in Blender (UE5 auto-detects by name)
- ZERO overlapping islands — hard requirement (overlap = light bake artifacts)
- Padding: 2–4% of texture resolution (`margin=0.02` in Blender Lightmap Pack)
- No mirrored / stacked islands (breaks baking)
