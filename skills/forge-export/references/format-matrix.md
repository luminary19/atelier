# Format Matrix & Interchange Reference
# forge-export | references/format-matrix.md

## Contents
- §1. Format capability matrix (full)
- §2. Hub format doctrine
- §3. Assimp CLI — export format IDs and post-processing flags
- §4. Assimp installation on Windows
- §5. Assimp gotchas and fixes
- §6. Validation with assimp

---

## §1. Format capability matrix

| Feature | glTF 2.0/GLB | FBX | OBJ+MTL | STL | 3MF | USD | Alembic | STEP |
|---|---|---|---|---|---|---|---|---|
| Geometry | Tri only | Tri/Quad/N-gon | Tri/Quad | Tri | Tri | Tri/Quad/Sub-d | Tri/Poly | B-Rep exact |
| Normals | Yes | Yes | Yes | Yes (face) | No | Yes | Yes | Analytic |
| UVs (multi-channel) | Yes | Yes | 1ch typically | No | No | Yes | Yes | No |
| Vertex colors | Yes | Yes (1ch) | Not standard | No | Yes | Yes | Yes | No |
| PBR metallic-rough | Native | Via extension | No | No | No | UsdPreviewSurface | No | No |
| Embedded textures | Yes (GLB) | Yes | No (external) | No | Yes (ZIP) | External refs | No | No |
| Skeleton/Skin | Yes | Yes | No | No | No | Yes | No | No |
| Keyframe animation | Yes (TRS) | Yes (bezier) | No | No | No | Yes | Baked only | No |
| Morph targets | Yes | Yes (blend shapes) | No | No | No | Yes | Yes | No |
| Units defined | Yes (meters) | Yes (cm default) | No | No | Yes (mm) | Yes (cm default) | Yes (cm) | Yes (mm) |
| Up-axis defined | Yes (+Y) | Yes (metadata) | Assumed +Y | Assumed +Z | Assumed +Z | Yes (+Y) | Yes (+Y) | +Z (ISO) |
| Assimp import | Full | Full | Full | Full | Good | Experimental | No (use Blender) | Basic |
| Assimp export | Full (glb2/gltf2) | Experimental | Yes (obj) | Yes (stl/stlb) | Experimental | No | No | Basic |
| Best use | Runtime/web delivery | DCC-to-engine pipeline | Static mesh, print | 3D printing | Colored print | Pipeline hub | Sim/baked anim | CAD viz |

**Key rule:** Use the **right hub per domain**:
- **GLB** — runtime hub (GPU-ready, PBR, embedded textures, compact). "JPEG of 3D."
- **USDC** — pipeline hub (layers, variants, non-destructive overrides). "PSD of 3D."
- **Alembic** — sim cache hub (time-sampled geometry, no materials).
- **STEP** — CAD ingress only; must be tessellated before any real-time use.

---

## §2. Hub format doctrine

**Use GLB when:**
- Delivering to Three.js / R3F / Babylon.js / CesiumJS (→ then forge-optimize for web)
- Delivering to Godot 4 (native headless import)
- Delivering to Unity with glTFast
- Delivering to Unreal via Interchange
- Any single-file delivery that must embed textures

**Use USDC/USDA when:**
- Authoring multi-asset pipeline (geometry + materials + lighting in separate layers)
- Delivering USDZ for iOS AR / Apple Quick Look
- Connecting Blender → Houdini → downstream renderer round-trip
- Layer-based non-destructive override workflow

**Use FBX when:**
- Target explicitly requires FBX (legacy Unity AssetPostprocessor, Unreal legacy importer)
- Source app only exports FBX well (3ds Max complex scenes, Maya skinned meshes with complex rigging)
- Note: assimp FBX *export* is experimental — use Blender's `bpy.ops.export_scene.fbx()` for FBX output

**Use Alembic when:**
- Exporting baked simulation (cloth, fluid, particle crowds)
- Note: Alembic has NO materials — always a two-pass workflow (abc cache + GLB for materials)

**Use STEP when:**
- Ingesting mechanical CAD geometry
- Always tessellate via FreeCAD CLI or Blender+STEPper NEXT addon before any real-time pipeline

---

## §3. Assimp CLI — format IDs and flags

### Format IDs (use with `-f` flag)

