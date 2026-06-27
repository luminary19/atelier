# Forge Validate — Render QA Guide
# Contents
- §1. Engine selection rules (Windows headless)
- §2. Render invocation (PowerShell)
- §3. Visual inspection — what to look for in the contact sheet
- §4. Defect catalogue
- §5. Contact sheet assembly

---

## §1. Engine Selection Rules (Windows Headless — Non-Negotiable)

| Use case | Engine | Reason |
|----------|--------|--------|
| All iterative QA renders (matcap, wireframe, flat) | `BLENDER_WORKBENCH` | Headless-safe on Windows, no GPU required, fast (0.3–2s/frame) |
| UV checker pass | `CYCLES` (CPU, 16 samples) | Workbench ignores shader nodes; Cycles honours UV mapping |
| Normal pass (world-space) | `CYCLES` (CPU, 1 sample) | Compositor normal pass; deterministic |
| Beauty / presentation | `CYCLES` (CPU or GPU) | Physically accurate; activate GPU via `prefs.refresh_devices()` |
| **NEVER use for headless QA** | `BLENDER_EEVEE` / `BLENDER_EEVEE_NEXT` | Requires OpenGL context on Windows — crashes in background mode |

**EEVEE headless error:** `RuntimeError: EEVEE requires an OpenGL context`. This is a hard
platform limitation on Windows (Blender 4.4 manual §Limitations). Never set
`scene.render.engine = "BLENDER_EEVEE"` or `"BLENDER_EEVEE_NEXT"` in Forge QA scripts.

---

## §1.5. Determinism (MANDATORY — FORGE_PLAN §A: seeded randomness)

The QA loop is **render → Read → critique → re-render**. That loop only works if two renders
of an *unchanged* asset are byte-comparable — otherwise the model cannot tell a real change
from sampler noise. **The rule: same input asset + same script ⇒ byte-comparable PNG. If two
renders of an unchanged mesh differ, the seed is unpinned.**

Cycles defaults to a per-frame *animated* seed, so every QA render of the same mesh produces
different noise. Pin it in every Cycles-based QA pass:

```python
# Inside any Cycles QA render script (Workbench needs none of this — it does no sampling)
scene = bpy.context.scene
scene.cycles.seed = 0
scene.cycles.use_animated_seed = False          # do NOT advance the seed per frame
scene.render.use_persistent_data = True         # reuse BVH/data across turntable frames
```

**Fixed sample counts per pass-type** (lower = faster + still deterministic once seeded):

| Pass | Engine | Samples | Why |
|------|--------|---------|-----|
| QA turntable | Workbench | n/a | No sampling — inherently deterministic |
| UV-checker | Cycles (CPU) | 16 | Flat checker; low noise floor |
| Normal pass | Cycles (CPU) | 1 | Compositor normal AOV — 1 sample is exact |
| Beauty / presentation | Cycles | 128–256 | Pin seed=0; same input ⇒ same PNG |

Also fix the **camera + lens** (same focal length, same orbit start angle, same elevation)
so silhouettes are comparable frame-to-frame. Mirror these settings in forge-render's actual
scripts — this guide is the gate's reference, forge-render owns the executable render path.

---

## §2. Render Invocation (PowerShell)

**Find Blender executable:**
```powershell
function Get-BlenderExe {
    $regPath = 'HKLM:\SOFTWARE\BlenderFoundation'
    if (Test-Path $regPath) {
        $installDir = (Get-ItemProperty $regPath -ErrorAction SilentlyContinue).Install_Dir
        $exe = Join-Path $installDir 'blender.exe'
        if (Test-Path $exe) { return $exe }
    }
    $candidates = Get-ChildItem 'C:\Program Files\Blender Foundation' -Filter 'blender.exe' -Recurse -ErrorAction SilentlyContinue
    if ($candidates) { return $candidates[0].FullName }
    # NOTE: Windows PowerShell 5.1 (this machine) has NO null-conditional `?.` or
    # null-coalescing `??` — both are PS7-only and HARD parser errors here, which would
    # kill the whole script block (and every $BLENDER-dependent render below). Use explicit
    # if-checks instead.
    $cmd = Get-Command blender.exe -ErrorAction SilentlyContinue
    if ($cmd) { return $cmd.Source }
    throw "Blender not found. Set BLENDER_EXE env var or install from blender.org"
}
if ($env:BLENDER_EXE) { $BLENDER = $env:BLENDER_EXE } else { $BLENDER = Get-BlenderExe }
```

**Turntable render (12 angles, Workbench, 512px):**
```powershell
$SCRIPTS = "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts"
& $BLENDER -b --python "$SCRIPTS/forge_turntable.py" `
    -- "C:/path/to/model.glb" "C:/qa/turntable" --n-angles 12 --size 512
if ($LASTEXITCODE -ne 0) { throw "Turntable render failed (exit $LASTEXITCODE)" }
```

**6-view ortho render:**
```powershell
& $BLENDER -b --python "$SCRIPTS/forge_6view.py" `
    -- "C:/path/to/model.glb" "C:/qa/6view" --size 512
```

**Diagnostic variants (matcap, wireframe, flat-normal, UV-checker):**
```powershell
& $BLENDER -b --python "$SCRIPTS/forge_diagnostic_variants.py" `
    -- "C:/path/to/model.glb" "C:/qa/diagnostic" --size 512 --angles 30 150
