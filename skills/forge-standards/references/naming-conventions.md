# Naming Conventions — forge-standards reference

## Contents
- §1. The canonical naming pattern
- §2. Type prefix master table (cross-engine)
- §3. Texture suffix table (PBR pipeline)
- §4. Blender in-file prefix system (film/animation)
- §5. LOD and collision suffixes
- §6. Directory / file structure
- §7. Validation regex patterns
- §8. Common pitfalls

---

## §1. The canonical naming pattern

```
[TypePrefix]_[AssetName]_[Descriptor]_[VariantOrNumber]
```

Rules:
- **No spaces.** No Unicode characters. No camelCase mixing.
- **Asset names:** `PascalCase` (e.g., `BarrelOak`, `HeroMale`).
- **Folder names:** `snake_case` (e.g., `hero_props/`, `environment_modular/`).
- **Numbers:** zero-padded two digits (`_01`, not `_1`).
- **Source files** (`.blend`) may carry a version suffix: `SM_Chair_Wood_v03.blend`.
  Strip the version on export. Runtime names must be stable — engine GUIDs break when they change.

Full example (oak barrel prop):
```
SM_Barrel_Oak_01.fbx           ← static mesh runtime export
T_Barrel_Oak_BC_01.png         ← base color, sRGB
T_Barrel_Oak_N_01.png          ← normal map, Linear/Non-Color
T_Barrel_Oak_ORM_01.png        ← packed AO(R)/Rough(G)/Metal(B), Linear
M_Barrel_Oak.uasset            ← Unreal material instance (named after source)
MI_Barrel_Oak_Weathered.uasset ← material instance variant
```

---

## §2. Type prefix master table

These prefixes are cross-engine consensus (UE5, Unity, Godot). Use them for all pipelines.

| Prefix | Asset type | Example |
|--------|-----------|---------|
| `SM_` | Static Mesh | `SM_Barrel_Oak_01` |
| `SK_` | Skeletal Mesh / Skinned | `SK_Hero_Male_A` |
| `T_` | Texture (generic) | `T_Barrel_Oak_BC` |
| `M_` | Material (master/parent) | `M_Wood_Planks` |
| `MI_` | Material Instance | `MI_Wood_Planks_Dark` |
| `MF_` | Material Function | `MF_Triplanar_Blend` |
| `MPC_` | Material Parameter Collection | `MPC_GlobalFX` |
| `BP_` | Blueprint / prefab logic | `BP_Door_Sliding` |
| `ABP_` | Animation Blueprint | `ABP_Hero_Male` |
| `SKEL_` | Skeleton asset (UE5 distinction) | `SKEL_Hero_Male` |
| `AM_` | Animation Montage | `AM_Attack_Slash_01` |
| `AS_` | Animation Sequence | `AS_Walk_Forward` |
| `PS_` | Particle System (legacy Cascade) | `PS_Dust_Impact` |
| `NS_` | Niagara System | `NS_Fire_Ember` |
| `FXS_` | FX System (generic) | `FXS_Rain_Splash` |
| `HDR_` | HDRI / environment map | `HDR_Studio_Neutral` |
| `RT_` | Render Target | `RT_MiniMap_A` |
| `DT_` | Data Table | `DT_WeaponStats` |
| `PHYS_` | Physics Asset | `PHYS_Hero_Male` |

---

## §3. Texture suffix table (PBR pipeline)

Append after asset name, before variant number: `T_[AssetName]_[Suffix]_[VariantNumber]`.

| Suffix | Channel / Map | Color space | Notes |
|--------|--------------|-------------|-------|
| `_BC` or `_D` | Base Color / Diffuse / Albedo | **sRGB** | Perceived color; must be sRGB for correct look |
| `_N` | Normal map (tangent-space) | **Linear / Non-Color** | OpenGL convention (+Y = up on screen) default |
| `_ORM` | Packed: AO(R) Roughness(G) Metallic(B) | **Linear / Non-Color** | Green channel → most bit precision in BC compression |
| `_R` | Roughness (standalone) | Linear | Only if not packing ORM |
| `_M` or `_MT` | Metallic (standalone) | Linear | Only if not packing ORM |
| `_AO` | Ambient Occlusion (standalone) | Linear | Only if not packing ORM |
| `_E` or `_EM` | Emissive | sRGB or Linear (HDR) | HDR emissive → Linear EXR |
| `_H` | Height / Displacement | Linear | 16-bit preferred |
| `_O` or `_A` | Opacity / Alpha | Linear | |
| `_UI` | UI-only texture | sRGB | No MIP generation needed |

**ORM channel-pack rationale:**
- R = AO (ambient occlusion)
- G = Roughness — gets the most bit precision under BC1/BC3 (6 bits vs 5 for R/B). Roughness has the
  most perceptually-critical gradients; this maximizes effective precision.
