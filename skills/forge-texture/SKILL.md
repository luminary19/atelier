---
name: forge-texture
version: 1.0.0
description: >
  Forge suite — texture baking and procedural texture authoring (the lookdev texture layer). Bakes
  normal maps, ambient occlusion, curvature, displacement/height, and combined PBR map sets from a
  high-poly source onto a low-poly mesh with cage support — headlessly via Blender + Cycles. Also
  builds procedural shader networks (Noise/Voronoi/Wave/Gradient nodes) and bakes them to tileable
  PNGs, generates PBR map sets from a single albedo image, downloads CC0 textures from PolyHaven or
  ambientCG, and compresses finals to KTX2 or WebP. Use whenever asked to: bake textures, bake
  normals, bake AO, high-poly to low-poly bake, cage bake, transfer detail from sculpt, bake curvature
  map, bake displacement or height map, bake PBR maps, build a procedural material and bake it,
  convert height to normal, make a tileable texture, compress textures to KTX2, flip normal map green
  channel for Unreal/DirectX, download a free PBR texture, or generate a seamless texture.
  HEADLESS-ONLY: driven from code, output verified by reading a PNG. Part of the Forge suite.
triggers:
  - bake normals
  - bake textures
  - bake AO
  - high poly to low poly bake
  - cage bake
  - curvature map
  - displacement bake
  - PBR bake
  - procedural texture
  - height to normal
  - tileable texture
  - KTX2 compress
  - flip normal map
  - polyhaven download
  - ambientcg download
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge — Texture Baking & Procedural Textures

The texture layer produces the full PBR map set every downstream consumer expects: Albedo, Normal,
Roughness, Metallic, AO, Height, Curvature. Maps are baked in Blender with Cycles (CPU fallback,
never EEVEE-Next headless on Windows), then verified pixel-statistically and visually by rendering a
preview sphere and reading the PNG.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries the
> PBR workflow (metallic-roughness vs specular-gloss), texel density (px/m), max texture resolution,
> normal-map convention (OpenGL/DirectX target engine), and output paths. If **`ATELIER.md`** also
> exists, extract the primary OKLCH hue and aesthetic to inform procedural palette choices.

---

> **Suite map — relevant skills:**
>
> - **forge** — router/entry point; dispatches here for bake + texture tasks
> - **forge-uv** — UV unwrapping and non-overlapping layout: a valid UV map is required before any
>   bake; run **forge-uv** first if the mesh has no UVs or overlapping islands
> - **forge-material** — PBR shading and Principled→glTF mapping; forge-texture produces the maps,
>   forge-material wires them into the final material. **Boundary:** the green-channel flip /
>   DX↔GL conversion of the baked normal PNG (pixel level) lives HERE; wiring that normal map into
>   a Principled BSDF / glTF material is forge-material.
> - **forge-render** — headless Cycles render for visual QA; the preview-sphere render in step 8
>   delegates to **forge-render**
> - **forge-validate** — the mandatory gate after all maps are produced; runs pixel stats, UV overlap,
>   and glTF-Validator; invoke before handing off to forge-export
> - **forge-export** — packages the map set into glTF/GLB/FBX with correct texture slots and color
>   spaces; consumes this skill's output paths
> - **forge-optimize** — KTX2/Meshopt/Draco compression and the atelier-webgl handoff; compress the
>   PNGs produced here before web delivery
> - **atelier-webgl** — receives the final GLB + poster for Three.js/R3F scenes
> - **codex-imagegen** — generates bespoke matcap/gradient/seamless textures via local Codex;
>   call `Skill("codex-imagegen")` when the procedural approach cannot produce the required aesthetic

---

## Decide first: bake type and tool availability

Before writing any bake script, answer these four questions from FORGE.md (or ask):

1. **Source type** — high-poly→low-poly (Selected-to-Active), Multires sculpt, or procedural shader?
2. **Map types required** — Normal / AO / Curvature / Displacement / Diffuse / Roughness / Metallic?
3. **Target engine** — Blender/Unity HDRP (OpenGL, G=+Y) vs Unreal/DirectX (G=−Y)?
4. **Resolution and sample budget** — 1K/2K/4K? GPU available (OptiX/CUDA) or CPU-only?

Then verify Blender is on PATH:

```powershell
# PowerShell — preflight
& blender --version
```

