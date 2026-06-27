# forge-data — Tool Invocations Reference

Headless CLI patterns, PowerShell wrappers, and Windows-specific gotchas for every tool
Forge skills invoke. All snippets are copy-paste-ready for native Windows 11.

## Contents
- §1. Blender headless fundamentals
- §2. Blender bpy export snippets
- §3. OpenSCAD / CadQuery headless
- §4. Assimp CLI
- §5. gltf-transform & gltfpack
- §6. Batch PowerShell loops
- §7. Windows-specific gotchas

---

## §1. Blender headless fundamentals

**Non-negotiable Windows truths (apply everywhere):**
- Use `CYCLES` engine, NOT EEVEE Next — EEVEE Next is unsupported headless on Windows.
- The `--` separator after the script path is MANDATORY; args before `--` go to Blender,
  args after go to the Python script via `sys.argv`.
- Call `--python-exit-code 1` so Python exceptions fail the Blender process.
- Use absolute forward-slash paths in `bpy.context.scene.render.filepath` — never `//`.
- Call `python`, not `python3`.

```powershell
# Minimal headless render (1 frame, Cycles, save PNG)
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
& $blender -b "C:/project/scene.blend" `
    --python-exit-code 1 `
    -P "C:/project/scripts/render.py" `
    -- --out "C:/project/out/frame_001.png" --samples 64
# The -- separates Blender args (left) from script args (right).
```

```powershell
# Open a .blend, run a script, render frame 1
& $blender -b "C:/project/asset.blend" `
    --python-exit-code 1 `
    -P "C:/project/scripts/setup.py" `
    -- --profile console `
    -f 1
```

```powershell
# Headless Python expression (no script file; quick one-liner)
$py = 'import bpy; bpy.ops.export_scene.gltf(filepath="C:/out/hero.glb", export_format="GLB")'
& $blender -b "C:/project/scene.blend" --python-exit-code 1 --python-expr $py
# WARNING: --python-expr embeds the string; avoid single quotes inside it.
```

**Blender render engine selection (headless safe):**
```python
import bpy
scene = bpy.context.scene
scene.render.engine = 'CYCLES'           # REQUIRED for Windows headless
scene.cycles.device = 'CPU'              # CPU fallback — always works
scene.cycles.samples = 64               # QA pass; use 256+ for final
scene.render.resolution_x = 512
scene.render.resolution_y = 512
scene.render.image_settings.file_format = 'PNG'
scene.render.filepath = 'C:/project/out/render_'  # absolute forward-slash
bpy.ops.render.render(write_still=True)
```

**Read render args from sys.argv (the -- pattern):**
```python
import bpy, sys, argparse

# Grab everything after '--'
argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
parser = argparse.ArgumentParser()
parser.add_argument("--out", required=True)
parser.add_argument("--samples", type=int, default=64)
args = parser.parse_args(argv)

bpy.context.scene.cycles.samples = args.samples
bpy.context.scene.render.filepath = args.out
bpy.ops.render.render(write_still=True)
```

---

## §2. Blender bpy export snippets

**GLB export (glTF 2.0 binary) — recommended for web / Godot:**
```python
import bpy, os
os.makedirs("C:/project/out", exist_ok=True)

bpy.ops.export_scene.gltf(
    filepath="C:/project/out/SM_Hero_01.glb",
    export_format='GLB',
    export_yup=True,           # glTF standard: Y-up
    export_apply=False,        # DO NOT bake Array modifiers (file explosion risk)
    export_animations=True,
    export_skins=True,
    export_morph=True,
    export_morph_normal=True,
    export_morph_animation=True,
    export_lights=False,
    export_cameras=False,
    export_materials='EXPORT',
    export_image_format='AUTO',
    export_draco_mesh_compression_enable=True,
    export_draco_mesh_compression_level=6,
)
```

**FBX export for UE5 (apply scale to cm):**
```python
bpy.ops.export_scene.fbx(
    filepath="C:/project/out/SM_Barrel_01.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_ALL',  # scales Blender m → UE5 cm
    apply_unit_scale=True,
    axis_forward='-Y',
    axis_up='Z',
    mesh_smooth_type='EDGE',
    use_mesh_modifiers=True,
    bake_anim=False,
    add_leaf_bones=False,
    use_armature_deform_only=True,
)
```

**FBX export for Unity (1 m = 1 m; apply transforms):**
```python
bpy.ops.object.transforms_apply(location=False, rotation=True, scale=True)
bpy.ops.export_scene.fbx(
    filepath="C:/project/out/SM_Chair_01.fbx",
    use_selection=True,
    apply_scale_options='FBX_SCALE_NONE',  # Unity is 1 m = 1 unit
    apply_unit_scale=True,
    axis_forward='-Z',
    axis_up='Y',
    mesh_smooth_type='EDGE',
    use_mesh_modifiers=True,
    bake_anim=True,
)
```

**USD export (Blender 4.2+, pipeline hub):**
```python
bpy.ops.wm.usd_export(
    filepath="C:/project/out/scene.usdc",
    export_animation=True,
    export_uvmaps=True,
    export_normals=True,
    export_materials=True,
    export_meshes=True,
    export_armatures=True,
    export_shapekeys=True,
    apply_modifiers=True,
    generate_preview_surface=True,
    export_pbr_extensions=True,
)
```

---

## §3. OpenSCAD / CadQuery headless

**OpenSCAD: call `openscad.com`, NOT `openscad.exe` (Windows headless):**
```powershell
# Render a .scad file to STL (headless, no window)
openscad.com -o "C:/out/part.stl" "C:/src/part.scad"

