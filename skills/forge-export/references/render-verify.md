# Render-Verify — Headless GLB Render-Check (PNG read-back)
# forge-export | references/render-verify.md

The export gate's "eyes." After every export, load the produced file into a **fresh** Blender
scene, render one deterministic Cycles frame, then `Read` the PNG. A blank / all-black PNG means
the export failed silently (no geometry, no material, broken transform) even when `gltf_validator`
reported zero errors — the validator checks the file *structure*, not whether anything is visible.

## Contents
- §1. Windows-headless truths for render-verify
- §2. The render-verify script (copy-paste)
- §3. Invocation (PowerShell)
- §4. Guard + Read loop
- §5. Failure -> detect -> fix table

---

## §1. Windows-headless truths for render-verify

- **EEVEE-Next is UNSUPPORTED headless on Windows** -> force `scene.render.engine='CYCLES'` and
  `scene.cycles.device='CPU'`. A render-verify that leaves the engine on EEVEE-Next yields a
  black or crashed PNG on a headless Windows box. (Same truth the SKILL.md preamble states.)
- **Deterministic settings** so re-verifies reproduce bit-for-bit enough to compare: a single
  fixed frame, a fixed sample count (`samples=32` is plenty for a visibility check), a fixed
  resolution, and `cycles.seed=0`. Do not animate the verify camera.
- `blender -b <file> -P render_verify.py -- <args>` — the `--` separator is mandatory; everything
  after it reaches the script via `sys.argv`.
- Always pass `--python-exit-code 1` so a Python exception fails the Blender process (exit != 0)
  instead of silently returning 0.
- Absolute forward-slash paths in every `filepath=`/import path (never `//`, never backslash).

---

## §2. The render-verify script (copy-paste)

```python
# render_verify.py — load an exported asset into a fresh scene, render 1 Cycles frame, verify non-black.
# Run as: blender -b --python-exit-code 1 -P render_verify.py -- --in C:/out/hero.glb --out C:/out/verify.png
# EEVEE-Next is unsupported headless on Windows -> Cycles CPU. Mirrors forge-sim/export-cache.md §8.
import bpy, sys, os, math, pathlib

def _arg(args, flag, default=None):
    return args[args.index(flag) + 1] if flag in args and args.index(flag) + 1 < len(args) else default

def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)  # fresh, empty scene

def import_asset(path: str):
    ext = pathlib.Path(path).suffix.lower()
    if ext in (".glb", ".gltf"):
        bpy.ops.import_scene.gltf(filepath=path)
    elif ext == ".fbx":
        bpy.ops.import_scene.fbx(filepath=path)
    elif ext in (".usd", ".usdc", ".usda", ".usdz"):
        bpy.ops.wm.usd_import(filepath=path)
    elif ext == ".obj":
        bpy.ops.wm.obj_import(filepath=path)
    elif ext == ".stl":
        bpy.ops.wm.stl_import(filepath=path)
    elif ext == ".abc":
        bpy.ops.wm.alembic_import(filepath=path)
    else:
        raise ValueError(f"render-verify: unsupported extension {ext}")

def frame_all_with_camera():
    # Bounding box over imported meshes -> place a 3/4 camera + key light that frames everything.
    objs = [o for o in bpy.context.scene.objects if o.type == 'MESH']
    if not objs:
        raise RuntimeError("render-verify: no MESH objects after import (export produced no geometry)")
    mins = [min((o.matrix_world @ v.co)[i] for o in objs for v in o.data.vertices) for i in range(3)]
    maxs = [max((o.matrix_world @ v.co)[i] for o in objs for v in o.data.vertices) for i in range(3)]
    center = [(mins[i] + maxs[i]) / 2 for i in range(3)]
    radius = max(maxs[i] - mins[i] for i in range(3)) or 1.0

    cam_data = bpy.data.cameras.new("VerifyCam")
    cam = bpy.data.objects.new("VerifyCam", cam_data)
    bpy.context.collection.objects.link(cam)
    d = radius * 2.2
    cam.location = (center[0] + d, center[1] - d, center[2] + d * 0.8)
    # Aim at center
    dir_vec = [center[i] - cam.location[i] for i in range(3)]
    cam.rotation_euler = (math.atan2(math.hypot(dir_vec[0], dir_vec[1]), dir_vec[2]) ,
                          0.0,
                          math.atan2(dir_vec[1], dir_vec[0]) + math.pi / 2)
    bpy.context.scene.camera = cam

    light_data = bpy.data.lights.new("VerifyKey", type='SUN')
    light_data.energy = 3.0
    light = bpy.data.objects.new("VerifyKey", light_data)
    light.rotation_euler = (math.radians(55), 0.0, math.radians(40))
    bpy.context.collection.objects.link(light)

    world = bpy.data.worlds.new("VerifyWorld")
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.05, 0.05, 0.06, 1.0)
    world.node_tree.nodes["Background"].inputs[1].default_value = 1.0  # ambient so unlit faces still register
    bpy.context.scene.world = world

def render(out_path: str, samples: int = 32, res: int = 512):
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'        # EEVEE-Next unsupported headless on Windows
    scene.cycles.device = 'CPU'           # CPU fallback — no GPU assumed headless
    scene.cycles.samples = samples
    scene.cycles.seed = 0                 # deterministic
    scene.render.resolution_x = res
    scene.render.resolution_y = res
    scene.render.image_settings.file_format = 'PNG'
    scene.frame_set(1)                    # single fixed frame
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    scene.render.filepath = out_path
    bpy.ops.render.render(write_still=True)

def verify_render(out_path: str, min_nonblack: float = 0.01) -> bool:
    p = pathlib.Path(out_path)
    if not p.exists():
        print("[RENDER QA FAIL] file not created"); return False
    if p.stat().st_size < 1024:
        print(f"[RENDER QA FAIL] suspiciously small ({p.stat().st_size} bytes) — likely silent export failure")
        return False
    img = bpy.data.images.load(out_path)
    pxs = list(img.pixels)                 # flat RGBA
    total = len(pxs) // 4
    nonblack = sum(1 for i in range(total) if max(pxs[i*4], pxs[i*4+1], pxs[i*4+2]) > 0.01)
    frac = nonblack / total if total else 0.0
    bpy.data.images.remove(img)
    print(f"[RENDER QA] non-black pixels: {frac:.2%} (threshold {min_nonblack:.2%}) -> {p.resolve()}")
    return frac >= min_nonblack

def main():
    args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    in_path = _arg(args, "--in", "C:/forge-build/out/model.glb")
    out_path = _arg(args, "--out", "C:/forge-build/out/verify.png")
    reset_scene()
    import_asset(in_path)
    frame_all_with_camera()
    render(out_path)
    ok = verify_render(out_path)
    if not ok:
        # Non-zero exit so the parent PowerShell sees the failure (with --python-exit-code 1).
        raise SystemExit("render-verify failed: blank / missing PNG — export likely produced no visible geometry")

main()
```

