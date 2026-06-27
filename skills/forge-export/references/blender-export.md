# Blender Headless Export — Commands & Parameters
# forge-export | references/blender-export.md

## Contents
- §1. Blender invocation pattern (Windows, mandatory `--`)
- §2. GLB export — bpy.ops.export_scene.gltf full parameter table
- §3. FBX export — bpy.ops.export_scene.fbx
- §4. USD export — bpy.ops.wm.usd_export
- §5. Alembic export — bpy.ops.wm.alembic_export
- §6. Coordinate system rules (Y-up/Z-up cheatsheet)
- §7. Critical gotchas

---

## §1. Blender invocation pattern (Windows)

**Windows binary path:**
```
C:\Program Files\Blender Foundation\Blender 4.2\blender.exe
```
(Adjust version substring; 4.2 LTS is the stable production default as of mid-2026.)

**Mandatory invocation pattern:**
```powershell
blender -b "C:/path/to/scene.blend" -P "C:/path/to/script.py" -- --arg1 value1
# OR headless with no .blend (procedural export):
blender -b --python "C:/path/to/script.py" -- --arg1 value1
```

- `-b` = background/headless mode (REQUIRED — without it, Blender opens a GUI).
- `-P script.py` = run Python script after Blender initializes.
- `--` = mandatory argument separator. Everything BEFORE `--` goes to Blender; everything AFTER goes to the Python script accessible via `sys.argv[sys.argv.index("--") + 1:]`.
- `--python-exit-code 1` = makes Python exceptions fail the Blender process with exit 1 (highly recommended for CI).
- **Never use `blender.exe` (bare)** — always use the full absolute path, quoted.
- **Absolute forward-slash paths** in Python `filepath=` arguments (never `//`, never backslash).

**Recommended full invocation for export scripts:**
```powershell
& "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" `
    -b "C:/project/scene.blend" `
    --python-exit-code 1 `
    -P "C:/scripts/export_glb.py" `
    -- `
    --out "C:/forge-build/out/hero.glb"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Blender export failed (exit $LASTEXITCODE)"
    exit 1
}
```

---

## §2. GLB export — full parameter table

```python
# export_glb.py — headless Blender GLB exporter
# Run as: blender -b scene.blend --python-exit-code 1 -P export_glb.py -- --out C:/out/hero.glb
import bpy, sys, os

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = "C:/forge-build/out/model.glb"
    for i, arg in enumerate(args):
        if arg == "--out" and i + 1 < len(args):
            out_path = args[i + 1]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    bpy.ops.export_scene.gltf(
        filepath=out_path,
        # --- Format ---
        export_format='GLB',             # 'GLB' = single binary file; 'GLTF_SEPARATE' = JSON + .bin + textures; 'GLTF_EMBEDDED' = JSON with base64
        # --- Coordinate system ---
        export_yup=True,                 # Convert Blender Z-up to glTF Y-up (ALWAYS True for glTF spec)
        # --- Geometry ---
        export_apply=False,              # CRITICAL: False = keep modifiers non-destructive; True = bake (destroys shape keys)
        export_normals=True,
        export_texcoords=True,
        export_tangents=False,           # False = let renderer compute via MikkTSpace (recommended); True = bake tangents
        use_mesh_edges=False,
        use_mesh_vertices=False,
        # --- Materials ---
        export_materials='EXPORT',       # 'EXPORT' = full PBR; 'PLACEHOLDER' = stubs; 'NONE' = no materials
        export_image_format='AUTO',      # 'AUTO' = PNG for alpha, JPEG otherwise; 'JPEG'; 'PNG'; 'WEBP'; 'NONE'
        export_jpeg_quality=75,
        export_image_quality=75,
        # --- Textures ---
        export_texture_dir='',           # '' = embed in GLB; relative path = sidecar textures (only for GLTF_SEPARATE)
        export_original_specular=False,
        # --- Draco compression ---
        export_draco_mesh_compression_enable=False,  # False = apply Draco AFTER export via forge-optimize (recommended)
        export_draco_mesh_compression_level=6,       # 0-10; default 6
        export_draco_position_quantization=14,
        export_draco_normal_quantization=10,
        export_draco_texcoord_quantization=12,
        export_draco_color_quantization=10,
        export_draco_generic_quantization=12,
        # --- Lights ---
        export_lights=False,             # False for render-engine portability; True emits KHR_lights_punctual
        # --- Cameras ---
        export_cameras=False,
        # --- Animation ---
        export_animations=True,
        export_frame_range=True,         # Respect scene frame start/end
        export_nla_strips=True,          # Export NLA editor strips
        export_nla_strips_merged_animation_name='Action',
        export_animate_single_object=False,
        export_anim_slide_to_zero=False,
        export_bake_animation=False,     # False = export curves; True = bake to every frame (large files)
        export_optimize_animation_size=True,   # Deduplicate animated frames
        export_optimize_animation_keep_anim_armature=True,
        export_optimize_animation_keep_anim_object=False,
        # --- Skinning ---
        export_skins=True,
        export_all_influences=False,     # False = max 4 influences (game standard); True = all
        # --- Morph targets ---
        export_morph=True,
        export_morph_normal=True,
        export_morph_tangent=False,
        export_morph_animation=True,
        # --- Visibility / selection ---
        use_selection=False,             # False = export entire scene; True = selection only
        use_visible=False,               # False = export all (including hidden layers)
        use_renderable=False,
        use_active_collection=False,
        use_active_scene=True,
        # --- Logging ---
        export_loglevel=0,               # 0=verbose
    )
    print(f"[forge-export] GLB written: {out_path} ({os.path.getsize(out_path) // 1024} KB)")