- B = Metallic
- One ORM replaces three maps → saves ~4 MB per 2048² material at BC1.
- This is the UE5 default PBR setup and Substance Painter's "Unreal Engine 4" export preset.

**DirectX vs OpenGL normal maps:**
- OpenGL (Blender default, glTF): +Y = up on screen (green channel is "up").
- DirectX (some UE5 materials): -Y = inverted green channel.
- If normals appear inverted: flip the G channel in the normal texture, or check the engine's
  material `Flip Green Channel` setting.
- Suffix: `_N_DX` for DirectX-convention normals when both coexist.

---

## §4. Blender in-file prefix system (Blender Studio / film pipeline)

For Blender-native productions (animation, film — not game engine export), use the Blender Studio
naming system for collections and datablocks.

### Collection prefixes

| Prefix | Type | Example |
|--------|------|---------|
| `CH-` | Character | `CH-hero_male` |
| `LI-` | Library asset / environment prop | `LI-barrel_oak_013` |
| `SE-` | Set | `SE-kitchen_set` |
| `LG-` | Light rig | `LG-key_light_rig` |
| `CA-` | Camera rig | `CA-main_camera` |
| `PR-` | Rigged prop | `PR-sword_prop` |

### Object prefixes within a collection

| Prefix | Type | Example |
|--------|------|---------|
| `GEO-` | Geometry (renders) | `GEO-hero_male-body` |
| `RIG-` | Armature | `RIG-hero_male` |
| `WGT-` | Bone widget shape | `WGT-hero_male-fk_arm.L` |
| `HLP-` | Empty / helper (not rendered) | `HLP-hero_male-aim_target` |
| `LGT-` | Mesh light | `LGT-key_fill_mesh` |
| `TMP-` | Placeholder (to be replaced) | `TMP-hero_male-rough_block` |

### Node group prefixes

| Prefix | Type | Example |
|--------|------|---------|
| `GN-` | Geometry Nodes | `GN-scatter_grass` |
| `SH-` | Shader | `SH-skin_subsurface` |
| `CM-` | Compositing | `CM-grade_neutral` |

### Blender naming rules

- All lowercase with `_` separator in base name.
- `-` separates the prefix from the hierarchical base name: `GEO-hero_male-eye.L`.
- `.L` / `.R` for symmetrical objects (safe for Mirror modifier). Use `_left` / `_right` when
  not truly symmetrical.
- **Rename `.001` auto-suffixes** to `_001` before publishing — `.001` is not safe for Library Overrides.
- Suffix `_001`, `_002` for uniqueness within a collection; strip before runtime export.

---

## §5. LOD and collision suffixes

### LOD slots (game engine auto-detection)

Both UE5 and Unity detect LOD slots from in-mesh or child object naming:

```
SM_Barrel_Oak_LOD0   ← highest detail (LOD slot 0, 0–10 m)
SM_Barrel_Oak_LOD1   ← LOD slot 1 (10–30 m)
SM_Barrel_Oak_LOD2   ← LOD slot 2 (30–60 m)
SM_Barrel_Oak_LOD3   ← LOD slot 3 (>60 m / imposter)
```

- UE5: all LOD meshes in the same FBX → auto-populates LOD slots on import.
- Unity: `_LOD0` / `_LOD1` child object names in FBX → auto-populates `LODGroup` component.

### Collision meshes (UE5 auto-assignment)

UE5 assigns collision from the same FBX when child meshes follow this naming:

```
UCX_SM_Barrel_Oak_01    ← convex hull collision (recommended for most props)
UBX_SM_Barrel_Oak_01    ← box collision (walls, crates)
USP_SM_Barrel_Oak_01    ← sphere collision (round objects)
UCP_SM_Barrel_Oak_01    ← capsule collision (pillars, tree trunks)
```

Multiple convex hulls (complex prop with concavity):
```
UCX_SM_Barrel_Oak_01_0
UCX_SM_Barrel_Oak_01_1
...
```

---

## §6. Directory / file structure

### Game engine target (UE5 / Unity / Godot)

```
project/
├── source/                         # .blend working files — Git LFS tracked
│   ├── characters/
│   │   └── SK_Hero_Male/
│   │       └── SK_Hero_Male_v03.blend   # WIP version; runtime name is stable
│   ├── props/
│   │   ├── SM_Barrel_Oak/
│   │   │   └── SM_Barrel_Oak_v01.blend
│   │   └── SM_Chair_Wood/
│   ├── environment/
│   │   ├── modular/
│   │   └── hero_pieces/
│   └── _HIGH/                      # High-poly sculpts; NEVER exported to engine
├── export/                         # Runtime engine files: FBX / GLB / USD
│   ├── SM_Barrel_Oak_01.fbx
│   └── SM_Chair_Wood_01.glb
├── textures/                       # Final baked PBR maps
│   ├── T_Barrel_Oak_BC_01.png
│   ├── T_Barrel_Oak_N_01.png
│   └── T_Barrel_Oak_ORM_01.png
└── FORGE_STANDARDS.json            # Machine-readable token file (see forge-standards-schema.md)
```

