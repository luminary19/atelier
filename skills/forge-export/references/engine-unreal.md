# Unreal Engine 5.x — Import Conventions
# forge-export | references/engine-unreal.md

## Contents
- §1. Coordinate system and scale
- §2. Headless import invocation
- §3. Static mesh FBX import (Python API)
- §4. Skeletal mesh FBX import
- §5. Interchange API (glTF/GLB preferred)
- §6. Nanite rules
- §7. Naming conventions (SM_, SK_, T_, UCX_, LOD_)
- §8. Texture sRGB table
- §9. Critical gotchas

---

## §1. Coordinate system and scale

| Property | Unreal Engine 5.x |
|---|---|
| Up axis | **+Z (left-handed)** |
| Forward axis | **+X** |
| Units | **1 Unreal Unit = 1 centimeter** |
| Handedness | **Left-handed** |

**Always set at import:**
- `convert_scene=True` — converts Blender/glTF Z-up RH → UE Z-up LH
- `convert_scene_unit=True` — converts meters → centimeters (1m → 100 cm)
  OR export from Blender with `apply_unit_scale=True` (1m = 100 FBX units)

**Scale sanity check:**
- A 1.8m human should have max bounding box dimension = 180 (cm)
- If 18000 → FBX 100× scale bug (forgot `apply_unit_scale=True` or `convert_scene_unit=True`)
- If 1.8 → meters instead of cm (forgot unit conversion)

---

## §2. Headless import invocation

```powershell
# Pattern A: Python commandlet (-nullrhi = no GPU, CI-safe)
& "C:\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" `
    "C:\MyProject\MyProject.uproject" `
    -run=pythonscript `
    -script="C:/scripts/import_assets.py" `
    -unattended `
    -nosplash `
    -nullrhi `
    -logdebug

if ($LASTEXITCODE -ne 0) { Write-Error "UE import failed (exit $LASTEXITCODE)"; exit 1 }

# Pattern B: Execute a single Python expression (brief inline work only)
& "C:\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" `
    "C:\MyProject\MyProject.uproject" `
    -ExecutePythonScript="C:/scripts/import_assets.py" `
    -unattended -nosplash

# Pattern C: ExecCmds (UE console command, no Python)
& "C:\Epic Games\UE_5.7\Engine\Binaries\Win64\UnrealEditor-Cmd.exe" `
    "C:\MyProject\MyProject.uproject" `
    -ExecCmds="Automation RunTests Unreal.Asset" `
    -unattended -nosplash -nullrhi
```

**Note on Interchange + headless:**
The Interchange CDO (Class Default Object) pipeline overrides may not be respected in `-nullrhi`
mode with some UE builds. If Interchange-based GLB import produces unexpected materials, fall back
to `-run=pythonscript` with a full editor tick (no `-nullrhi`) in a remote desktop session.
This is a known UE limitation as of 5.5 (tracked: UE-210193).

---

## §3. Static mesh FBX import (Python API)

```python
# import_static_mesh.py — UE5 Python (run via -run=pythonscript)
import unreal

def import_static_mesh_fbx(
    fbx_path: str,
    destination_path: str,    # e.g. "/Game/Meshes"
    asset_name: str = None,
    build_nanite: bool = True,
    max_lumen_mesh_cards: int = 12,
) -> unreal.StaticMesh:
    task = unreal.AssetImportTask()
    task.filename = fbx_path
    task.destination_path = destination_path
    if asset_name:
        task.destination_name = asset_name
    task.automated = True          # Suppress dialog
    task.save = True

    # FbxImportUI options
    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = False
    options.import_materials = True
    options.import_textures = True
    options.import_animations = False
    options.create_physics_asset = False

    # Coordinate system CRITICAL settings
    options.convert_scene = True            # Z-up RH → Z-up LH (Blender/glTF → UE)
    options.convert_scene_unit = True       # meters → centimeters
    options.force_front_x_axis = False      # UE expects +X forward

    # Normal import
    options.normal_import_method = unreal.FBXNormalImportMethod.FBXNIM_IMPORT_NORMALS_AND_TANGENTS

    # Mesh options
    mesh_options = unreal.FbxStaticMeshImportData()
    mesh_options.auto_generate_collision = False    # Use UCX_ explicit hulls instead
    mesh_options.build_nanite = build_nanite
    mesh_options.build_reversed_index_buffer = True
    mesh_options.generate_lightmap_uvs = True
    mesh_options.one_convex_hull_per_ucx = True
    mesh_options.remove_degenerates = True
    mesh_options.max_lumen_mesh_cards = max_lumen_mesh_cards
    mesh_options.import_collision_according_to_mesh_name = True  # UCX_ suffix recognition
    options.static_mesh_import_data = mesh_options
    task.options = options

    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    return task.get_objects()[0] if task.get_objects() else None