# Render with parameter override
openscad.com -o "C:/out/part.stl" -D "wall_thickness=3" "C:/src/part.scad"

# Render to PNG for visual QA
openscad.com --render --colorscheme=Tomorrow `
    --imgsize=800,600 `
    -o "C:/out/part_preview.png" `
    "C:/src/part.scad"

# Export to SVG (2D shapes)
openscad.com -o "C:/out/profile.svg" "C:/src/profile.scad"
```

**CadQuery / build123d headless (Python):**
```python
# cadquery_export.py — run with: python cadquery_export.py
import cadquery as cq

box = cq.Workplane("XY").box(10, 10, 5).fillet(1)

# Export to STEP (CAD-grade, round-trippable)
cq.exporters.export(box, "C:/out/box.step")

# Export to STL (for 3D print / Blender import)
cq.exporters.export(box, "C:/out/box.stl", tolerance=0.01, angularTolerance=0.1)

# Export to SVG (flat profile, 2D)
cq.exporters.export(box, "C:/out/box.svg")
```

**FreeCAD CLI (STEP → STL, then assimp → GLB):**
```powershell
$freecad = "C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe"
& $freecad "C:/scripts/step_to_stl.py" input.step output.stl
# step_to_stl.py uses FreeCAD's OCC kernel for CAD-accurate tessellation
```

---

## §4. Assimp CLI

```powershell
$assimp = "C:\Tools\assimp\bin\assimp.exe"

# Inspect: mesh count, materials, bounding box, node tree
& $assimp info "C:/assets/char.fbx"

# List all import-capable extensions
& $assimp listext

# List all export format IDs
& $assimp listexport
# Key IDs: glb2 (binary glTF 2.0), gltf2 (JSON glTF), fbx, fbxa, obj, stl, stlb, collada, 3mf

# FBX → GLB (most common conversion)
& $assimp export "C:/assets/char.fbx" "C:/out/char.glb" -fglb2 -tri -jiv -gsn -cts -fuv -icl

# OBJ → GLB
& $assimp export "C:/assets/prop.obj" "C:/out/prop.glb" -fglb2 -tri -jiv -gsn

# Dump to XML for scene-graph debugging
& $assimp dump "C:/assets/model.fbx" "C:/out/model.assxml"
```

**Assimp post-processing flags:**

| Flag | Effect |
|------|--------|
| `-tri` | Triangulate quads / n-gons (REQUIRED for GLB) |
| `-jiv` | Weld duplicate vertices, build index buffer |
| `-gsn` | Generate smooth normals if absent |
| `-cts` | Compute tangents + bitangents for normal maps |
| `-fuv` | Flip V coordinate (for OpenGL / WebGL convention) |
| `-icl` | Reorder for GPU cache (Tipsify) |
| `-ptv` | Pre-transform vertices (bakes hierarchy — breaks rig) |
| `-vds` | Full validation (QA only; ~30% slower) |
| `-lh` | Convert to left-handed (DirectX) — OMIT for WebGL |

**Critical FBX unit-scale gotcha — use Blender instead of assimp for scale-correct output:**
The assimp CLI has no `--global-scale` flag. A Maya FBX authored at 1 m arrives as 100 assimp
units (cm). Use `blender -b --python-expr "bpy.ops.import_scene.fbx(apply_unit_scale=True)..."` 
for scale-critical conversions.

---

## §5. gltf-transform & gltfpack

