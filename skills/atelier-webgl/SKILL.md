---
name: atelier-webgl
version: 1.0.0
description: >
  Atelier suite — 3D, WebGL & shader craft (the flagship layer). Build award-grade 3D and generative
  graphics: React Three Fiber + Drei scenes, hand-written GLSL/TSL shaders (fresnel, fbm noise, mesh
  gradients, distortion, dithering), WebGPU via WebGPURenderer, Spline integration, Gaussian splatting, faux-3D, and WebGL
  image hover/scroll distortion — always with lazy-loading, static fallbacks, and accessibility. Use
  whenever building 3D scenes, WebGL/Three.js/R3F, shaders/GLSL, a 3D or generative hero, product
  viewers, shader gradients/grain/distortion, Spline scenes, Gaussian-splat / radiance-field scenes, or interactive 3D graphics. Default stack:
  React Three Fiber + Drei; vanilla Three.js / OGL for non-React or shader-only work. Gate everything with atelier-perf-a11y. Part of the Atelier suite.
triggers:
  - webgl
  - three.js
  - react three fiber
  - r3f
  - shader
  - glsl
  - 3d hero
  - product viewer
  - spline
  - generative graphics
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - Skill   # delegate authored-3D geometry to the Forge suite
  - Agent   # invoke the forge-director agent for the full Forge pipeline
  - Task    # legacy alias of Agent (pre-v2.1.63), kept for compatibility
---

# Atelier — 3D, WebGL & Shaders

The highest-ceiling, highest-cost layer. A WebGL hero can be the thing people remember — or a multi-MB,
inaccessible LCP disaster. The discipline: **the 3D is a single earned moment, engineered with fallbacks,
never the substrate of the page.**

> **Project memory:** if **`ATELIER.md`** exists, read its **Interactivity** level + **Motion policy** first
> (an award-grade signature moment must be sanctioned by the project's budget; set up via **`/atelier init`**
> — the **`atelier`** router).
>
> **Inputs:** the Direction Doc's signature moment + motion budget (this is award/creative-world spend).
> **Default stack:** React Three Fiber + Drei (vanilla Three noted). **Gate:** `atelier-perf-a11y` is
> mandatory here — canvas is opaque to assistive tech and heavy on LCP/INP; production resilience
> (device/context-loss fallback, static poster, offline + reduced-motion paths) is **`atelier-harden`**
> before that gate. **For new flagship 3D, default
> to WebGPU** (`three/webgpu` + TSL, `await renderer.init()`) — **zero-config since r171**, a one-line swap
> with automatic WebGL2 fallback; `WebGLRenderer` is now **maintenance-only** (still the mature baseline) —
> see `references/shaders-glsl-tsl.md` and `references/r3f-drei.md`. Deep reference:
> `references/fundamentals-deepdive.md` (§2). Library versions
> move fast — verify current (≈ Three r184 · R3F v9 stable for React 19 · Drei ~10.7 at writing).
>
> **Data — `atelier-data`:** a vetted Three.js do/don't table via `scripts/search.py "<topic>" --stack threejs` (version pitfalls, single-renderer-per-page, pixel-ratio cap). Implementation cross-check only.

---

## Decide first: should this be WebGL at all?

Be honest about cost (full breakdown in `references/integration-fallbacks.md`):
- A 3D hero ships a big engine (Three core ~150KB+ gzip) + multi-MB assets + shader compile + a
  continuous rAF loop → hurts LCP, INP, battery, thermals.
- **Canvas is invisible to assistive tech** (not focusable, not readable), can trigger vestibular issues.
- **Justified** when the experience *is* the product (portfolios, agencies, product showcases, launches).
  A **net negative** as a decorative background on a content/conversion site — use a grainy CSS/SVG
  gradient or faux-3D instead.
- Often the right answer is **faux-3D** (image sequence, CSS/shader trick) — the 3D *look* without the
  WebGL cost.

If it's justified, proceed. Always build the fallback first.

## Authored 3D geometry — delegate to Forge

When the signature moment needs **authored 3D geometry** — a specific product model, sculpt, organic form,
parametric object, or baked-texture look-dev piece that can't be generated procedurally in GLSL/TSL —
delegate the *asset production* to the standalone **Forge** suite (this skill still owns the *web runtime*):

1. Read `ATELIER.md` — confirm **Interactivity: Award-grade** (or the World explicitly calls for a 3D moment).
   If absent, run `/atelier init` first; don't spin up heavy authored 3D for a Production-world content site.
2. **`Skill(forge)`** (the Forge router skill) — or **`Agent(forge-director)`** (the Agent tool,
   `subagent_type: "forge-director"`) for the full brief→model→look-dev→render→export pipeline — passing
   the Direction Doc's aesthetic + the signature-moment description. (`forge-director` is an *agent*, not a
   skill, so it is invoked with the Agent tool, never `Skill(...)`.)