```

---

## §4. Skeletal mesh FBX import

```python
def import_skeletal_mesh_fbx(
    fbx_path: str,
    destination_path: str,
    existing_skeleton_path: str = None,   # "/Game/Characters/SK_Base_Skeleton" or None
    use_t0_ref_pose: bool = True,
) -> unreal.SkeletalMesh:
    task = unreal.AssetImportTask()
    task.filename = fbx_path
    task.destination_path = destination_path
    task.automated = True
    task.save = True

    options = unreal.FbxImportUI()
    options.import_mesh = True
    options.import_as_skeletal = True
    options.import_materials = True
    options.import_textures = True
    options.import_animations = True
    options.convert_scene = True
    options.convert_scene_unit = True

    skel_options = unreal.FbxSkeletalMeshImportData()
    skel_options.use_t0_as_ref_pose = use_t0_ref_pose   # Use T-pose at frame 0 as bind pose
    skel_options.import_morph_targets = True
    skel_options.update_skeleton_reference_pose = True
    skel_options.import_meshlods = True
    skel_options.threshold_position = 0.00002
    skel_options.threshold_tangent_normal = 0.00002
    skel_options.threshold_uv = 0.000977
    options.skeletal_mesh_import_data = skel_options

    if existing_skeleton_path:
        skel_obj = unreal.load_asset(existing_skeleton_path)
        if skel_obj:
            options.skeleton = skel_obj
            skel_options.import_meshes_in_bone_hierarchy = False

    task.options = options
    asset_tools = unreal.AssetToolsHelpers.get_asset_tools()
    asset_tools.import_asset_tasks([task])
    return task.get_objects()[0] if task.get_objects() else None
```

---

## §5. Interchange API (glTF / GLB — preferred for UE 5.4+)

```python
# Interchange is the recommended importer for GLB/glTF in UE 5.4+
import unreal

def interchange_import_glb(
    glb_path: str,
    destination_path: str,
    enable_nanite: bool = True,
    max_lumen_cards: int = 12,
) -> list:
    import_pipeline = unreal.InterchangeImportTestPlan()
    # Configure via source data
    source = unreal.InterchangeManager.create_source_data(glb_path)
    import_params = unreal.ImportAssetParameters()
    import_params.is_automated = True
    import_params.override_pipelines = []

    # Build the generic mesh pipeline
    mesh_pipeline = unreal.InterchangeGenericMeshPipeline()
    mesh_pipeline.import_static_meshes = True
    mesh_pipeline.import_skeletal_meshes = True
    mesh_pipeline.enable_nanite_for_static_meshes = enable_nanite
    mesh_pipeline.nanite_triangle_threshold = 10000
    mesh_pipeline.max_lumen_mesh_cards = max_lumen_cards
    mesh_pipeline.import_collision_according_to_mesh_name = True
    mesh_pipeline.bake_meshes = False

    mat_pipeline = unreal.InterchangeGenericMaterialPipeline()
    mat_pipeline.import_materials = True
    mat_pipeline.import_textures = True
    mat_pipeline.search_location = unreal.InterchangeMaterialSearchLocation.LOCAL

    import_params.override_pipelines = [mesh_pipeline, mat_pipeline]

    manager = unreal.InterchangeManager.get_interchange_manager_scripted()
    result = manager.import_scene_under_path_and_blocking(
        destination_path, source, import_params
    )
    return result

# Batch enable Nanite on already-imported static meshes
def enable_nanite_batch(mesh_paths: list[str]) -> None:
    with unreal.ScopedEditorTransaction("Enable Nanite") as trans:
        for path in mesh_paths:
            mesh = unreal.load_asset(path)
            if not isinstance(mesh, unreal.StaticMesh):
                continue
            ns = mesh.get_editor_property("nanite_settings")
            ns.set_editor_property("enabled", True)
            mesh.set_editor_property("nanite_settings", ns)
            unreal.EditorAssetLibrary.save_asset(path)