```powershell
# One-shot optimize: prune + dedup + weld + Draco + WebP textures
gltf-transform optimize input.glb output.glb --compress draco --texture-compress webp

# Inspect BEFORE touching anything
gltf-transform inspect input.glb

# Validate against Khronos glTF spec
gltf-transform validate input.glb

# Draco geometry compression (static meshes only)
gltf-transform draco input.glb output.glb --method edgebreaker

# Meshopt (animated meshes, morph targets)
gltf-transform meshopt input.glb output.glb --level medium

# KTX2: UASTC for normal / ORM maps (high precision)
gltf-transform uastc input.glb out.glb `
  --slots "{normalTexture,occlusionTexture,metallicRoughnessTexture}" `
  --level 4 --rdo --rdo-lambda 4 --zstd 18

# KTX2: ETC1S for albedo / color (small file)
gltf-transform etc1s input.glb output.glb --quality 255

# Resize oversized textures
gltf-transform resize input.glb output.glb --width 1024 --height 1024

# Join meshes (reduce draw calls — static only)
gltf-transform join input.glb output.glb

# GPU instancing for repeated meshes
gltf-transform instance input.glb output.glb
```

**gltfpack (native binary — faster for animation, single-step):**
```powershell
$gltfpack = "C:\tools\gltfpack.exe"
# Static mesh, Meshopt compression
& $gltfpack -i input.glb -o output.glb -cc
# With KTX2 texture compression (native binary only)
& $gltfpack -i input.glb -o output.glb -cc -tc
# LOD simplification (50% triangle target)
& $gltfpack -i input.glb -o output.glb -cc -si 0.5
```

**toktx for KTX2 encoding (requires `toktx` on PATH):**
```powershell
# ETC1S (albedo): small file, good for flat/tiled color
toktx --t2 --encode etc1s --clevel 4 --qlevel 255 --genmipmap out.ktx2 in.png
# UASTC (normals, ORM): higher quality, more VRAM
toktx --t2 --encode uastc --uastc_quality 4 --zcmp 22 --genmipmap out.ktx2 in.png
```

---

## §6. Batch PowerShell loops

```powershell
# Batch validate all .blend files in a project
$blender  = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$validate = "C:\project\tools\forge_validate.py"
Get-ChildItem "C:\project\source\" -Recurse -Filter "*.blend" | ForEach-Object {
    Write-Host "Validating: $($_.Name)"
    & $blender -b $_.FullName --python-exit-code 1 -P $validate -- --profile console
    if ($LASTEXITCODE -ne 0) { Write-Error "FAIL: $($_.Name)" }
}

# Batch convert FBX → GLB using assimp
$assimp = "C:\Tools\assimp\bin\assimp.exe"
Get-ChildItem "C:\project\source\" -Recurse -Filter "*.fbx" | ForEach-Object {
    $out = "C:\project\out\$($_.BaseName).glb"
    & $assimp export $_.FullName $out -fglb2 -tri -jiv -gsn -cts -fuv
    Write-Host "[$(if ($LASTEXITCODE -eq 0){"OK"}else{"FAIL"})] $($_.Name) → $out"
}
```

---

## §7. Windows-specific gotchas

| Topic | Symptom | Fix |
|-------|---------|-----|
| EEVEE Next headless | Render fails with GL / display error | Switch to `CYCLES`; set `device = 'CPU'` |
| `--` separator missing | Script args parsed as Blender args; `sys.argv` empty | Always add `-- <args>` after `-P script.py` |
| `openscad.exe` headless | Window flickers and blocks CI | Use `openscad.com` (the console binary) |
| `python3` not found | Command not found | Use `python` everywhere on Windows |
| stdout cp1252 | Non-ASCII output corrupts / crashes | Add UTF-8 stdout wrapper at script top |
| CSV BOM header | First column key mismatch, zero results | Open with `encoding='utf-8-sig'` |
| `//` relative path in Blender | Wrong render output path | Use absolute forward-slash paths always |
| FBX 100× scale | Character 100× too large in-engine | Use Blender with `apply_unit_scale=True` |
| Unapplied transforms | Bounding-box wrong; scale mismatch in-engine | Run `Ctrl+A > Apply All Transforms` before export |
| `export_apply=True` Array | 100-segment road → 56 MB GLB | Set `export_apply=False` unless modifiers must be baked |
| MAX_PATH 260 chars | Export fails silently; Python `FileNotFoundError` | Enable long paths via `LongPathsEnabled` registry key |
| pyassimp CVE-2024-48423 | Path traversal on untrusted files | Use `assimpcy` or assimp CLI subprocess instead |
| glTF Y-up root rotation | Three.js shows -90° root bone | Expected behavior; GLTFLoader handles it automatically |
| Draco breaks animations | T-pose on load | Use Meshopt for all rigged / morph-target assets |
| WebP = no GPU savings | Mobile VRAM still maxed | Use KTX2 (ETC1S / UASTC) for GPU-memory-critical scenes |
| toktx not on PATH | `gltf-transform etc1s` fails | Add `C:\Program Files\KTX-Software\bin` to `$env:PATH` |
| KTX2Loader before renderer | `detectSupport` no-ops silently | Call `detectSupport(renderer)` AFTER `new THREE.WebGLRenderer` |
