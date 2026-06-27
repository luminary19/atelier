---
name: forge-optimize
version: 1.0.0
description: >
  Forge suite — web/runtime optimization pipeline for 3D assets: compress, budget, and hand off
  GLB files to the browser. Takes a raw GLB exported by Blender (or another DCC) and delivers
  a browser-ready GLB with Draco or Meshopt geometry compression, KTX2/Basis Universal or WebP
  texture compression, mesh quantization, LOD generation, and spec-validation — then produces
  the handoff package that atelier-webgl expects (optimized GLB + poster WebP + decoder paths).
  Use whenever: compressing a GLB for web delivery, reducing file size, applying Draco or
  Meshopt, encoding KTX2 textures with UASTC or ETC1S, generating LOD levels from a GLB,
  setting up DRACOLoader / KTX2Loader / MeshoptDecoder in Three.js or R3F, validating a GLB
  against the Khronos spec, building a before/after size report, running gltf-transform or
  gltfpack, meeting web 3D budget targets (< 3 MB, < 100 draw calls, < 500k triangles), or
  preparing assets for the atelier-webgl handoff. Trigger phrases: "optimize GLB", "compress
  3D model", "Draco compress", "Meshopt", "KTX2 textures", "web 3D budget", "gltf-transform",
  "gltfpack", "LOD for web", "GLB too large", "atelier handoff". HEADLESS-ONLY: driven from
  code, output verified by reading a PNG. Part of the Forge suite.
triggers:
  - optimize glb
  - compress 3d model
  - draco compress
  - meshopt
  - ktx2 textures
  - gltf-transform
  - gltfpack
  - web 3d budget
  - glb too large
  - atelier handoff
  - lod for web
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge — Web Optimization & Atelier Handoff

The delivery boundary of the Forge pipeline: every raw GLB produced upstream is too large to
serve unoptimized. This skill compresses, budgets, validates, and packages the asset so
**`atelier-webgl`** can load it without a second thought.

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries
> the target engine, poly budget, texture constraints, output paths, and the Atelier aesthetic
> link. If **`ATELIER.md`** also exists, note the world (production vs award-grade) and primary
> OKLCH hue — they constrain which quality tier to use.
>
> **Inputs:** an uncompressed GLB from **`forge-export`** (or Blender direct), a budget tier
> from **`forge-standards`**, and any LOD mesh variants from **`forge-topology`**.
> **Gate downstream:** optimized GLB + poster WebP → hand to **`atelier-webgl`** via
> `Skill("atelier-webgl")`. Web runtime perf gate lives in **`atelier-perf-a11y`**; Forge's
> own spec/mesh gate is **`forge-validate`**. Run = call the Skill tool — writing the name
> in prose runs nothing.

---

> **Suite map** — where `forge-optimize` sits:
>
> **`forge-brief`** → **`forge-standards`** (budgets) → model/UV/material/texture/light pipeline
> → **`forge-render`** (QA PNG) → **`forge-export`** (GLB/USD) → **`forge-optimize`** ← YOU ARE HERE
> → **`atelier-webgl`** (R3F scene) → **`atelier-perf-a11y`** (CWV gate)
>
> Cross-skill calls: **`forge-topology`** generates LOD meshes this skill then compresses.
> **`forge-validate`** should gate every output GLB (spec + mesh quality). The web runtime gate
> (LCP, INP, CLS, a11y) is **`atelier-perf-a11y`**'s job — do NOT skip it.

---

## Decide first: tool + mode

Before touching any file, confirm availability and pick the right codec:

```powershell
# 1. Check tools
where.exe gltf-transform    # primary: npx gltf-transform
where.exe node              # required for gltf-transform
where.exe gltfpack          # secondary: native binary
where.exe toktx             # required for KTX2 via gltf-transform uastc/etc1s
```

Then decide:

