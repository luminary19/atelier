# Unity 6 (URP/HDRP) — Import Conventions
# forge-export | references/engine-unity.md

## Contents
- §1. Coordinate system, scale, and axis baking
- §2. AssetPostprocessor — ForgeModelImportFixer
- §3. ORM channel layout (CRITICAL — differs per pipeline)
- §4. Headless import invocation
- §5. glTFast 6.x (com.unity.cloud.gltfast) runtime/editor import
- §6. Texture import settings
- §7. Animation import
- §8. Critical gotchas and fixes

---

## §1. Coordinate system, scale, and axis baking

| Property | Unity 6 |
|---|---|
| Up axis | **+Y** |
| Forward axis | **+Z** |
| Handedness | **Left-handed** |
| Scale | **1 unit = 1 meter** |

**Two mandatory ModelImporter flags (in AssetPostprocessor):**
- `useFileUnits = true` — reads the FBX UnitScaleFactor and converts to Unity meters automatically.
  Without this, a Blender 1m cube arrives as 100 units (cm).
- `bakeAxisConversion = true` — BAKES the axis conversion into vertex positions instead of adding a
  root Transform rotation. **This is critical for physics and NavMesh correctness.** A root -90° or
  90° Transform rotation breaks raycasts, physics queries, and NavMesh baking.

---

## §2. AssetPostprocessor — ForgeModelImportFixer

```csharp
// ForgeModelImportFixer.cs — place in Editor/ folder
// Applies to all meshes that contain "Forge_" prefix in their folder path
using UnityEditor;
using UnityEngine;

public class ForgeModelImportFixer : AssetPostprocessor
{
    // IMPORTANT: bump this number every time you change logic,
    // or Unity will not reimport existing assets
    public override uint GetVersion() => 7;

    void OnPreprocessModel()
    {
        if (!assetPath.Contains("Forge_") && !assetPath.Contains("/forge/"))
            return;

        var mi = assetImporter as ModelImporter;
        if (mi == null) return;

        // Scale / axis
        mi.useFileUnits = true;
        mi.bakeAxisConversion = true;   // bake into verts, NOT root transform rotation

        // Normals and tangents
        mi.importNormals = ModelImporterNormals.Import;         // use authored normals
        mi.importTangents = ModelImporterTangents.CalculateMikktspace;

        // Materials / textures
        mi.materialImportMode = ModelImporterMaterialImportMode.ImportViaMaterialDescription;
        mi.materialLocation = ModelImporterMaterialLocation.InPrefab;

        // Mesh
        mi.isReadable = false;        // saves VRAM; set true only for runtime mesh access
        mi.optimizeMeshPolygons = true;
        mi.optimizeMeshVertices = true;
        mi.generateSecondaryUV = false;    // Lightmap UVs: author them in Blender if needed

        // LOD
        mi.importBlendShapes = true;

        Debug.Log($"[Forge] Configured: {assetPath}");
    }

    // Detect wrong scale at import time (100x FBX scale bug)
    void OnPostprocessModel(GameObject root)
    {
        if (!assetPath.Contains("Forge_") && !assetPath.Contains("/forge/"))
            return;

        var scale = root.transform.localScale;
        if (Mathf.Abs(scale.x - 1f) > 0.001f ||
            Mathf.Abs(scale.y - 1f) > 0.001f ||
            Mathf.Abs(scale.z - 1f) > 0.001f)
        {
            Debug.LogWarning(
                $"[Forge] ROOT SCALE != 1,1,1 on {assetPath}: scale={scale}. " +
                "Check FBX export unit settings (apply_unit_scale=True in Blender)."
            );
        }
    }

    // Pink material check (shader not found in build)
    [MenuItem("Forge/Check Pink Materials")]
    static void CheckPinkMaterials()
    {
        var mats = AssetDatabase.FindAssets("t:Material")
            .Select(AssetDatabase.GUIDToAssetPath)
            .Select(p => AssetDatabase.LoadAssetAtPath<Material>(p))
            .Where(m => m != null && m.shader.name == "Hidden/InternalErrorShader");
        foreach (var m in mats)
            Debug.LogError($"[Forge] PINK MATERIAL: {AssetDatabase.GetAssetPath(m)}");
    }
}
```

---

## §3. ORM channel layout — CRITICAL (differs per pipeline)

**This is the most common Forge→Unity integration failure.** glTF spec ORM ≠ Unity ORM.

| Channel | glTF 2.0 spec | Unity URP Metallic Map | Unity HDRP Mask Map |
|---|---|---|---|
| R | **Ambient Occlusion** | **Metallic** | **Metallic** |
| G | **Roughness** | **Occlusion (AO)** | **Occlusion (AO)** |
| B | **Metallic** | (unused) | **Detail Mask** |
| A | (unused) | **Smoothness** (1−Roughness) | **Smoothness** (1−Roughness) |