main()
```

### Critical parameter notes

| Parameter | Warning |
|---|---|
| `export_apply=False` | **Never set True when shape keys / morph targets exist** — it destroys them. Only set True when consuming engine cannot interpret Blender modifiers AND there are no shape keys. |
| `export_yup=True` | **Always True** — this is the glTF spec. Without it, assets arrive rotated 90° in all viewers. |
| `export_draco_mesh_compression_enable=False` | Keep False and apply Draco via `forge-optimize` (gltf-transform). Blender's Draco requires external Draco library; gltf-transform handles it more reliably. |
| `export_tangents=False` | Recommended False — most renderers compute MikkTSpace tangents at load time. Exporting explicit tangents doubles UV derivation risk (tangent seams at UV boundaries). |
| `export_image_format='AUTO'` | Produces JPEG for non-alpha, PNG for alpha. For web: prefer WEBP for color textures after export (via forge-optimize). |

---

## §3. FBX export

```python
# export_fbx.py — Blender FBX export for Unreal / Unity pipelines
# Run as: blender -b scene.blend --python-exit-code 1 -P export_fbx.py -- --out C:/out/char.fbx
import bpy, sys, os

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = "C:/forge-build/out/model.fbx"
    for i, arg in enumerate(args):
        if arg == "--out" and i + 1 < len(args):
            out_path = args[i + 1]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    bpy.ops.export_scene.fbx(
        filepath=out_path,
        # --- Coordinate system ---
        axis_forward='-Z',               # Blender +Y forward → FBX -Z forward (UE/Unity convention)
        axis_up='Y',                     # Blender +Z up → FBX +Y up
        apply_unit_scale=True,           # Normalize Blender meters → FBX centimeters (1m = 100 units)
        apply_scale_options='FBX_SCALE_NONE',  # 'FBX_SCALE_NONE', 'FBX_SCALE_UNITS', 'FBX_SCALE_CUSTOM', 'FBX_SCALE_ALL'
        # --- Geometry ---
        use_space_transform=True,
        bake_space_transform=False,      # False = preserve transforms; True = bake into vertex positions (loses hierarchy)
        use_mesh_modifiers=False,        # CRITICAL: False preserves shape keys / morph targets. True BAKES & DROPS them
                                         # (matches forge-rig §13 / blendshapes-morphs §8). Set True ONLY when no shape
                                         # keys exist AND the engine cannot read Blender modifiers.
        use_mesh_modifiers_render=False,
        mesh_smooth_type='FACE',         # 'FACE' or 'EDGE' smoothing groups (not 'NORMALS ONLY')
        # --- Materials ---
        path_mode='COPY',                # 'COPY' = embed textures in FBX; 'ABSOLUTE' = keep paths; 'RELATIVE'
        embed_textures=True,
        # --- Animation ---
        bake_anim=True,
        bake_anim_use_all_bones=True,
        bake_anim_use_nla_strips=True,
        bake_anim_use_all_actions=True,
        bake_anim_force_startend_keying=True,
        bake_anim_step=1.0,
        bake_anim_simplify_factor=1.0,
        # --- Rig ---
        add_leaf_bones=False,            # NEVER True for UE5/Unity — leaf bones corrupt the skeleton
                                         # (matches forge-rig rigging-armatures §16 / forge-animate skeletal-morph-export §8).
        primary_bone_axis='Y',           # Bone Y = bone direction (Blender default)
        secondary_bone_axis='X',
        armature_nodetype='NULL',
        use_armature_deform_only=True,   # Drop non-deform/control bones from the export skeleton (game-ready). Set False
                                         # only when the target needs the full control rig (rare for engine egress).
        # --- Selection ---
        use_selection=False,
        use_visible=False,
        use_active_collection=False,
        use_mesh_edges=False,
        # --- Misc ---
        use_tspace=True,                 # Export tangent space (MikkTSpace)
        use_custom_props=True,
        use_metadata=True,
    )
    print(f"[forge-export] FBX written: {out_path} ({os.path.getsize(out_path) // 1024} KB)")