| Situation | Tool | Mode |
|-----------|------|------|
| Static mesh, smallest file | `gltf-transform` | `--compress draco` |
| Animated mesh / morph targets | `gltf-transform` | `--compress meshopt` |
| Batch pipeline, no Node | `gltfpack` native binary | `-cc` |
| KTX2 textures (VRAM critical) | `gltf-transform uastc` + `etc1s` | requires toktx |
| Quick scenes, 1–3 textures | `gltf-transform` | `--texture-compress webp` |

**Never apply both Draco and Meshopt to the same file.** They are alternative encodings.

Full CLI reference: **`references/cli-invocations.md`**
Installation & Windows gotchas: **`references/install-windows.md`**
Budget tiers and runtime loader wiring: **`references/budgets-and-runtime.md`**

---

## The flow

**0. Read FORGE.md** (if present) for output paths, budget tier, and engine target.

**1. Inspect** — always run before optimizing:
```
gltf-transform inspect input.glb
```
Read triangle count, draw calls, texture sizes, extension list. Textures dominate (~70–80%
of file size); don't apply Draco if you have 5 triangles and 4 MB of textures.

**2. Gate: pick codec + texture strategy** — from the decide-first table above.
Animated? → Meshopt. Static + max compression? → Draco. VRAM critical? → KTX2 (UASTC+ETC1S).
Quick? → WebP. Document the choice in `FORGE.md` under `## Optimization`.

**3. Optimize** — run `scripts/optimize.ps1` (wrapper over gltf-transform):
```powershell
# Safe defaults — meshopt + WebP, reports before/after KB
powershell -File "$env:CLAUDE_CONFIG_DIR\skills\forge-optimize\scripts\optimize.ps1" `
  -InputPath ".\raw\hero.glb" -Output ".\public\forge\hero-hero.glb"

# With KTX2 (requires toktx in PATH):
powershell -File "...\optimize.ps1" -InputPath .\raw\hero.glb -Output .\public\forge\hero-hero.glb -KTX2

# With Draco (auto-falls-back to Meshopt if the GLB is animated / has morph targets):
powershell -File "...\optimize.ps1" -InputPath .\raw\hero.glb -Output .\public\forge\hero-hero.glb -Draco

# With the poster gate (enforces poster >= 10 KB so there is an image to Read back):
powershell -File "...\optimize.ps1" -InputPath .\raw\hero.glb -Output .\public\forge\hero-hero.glb `
  -Poster .\public\forge\hero-hero-poster.webp
```
The script reports input KB → output KB and exits non-zero if validation fails. It refuses to
run when `-Output` resolves to the same file as `-InputPath` (the source GLB is sacred), and warns
before overwriting an existing output (`-Force` to silence). `-Input` is accepted as an alias for
`-InputPath`. PS 5.1-compatible.

**4. Fine-grained pipeline** (when one-shot is insufficient) — follow the ordered chain in
`references/cli-invocations.md §2`: prune → dedup → weld → (LOD simplify) → geometry codec
→ texture resize → texture codec → validate. Order is load-bearing: never simplify after
a geometry codec; never geometry-codec before weld.

**5. LOD variants** (if FORGE.md specifies LOD): produce `hero-lod0.glb`, `hero-lod1.glb`,
`hero-lod2.glb` via cascaded simplification. See `references/cli-invocations.md §3`.
Use **`forge-topology`** (`Skill("forge-topology")`) for Blender-side remesh before this step.

**6. Validate** — Khronos spec conformance:
```powershell
gltf-transform validate .\public\forge\hero-hero.glb
```
Then run `Skill("forge-validate")` for the full Forge gate (manifold, normals, UV, polycount).

**7. Poster** — generate a static WebP poster (the fallback image for no-WebGL / reduced-motion
paths). Must exist BEFORE the Canvas mounts. Use `frame3d` or `screenshot-glb` (details in
`references/budgets-and-runtime.md §4`). The poster IS the reduced-motion fallback — build it
first. Pass it to `optimize.ps1 -Poster <path>` to enforce the >= 10 KB size gate.
**Then `Read` the poster PNG/WebP with the Read tool** — a blank/black/wrong-color poster means
the GLB is broken upstream (e.g. `IMAGE_COLORSPACE_MISMATCH`, lost geometry). `validate` passing
does NOT mean the asset renders correctly. Do not hand off on a blank poster.