**Path length limit (Windows, MAX_PATH = 260 chars):**
Blender silently fails to export when the output path exceeds 260 chars.
- Keep folder depth ≤ 4 levels.
- Asset names ≤ 40 characters.
- Full path from project root ≤ 150 characters.
- Enable long paths if needed: `Set-ItemProperty "HKLM:\SYSTEM\CurrentControlSet\Control\FileSystem" -Name LongPathsEnabled -Value 1`

### Git LFS (required for any project with binaries)

```gitattributes
*.blend filter=lfs diff=lfs merge=lfs -text
*.fbx   filter=lfs diff=lfs merge=lfs -text
*.glb   filter=lfs diff=lfs merge=lfs -text
*.png   filter=lfs diff=lfs merge=lfs -text
*.tga   filter=lfs diff=lfs merge=lfs -text
*.exr   filter=lfs diff=lfs merge=lfs -text
*.psd   filter=lfs diff=lfs merge=lfs -text
*.wav   filter=lfs diff=lfs merge=lfs -text
*.mp4   filter=lfs diff=lfs merge=lfs -text
```

Migrate existing large files: `git lfs migrate import --include="*.blend,*.fbx,*.png" --everything`

---

## §7. Validation regex patterns

These are the regexes used in `forge_validate.py` and `FORGE_STANDARDS.json`.

```python
import re

# Cross-engine runtime naming (SM_, SK_, T_, M_, MI_, etc.)
RUNTIME_PATTERN = (
    r"^(SM|SK|T|M|MI|MF|MPC|BP|ABP|SKEL|AM|AS|PS|NS|FXS|HDR|RT|DT|PHYS)"
    r"_[A-Z][A-Za-z0-9]+"             # TypePrefix + PascalCase name
    r"(_[A-Za-z0-9]+)*"               # optional _Descriptor segments
    r"(_LOD\d)?$"                      # optional LOD suffix
)

# Texture naming: T_AssetName_Suffix_NN
TEXTURE_PATTERN = (
    r"^T_[A-Z][A-Za-z0-9]+"
    r"_(BC|D|N|ORM|R|M|MT|AO|E|EM|H|O|A|UI)"
    r"(_\d{2})?$"
)

# Collision mesh naming (UE5)
COLLISION_PATTERN = r"^(UCX|UBX|USP|UCP)_SM_[A-Z][A-Za-z0-9]+(_\d{2})?(_\d+)?$"

# Blender in-file datablocks (film pipeline)
BLENDER_OBJECT_PATTERN = (
    r"^(GEO|RIG|WGT|HLP|LGT|TMP)-[a-z][a-z0-9_]+"
    r"(-[a-z][a-z0-9_]+)*"
    r"(\.[LR]|_\d{3})?$"
)

# Quick check functions
def is_valid_runtime_name(name):
    return bool(re.match(RUNTIME_PATTERN, name))

def is_valid_texture_name(name):
    """Strip extension before checking."""
    stem = name.rsplit('.', 1)[0] if '.' in name else name
    return bool(re.match(TEXTURE_PATTERN, stem))

# Examples
assert is_valid_runtime_name("SM_Barrel_Oak_01")       # True
assert is_valid_runtime_name("SM_Barrel_Oak_LOD0")     # True
assert not is_valid_runtime_name("barrel_oak_01")      # False — no prefix
assert not is_valid_runtime_name("SM_barrel_oak")      # False — lowercase after prefix
assert is_valid_texture_name("T_Barrel_Oak_BC_01")     # True
assert is_valid_texture_name("T_Barrel_Oak_ORM")       # True
```

---

## §8. Common pitfalls

| Pitfall | Symptom | Fix |
|---------|---------|-----|
| `Material.001` / `Material.002` duplicates | Extra draw calls in engine; validation fail | `[m.name for m in bpy.data.materials if re.search(r'\.\d{3}$', m.name)]` → merge or rename |
| Spaces in material names | Engine import error | Check: `' ' in mat.name`; rename to `M_` + `_` convention |
| `.001` Blender auto-suffix in exports | Library Override breaks; duplicate LOD confusion | Rename to `_001` in source; Blender won't auto-suffix renamed objects |
| Version suffix on runtime name | Engine GUID breaks on rename | `SM_Chair_v03.fbx` → `SM_Chair_01.fbx`; version lives on source .blend only |
| camelCase asset name | Fails regex; inconsistent sort order | PascalCase: `BarrelOak` not `barrelOak` or `barrel_oak` |
| Path > 260 chars | Blender silently fails to export | Keep path ≤ 150 chars from project root; enable LongPathsEnabled |
