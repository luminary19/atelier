# forge-data — Format Interchange Matrix Reference

Full format-capability table, conversion recipes, FBX unit-scale fix, axis-mapping rules, and
Blender↔glTF coordinate transform details. Decision authority: **forge-export**.

## Contents
- §1. Format capability matrix (full)
- §2. Hub-format doctrine
- §3. Tool selection per conversion task
- §4. FBX unit-scale fix
- §5. Axis-mapping rules
- §6. Conversion recipes (copy-paste)

---

## §1. Format capability matrix

| Feature | glTF 2.0 / GLB | FBX | OBJ+MTL | STL | 3MF | USD | Alembic | STEP |
|---------|---------------|-----|---------|-----|-----|-----|---------|------|
| Geometry | Tri only | Tri/Quad/N-gon | Tri/Quad/N-gon | Tri only | Tri only | Tri/Quad/Sub-d | Tri/Poly | B-Rep (exact) |
| Normals | Yes | Yes | Yes | Face only | No | Yes | Yes | Analytic |
| UVs multi-channel | Yes | Yes | 1 ch typically | No | No | Yes | Yes | No |
| Vertex colors | Yes | Yes (1 ch) | Not standard | No | Yes | Yes | Yes | No |
| Materials | PBR metal-rough | Phong/Lambert + partial PBR | Phong (MTL) | None | Color only | UsdPreviewSurface | None | Color (optional) |
| PBR metallic-rough | Native | Via extension (FBX7+) | No | No | No | Yes | No | No |
| Embedded textures | Yes (GLB) | Yes | No (external) | No | Yes (ZIP) | External refs | No | No |
| Skeleton / Skin | Yes | Yes | No | No | No | Yes | No | No |
| Animation (keyframe) | Yes (TRS) | Yes (curves) | No | No | No | Yes | Yes (baked) | No |
| Morph targets | Yes | Yes | No | No | No | Yes | Yes | No |
| Instancing | Yes (node reuse) | Yes | No | No | No | Yes (PointInstancer) | Yes | Yes |
| Units defined | Yes (meters) | Yes (cm default) | No | No | Yes (mm) | Yes (cm default) | Yes (cm) | Yes (mm) |
| Up-axis defined | Yes (+Y) | In metadata | Assumed +Y | Assumed +Z | Assumed +Z | Yes (+Y) | Yes (+Y) | +Z (ISO) |
| Lossy | No | No | No | No | No | No | No | No (exact) |
| Assimp import | Full | Full | Full | Full | Good | Experimental | No | Basic |
| Assimp export | Full (glb2/gltf2) | Experimental | Yes (obj) | Yes (stlb) | Experimental | No | No | Basic |
| Best use | Runtime/web/AR | DCC-to-engine | Static mesh / print | 3D printing | Colored print | Pipeline hub / VFX | Sim cache / baked anim | CAD visualization |

---

## §2. Hub-format doctrine

- **glTF 2.0 / GLB** — runtime hub: GPU-ready triangles, PBR metal-rough, embedded textures,
  skeleton + morph, compact. "The JPEG of 3D." Use for web, AR, Godot, real-time delivery.
- **USD / USDA / USDC** — pipeline hub: non-destructive layers, overrides, instancing at scale,
  variant sets. "The PSD of 3D." Use for multi-DCC pipelines where assets are round-tripped.
- **Alembic (.abc)** — baked simulation / animation cache hub: time-sampled geometry (cloth, fluid,
  crowd). No materials; pure geometry + transform stream. Use to transfer sims between DCCs.
- **STEP (.stp/.step)** — CAD ingress only. Exact B-Rep from mechanical CAD tools. Must be
  tessellated before any real-time use; not an interchange format between render tools.

---

## §3. Tool selection per conversion task

| Conversion task | Recommended tool | Notes |
|----------------|-----------------|-------|
| FBX → GLB (material quality) | **Blender** | Best material round-trip fidelity |
| FBX → GLB (batch / speed) | **assimp CLI** | No DCC startup overhead; use `-tri -jiv -gsn` |
| OBJ / STL / PLY → GLB | assimp CLI | Fast batch; add `-gsn -cts` for normals/tangents |
| Alembic → any | Blender | assimp cannot handle Alembic |
| USD → any | Blender | assimp USD import is experimental / disabled by default |
| STEP → GLB | FreeCAD CLI + assimp | FreeCAD tessellates via OCC; then assimp wraps to GLB |
| glTF → FBX (for Unity/Unreal) | Blender | Better round-trip than assimp FBX exporter |
| Programmatic batch pipeline | assimpcy or assimp CLI | No 2–3 s Blender startup per file |