3. Forge returns a web-ready pair: `public/forge/<slug>-hero.glb` (DRACO *or* Meshopt geometry compression
   — they're mutually exclusive — plus KTX2 textures) + `public/forge/<slug>-hero-poster.webp` — **the
   poster IS the reduced-motion / no-WebGL fallback**.
4. Wire it with the `useGLTF` + poster-fallback pattern in `references/r3f-drei.md`; copy the local DRACO
   decoder to `public/draco/` (and the KTX2/Basis transcoder to `public/basis/` when textures are KTX2).
   Forge keeps its own asset gate (`forge-validate`); the **web-runtime** gate (LCP/CLS/INP, canvas DOM
   alternative) stays here → `atelier-perf-a11y`.

**Run = call the tool.** Writing "hand off to Forge" in prose does nothing — invoke `Skill(forge)` (the
router) or `Agent(forge-director)` (the full autonomous pipeline). Forge owns the *asset*
(geometry/materials/render); this skill owns the *web scene* (R3F, lazy-load, fallbacks, a11y). Always wire
the poster Forge produces — never omit the fallback.

## The flow

1. **Confirm it's worth it** → 2. **R3F scene** → 3. **Shaders (GLSL/TSL)** → 4. **Integrate**
(Spline / faux-3D / DOM distortion) → 5. **Lazy-load + fallback + a11y gate.**

## 2. R3F scene

React Three Fiber renders JSX to a Three scene graph. Essentials + Drei helpers in
**`references/r3f-drei.md`**: `<Canvas>`, `useFrame` (mutate refs, never `setState` per frame),
`useThree`, Suspense loading; Drei `<Environment>` (IBL — makes PBR/glass look right), `useGLTF`,
`<Html>`, `<Text>`, `<Instances>`, `<MeshTransmissionMaterial>`, `<PerformanceMonitor>`/`<AdaptiveDpr>`.
Perf: instancing, dispose, clamp DPR ≤2, `frameloop="demand"` for static scenes.

## 3. Shaders (GLSL / TSL)

The substrate of the "WebGL look." Full recipes in **`references/shaders-glsl-tsl.md`**: vertex vs
fragment, uniforms/attributes/varyings, and copy-paste effects — gradient, **fbm noise**, **fresnel rim**,
**UV distortion**, **dithering**, **mesh-gradient blob**. How to attach (`ShaderMaterial`,
`onBeforeCompile`, Drei `shaderMaterial()`), animate uniforms each frame, and the modern **TSL**
(node-based, compiles to GLSL *and* WGSL) + `WebGPURenderer` path for future-proofing.

## 4. Integrate

In **`references/integration-fallbacks.md`**:
- **Spline** — no-code 3D via `@splinetool/react-spline`; fast, but heavy payload → lazy-load, self-host
  the scene.
- **Faux-3D** — image sequence on scroll, CSS 3D transforms, or a flat shader — the look without the cost.
- **DOM image hover/scroll distortion** — OGL / gpu-curtains (WebGPU; curtains.js is legacy) + GSAP-driven
  uniforms; lives at the border with `atelier-scroll`.
- **Scroll-driven 3D** (scrubbed camera/timeline, pinned canvas, scene progress tied to scroll) — drive it
  from **`atelier-scroll`** (Lenis + ScrollTrigger) and feed the scroll progress into `useFrame`/uniforms:
  this skill owns the *scene*, `atelier-scroll` owns the *scroll plumbing*.
- **Source images & textures (generate, don't stock-grab)** — the image a shader distorts, plus matcaps,
  gradient / dither / displacement maps, and sprite sheets, should be **generated on the Direction Doc's
  aesthetic** via **`/codex-imagegen`** (local Codex, no key), then compressed (KTX2/WebP) and lazy-loaded:
  ```powershell
  $skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
  & "$skills\codex-imagegen\scripts\codex-image.ps1" `
    -Prompt "<texture / matcap / source-image prompt on the aesthetic>" -OutDir ".\public\tex" -Count 1 -Size 1024x1024
  ```
  `-Transparent` for sprites/cut-outs. The same generated image is the **static poster fallback** for the
  no-WebGL / reduced-motion path — so it must exist regardless of the shader.

## 5. Lazy-load, fallback, gate (non-negotiable)

- **Lazy-load** the whole 3D bundle (dynamic import / below the fold); never block first paint with it.
- **Pause** the rАF loop offscreen (IntersectionObserver) and when the tab is hidden.
- **Static poster fallback** for no-WebGL/low-end/reduced-motion; **DOM/text alternative** for any content
  conveyed in the canvas (it's invisible to screen readers).
- **Reduced motion** → static render or poster. **Clamp DPR ≤ 2**, compress assets (DRACO/Meshopt/KTX2 —
  loader-wiring snippet in `references/r3f-drei.md`; feature-detect WebGPU with `navigator.gpu` before init).
- **Handle WebGPU device loss** — the auto WebGL2 fallback only covers *unsupported* browsers at init. After
  a successful init, listen for `renderer.getDevice?.().lost` (or `device.lost`) — a GPU reset / driver crash
  / long backgrounding loses the device and blanks the canvas; on loss, re-init the renderer or swap to the
  static poster.
- Run the full **`atelier-perf-a11y`** gate — this layer is where perf/a11y most often breaks.

---

## Operating principles
- **One earned moment, never the substrate.** Essential content/nav lives in the DOM, not the canvas.
- **Build the fallback first** — static poster + DOM alternative — then enhance to WebGL.
- **R3F + Drei is the default;** drop to vanilla Three/OGL for tiny shader-only widgets; consider
  faux-3D before real 3D.
- **Default new work to TSL + `WebGPURenderer`** (`three/webgpu`, `await renderer.init()`) — write-once
  for WebGPU *and* WebGL2, with the automatic WebGL2 fallback. WebGPU hit **Baseline (Jan 2026)** but is
  only ~**87% desktop / ~71% mobile** and not yet full parity → the **WebGL2 fallback is mandatory, not
  optional**; verify on it. `WebGLRenderer` stays the mature/compatible baseline (maintenance-only).
- **Perf/a11y is mandatory here** — lazy-load, pause offscreen, clamp DPR, provide alternatives. Gate with
  `atelier-perf-a11y`.