**Key differences:**
- Unity URP Lit: no separate roughness channel — uses **A = Smoothness** (= 1 − Roughness).
  You must invert the roughness map into the alpha channel.
- Unity HDRP: B = DetailMask (not Metallic); A = Smoothness.
- glTFast auto-remaps from glTF spec to URP/HDRP Lit at import — do NOT manually repack
  when using glTFast as the importer.
- FBX import (standard ModelImporter) does NOT auto-remap — provide pre-packed textures.

**ImageMagick ORM repack for URP Lit (PowerShell):**
```powershell
# Source maps: metallic.png (grayscale), ao.png (grayscale), roughness.png (grayscale)
# Target: URP Metallic Map (R=Metallic, G=AO, B=0, A=Smoothness)
$metal = "C:\textures\src\T_Chair_Metallic.png"
$ao    = "C:\textures\src\T_Chair_AO.png"
$rough = "C:\textures\src\T_Chair_Roughness.png"
$out   = "C:\textures\T_Chair_MetallicSmoothness.png"

# Negate roughness to get smoothness (Smoothness = 1 - Roughness)
# Pack: -set colorspace Gray for per-channel isolation
magick convert `
    $metal $ao `
    -size 2048x2048 xc:black `
    $rough -negate `
    -channel R -combine `
    -colorspace sRGB `
    $out

Write-Host "[Forge] URP Metallic Map written: $out"
```

**ImageMagick ORM repack for HDRP Mask Map:**
```powershell
$metal      = "C:\textures\src\T_Chair_Metallic.png"
$ao         = "C:\textures\src\T_Chair_AO.png"
$detailmask = "C:\textures\src\T_Chair_DetailMask.png"   # or xc:black if none
$rough      = "C:\textures\src\T_Chair_Roughness.png"
$out        = "C:\textures\T_Chair_HDRPMaskMap.png"

magick convert `
    $metal $ao $detailmask `
    $rough -negate `
    -channel RGBA -combine `
    $out
```

---

## §4. Headless import invocation

```powershell
# Unity batch import
$unityExe = "C:\Program Files\Unity\Hub\Editor\6000.0.1f1\Editor\Unity.exe"
& $unityExe `
    -projectPath "C:\MyUnityProject" `
    -batchmode `
    -quit `
    -executeMethod "ForgeEditorTools.ImportForgeAssets" `
    -logFile "C:\Logs\unity_import.log"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Unity batch import failed"
    Get-Content "C:\Logs\unity_import.log" -Tail 40 | Write-Host
    exit 1
}
```

**ForgeEditorTools.ImportForgeAssets (C#):**
```csharp
using UnityEditor;
using System.IO;

public static class ForgeEditorTools
{
    public static void ImportForgeAssets()
    {
        string sourceDir = "C:/forge-build/out";
        string destDir = "Assets/Forge";

        if (!Directory.Exists(destDir))
            Directory.CreateDirectory(destDir);

        foreach (var fbx in Directory.GetFiles(sourceDir, "*.fbx"))
        {
            string dest = Path.Combine(destDir, Path.GetFileName(fbx));
            File.Copy(fbx, dest, overwrite: true);
        }
        foreach (var glb in Directory.GetFiles(sourceDir, "*.glb"))
        {
            string dest = Path.Combine(destDir, Path.GetFileName(glb));
            File.Copy(glb, dest, overwrite: true);
        }

        AssetDatabase.Refresh();
        AssetDatabase.SaveAssets();
    }
}
```

---

## §5. glTFast 6.x — runtime and editor import

**Package ID:** `com.unity.cloud.gltfast` (6.17.0 as of Unity 6 / 2023.x LTS)

**Runtime GLB load (C#, glTFast):**
```csharp
using GLTFast;
using UnityEngine;

public class ForgeGLTFLoader : MonoBehaviour
{
    async void Start()
    {
        // Load from filesystem (editor or development build)
        var gltf = new GltfImport();
        bool success = await gltf.Load("C:/forge-build/out/hero.glb");
        if (success)
        {
            await gltf.InstantiateMainSceneAsync(transform);
        }
        else
        {
            Debug.LogError("[Forge] glTFast failed to load hero.glb");
        }
    }
}
```

**Editor scripted import with glTFast:**
```csharp
// In an EditorWindow or AssetPostprocessor for .glb files
using GLTFast.Editor;
using UnityEditor;