---

## §4. FBX unit-scale fix

**The most common production failure.** FBX internal unit = centimeters. A 2-meter character
arrives as 200 assimp units tall (100× too large in UE5 cm space).

**Detect:** `assimp info model.fbx` — bounding box `[0, 200]` for a 2 m human = red flag.

**Fix via Blender (recommended):**
```python
bpy.ops.import_scene.fbx(apply_unit_scale=True)  # normalizes cm to meters
# Then export to GLB or FBX with correct scale settings
```

**Fix via C++ assimp API:**
```cpp
importer.SetPropertyFloat(AI_CONFIG_GLOBAL_SCALE_FACTOR_KEY, 1.0f);
// OR-in aiProcess_GlobalScale to import flags
```

**Fix via assimp CLI (no direct flag):** Use Blender as the intermediary.

**UE5 FBX export fix from Blender:**
```python
bpy.ops.export_scene.fbx(
    apply_scale_options='FBX_SCALE_ALL',  # scales Blender meters → UE5 cm
    apply_unit_scale=True,
    axis_forward='-Y', axis_up='Z',
)
```

---

## §5. Axis-mapping rules

**Coordinate systems:**
- Blender: Z-up, right-handed (+X right, +Y forward, +Z up)
- glTF / USD: Y-up, right-handed (+X right, +Z back, +Y up)
- UE5: Z-up, left-handed (+X forward, +Y right, +Z up)
- Unity: Y-up, left-handed
- FBX: Y-up by convention (stored in metadata, varies by DCC)

**Blender → glTF axis mapping:**
```
Blender X  →  glTF X
Blender Y  →  glTF -Z   (Blender forward = glTF backward)
Blender Z  →  glTF Y    (Blender up = glTF up)
```
Set `export_yup=True` in `bpy.ops.export_scene.gltf()` — the exporter handles this transform.

**Assimp UV-flip rule:**
- OpenGL / WebGL / Vulkan downstream → add `-fuv` (flip V to lower-left origin)
- DirectX downstream → do NOT add `-fuv`
- glTF spec uses upper-left origin — leave V as-is for glTF output

---

## §6. Conversion recipes (copy-paste)

**assimp CLI: FBX → GLB (full quality flags):**
```powershell
assimp export "C:/in/char.fbx" "C:/out/char.glb" -fglb2 -tri -jiv -gsn -cts -fuv -icl
```

**assimp CLI: validate a converted GLB:**
```powershell
assimp info "C:/out/char.glb" --vds
```

**gltf-transform: full web pipeline:**
```powershell
gltf-transform optimize input.glb optimized.glb --compress draco --texture-compress webp
gltf-transform validate optimized.glb
gltf-transform inspect optimized.glb
```

**gltf-transform: fine-grained (static asset):**
```powershell
gltf-transform prune input.glb step1.glb
gltf-transform dedup step1.glb step2.glb
gltf-transform weld step2.glb step3.glb
gltf-transform join step3.glb step4.glb
gltf-transform draco step4.glb step5.glb --method edgebreaker
gltf-transform resize step5.glb step6.glb --width 1024 --height 1024
gltf-transform uastc step6.glb step7.glb --slots "{normalTexture,occlusionTexture,metallicRoughnessTexture}" --level 4 --rdo --zstd 18
gltf-transform etc1s step7.glb output.glb --quality 255
```

**Blender headless: FBX → GLB (PowerShell):**
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.4\blender.exe"
$py = @"
import bpy, os
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete()
bpy.ops.import_scene.fbx(filepath='INPUT_PATH', apply_unit_scale=True, axis_forward='-Z', axis_up='Y')
os.makedirs('OUTPUT_DIR', exist_ok=True)
bpy.ops.export_scene.gltf(filepath='OUTPUT_PATH', export_format='GLB', export_yup=True, export_apply=False)
"@
& $blender --background --python-exit-code 1 --python-expr $py
```

**STEP → GLB via FreeCAD:**
```powershell
$freecad = "C:\Program Files\FreeCAD 0.21\bin\FreeCADCmd.exe"
& $freecad step_to_stl.py input.step temp.stl
assimp export temp.stl output.glb -fglb2 -gsn
Remove-Item temp.stl
```