main()
```

**`mesh_smooth_type` note:** Must be `'FACE'` or `'EDGE'` — NOT `'NORMALS ONLY'`. Unreal will warn
"No smoothing group information was found" and import the mesh with hard edges everywhere if set to
`'NORMALS ONLY'`.

---

## §4. USD export

```python
# export_usd.py — Blender USD export for multi-DCC pipeline
# Run as: blender -b scene.blend --python-exit-code 1 -P export_usd.py -- --out C:/out/scene.usdc
import bpy, sys, os

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = "C:/forge-build/out/scene.usda"
    for i, arg in enumerate(args):
        if arg == "--out" and i + 1 < len(args):
            out_path = args[i + 1]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    bpy.ops.wm.usd_export(
        filepath=out_path,
        # Use .usda for text/debug; .usdc for binary production; .usdz for AR
        # --- Geometry ---
        export_meshes=True,
        apply_modifiers=True,
        export_normals=True,
        export_uvmaps=True,
        rename_uvmaps=True,              # Renames Blender's "UVMap" → "st" (USD/UsdPreviewSurface convention)
        # --- Materials ---
        export_materials=True,
        generate_preview_surface=True,   # Convert Principled BSDF → UsdPreviewSurface (REQUIRED for Apple AR)
        export_pbr_extensions=True,      # Export MaterialX-based PBR extensions where available
        export_textures=True,
        overwrite_textures=False,
        convert_world_material=True,     # Convert Blender world shader → USD dome light
        # --- Skeleton / Animation ---
        export_armatures=True,
        export_shapekeys=True,
        export_animation=True,
        # --- Coordinate system ---
        # Use ONE axis mechanism. The explicit forward/up selectors below ARE the conversion;
        # do NOT also set convert_orientation=True or the axis fix double-applies (mesh ends up
        # mis-rotated). convert_orientation defaults False — leave it off when using these selectors.
        export_global_forward_selection='NEGATIVE_Z',  # Blender -Z forward → USD
        export_global_up_selection='Y',                # Y-up for USD
        # --- Scene structure ---
        export_selected_objects=False,
        default_prim_path='/root',       # the named defaultPrim under the pseudo-root
        root_prim_path='/',              # pseudo-root ('/'), NOT '/root' — some 4.x reject root==default;
                                         # matches forge-sim/export-cache.md §3
    )
    print(f"[forge-export] USD written: {out_path}")

main()
```

**Blender USD limitations (4.2 / 5.x):**
- Flat export only — no USD layers, variants, or references on export
- Only perspective cameras
- UDIM textures cannot be included in USDZ (tracked upstream)
- Nested instances/collections: experimental only

**After Blender USD export, convert to binary for production:**
```powershell
# Requires full USD prebuilt: https://openusd.org/release/dl_downloads.html
usdcat "C:/out/scene.usda" --out "C:/out/scene.usdc"
```

---

## §5. Alembic export

```python
# export_alembic.py — baked simulation/animation cache
# Run as: blender -b scene.blend --python-exit-code 1 -P export_alembic.py -- --out C:/out/sim.abc
import bpy, sys, os

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    out_path = "C:/forge-build/out/sim.abc"
    for i, arg in enumerate(args):
        if arg == "--out" and i + 1 < len(args):
            out_path = args[i + 1]

    os.makedirs(os.path.dirname(out_path), exist_ok=True)

    # CRITICAL: read frame range AFTER any simulation bake (frame_start/end updates post-sim)
    scene = bpy.context.scene
    start = scene.frame_start
    end = scene.frame_end

    bpy.ops.wm.alembic_export(
        filepath=out_path,
        start=start,                     # MUST be explicit — default is current frame only
        end=end,
        xsamples=1,                      # Geometry samples per frame
        gsamples=1,                      # Transform samples per frame
        sh_open=0.0,
        sh_close=1.0,
        selected=False,
        visible_objects_only=False,
        flatten=False,
        uvs=True,
        packuv=True,
        normals=True,
        vcolors=True,
        face_sets=False,
        use_instancing=True,
        global_scale=1.0,
        triangulate=True,
        quad_method='SHORTEST_DIAGONAL',
        ngon_method='BEAUTY',
        export_hair=False,
        export_particles=False,
    )
    print(f"[forge-export] Alembic written: {out_path}")