---

## §3. Invocation (PowerShell)

```powershell
& "C:\Program Files\Blender Foundation\Blender 4.2\blender.exe" `
    -b `
    --python-exit-code 1 `
    -P "C:/scripts/render_verify.py" `
    -- `
    --in  "C:/forge-build/out/hero.glb" `
    --out "C:/forge-build/out/verify.png"

if ($LASTEXITCODE -ne 0) { Write-Error "Render-verify FAILED (blank/black PNG = silent export failure)"; exit 1 }
```

---

## §4. Guard + Read loop

After the script returns, the model still inspects the image visually. Guard the `Read` so a
missing/blank file reads as the documented diagnosis, not a generic "file not found":

1. Confirm `verify.png` exists and is **> 1 KB** (the script already exits non-zero otherwise).
2. `Read("C:/forge-build/out/verify.png")` — inspect geometry, material, orientation, scale.
3. If blank / all-black / wrong: amend the export (not the verify script) and re-run. A black
   frame with the engine correctly on Cycles points at the **export**, not the renderer — check
   for missing geometry, an all-emissive-black material, or a 100x scale that pushed the mesh
   outside the framed bound.

This is the Forge loop: export -> render-verify (Cycles CPU, fixed frame/samples/seed) ->
verify size + non-black -> `Read` PNG -> critique vs brief -> fix export -> re-verify.

---

## §5. Failure -> detect -> fix

| Symptom in verify.png | Likely cause | Fix |
|---|---|---|
| All black, file < 1 KB | EEVEE-Next left on (headless crash) OR no geometry imported | Force `engine='CYCLES'`, `device='CPU'`; confirm import produced MESH objects |
| All black, file > 1 KB | Material all-black / no lights reaching surface | Script adds a sun + ambient world; if still black, the exported material emits/absorbs all light — re-check PBR export |
| Tiny speck in frame | 100x scale bug (mesh huge or microscopic vs camera) | Re-export with correct unit scale (FBX `apply_unit_scale=True`; glTF meters) |
| Rotated 90 degrees | Axis not converted on export | glTF: `export_yup=True`; FBX: `axis_forward='-Z', axis_up='Y'` |
| `no MESH objects after import` raised | Export wrote an empty file / wrong selection | Re-export with `use_selection=False` (or select the right objects) |
| Pink / magenta surfaces | Missing/biased textures (engine-side, not export) | Inspect the source material; for engine imports see the per-engine reference |