**8. Decoder files** — copy static decoder assets into `public/`:
```powershell
# Copy from node_modules (do this once per web project):
Copy-Item -Path ".\node_modules\three\examples\jsm\libs\draco" -Destination ".\public\draco" -Recurse
Copy-Item -Path ".\node_modules\three\examples\jsm\libs\basis" -Destination ".\public\basis" -Recurse
```

**9. Handoff** — write the handoff note and invoke atelier-webgl:
```
public/forge/<slug>-hero.glb          ← optimized GLB
public/forge/<slug>-hero-poster.webp  ← static fallback image
public/draco/                         ← DRACOLoader decoder files
public/basis/                         ← KTX2Loader transcoder files
```
Then: `Skill("atelier-webgl")` — pass the GLB path, poster path, and decoder paths.
**Run = call the Skill tool. Writing "hand off to atelier-webgl" in prose runs nothing.**

---

## When it goes wrong

The optimize pipeline fails in a small set of recurring ways. Triage here first; full detail +
fixes live in **`references/install-windows.md §4`** (12-row gotcha table).

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `ERR_DLOPEN_FAILED` / "Could not load the sharp module" | Sharp native binary mismatch (wrong Node/OS/CPU) | Reinstall: `npm install --os=win32 --cpu=x64 sharp` then `-g @gltf-transform/cli --force` (Gotcha 1) |
| `toktx not found` with `-KTX2` | KTX-Software not on PATH (NullSoft `setx` truncates PATH at 1024 chars) | Re-add `C:\Program Files\KTX-Software\bin` to user PATH, restart shell (Gotcha 2) |
| KTX2 GLB **larger** than the WebP version | UASTC without Zstandard supercompression | Add `--zstd 18`; ETC1S for color slots, UASTC only for normal/ORM (Gotcha 6/7) |
| Animated GLB plays in T-pose / loses animation | Draco was applied to an animated/morph mesh | Use Meshopt (the script auto-falls-back; never `-Draco` on animated assets) (Gotcha 4/5) |
| `simplify` gives no reduction or holes | Mesh not welded before simplify | `weld --tolerance 0.0001` before `simplify` (Gotcha 8) |
| **Poster renders blank/black** but `validate` passes | Spec-valid but visually broken (colorspace, lost geometry) | Read the poster; fix upstream in `forge-export`/`forge-material` — do NOT hand off |

Determinism: gltf-transform is deterministic for a given input + flags. Re-running `optimize.ps1`
on the same input is **idempotent** — it rebuilds the same artifact and never touches the source.

---

## Operating principles

- **Inspect before every compress.** File size breakdown decides the strategy; never guess.
  Textures almost always dominate — resize them before encoding.
- **Source files are sacred.** Draco and Meshopt are lossy. The uncompressed GLB from
  `forge-export` is the source of truth; the optimized output is a build artifact. Never
  overwrite the source — `optimize.ps1` refuses when `-Output` equals `-InputPath`.
  Re-running optimize on the same input is safe and idempotent; never point `-Output` at the source GLB.
- **Codec choice is a contract.** The runtime loader must match the compression (DRACOLoader
  for Draco, MeshoptDecoder for Meshopt, KTX2Loader for KTX2). Document the codec in
  `FORGE.md`; pass it to `atelier-webgl` in the handoff note.
- **Poster first, canvas second.** The static fallback must exist before the Canvas mounts.
  Build the poster during this step, not as an afterthought in `atelier-webgl`.
- **Validate before handing off.** Run `gltf-transform validate` + `Skill("forge-validate")`
  on every optimized GLB. A corrupt asset discovered in `atelier-webgl` is expensive to
  debug.