```powershell
# List all supported export formats
assimp listexport

# Common IDs:
# glb2      binary glTF 2.0  ← preferred for runtime
# gltf2     JSON glTF 2.0 + .bin sidecar
# fbx       FBX binary  ← EXPERIMENTAL in assimp export; prefer Blender
# fbxa      FBX ASCII   ← EXPERIMENTAL
# obj       OBJ + MTL
# objnomtl  OBJ without MTL
# stl       STL ASCII
# stlb      STL binary
# 3mf       3MF (colored printing)
# collada   COLLADA (.dae)
# ply       PLY ASCII
# plyb      PLY binary
# x3d       X3D
# step      STEP (basic, geometry only)
```

### Convert FBX → GLB (most common Forge conversion)

```powershell
# Basic: triangulate + weld verts + smooth normals + tangents + flip UV + cache
assimp export "C:\assets\character.fbx" "C:\out\character.glb" `
    -fglb2 -tri -jiv -gsn -cts -fuv -icl

# Inspect a model (print mesh count, bounding box, node tree)
assimp info "C:\assets\robot.fbx"

# Inspect without post-processing (raw data for debugging)
assimp info "C:\assets\robot.fbx" -r

# Dump scene to XML for debugging
assimp dump "C:\assets\model.fbx" "C:\out\model-dump.assxml"

# Extract all embedded textures
assimp extract "C:\assets\model.fbx" "C:\out\tex_" -f bmp

# Regression compare two dumps
assimp cmpdump "C:\out\new-dump.assxml" "C:\reference\ref-dump.assxml"
```

### Post-processing flags table

| Flag | Long form | Effect | Mandatory for GLB? |
|---|---|---|---|
| `-tri` | `--triangulate` | Convert quads/n-gons to triangles | YES |
| `-jiv` | `--join-identical-vertices` | Weld verts, build index buffer | YES |
| `-gsn` | `--gen-smooth-normals` | Generate smooth normals if absent | Recommended |
| `-gn` | `--gen-normals` | Generate flat (face) normals | Only if -gsn not used |
| `-cts` | `--calc-tangent-space` | Compute tangents+bitangents for normal maps | Recommended |
| `-fuv` | `--flip-uv` | Flip V coordinate (upper-left ↔ lower-left) | For glTF output: NO (glTF is upper-left) |
| `-fwo` | `--flip-winding-order` | Flip CCW ↔ CW winding | Only for specific renderers |
| `-lh` | `--convert-to-lh` | Convert to left-handed space | Only for DirectX targets (NOT WebGL/Vulkan) |
| `-ptv` | `--pretransform-vertices` | Bake transforms, collapse hierarchy | Lose rig hierarchy |
| `-lbw` | `--limit-bone-weights` | Max 4 bone influences per vertex | Recommended for game rigs |
| `-icl` | `--improve-cache-locality` | Reorder for GPU cache (Tipsify) | Recommended |
| `-rrm` | `--remove-redundant-materials` | Deduplicate materials | Recommended |
| `-vds` | `--validate-data-structure` | Full validation (slow) | QA only |
| `-fixn` | `--fix-normals` | Heuristic to detect/fix inverted normals | When normals are wrong |
| `-guv` | `--gen-uvcoords` | Replace abstract UV mappings with UV channels | When UVs missing |

**UV flip note:** `glTF` spec uses **upper-left** UV origin. Do NOT add `-fuv` when exporting to `glb2` format. Only add `-fuv` if source is OpenGL-convention (lower-left) AND target renderer is OpenGL-convention.

---

## §4. Assimp installation on Windows

```powershell
# Option A: Pre-built release binary (fastest — includes CLI tool)
# Download: https://github.com/assimp/assimp/releases/tag/v6.0.5
# File: windows-x64-v6.0.5.zip (~17 MB)
# Extract to C:\Tools\assimp\
$env:PATH += ";C:\Tools\assimp\bin"
assimp version   # verify — should print: assimp 6.0.5

# If assimp.exe is missing from the zip (DLL-only builds exist):
# Build from source with CLI tools enabled:
git clone https://github.com/assimp/assimp
cd assimp
cmake -G "Visual Studio 17 2022" -A x64 `
      -DASSIMP_BUILD_ASSIMP_TOOLS=ON `
      -DASSIMP_BUILD_TESTS=OFF `
      -DASSIMP_BUILD_DRACO=ON `
      -S . -B build
cmake --build build --config Release
# Output: build\bin\Release\assimp.exe