```

**Key Blender headless gotchas:**
- `--` separator is MANDATORY. Everything after `--` goes to `sys.argv` in the script.
  Missing `--` → Blender tries to interpret script args as blend filenames (silent failure).
- Always use absolute, forward-slash paths in `scene.render.filepath`.
  Relative paths with `//` resolve relative to a blend file path — which does not exist
  when using `wm.read_factory_settings(use_empty=True)`.
- `bpy.ops.render.render(write_still=True)` — the `write_still=True` is REQUIRED.
  Without it, Blender renders but does not save the PNG.
- Call `bpy.context.view_layer.update()` after each camera transform change before render,
  or all frames render from the same angle.
- Output directory must exist before render: `pathlib.Path(out_dir).mkdir(parents=True, exist_ok=True)`

---

## §3. Visual Inspection — What to Look For

After the contact sheet is assembled, call `Read(contact_sheet_path)` and inspect:

**Turntable frames:**
- Silhouette consistency across all N angles — no sudden pop or crease
- Scale appears correct vs. FORGE.md target dimensions
- No floating geometry (disconnected pieces orbiting at wrong position)
- Smooth, continuous outline — jagged ngon edges visible as faceting

**6-view ortho:**
- Proportions match brief from all 6 axes
- No unexpected asymmetry (left/right views should mirror for symmetric assets)
- Scale markers visible if added; dimensions look correct

**Matcap frame:**
- Smooth gradient across surfaces — **black patches = inverted normals** (hard stop)
- No sharp seams where smooth shading should flow (shading discontinuity)
- No faceting on faces marked smooth (custom normals / smooth shading issue)

**Wireframe frame:**
- Edge density uniform — no dense pole clusters (> 6 edges at a vertex = WARN)
- No stray floating edges or isolated vertices (appear as dots)
- N-gons visible as irregular polygons — flag for subdivision/export compatibility
- T-junctions or dangling edges = non-manifold geometry

**Normal (RGB) frame:**
- Surface shows smooth color gradients (consistent normal directions)
- Abrupt color reversals (e.g., red adjacent to cyan) = normal discontinuity

**UV checker frame:**
- Checker squares uniform in screen size = even texel density
- Elongated/distorted squares > 2:1 = UV stretch — re-unwrap the island
- Very small squares = over-scaled UV (wasted texture space)
- Checker seams at UV island boundaries = normal; seams at unexpected locations = UV placement error
- Mirrored checker on a face = flipped UV winding — fix with `bmesh.ops.reverse_uvs`

---

## §4. Defect Catalogue

| Defect | Visual signal | Programmatic signal | Fix action |
|--------|--------------|---------------------|------------|
| Inverted normals | Black patches on matcap | `flipped_faces > 0` | `bmesh.ops.recalc_face_normals` or `repair.fix_normals` |
| UV flip | Checker mirrored on face | `flipped_uv_faces > 0` | `bmesh.ops.reverse_uvs` |
| UV stretch (> 2:1) | Elongated checker squares | (visual only) | Re-unwrap affected island; `Skill("forge-uv")` |
| Scale error | Silhouette doesn't match brief | bounds mismatch vs FORGE.md | `bpy.ops.transform.resize` + apply |
| Non-manifold edge | Black line in wireframe | `non_manifold_edges > 0` | Fill hole or merge vertices |
| Floating geometry | Isolated element in turntable | BVHTree self-overlap | Delete or re-attach |
| Self-intersection | Overlapping faces visible | `self_intersect_faces > 0` | Boolean union or manual fix |
| Degenerate face | Tiny dark triangle in matcap | `degenerate_faces > 0` | bmesh dissolve / merge by distance |
| N-gon on SDS surface | Irregular polygon in wireframe | (visual / bmesh count) | Triangulate / re-loop; `Skill("forge-topology")` |
| Shading seam | Hard crease in matcap where smooth expected | (visual) | Mark/clear smooth, check custom normals |
| Wrong coordinate system | Asset rotated 90° in viewer | `export_yup` missing | Re-export Blender with `export_yup=True` |
| sRGB normal map | Washed-out blue normal map | `IMAGE_COLORSPACE_MISMATCH` validator warning | Set to "Non-Color" in Blender image node |

---

## §5. Contact Sheet Assembly

The contact sheet is assembled by `forge-render`'s `contact_sheet.py` (system Python + Pillow).
`forge-validate` calls the assembler after all render passes complete, then calls `Read` on
the resulting PNG.

**Assembly pattern (PowerShell):**
```powershell
$staging = Join-Path $OutputDir "_staging"
New-Item -ItemType Directory -Force $staging | Out-Null
Get-ChildItem -Path $turntableDir, $sixviewDir, $diagnosticDir -Filter "*.png" |
    Copy-Item -Destination $staging

$SCRIPTS = "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts"
python "$SCRIPTS/contact_sheet.py" $staging (Join-Path $OutputDir "qa_contact_sheet.png") --cols 6
```

**Contact sheet layout (canonical order):**
1. Row 1+: turntable frames (12 angles at 512px)
2. Next row: 6-view ortho (front, back, right, left, top, bottom)
3. Last row: diagnostic variants (matcap, wireframe, flat-normal, UV-checker at each of 2 angles)

**Size discipline:**
- Cell size: 512×512 max (larger bloats PNG; model has a practical resolution ceiling for inspection)
- Background: dark grey (30, 30, 30) — maximizes contrast for both dark and light geometry
- Label every cell with variant name and angle
- For > 36 images: split into separate contact sheets (turntable / diagnostics)
- Keep under 10 MB total for `Read` tool performance