```

---

## §6. Nanite rules

**Enable Nanite when:**
- Mesh has > 10,000 triangles
- Material blend mode is Opaque or Masked
- Not used on mobile or Forward Rendering target
- Not an instanced Foliage with complex LOD requirements

**NEVER enable Nanite when:**
| Condition | Why |
|---|---|
| Material is Translucent | Nanite cannot render transparent surfaces |
| Mesh has morph targets | Nanite path does not support morphs (silently disables) |
| World Position Offset (WPO) material | Nanite uses raster/software fallback only in limited WPO mode |
| Mobile forward renderer target | Nanite not supported |
| Non-skeletal animated mesh | Use standard LOD pipeline |
| Flat planes, decals, particles | Zero benefit; adds GPU overhead |

**Lumen mesh cards:**
- Default = 12 cards (most props)
- 0 for strictly flat objects (walls, floors)
- 32 for complex interior set pieces with many recesses

---

## §7. Naming conventions

| Asset type | Prefix | Example |
|---|---|---|
| Static Mesh | `SM_` | `SM_Chair_01` |
| Skeletal Mesh | `SK_` | `SK_Character_Hero` |
| Skeleton | `SKEL_` | `SKEL_Character_Hero` |
| Physics Asset | `PHYS_` | `PHYS_Character_Hero` |
| Material | `M_` | `M_Rock_Granite` |
| Material Instance | `MI_` | `MI_Rock_Granite_Dark` |
| Texture | `T_` | `T_Rock_BaseColor` |
| Anim Blueprint | `ABP_` | `ABP_Character_Hero` |
| Anim Sequence | `AS_` | `AS_Idle_Loop` |

**Collision mesh naming (inside FBX):**
| Prefix | Hull type | Notes |
|---|---|---|
| `UCX_MeshName_00` | Convex hull | Most common; up to 32 hulls per mesh (`_00`–`_31`) |
| `UBX_MeshName_00` | Box (AABB) | For box-shaped objects |
| `UCP_MeshName_00` | Capsule | For capsule-shaped objects |
| `USP_MeshName_00` | Sphere | For sphere-shaped objects |

**LOD naming inside FBX (legacy FBX importer):**
- Root mesh: `SM_Chair` → `SM_Chair_LOD0`
- Subsequent LODs: `SM_Chair_LOD1`, `SM_Chair_LOD2`, `SM_Chair_LOD3`
- Suffix case-sensitive: must be `_LOD0` not `_lod0`
- With Nanite enabled: manual LODs are unnecessary — omit them

---

## §8. Texture sRGB table

| Texture type | sRGB in UE | Notes |
|---|---|---|
| Base Color / Albedo | **ON** | Gamma-corrected color data |
| Emissive | **ON** | Gamma-corrected color |
| Normal Map | **OFF** (Linear) | Raw tangent-space vector data |
| Roughness | **OFF** (Linear) | Scalar |
| Metallic | **OFF** (Linear) | Scalar |
| AO (Ambient Occlusion) | **OFF** (Linear) | Scalar |
| ORM packed | **OFF** (Linear) | All channels linear |
| Packed RMAO | **OFF** (Linear) | All channels linear |
| Opacity / Mask | **OFF** (Linear) | Scalar |

**The #1 import failure**: importing ORM or normal maps with sRGB enabled. The texture will look
"washed out" or "metallic everything / rough nothing." Set compression to `TC_Masks` for ORM
(enforces linear) and `TC_NormalMap` for normals (enforces linear + BC5 compression).

---

## §9. Critical gotchas

| Gotcha | Symptom | Fix |
|---|---|---|
| **100× scale (FBX)** | 1.8m character is 180m in UE | `apply_unit_scale=True` in Blender + `convert_scene_unit=True` in UE |
| **Axis flip (Z-up flip)** | Mesh arrives rotated 90° | `convert_scene=True` at UE import |
| **No smoothing groups** | UE warning: "No smoothing group information was found" | Blender FBX: `mesh_smooth_type='FACE'` (NOT 'NORMALS ONLY') |
| **Material not connected** | Geometry imports but material is empty/grey | FBX Phong→PBR: enable `Import Materials=True`; remap manually if needed |
| **Lightmap UV overlap** | UE "overlapping UVs" warning; broken baked lighting | Blender: second UV channel (TEXCOORD_1) must be non-overlapping; or `generate_lightmap_uvs=True` |
| **Skeletal mesh imports as static** | `import_as_skeletal=False` default | Explicitly set `import_as_skeletal=True` in FbxImportUI |
| **Bone naming clash** | UE renames bones; existing Skeleton mismatches | Match bone names to existing skeleton exactly; set `options.skeleton` |
| **UCX_ not recognized** | Collision ignored | Import option: `import_collision_according_to_mesh_name=True` |
| **Interchange CDO not respected headless** | Interchange ignores pipeline settings in -nullrhi | Provide explicit `override_pipelines` in `ImportAssetParameters` (see §5) |
| **FBX version incompatibility** | "Unsupported FBX version" | Blender exports FBX 7.4 by default — UE 5.x accepts this; problem is with FBX 6.x from old DCCs |
| **USD not loading** | USD assets ignored | Enable: Editor Preferences → Plugins → USD Importer + USD Stage Actor |
| **Windows path separators** | `unreal.load_asset("C:\\...")` fails | Always use forward slashes: `"C:/path"` |

### Validate imported StaticMesh (Python)
```python
def validate_static_mesh(path: str) -> dict:
    mesh = unreal.load_asset(path)
    if not isinstance(mesh, unreal.StaticMesh):
        return {"ok": False, "error": "not_a_static_mesh"}
    lod0 = mesh.get_static_mesh_lod_for_lod(0)
    bounds = mesh.get_editor_property("extended_bounds")
    max_dim = max(
        bounds.box_extent.x, bounds.box_extent.y, bounds.box_extent.z
    ) * 2  # extent is half-size
    return {
        "ok": True,
        "path": path,
        "nanite_enabled": mesh.nanite_settings.enabled,
        "lod_count": mesh.get_num_lods(),
        "scale_ok": 1 < max_dim < 100_000,  # > 1cm, < 1000m in UE cm units
        "max_extent_cm": max_dim,
    }
```
