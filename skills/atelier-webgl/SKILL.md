---
name: atelier-webgl
version: 1.0.0
description: >
  Atelier suite — 3D, WebGL & shader craft (the flagship layer). Build award-grade 3D and generative
  graphics: React Three Fiber + Drei scenes, hand-written GLSL/TSL shaders (fresnel, fbm noise, mesh
  gradients, distortion, dithering), WebGPU via WebGPURenderer, Spline integration, faux-3D, and WebGL
  image hover/scroll distortion — always with lazy-loading, static fallbacks, and accessibility. Use
  whenever building 3D scenes, WebGL/Three.js/R3F, shaders/GLSL, a 3D or generative hero, product
  viewers, shader gradients/grain/distortion, Spline scenes, or interactive 3D graphics. Default stack:
  React Three Fiber + Drei. Gate everything with atelier-perf-a11y. Part of the Atelier suite.
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
---

# Atelier — 3D, WebGL & Shaders

The highest-ceiling, highest-cost layer. A WebGL hero can be the thing people remember — or a multi-MB,
inaccessible LCP disaster. The discipline: **the 3D is a single earned moment, engineered with fallbacks,
never the substrate of the page.**

> **Inputs:** the Direction Doc's signature moment + motion budget (this is award/creative-world spend).
> **Default stack:** React Three Fiber + Drei (vanilla Three noted). **Gate:** `atelier-perf-a11y` is
> mandatory here — canvas is opaque to assistive tech and heavy on LCP/INP. **For new flagship 3D, default
> to WebGPU** (`three/webgpu` + TSL, `await renderer.init()`) with the automatic WebGL2 fallback — see
> `references/shaders-glsl-tsl.md` and `references/r3f-drei.md`. Deep reference:
> `references/fundamentals-deepdive.md` (§2). Library versions
> move fast — verify current (≈ Three r18x · R3F v9 · React 19 at writing).

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
  # Codex helper, bundled in your Claude skills dir:
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
- **Reduced motion** → static render or poster. **Clamp DPR ≤ 2**, compress assets (DRACO/Meshopt/KTX2).
- Run the full **`atelier-perf-a11y`** gate — this layer is where perf/a11y most often breaks.

---

## Operating principles
- **One earned moment, never the substrate.** Essential content/nav lives in the DOM, not the canvas.
- **Build the fallback first** — static poster + DOM alternative — then enhance to WebGL.
- **R3F + Drei is the default;** drop to vanilla Three/OGL for tiny shader-only widgets; consider
  faux-3D before real 3D.
- **Default new work to TSL + `WebGPURenderer`** (`three/webgpu`, `await renderer.init()`) — write-once
  for WebGPU *and* WebGL2, with the automatic WebGL2 fallback. WebGPU is still maturing (not full parity),
  so verify on the fallback; `WebGLRenderer` stays the mature/compatible baseline.
- **Perf/a11y is mandatory here** — lazy-load, pause offscreen, clamp DPR, provide alternatives. Gate with
  `atelier-perf-a11y`.