// glTFast registers its own ScriptedImporter for .glb and .gltf
// Configure it via GltfAssetImporter settings in the inspector,
// or override defaults via GltfImportSettings:
var settings = new GLTFast.ImportSettings
{
    GenerateMipMaps = true,
    AnisotropicFilterLevel = 4,
    NodeNameMethod = GLTFast.NodeNameMethod.OriginalUnique,
};
```

**Critical glTFast note — missing shader variants in builds:**
If GLB assets render as pink in a standalone build, the required glTFast shader variants are
not included. Fix: In Project Settings → Graphics → Shader Preloading, add the
`glTFast` shader variant collection. Or add `GLTFast.Materials.StandardMaterialGenerator`
to the preloaded assets.

---

## §6. Texture import settings

```csharp
// ForgeTextureImporter.cs — set correct texture types and color spaces
using UnityEditor;

public class ForgeTextureImporter : AssetPostprocessor
{
    public override uint GetVersion() => 4;

    void OnPreprocessTexture()
    {
        if (!assetPath.Contains("/forge/") && !assetPath.Contains("Forge_"))
            return;

        var ti = assetImporter as TextureImporter;
        if (ti == null) return;

        string lower = assetPath.ToLower();
        if (lower.Contains("_normal") || lower.Contains("_norm"))
        {
            ti.textureType = TextureImporterType.NormalMap;
            // Unity AUTOMATICALLY sets sRGB=false when type=NormalMap
            ti.convertToNormalmap = false;
        }
        else if (lower.Contains("_orm") || lower.Contains("_metallic") ||
                 lower.Contains("_roughness") || lower.Contains("_ao") ||
                 lower.Contains("_mask"))
        {
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = false;  // LINEAR — CRITICAL
        }
        else if (lower.Contains("_albedo") || lower.Contains("_basecolor") ||
                 lower.Contains("_diffuse") || lower.Contains("_emissive"))
        {
            ti.textureType = TextureImporterType.Default;
            ti.sRGBTexture = true;   // sRGB — color data
        }
    }
}
```

---

## §7. Animation import

**Humanoid vs Generic:**
```csharp
// Humanoid: for characters using Unity's Avatar system (retargeting)
mi.animationType = ModelImporterAnimationType.Human;
mi.avatarSetup = ModelImporterAvatarSetup.CreateFromThisModel;
mi.optimizeGameObjects = true;   // Removes unused joints from runtime hierarchy

// Generic: for non-humanoid characters and mechanical rigs
mi.animationType = ModelImporterAnimationType.Generic;
mi.avatarSetup = ModelImporterAvatarSetup.NoAvatar;
```

**Animation-only FBX (@ convention):**
```
SkeletonBase.fbx       ← mesh + skeleton, NO animations
@Walk.fbx              ← animations only, references same skeleton
@Run.fbx               ← animations only
@Idle.fbx              ← animations only
```
The `@` prefix tells Unity's legacy importer to apply animations to the skeleton in the
corresponding non-@ file. The base and animation files must be in the same directory.

---

## §8. Critical gotchas

| Gotcha | Symptom | Fix |
|---|---|---|
| **Pink materials** | Material renders bright pink | Shader missing in build. Check `shader.name == "Hidden/InternalErrorShader"`. Causes: shader stripped in build, URP↔HDRP mismatch, custom shader not added to Graphics settings. |
| **Wrong scale (0.01 bug)** | Asset 100× too small in Unity | `useFileUnits=false` (default). Fix: set `useFileUnits=true` in ModelImporter. |
| **Root Transform rotation** | Physics/NavMesh broken, root has 90° rotation | `bakeAxisConversion=false`. Fix: set `bakeAxisConversion=true`. |
| **Flipped/incorrect normals** | Faces lit from wrong direction | Wrong normal map convention (DX vs OpenGL). Check `textureType == NormalMap` and if source is DirectX-convention, flip green channel via ImageMagick. |
| **Normal map sRGB enabled** | Normals look "mushy" / incorrect | `sRGBTexture=true` on normal. Fix: type=NormalMap (Unity auto-corrects) or `sRGBTexture=false` explicitly. |
| **ORM sRGB enabled** | Roughness/metallic all wrong | `sRGBTexture=true` on ORM. Fix: `sRGBTexture=false` explicitly. |
| **glTFast shader variants missing** | Pink in standalone build | Add `gltFast Shader Variants` to Graphics Settings → Preloaded Assets. |
| **Windows paths in AssetDatabase** | `AssetDatabase.ImportAsset` fails | Always use forward slashes: `"Assets/Forge/mesh.fbx"` not backslash. |
| **Prefab creation in OnPostprocessModel** | "Cannot create prefab in OnPostprocessModel" | Move prefab creation to `OnPostprocessAllAssets()` instead. |
| **AssetPostprocessor version not bumped** | Logic change ignored; old settings persist | Increment `GetVersion()` return value on every logic change. |