main()
```

**Warning:** If `start` and `end` default, Alembic exports only the current frame (static).
Always read `scene.frame_start / scene.frame_end` explicitly AFTER any sim bake.

---

## §6. Coordinate system cheatsheet

| Engine/Format | Up axis | Handedness | Forward | Units |
|---|---|---|---|---|
| **glTF 2.0** | **+Y** | **Right** | **−Z** | **Meters** |
| **Blender** | +Z | Right | −Y (object convention) | Meters |
| **Unreal Engine 5** | +Z | **Left** | +X | Centimeters (1 UU = 1 cm) |
| **Unity** | +Y | **Left** | +Z | Meters |
| **Godot 4** | +Y | Right | −Z | Meters |
| **USD** | +Y (default) | Right | −Z | Centimeters (metersPerUnit=0.01 default) |
| **FBX (Maya)** | +Y | Right | −Z | Centimeters |
| **Alembic** | +Y | Right | −Z | Centimeters |

**Blender → glTF:** Set `export_yup=True`. The exporter adds a root -90° X rotation.
**Do NOT** manually rotate the Blender scene — let the exporter handle the axis.

**Blender → FBX → Unreal:**
- Export: `axis_forward='-Z'`, `axis_up='Y'`, `apply_unit_scale=True`
- Import UE: `convert_scene=True`, `convert_scene_unit=True`

**Blender → FBX → Unity:**
- Export: `axis_forward='-Z'`, `axis_up='Y'`
- Import Unity: `useFileUnits=true`, `bakeAxisConversion=true`
- `bakeAxisConversion=True` bakes the Z→Y flip into vertex positions (no root Transform rotation).
  A root Transform rotation breaks physics raycasts and NavMesh — always bake.

---

## §7. Critical gotchas

### G1 — export_apply=True + shape keys = lost morphs
**Symptom:** Shape keys / morph targets absent from GLB.
**Cause:** `export_apply=True` bakes and removes shape key data.
**Fix:** Never set `export_apply=True` when shape keys exist. Apply modifiers manually first.

### G2 — Non-color textures in sRGB color space
**Symptom:** glTF-Validator warns `IMAGE_COLORSPACE_MISMATCH`. ORM / normals render wrong.
**Cause:** Blender ORM/normal Image Texture nodes left at "sRGB" instead of "Non-Color."
**Fix:** In Blender Python before export: `img.colorspace_settings.name = 'Non-Color'` for all
ORM, normal, roughness, metallic, AO, displacement images. BaseColor and emissive stay "sRGB."

### G3 — Blender Z-up bone root rotation in GLB
**Symptom:** Root bone has unexpected −90° X rotation in the exported GLB.
**Cause:** Blender bones use Y along bone axis; glTF uses Y-up. The exporter injects a root
coordinate-change transform. This is CORRECT behavior per glTF spec.
**Fix:** Not a bug. Three.js GLTFLoader handles this automatically.

### G4 — export_apply=False with Array modifier = correct (do not change)
**Cause confusion:** Setting `export_apply=True` on a 100-segment road mesh with Array turns
a 1 MB file into 56+ MB. Never set True unless the consuming engine cannot interpret modifiers
AND you have verified there are no shape keys.

### G5 — `--python-exit-code 1` missing from CLI
**Symptom:** Blender script crashes silently; parent PowerShell sees exit code 0.
**Fix:** Always add `--python-exit-code 1` to the Blender invocation in CI.

### G6 — FBX `use_mesh_modifiers=True` bakes away shape keys
**Symptom:** Morph targets / shape keys absent from the FBX (same failure as G1, but on the FBX path).
**Cause:** `bpy.ops.export_scene.fbx(use_mesh_modifiers=True)` applies modifiers, which silently
strips shape keys — exactly the outcome forge-rig (blendshapes-morphs §8 rule #6) warns against.
**Fix:** Keep `use_mesh_modifiers=False` (the canonical §3 default). Set True ONLY when there are
no shape keys AND the engine cannot interpret Blender modifiers. For a morph-safe rigged export,
pair `use_mesh_modifiers=False` with `use_armature_deform_only=True`.

### G7 — FBX `add_leaf_bones=True` corrupts UE5/Unity skeletons
**Symptom:** Extra end/leaf bones appear in the imported skeleton; retargeting and existing-skeleton
matches break.
**Cause:** Blender's `add_leaf_bones=True` appends synthetic endpoint bones. UE5 and Unity treat
these as real joints. Both forge-rig (rigging-armatures §16) and forge-animate (skeletal-morph-export
§8) mark this **NEVER** for engine targets.
**Fix:** `add_leaf_bones=False` for any FBX bound for UE5/Unity (the §3 default).