If Blender is not found, check `C:\Program Files\Blender Foundation\` for the versioned folder and
use the absolute path. Full reference: **`references/headless-invocation.md`**.

---

## The flow

1. **Read FORGE.md** (if present) → extract PBR workflow, texel density, normal convention, output paths.

2. **Decide bake type** — answer the four gate questions above; consult
   **`references/bake-types-samples.md`** for sample counts, color spaces, and file formats per map type.

3. **Verify prerequisites** — UV map is non-overlapping on the low-poly (run `Skill("forge-uv")` if
   missing); transforms are applied (`scale=True, rotation=True`); any Multires or Subdivision
   modifier is at the correct level.

4. **Write the bake Python script** — use the patterns in **`references/bake-scripts.md`** (all
   canonical bpy snippets for hi→lo, Multires, AO, curvature, UDIM tile-shift workaround, and the
   Roughness/Metallic-via-Emission trick). The UDIM tile-shift workaround, the complete headless
   PowerShell bake pipeline, the `sys.argv`-after-`--` parsing pattern, and the full G1–G15 bake
   **gotcha → fix table** (black bake, green/mustard splotches, seams, inverted normals,
   GPU-not-activated, native ROUGHNESS/METALLIC black, Musgrave removal) live in
   **`references/bake-advanced.md`**. Key invariants every script must enforce:
   - `scene.render.engine = 'CYCLES'`
   - `prefs.refresh_devices()` called after setting `compute_device_type`
   - Image Texture node set as **both** `select = True` AND `nodes.active` before `bpy.ops.object.bake()`
   - `img.colorspace_settings.name = 'Non-Color'` for all data maps; `'sRGB'` for Albedo only
   - `img.filepath_raw = "C:/absolute/forward/slash/path.png"` (forward slashes; never raw backslashes)
   - `img.save()` called explicitly after baking — Blender does not auto-save baked images

5. **Invoke Blender headlessly** — the canonical form on Windows (mandatory `--` separator):
   ```powershell
   & blender --background "C:/path/to/scene.blend" `
       --python "C:/path/to/bake_script.py" `
       --python-exit-code 1 `
       -- --lowpoly "Hero_LP" --highpoly "Hero_HP" --out "C:/out" --res 2048
   ```
   Full PowerShell pipeline script: **`references/headless-invocation.md §3`**.

6. **Procedural textures** (when no high-poly source exists) — build Noise/Voronoi/Wave networks
   via bpy, bake to PNG on a unit plane, then apply seam-removal if tileability is required.
   Patterns, node property tables, and the Roughness/Metallic-via-Emission bake trick:
   **`references/procedural-nodes.md`**. For AI-generated textures (matcap, gradient ramp, bespoke
   seamless), call `Skill("codex-imagegen")` then post-process for tileability.

7. **Pixel-level validation** — after every bake, run the per-type stat checks from
   **`references/validation.md`**: normal-map B-channel mean >= 160, AO max > 0.5, roughness std > 10,
   tileability edge-diff < 5.0. A failed check means rerun with corrected settings. When a check fails
   (or a bake comes back black, splotchy, seamed, or inverted), consult the G1–G15
   **gotcha → fix table** in **`references/bake-advanced.md §4`** for the exact cause and remedy.

8. **Visual QA render** — apply the baked maps to a UV sphere, render to PNG via Cycles (32 samples),
   then call `Read` on the PNG to inspect visually. If the sphere shows uniform grey or black, the
   material wiring is wrong — fix and re-bake. Run `Skill("forge-render")` for the full turntable QA.

9. **Green-channel flip for DirectX targets** — if FORGE.md says Unreal or DirectX target, flip the
   G channel. One-liner: `n[:,:,1] = 255 - n[:,:,1]` (cv2 BGR, index 1 = G). Pattern in
   **`references/validation.md §normal-convention`**.

10. **Compression** — compress PNG outputs to KTX2 (ETC1S for albedo/AO, UASTC for normals) or WebP.
    The `ktx` CLI commands, encode-quality guide, WebP conversion, and the POT-resize guard live in
    **`references/headless-invocation.md §§4–6`**. For web delivery, call `Skill("forge-optimize")` —
    it owns KTX2 and runs the full gltf-transform + KTX2 pipeline. **Degrade gracefully:** if the
    `ktx` CLI is absent, ship WebP instead and note the missing-KTX2 gap in FORGE.md under
    `## Texture maps` so forge-optimize can finish the compression later.

11. **Hand off** — write final map paths back to FORGE.md under `## Texture maps`; call
    `Skill("forge-validate")` as the mandatory gate; then `Skill("forge-export")` to package the GLB.

> **Run = call the Skill tool with the exact name.** Writing "next, run forge-validate" in prose runs
> nothing. Every cross-skill handoff is a `Skill("forge-validate")` call.

---

## Operating principles

- **UV first, bake second.** A missing or overlapping UV map produces a black bake with no error. Confirm
  non-overlapping UVs and applied transforms before touching any bake operator.
- **Image Texture node must be active.** `node.select = True` AND `nodes.active = node` are both
  required — one without the other silently writes to the wrong image or raises a poll error.
- **Data maps are Non-Color; albedo is sRGB.** Setting the wrong color space on a normal or roughness
  map corrupts engine shading with gamma de-correction artifacts that are invisible in Blender but
  catastrophic in game engines.
- **Roughness and Metallic bake via Emission.** The native `ROUGHNESS` and `METALLIC` bake types are
  unreliable in Blender 4.x. Route the socket through an Emission node and bake as `EMIT`.
- **Verify, then ship.** Every map gets pixel-stat validation (step 7) and a preview-sphere render
  (step 8) before being handed to forge-export. A bake that looks correct in Blender can still have
  wrong color space, wrong green channel, or undetected seams — the validation catches all three.
- **Know the gotcha table.** Every recurring bake failure — black bake, green/mustard splotches,
  edge seams, inverted normals, GPU-falls-back-to-CPU, native ROUGHNESS/METALLIC black, missing
  Musgrave node — has a one-line fix in the G1–G15 table at **`references/bake-advanced.md §4`**.
  Reach for it the instant a bake looks wrong instead of re-deriving the cause.
