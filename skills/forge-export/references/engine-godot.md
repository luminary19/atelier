# Godot 4.3–4.6 — Import Conventions
# forge-export | references/engine-godot.md

## Contents
- §1. Coordinate system and headless import
- §2. GLB headless batch import (PowerShell)
- §3. .import sidecar file (full reference)
- §4. ORM channel setup (StandardMaterial3D)
- §5. Collision suffix naming
- §6. Runtime GLB load (GDScript + C#)
- §7. EditorScenePostImport hook
- §8. Version-specific bugs
- §9. CI validation pipeline
- §10. Critical gotchas

---

## §1. Coordinate system and headless import

| Property | Godot 4.x |
|---|---|
| Up axis | **+Y** |
| Forward axis | **−Z** |
| Handedness | **Right-handed** |
| Scale | **1 unit = 1 meter** |

Godot 4 shares glTF's Y-up right-handed coordinate system — no axis conversion needed for GLB exports.
FBX imports via built-in ufbx (since Godot 4.3, no external FBX SDK needed) are also auto-converted.

**Headless import command (Godot 4.3+):**
```powershell
# The --import flag was added in Godot 4.3 (PR #90431)
# Blocks until ALL assets in the project are imported
& "C:\Godot\Godot_v4.4.1-stable_win64.exe" `
    --headless `
    --import `
    --path "C:\MyGodotProject"

if ($LASTEXITCODE -ne 0) {
    Write-Error "Godot headless import failed (exit $LASTEXITCODE)"
    exit 1
}
```

**Before 4.3 (--editor --quit pattern — has race condition):**
```powershell
# Only use if stuck on 4.2.x — tends to exit before import finishes
& "C:\Godot\Godot_v4.2.2-stable_win64.exe" `
    --headless `
    --editor `
    --path "C:\MyGodotProject" `
    --quit
Start-Sleep -Seconds 10   # unreliable; use --import in 4.3+
```

---

## §2. GLB headless batch import (PowerShell)

```powershell
# forge_godot_import.ps1 — copy GLBs into project and trigger headless import
param(
    [string]$SourceDir  = "C:\forge-build\out",
    [string]$ProjectDir = "C:\MyGodotProject",
    [string]$AssetsSubDir = "assets\models",
    [string]$GodotExe = "C:\Godot\Godot_v4.4.1-stable_win64.exe"
)

$dest = Join-Path $ProjectDir $AssetsSubDir
if (-not (Test-Path $dest)) { New-Item -ItemType Directory -Force $dest | Out-Null }

# Copy all GLBs from the Forge output directory
$glbs = Get-ChildItem $SourceDir -Filter "*.glb"
foreach ($glb in $glbs) {
    $target = Join-Path $dest $glb.Name
    Copy-Item $glb.FullName $target -Force
    Write-Host "[Forge] Copied: $($glb.Name)"
}

if ($glbs.Count -eq 0) {
    Write-Warning "[Forge] No .glb files found in $SourceDir"
    exit 0
}

# Run headless import
Write-Host "[Forge] Running Godot headless import..."
& $GodotExe --headless --import --path $ProjectDir
if ($LASTEXITCODE -ne 0) {
    Write-Error "[Forge] Godot headless import FAILED"
    exit 1
}

# Verify .import sidecars were created
$missing = $glbs | Where-Object {
    -not (Test-Path (Join-Path $dest "$($_.Name).import"))
}
if ($missing) {
    Write-Error "[Forge] Missing .import for: $($missing.Name -join ', ')"
    exit 1
}

Write-Host "[Forge] Import complete. $($glbs.Count) GLB(s) imported."
```

---

## §3. .import sidecar file (full reference)

Godot creates `<file>.import` next to every imported asset. **Commit these files — they encode
all import settings.** Do NOT commit the `.godot/imported/` cache directory (gitignore it).

```ini
; Example: hero.glb.import
; Place this file alongside hero.glb in the assets/ directory

[remap]
importer="scene"
importer_version=1
type="PackedScene"
uid="uid://forgeheroglb001"
path=".godot/imported/hero.glb-abc123.scn"

[deps]
source_file="res://assets/models/hero.glb"
dest_files=[".godot/imported/hero.glb-abc123.scn"]

[params]
; Mesh settings
meshes/ensure_tangents=true
meshes/generate_lods=true
meshes/create_shadow_meshes=true
meshes/lod_bias=1.0
meshes/compression_ratio=0.5

; FBX / glTF settings
gltf/naming_version=2            ; 4.5+ naming convention (avoids _ separators in old names)
gltf/embedded_image_handling=1  ; 0=discard, 1=extract, 2=embed-as-is. 1=extract is strongly recommended

; Node cleanup
nodes/apply_root_scale=true
nodes/root_scale=1.0
nodes/root_type="Node3D"
nodes/import_as_skeleton_bones=false

; Animation
animation/import=true
animation/fps=30
animation/trimming=false
animation/remove_immutable_tracks=true

; Skins
skins/use_named_skins=true      ; preserve bone names for animations

; Physics
meshes/occluder_import_mode=0   ; 0=disabled, 1=occluder only, 2=occluder+mesh

; Lights
lights/import=true

; Cameras
cameras/import=true
```

**gltf/naming_version note:**
- **Version 1** (Godot <4.5): underscores added between words in node names → `"My Mesh"` → `"My_Mesh"`
- **Version 2** (Godot 4.5+): node names preserved as-is → `"My Mesh"` → `"My Mesh"`
- Mismatch causes animations to not find their target nodes. Always set consistently.

**gltf/embedded_image_handling:**
- `0` = discard (never use for final assets)
- `1` = extract to separate files (recommended — keeps textures reimportable)
- `2` = embed as-is in the scene (larger scene file)

---

## §4. ORM channel setup (StandardMaterial3D)

Godot 4's StandardMaterial3D follows the glTF 2.0 ORM channel layout — unlike Unity.

| Channel | glTF spec | Godot StandardMaterial3D |
|---|---|---|
| R | Ambient Occlusion | `ao_texture_channel = RED` |
| G | Roughness | `roughness_texture_channel = GREEN` |
| B | Metallic | `metallic_texture_channel = BLUE` |
| A | (unused in core) | — |

**GDScript: set ORM texture on a StandardMaterial3D:**
```gdscript
var mat := StandardMaterial3D.new()
var orm_tex := load("res://assets/textures/T_Chair_ORM.png")

mat.metallic_texture = orm_tex
mat.metallic_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_BLUE

mat.roughness_texture = orm_tex
mat.roughness_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_GREEN

mat.ao_enabled = true
mat.ao_texture = orm_tex
mat.ao_texture_channel = BaseMaterial3D.TEXTURE_CHANNEL_RED

# CRITICAL: ORM textures must be imported as linear (non-sRGB)
# In the .import file: set flags/srgb=false
# Or in the Import dock: uncheck "sRGB" flag
```

**Force linear import on ORM textures** by adding to the texture .import file:
```ini
[params]
flags/srgb=false
```
Without this, roughness and metallic channels are gamma-corrected and physically wrong.

---

## §5. Collision suffix naming

Add suffixes to **node names** (not mesh data names) in Blender before export.

| Suffix | Collision shape | Mesh visibility | Notes |
|---|---|---|---|
| `-col` | Trimesh (StaticBody3D) | Visible | Use for visible static geometry |
| `-convcol` | Convex hull | Visible | Use for convex-shaped visible geometry |
| `-colonly` | Trimesh | **Invisible** | Pure collision, no render |
| `-convcolonly` | Convex hull | **Invisible** | Pure convex collision |
| `-navmesh` | NavigationMesh | Invisible | For pathfinding |
| `-occ` | OccluderMesh | Visible | Occlusion culling |
| `-occonly` | OccluderMesh | **Invisible** | Occlusion culling, no render |
| `-rigid` | RigidBody3D | Visible | Physics-simulated rigid body |
| `-vehicle` | VehicleBody3D | Visible | Vehicle physics |
| `-wheel` | VehicleWheel3D | Visible | Vehicle wheel |

**Important:** Suffix applies to the **node name** in the scene hierarchy, not the mesh data block name.
If your FBX/GLB was exported from Blender with a mesh named `Chair_col`, you must also rename the
**scene node** to `Chair-col` (or export with the suffix already in the node name).
Open bug #115869 as of Godot 4.4: only node names, not mesh names, are read for collision suffixes.

**Trimesh vs convex for gameplay:**
- Trimesh: exact shape — best for terrain, walls, floors. Cannot be used with RigidBody3D (only StaticBody3D).
- Convex hull: approximate but works with all physics bodies including RigidBody3D.

---

## §6. Runtime GLB load

**GDScript (simplest — sync load):**
```gdscript
extends Node3D

func load_forge_model(path: String) -> Node3D:
    var gltf := GLTFDocument.new()
    var gltf_state := GLTFState.new()
    gltf_state.handle_binary_image = GLTFState.HANDLE_BINARY_EMBED_AS_BASISU

    var err := gltf.append_from_file(path, gltf_state)
    if err != OK:
        push_error("[Forge] Failed to load GLB: %s (error %d)" % [path, err])
        return null

    var scene := gltf.generate_scene(gltf_state)
    add_child(scene)
    return scene

func _ready() -> void:
    load_forge_model("res://assets/models/hero.glb")
```

**Load from buffer (for streamed/downloaded GLB):**
```gdscript
func load_forge_from_buffer(buffer: PackedByteArray, base_path: String = "") -> Node3D:
    var gltf := GLTFDocument.new()
    var gltf_state := GLTFState.new()
    var err := gltf.append_from_buffer(buffer, base_path, gltf_state)
    if err != OK:
        push_error("[Forge] Buffer load failed: %d" % err)
        return null
    return gltf.generate_scene(gltf_state)
```

**C# runtime load:** equivalent to the GDScript pattern above — use `new GltfDocument()`, `new GltfState()`, `AppendFromFile(path, state)`, `GenerateScene(state)`, `AddChild(scene)`.

---

## §7. EditorScenePostImport hook

```gdscript
# forge_post_import.gd — assign in Import dock → "Script" dropdown
@tool
extends EditorScenePostImport

func _post_import(scene: Node) -> Object:
    _fix_culling(scene)   # Fix backface culling disabled by Blender
    return scene

func _fix_culling(node: Node) -> void:
    if node is MeshInstance3D:
        for i in (node as MeshInstance3D).get_surface_override_material_count():
            var mat := (node as MeshInstance3D).get_active_material(i)
            if mat is StandardMaterial3D:
                (mat as StandardMaterial3D).cull_mode = BaseMaterial3D.CULL_BACK
    for child in node.get_children(): _fix_culling(child)
```

---

## §8. Version-specific bugs

| Version | Bug | Status | Workaround |
|---|---|---|---|
| 4.3 | `--import` flag added (PR #90431) | FIXED in 4.3 | Before 4.3: `--editor --quit` (racy) |
| 4.4.x | `ERROR: Parameter "t" is null` during headless GLB import | FIXED in 4.6 (PR #109116) | Non-fatal; ignore in 4.4/4.5. Import completes correctly. |
| 4.4–4.5 | Progress bar shows >100% during headless import | FIXED in 4.6 | Cosmetic only — not a real error. |
| 4.5.0 | AnimationTree regression — animations baked into scene instead of library | FIXED in 4.5.1 | Upgrade to 4.5.1 or set import mode to "Animation Library" |
| 4.3–4.4 | GLB not reimporting after source file change | Known bug (open) | Delete `.godot/imported/<filename>-*.scn` cache file and reimport |
| Any | `gltf/naming_version` mismatch between .import and actual Godot version | Ongoing | Always set explicitly in .import (version 2 for 4.5+) |
| Any | Backface culling disabled from Blender export | Ongoing | Use EditorScenePostImport hook (see §7) or enable in material |

---

## §9. CI validation pipeline (PowerShell)

```powershell
# forge_godot_ci.ps1 — 4-step Godot validation pipeline
param(
    [string]$ProjectDir = "C:\MyGodotProject",
    [string]$GodotExe   = "C:\Godot\Godot_v4.4.1-stable_win64.exe",
    [string]$SourceDir  = "C:\forge-build\out",
    [string]$AssetsDir  = "assets\models"
)

$assetPath = Join-Path $ProjectDir $AssetsDir

# STEP 1: Check all GLBs have .import sidecars
Write-Host "[CI Step 1] Checking .import sidecars..."
$glbs = Get-ChildItem $assetPath -Filter "*.glb" -ErrorAction SilentlyContinue
foreach ($glb in $glbs) {
    $importFile = "$($glb.FullName).import"
    if (-not (Test-Path $importFile)) {
        Write-Error "MISSING .import: $($glb.Name)"
        exit 1
    }
}
Write-Host "  OK — $($glbs.Count) sidecars present"

# STEP 2: Headless import (re-import to verify no errors)
Write-Host "[CI Step 2] Headless import..."
& $GodotExe --headless --import --path $ProjectDir
if ($LASTEXITCODE -ne 0) { Write-Error "Headless import FAILED"; exit 1 }
Write-Host "  OK"

# STEP 3: Run a render-validation GDScript headless (optional)
# Requires a pre-built render_validate.pck in the project
$valScript = Join-Path $ProjectDir "tools\render_validate.gd"
if (Test-Path $valScript) {
    Write-Host "[CI Step 3] Render validation..."
    & $GodotExe --headless --path $ProjectDir --script $valScript
    if ($LASTEXITCODE -ne 0) { Write-Error "Render validation FAILED"; exit 1 }
    Write-Host "  OK"
} else {
    Write-Host "[CI Step 3] Skipped (no render_validate.gd found)"
}

# STEP 4: Check no render outputs are all-black
$pngs = Get-ChildItem (Join-Path $ProjectDir ".forge-renders") -Filter "*.png" -ErrorAction SilentlyContinue
foreach ($png in $pngs) {
    $size = $png.Length
    if ($size -lt 2000) {
        Write-Warning "Suspiciously small PNG ($size bytes): $($png.Name) — possible all-black frame"
    }
}

Write-Host "[CI] All steps passed."
```

---

## §10. Critical gotchas

| Gotcha | Symptom | Fix |
|---|---|---|
| **`--import` vs `--editor --quit` race** | Import exits before finishing | Use `--import` (4.3+). Before 4.3 add sleep after quit. |
| **"Parameter t is null"** | ERROR in headless output | Non-fatal in 4.4.x, fixed in 4.6. Do not block CI on it. |
| **DirectX normal maps** | Surfaces lit incorrectly / inverted normals | Flip green channel: `magick convert normal_dx.png -channel G -negate normal_gl.png` |
| **Backface culling disabled** | Transparent/double-sided from Blender | Use EditorScenePostImport to set `cull_mode=CULL_BACK` |
| **ORM sRGB** | Metallic/roughness physically wrong | Set `flags/srgb=false` in texture .import sidecar |
| **GLB not reimporting** | Stale asset after source change | Delete `.godot/imported/filename-*.scn` cache entry |
| **naming_version mismatch** | Animations don't find bone targets | Set `gltf/naming_version=2` consistently in all .import files for 4.5+ |
| **AnimationTree regression (4.5.0)** | Animations baked into scene | Upgrade to 4.5.1 or import in "Animation Library" mode |
| **Windows paths in GDScript** | `load("C:\\path")` fails | Use `res://` paths or `ProjectSettings.globalize_path()` for absolute |
| **MeshLibrary headless** | Cannot create MeshLibrary programmatically in headless mode | No headless API yet (proposal #5375 open); must use editor menu or `--editor` mode |