# Option B: vcpkg (library only — does NOT install CLI by default)
C:\vcpkg\vcpkg install assimp
```

**IMPORTANT:** assimp USD import is disabled by default (`ASSIMP_BUILD_USD_IMPORTER=OFF`).
For USD workflows, use Blender's `bpy.ops.wm.usd_export()` instead.

---

## §5. Assimp gotchas and fixes

### Gotcha 1 — FBX 100× scale (most common production failure)
**Symptom:** Imported character is 100× too large (200 units tall instead of 2).
**Cause:** FBX internal unit = centimeters; `UnitScaleFactor=1.0` means "I am in centimeters."
**Detect:** `assimp info model.fbx` — bounding box should be ~[0, 2] for a 2m human; if [0, 200] → scale bug.
**Fix (assimp C++ API):**
```cpp
importer.SetPropertyFloat(AI_CONFIG_GLOBAL_SCALE_FACTOR_KEY, 1.0f);
// flags |= aiProcess_GlobalScale;  // reads UnitScaleFactor from FBX metadata
```
**Fix (CLI — no GlobalScale flag):** Use Blender as intermediary: `import_scene.fbx(apply_unit_scale=True)`.
**Fix (Blender import):** `bpy.ops.import_scene.fbx(apply_unit_scale=True)` correctly normalizes.

### Gotcha 2 — assimp FBX exporter is experimental
**Symptom:** FBX exported via `assimp export -ffbx` loses rigs, blend shapes, or has wrong transforms.
**Fix:** Use `bpy.ops.export_scene.fbx()` for FBX output. Blender's FBX exporter is battle-tested.

### Gotcha 3 — OBJ has no animation, skeleton, or PBR
**Symptom:** Animated character from OBJ is static.
**Cause:** OBJ format has no concept of animation, skeleton, or PBR. It is geometry + Phong MTL only.
**Fix:** Obtain FBX or GLB from the original author.

### Gotcha 4 — STL has no materials or colors
**Symptom:** STL import is solid grey.
**Cause:** STL = triangle soup (position + face normal only). No UVs, no colors, no materials.
Binary STL attribute bytes for color are non-standard and not decoded by assimp.
**Fix:** Use 3MF for colored print, or OBJ+MTL.

### Gotcha 5 — Windows path backslashes in assimp CLI
**Symptom:** `assimp export C:\assets\model.fbx` returns "file not found."
**Fix:** Always quote paths: `assimp export "C:\assets\model.fbx" "C:\out\model.glb"`.

### Gotcha 6 — pyassimp CVE-2024-48423
**Package:** pyassimp 5.2.5 on PyPI has a path traversal vulnerability.
**Fix:** Use `assimpcy` (Cython-based, more up-to-date) or call `assimp.exe` CLI via subprocess.
Never feed untrusted user-uploaded files to pyassimp.

---

## §6. Validation with assimp

```python
# validate_with_assimp.py — run assimp info + validate on a converted file
import subprocess, json, pathlib, sys

ASSIMP = r"C:\Tools\assimp\bin\assimp.exe"

def validate_model(path: str) -> dict:
    p = pathlib.Path(path)
    if not p.exists():
        return {"ok": False, "error": "file_not_found"}

    result = subprocess.run(
        [ASSIMP, "info", str(p), "--vds"],  # --vds = validate-data-structure
        capture_output=True, text=True
    )
    out = result.stdout + result.stderr
    metrics = {"file": str(p), "ok": result.returncode == 0}
    for line in out.splitlines():
        l = line.strip()
        if "Meshes:" in l:
            try: metrics["meshes"] = int(l.split(":")[1].strip())
            except: pass
        elif "Faces:" in l:
            try: metrics["faces"] = int(l.split(":")[1].strip())
            except: pass
        elif "Vertices:" in l:
            try: metrics["vertices"] = int(l.split(":")[1].strip())
            except: pass
        elif "Animations:" in l:
            try: metrics["animations"] = int(l.split(":")[1].strip())
            except: pass
        elif "Validation" in l and "failed" in l.lower():
            metrics["validation_error"] = l
    size_mb = p.stat().st_size / (1024 * 1024)
    metrics["size_mb"] = round(size_mb, 2)
    if size_mb > 50:
        metrics["warning"] = f"File is {size_mb:.1f} MB — check for unapplied modifiers or FBX scale issue"
    return metrics

if __name__ == "__main__":
    result = validate_model(sys.argv[1])
    print(json.dumps(result, indent=2))
    sys.exit(0 if result["ok"] else 1)
```

**Mesh integrity assertions after conversion:**
- `meshes > 0` — conversion produced geometry
- `vertices > 0` — not empty
- `size_mb < 50` — for typical props (> 50 MB = FBX scale bug or unapplied Array modifier)
- `faces / vertices ≈ 2:3` — typical triangulated mesh (ratio > 4:1 = n-gon explosion)
- `animations == expected_count` — FBX→OBJ silently drops all animations; assert count matches
- assimp exit code 0 — no validation errors
