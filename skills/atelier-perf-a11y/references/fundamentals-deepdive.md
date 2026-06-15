# Beautiful UI/UX — Deep Dive Knowledge Base

A consolidated, practitioner-grade companion to `fundamentals.md`. Where the parent file is a *map* (vocabulary + pointers), this is the *territory*: how each tool actually works, the current (verified mid-2026) state of the ecosystem, concrete recipes/code, decision matrices, and the cross-cutting principles that separate "expensive" from "cheap."

**How to use:** Read §0 first — it corrects the things most likely to be stale. Then jump to the section you need. The back matter (§14–16) holds the decision logic, the expensive-vs-cheap rules, and the pre-ship gates that apply to *everything*.

---

## §0. Current-state deltas (what changed — read this first)

These are the facts most likely to differ from default assumptions. Internalize them; they change which tool you reach for.

- **GSAP is 100% free, including every former premium plugin** (ScrollTrigger, ScrollSmoother, SplitText, MorphSVG, DrawSVG, Flip, Inertia, etc.), commercial use included — since **GSAP 3.13, Apr 30 2025**. Webflow acquired GreenSock (Oct 2024). The historical "ScrollTrigger costs money" reasoning is dead.
- **Framer Motion → "Motion."** New home `motion.dev`, canonical package `motion`, React import path `motion/react`. It's now a **hybrid React + vanilla-JS** library with a WAAPI-backed hardware-accelerated engine. `framer-motion` still publishes as an alias — migrate imports.
- **Anime.js v4** is a full ESM rewrite. The global `anime` object is gone; you import named functions (`animate`, `createTimeline`, `stagger`, `utils`, `createScope`, `onScroll`). v3 code does not run on v4.
- **Tailwind v4** (Jan 2025): CSS-first config via `@theme {}` (no `tailwind.config.js` by default), Rust "Oxide" engine (~5× full / 100×+ incremental build speed), OKLCH color tokens, native CSS variables for every token, container queries built in. Migration from v3 is breaking (`npx @tailwindcss/upgrade` codemod helps).
- **shadcn/ui** now lets you pick **Radix OR Base UI** as the primitive layer (`init --base radix|base`). Radix development slowed post-WorkOS acquisition; **Base UI (by the MUI team) hit v1 on Dec 11 2025** and is a serious new default for the headless layer. shadcn CLI is Tailwind-v4-native.
- **Color: OKLCH is the modern perceptual standard** (uniform lightness, P3 gamut, predictable ramps). **APCA was *removed* from the WCAG 3 working draft** for lack of consensus — *design* with APCA (especially dark mode) but **ship conformance to WCAG 2.2 AA**.
- **INP replaced FID** as a Core Web Vital (Mar 2024) and is the most-failed one. Targets (p75, field): **LCP ≤ 2.5s, CLS ≤ 0.1, INP ≤ 200ms.**
- **Lenis replaced Locomotive Scroll** as the default smooth-scroll lib (Locomotive v5 is now built *on* Lenis). It wins by modifying the *real* scroll position (sticky, IntersectionObserver, anchors, a11y keep working).
- **Native CSS scroll-driven animations** (`animation-timeline: scroll()/view()`) ship in Chromium + Safari (NOT Firefox, ~85% global) — progressive enhancement only.
- **View Transitions API**: same-document (SPA) is Baseline (Oct 2025); cross-document (MPA) is now cross-browser (Chrome/Edge 126+, Safari 18.2+, Firefox 144+).
- **WebGPU is broadly baseline** (Chrome/Edge, Firefox on Win + Apple-Silicon macOS, Safari 26 on macOS/iOS) — ~95% with WebGL2 fallback. For new 3D work, plan for **Three.js `WebGPURenderer` + TSL** with a WebGL2 fallback.
- **Subgrid, container queries, and dynamic viewport units (`svh`/`lvh`/`dvh`)** are all Baseline / production-safe now.
- **curtains.js is legacy WebGL**; the actively-developed successor is **gpu-curtains** (WebGPU) for DOM→GPU plane effects.
- **React 19** ships `useOptimistic` (first-class optimistic UI) and bumped R3F to its v9 line.

---

## §1. JavaScript Animation Libraries

### GSAP (GreenSock) — the industry standard
- **Model:** a property-tweening engine on a single rAF ticker that interpolates *anything numeric* (CSS, SVG attrs, canvas props, JS objects, three.js values), writing inline styles. Two primitives: **Tween** (`gsap.to/from/fromTo/set(targets, vars)`) and **Timeline** (sequenced container; position params `"+=0.5"`, `"<"`, `">"`, `"label"`, absolute seconds; nestable + seekable/reversible).
- **Easing is its superpower:** `power1..4`, `back`, `elastic`, `expo`, `circ`, `bounce`, `steps()`, each `.in/.out/.inOut`; `CustomEase` for arbitrary curves. Default `power1.out`.
- **Key plugins (all free now):** **ScrollTrigger** (`trigger`, `start`/`end`, `scrub: true|<num>`, `pin`, `snap`, `toggleActions`, `markers`, `invalidateOnRefresh`); **ScrollSmoother** (smooth scroll + `data-speed`/`data-lag` parallax, needs `#smooth-wrapper > #smooth-content`); **Flip** (capture `Flip.getState`, mutate DOM, `Flip.from` animates the delta — best shared-element/layout tool for vanilla); **MorphSVG**, **DrawSVG**, **MotionPathPlugin**, **SplitText** (rewritten 2025: ~50% smaller, screen-reader a11y, responsive re-split via `autoSplit`/`onSplit`).
- **React:** `useGSAP(callback, { scope, dependencies })` from `@gsap/react` — wraps in `gsap.context()` and auto-reverts on unmount (solves the #1 React-GSAP footgun). `scope` confines selectors; `contextSafe` wraps handlers created after the initial run.
- **Responsive + reduced motion:** `gsap.matchMedia()` — `mm.add("(min-width:800px)", () => {...})` and `mm.add("(prefers-reduced-motion: reduce)", () => {...})`; tweens auto-clean as queries flip.
- **Gotchas:** animate `x/y/scale/rotation/opacity` not `top/left/width`; register plugins once (`gsap.registerPlugin(...)`); call `ScrollTrigger.refresh()` after async layout; ~50KB+ core but tree-shakeable per plugin.

```js
gsap.registerPlugin(ScrollTrigger);
gsap.timeline({ scrollTrigger:{ trigger:".panel", start:"top center", end:"+=500", scrub:true, pin:true }})
  .to(".box", { x:300, rotation:360, ease:"none" })
  .to(".box", { backgroundColor:"var(--accent)" }, "<");
```

### Motion (formerly Framer Motion)
- **Model (React):** `<motion.div>` driven by `initial`/`animate`/`exit` (can be **variants** with `staggerChildren`/`delayChildren`), `transition` (`type:"spring"` with `stiffness`/`damping`/`mass`, or `tween` with `duration`/`ease`), gesture states `whileHover`/`whileTap`/`whileInView`/`whileDrag`, and `drag`+`dragConstraints`.
- **Springs are the default** for physical props (real solvers, interruptible, carry velocity).
- **`<AnimatePresence>`** enables `exit` animations (defers unmount); modes `wait`/`popLayout`/`sync`.
- **Layout animations:** `layout` prop auto-animates layout changes (FLIP); **`layoutId`** does shared-element "magic move"; `<Reorder.Group>` for drag-reorder.
- **Hooks:** `useScroll` (`scrollYProgress`), `useTransform`, `useSpring`, `useMotionValue`, `useInView`, `useAnimate`.
- **Hybrid engine:** runs on WAAPI (hardware-accelerated, off main thread) where possible, JS engine for springs/layout/interruption. **Mini bundle** `motion/mini` (`animate`) ~2.3KB for smallest footprint; `LazyMotion` + `domAnimation`/`domMax` to shrink the React bundle.

```jsx
import { motion, AnimatePresence } from "motion/react";
<AnimatePresence mode="wait">
  {open && <motion.div layoutId="card"
    initial={{opacity:0,y:20}} animate={{opacity:1,y:0}} exit={{opacity:0,y:-20}}
    transition={{type:"spring",stiffness:300,damping:30}} whileHover={{scale:1.05}} />}
</AnimatePresence>
```

### The rest
- **Motion One** — the standalone WAAPI micro-lib (`animate` ~3.8KB); now folded into `motion`'s vanilla surface. Use `motion`/`motion/mini` for new work. Lightest pure-WAAPI option; springs approximate, no FLIP/layout.
- **Anime.js v4** — free MIT, lightweight, tree-shakeable timeline engine. Middle ground between Motion One and GSAP. `import { animate, createTimeline, stagger, utils, onScroll, createDraggable } from "animejs"`. Promises opt-in via `utils.promisify`; use `createScope` for React cleanup.
- **Lottie** — plays After Effects vector animations as JSON. Renderers: `svg` (fidelity, heavy), `canvas` (faster), `html`. **Prefer dotLottie** (`@lottiefiles/dotlottie-web`, ThorVG WASM, 2–10× smaller, WebGL/WebGPU, `DotLottieWorker` for off-main-thread). Timeline *playback*, not data-bound logic.
- **Rive** — real-time interactive vector runtime + editor. **State machines + data binding** live inside the `.riv` file → genuine interactive/stateful/data-driven graphics. WASM canvas/WebGL. Pick over Lottie for interactive UI characters, game-like UI, data-driven motion. `useRive`/`useStateMachineInput` in React.
- **Theatre.js** — visual sequencer + studio for keyframed 3D/DOM motion; powerful but **dormant since early 2024** — weigh for new projects.
- **Auto-Animate** — one-line FLIP for add/remove/move of a parent's *direct children*; ~2KB, respects reduced motion. Outgrow it → Motion `layout` / GSAP Flip.
- **Popmotion / Velocity** — legacy; migrate off (Popmotion's lineage → Motion).

**Decision:** scroll storytelling/SVG morph/text-split → **GSAP**; declarative React + gestures + layout/shared-element + springs → **Motion**; smallest WAAPI tween → **Motion mini**; free lightweight general timeline → **Anime.js v4**; designer AE motion → **Lottie/dotLottie**; interactive/stateful/data-bound → **Rive**; effortless list motion → **Auto-Animate**.

---

## §2. 3D / WebGL / Generative Graphics

**Big picture:** Two GPU APIs — WebGL2 (universal) and WebGPU (now baseline, adds compute + lower CPU overhead). 2025–26 is the crossover; libraries dual-target with WebGPU→WebGL2 fallback. Abstraction ladder: Spline (no-code) → R3F+Drei / Babylon (batteries) → Three.js (engine) → OGL (thin) → raw WebGL/WebGPU. Node-based shading (TSL, Babylon NodeMaterial, p5.strands) is the new paradigm because it compiles to *both* backends.

- **Three.js** (r184, monthly cadence) — retained-mode scene graph: `Scene` → `Mesh` (`BufferGeometry` + `Material`) + `Camera` + `Renderer`. Material tiers: Basic → Lambert/Phong → **Standard/Physical (PBR)** → ShaderMaterial → **`*NodeMaterial` (TSL)**. Two renderers coexist: `WebGLRenderer` (stable, GLSL) and **`WebGPURenderer`** (`import 'three/webgpu'`, `await renderer.init()`, falls back to WebGL2 — the strategic future). Addons live in `three/addons/` (OrbitControls, GLTFLoader, EffectComposer) — import per-file.
  - **Perf:** draw calls dominate → `InstancedMesh`/`BatchedMesh`/merge geometry/reuse materials; **dispose manually** (geometries/textures/RTs aren't GC'd); clamp `setPixelRatio(min(dpr,2))`; DRACO/Meshopt + KTX2 compression.
- **React Three Fiber (R3F)** (v9 for React 19; v10 beta) — a React reconciler rendering to the Three scene graph. JSX maps to Three classes (`<mesh>`, `<boxGeometry args={[1,1,1]}>`), props set properties, `attach` wires child→parent property. `useFrame((state,dt)=>...)` is the render loop — **mutate refs, never `setState` per frame**. `frameloop="demand"` for static scenes.
- **Drei** — ~150 R3F helpers. Load-bearing: `<OrbitControls>`, **`<Environment>`** (HDRI/IBL — makes PBR/glass look right), `useGLTF`/`useTexture`, **`<Html>`**, **`<Text>`** (SDF/troika), `shaderMaterial()` factory, **`<MeshTransmissionMaterial>`** (glass/refraction, expensive), `<Instances>`/`<Merged>`, `<PerformanceMonitor>`/`<AdaptiveDpr>`.
- **Babylon.js 8** — full batteries-included engine (Havok physics, character controller, GUI, **Node Material Editor**, editor, audio, Gaussian splats). v8 ships all shaders in GLSL *and* WGSL → ~2× smaller WebGPU bundles. Pick for games/sims/integrated physics + editor.
- **OGL** — thinnest WebGL2 wrapper (Three-like API, you write the GLSL). Tiny bundle for shader-centric work; alpha, no WebGPU, no loaders/PBR.
- **PixiJS v8** — fastest **2D** GPU renderer; WebGPU is core (WebGL2 fallback), async `await app.init()`. Games, data-viz at scale, image filters. Atlases + batching to keep draw calls low.
- **Spline** — no-code 3D; exports React component/runtime/glTF. Fast for designers but **heavy multi-MB payloads** (LCP-hostile) — lazy-load.
- **GLSL shaders** — **vertex** (per-vertex, transforms position, displaces geometry) + **fragment** (per-pixel, 99% of effects). Data flow: attributes → vertex, uniforms (time/resolution/textures) → both, varyings (interpolated) vertex→fragment. Canonical effects: gradients (`mix`), noise/fBm (organic), distortion (offset UVs), dithering (Bayer/blue-noise), fresnel (`pow(1-dot(view,normal),p)` — rim glow). Attach in Three via `ShaderMaterial`, `onBeforeCompile` (patch built-in PBR material), Drei `shaderMaterial()`, or **TSL**.
- **TSL (Three Shading Language)** — write shaders as JS node graphs; compiles to **GLSL *and* WGSL** automatically. The only write-once path for both backends; unlocks GPU **compute** (particles/physics). Assign `material.colorNode`/`positionNode`. The future of Three shading.
- **WebGPU** — successor to WebGL: compute shaders, lower overhead, WGSL. Broadly baseline; keep WebGL2 fallback. Async init everywhere; handle device-lost.
- **p5.js 2.x** — creative coding; `createCanvas(w,h,WEBGL)`, **p5.strands** (shaders in JS), experimental WebGPU. Art/teaching, not app UIs. (2.0 has breaking changes vs 1.x.)
- **Two.js** (active) — renderer-agnostic 2D vector (SVG/Canvas/WebGL). **Paper.js** (stale) — best 2D path geometry/boolean ops.
- **gpu-curtains** (WebGPU, active) / **curtains.js** (WebGL, legacy) — map DOM `<img>`/`<video>` onto GPU planes for hover/scroll distortion.

**The honest cost of WebGL/WebGPU heroes:** big JS engine (Three core ~150KB+ gzip) + multi-MB assets + shader compile + continuous rAF → hurts LCP/INP/battery. Canvas is **opaque to assistive tech** (not focusable, not screen-reader-readable). **Rule:** never put essential content/nav only in WebGL; provide a DOM equivalent + static poster fallback + `prefers-reduced-motion`. Justified when the experience *is* the product; a net negative as a decorative background on content sites.

---

## §3. Visual Styles & Aesthetic Keywords

The meta-rule for every style: **execute the underlying system, not the surface.** AI-slop is always "the look without the discipline." For each: signature → recipe → avoid-slop.

- **Glassmorphism** — frosted translucent panels with a light edge rim. `background:rgba(255,255,255,.10); backdrop-filter:blur(12px) saturate(160%); border:1px solid rgba(255,255,255,.18)`. Keep blur 8–15px; needs a *colorful* backdrop; **`backdrop-filter` not `filter`**; never inside `overflow:hidden`. Slop: frosted-purple card on everything, no edge light.
- **Neumorphism / Soft UI** — same-color extrusion via **dual shadow** (`box-shadow: 10px 10px 20px #bebebe, -10px -10px 20px #fff`); `inset` = pressed. **Inherently fails WCAG 3:1** — fix needs a real border/fill (then it's barely neumorphism). Decorative accents only.
- **Skeuomorphism (modern)** — material realism: liquid glass that refracts, specular edge highlights, context-aware legibility (Apple Liquid Glass / Vision Pro). Glass + inset specular rims + SVG `feDisplacementMap` refraction + parallax. Slop: photoreal textures on everything OR flat translucent box with no edge light.
- **Brutalism / Neo-brutalism** — hard borders + **zero-blur offset shadow** (`border:3px solid #000; box-shadow:6px 6px 0 #000; border-radius:0`), flat saturated/pastel fills, heavy grotesque type. Examples: Gumroad, Bloomberg Businessweek. Slop: the border-kit applied without intent/strong content.
- **Flat / Material / Material You** — Material You: dynamic color from one seed via HCT → 13-tone palettes → role tokens; **tonal elevation** (surface tint) over heavy shadows; M3 type/shape scales; 48dp targets. Slop: generic indigo + giant shadows + default Roboto.
- **Claymorphism** — puffy 3D toy surfaces: big rounded corners + **tinted** outer shadow + two insets (`0 35px 68px rgba(tint,.42), inset 0 -8px 16px ..., inset 0 8px 16px rgba(255,255,255,.6)`). Pastels, 2–3 colors, sparingly. Slop: pure-black shadows, balloons everywhere.
- **Aurora / Mesh gradients** — overlapping color blobs. CSS: stacked `radial-gradient()` spotlights + `blur(60–100px)` on a wrapper. SVG (Stripe's actual approach): blurred `<circle>`s + `feBlend`. Shader for real-time motion. **Add grain** to kill banding. Slop: two-stop linear "mesh," lazy purple blob.
- **Bento grids** — modular rounded tiles of *different sizes*, one hero cell. CSS Grid with `span`s; never empty cells; consistent radius (~18px) + gap; `#f5f5f7`/`#1a1a1a` surfaces. Slop: uniform equal boxes (kills hierarchy), cards-in-cards.
- **Bauhaus / Swiss / International Typographic Style** — rigorous grid, flush-left grotesque on a baseline, asymmetric balance, black/white + one accent. `repeat(12,1fr)` + baseline multiples; Helvetica/Inter/Suisse/Söhne; never justified. Slop: Helvetica + a red square but *no actual grid*; centered everything.
- **Editorial / Magazine** — oversized display type, dramatic scale contrast, whitespace, pull quotes, drop caps, serif+sans, broken grid. `clamp(2.5rem,8vw,7rem); line-height:.95; letter-spacing:-.02em`; body `max-width:65ch`. Slop: Playfair Display + centered headline + stock photo.
- **Maximalism** — curated chaos: `mix-blend-mode` layering, 8–12 clashing saturated hues, eclectic type 12px–30vw, texture/marquees/stickers. Needs recurring motifs + one anchor. Examples: Spotify Wrapped, Liquid Death.
- **Y2K / Frutiger Aero** — Y2K = chrome/holographic/blobjects; Frutiger Aero = glossy aqua + bokeh + nature photography. Glossy button: high radius + `::before` top-half white→transparent shine + inner glow + grounded drop shadow; gradients behave like *light*. Slop: flat color + one fake gloss stripe.
- **Vaporwave / Synthwave / Retrowave** — synthwave = sincere 80s; vaporwave = ironic/glitch/pastel. **Layered neon glow** (white core → colored bloom via stacked `text-shadow`), perspective grid floor, gradient sun. Slop: flat purple→pink + one grid PNG + Orbitron.
- **Cyberpunk / Sci-fi HUD** — near-black + neon, mono type, glitch (chromatic aberration via offset `::before`/`::after`), subtle scanlines (`repeating-linear-gradient` ~.07 alpha), notched `clip-path` HUD frames. Glitch occasional, palette restrained. Slop: neon-green Courier + constant glitch loop.
- **Dark mode / Dark-tech** — charcoal not `#000` (`#0a0a0f`–`#141416`); elevation by **lighter surfaces / translucent white overlays** (.03→.06→.09) not shadow; build in **OKLCH/LCH**; off-white text (~87%), **desaturated** accent; sparse radial glow. Examples: Linear, Vercel, Raycast. Slop: pure `#000` + grey text + purple gradient + frosted card (the #1 vibe-coded tell).
- **Dithering / Halftone** — luminance-driven dot/pixel patterns. CSS (`radial-gradient` dots + mask), SVG filters, canvas (sample luminance), or **WebGL Bayer-matrix shader** (real-time). Examples: Obys, Minh Pham, Obra Dinn. Monochrome/duotone. Slop: flat halftone PNG overlay.
- **Grain / Noise** — the highest-ROI "expensive" tactic. SVG `feTurbulence` (`fractalNoise`, `baseFrequency` .6–.9, `numOctaves` 1–3) at **opacity .03–.08** + `mix-blend-mode:overlay`. Kills gradient banding (grainy gradients). Slop: visible/too strong, or tiled PNG that repeats.
- **Liquid / Fluid / Metaball** — SVG goo filter (`feGaussianBlur` + `feColorMatrix` alpha contrast on a container) for 2D; WebGL SDF metaballs (`smin`) / refractive liquid glass (snapshot page → refract UVs → specular + chromatic aberration) for brand-level. CSS `backdrop-filter` **cannot refract** — WebGL only; CSS blur is the fallback. One earned moment + reduced-motion fallback.
- **Kinetic typography** — type performs (char reveals, horizontal scroll, weight morph). Stack: GSAP + ScrollTrigger + **SplitText** + **Lenis** + variable fonts. `clamp()` sizing, `transform`/`opacity` only, reduced-motion fallback. Slop: generic char-stagger on every heading with a default font.
- **Anti-design** — deliberate convention-breaking (default styles, clashing type, broken grids). Needs intent + strong content; stay usable/accessible underneath. Neo-brutalism is its prettified descendant.

**Pairings that work:** Swiss grid + editorial display + grain; dark-tech + mesh gradient + grain + restrained glass; bento + flat + subtle depth; kinetic type + liquid + dark-tech. **Clash:** neumorphism + anything needing contrast; glass everywhere + dark-tech (slop signature); maximalism + bento. **Dated:** neumorphism, literal-texture skeuomorphism, glass-everywhere.

---

## §4. Scroll & Interaction Techniques

- **Parallax** — layers move at different rates. Native `animation-timeline:scroll()` (best), GSAP `scrub`, or Lenis+transform. Avoid `background-attachment:fixed`. Strong vestibular trigger → gate on reduced motion; keep subtle.
- **Scroll-jacking** — overriding native scroll. Breaks velocity expectations, keyboard, SR, find-in-page. Prefer *scrubbing* (still native) over true hijacking; always provide a non-hijacked fallback.
- **Scroll-triggered reveals** — **IntersectionObserver** (lightweight, toggle a class, CSS does the transition) for one-shot; **ScrollTrigger** when tied to scroll *progress*/pin/sequence. Never raw `scroll` listeners.
- **Scroll scrubbing** — progress bound to scroll. ScrollTrigger `{scrub:true|<sec>}` or native `scroll()`/`view()`. `scrub:<num>` + Lenis = buttery.
- **Pinning** — **`position:sticky` first** (cheap, accessible; breaks under ancestor `overflow`/`transform`); ScrollTrigger `pin:true` (wraps in pin-spacer, `position:fixed`) only when sticky can't express it.
- **Horizontal scroll** — pin + `gsap.to(track,{x:()=>-(track.scrollWidth-innerWidth), scrollTrigger:{scrub,pin,invalidateOnRefresh:true}})`. Provide arrows/keyboard escape.
- **Smooth scroll — Lenis** is the standard. Wire it to GSAP:
  ```js
  lenis.on('scroll', ScrollTrigger.update);
  gsap.ticker.add((t)=>lenis.raf(t*1000)); gsap.ticker.lagSmoothing(0);
  ```
  Options: `lerp` (~0.1) **or** `duration`+`easing`. Don't init (or `lenis.destroy()`) under reduced motion. Locomotive v5 wraps Lenis.
- **Sticky stacking cards** — `position:sticky; top:0` per card + scale/radius change on scroll; native `view()` can do scale-on-leave with zero JS.
- **Scroll snapping** — CSS `scroll-snap-type:y proximity` (gentler than `mandatory`) + `scroll-snap-align`; `scroll-padding` for fixed headers. Prefer over JS snapping.
- **Native scroll-driven animations** — `animation-timeline:scroll()`/`view()` + `animation-range` (`entry`/`exit`/`cover`); off main thread. Chromium+Safari only → feature-detect `CSS.supports('animation-timeline: scroll()')`, fall back to IO/ScrollTrigger.
- **Magnetic buttons / cursor** — translate by a fraction of cursor delta on `mousemove`, ease back on leave (GSAP `quickTo`). Pointer-only → never gate function; disable under reduced motion.
- **Custom cursors** — hide native, lerp a follower. Preserve focus states, keyboard usability, hit areas; provide fallback.
- **Hover distortion** — OGL/curtains.js/three WebGL planes + GSAP-driven uniforms (flowmap). Lazy-init + plain `<img>` fallback.
- **Marquee** — CSS: duplicate content, `@keyframes` translateX -50%, `linear infinite`; JS (GSAP modulo) for pause/drag/velocity. Pause under reduced motion; `aria-hidden` the duplicate.
- **Page transitions — View Transitions API** first: SPA `document.startViewTransition(()=>updateDOM())` + `view-transition-name` for shared elements; MPA `@view-transition { navigation: auto; }` (zero JS). Barba.js/Swup for bespoke control or legacy support.
- **FLIP** — First (measure), Last (apply final state, measure), Invert (transform back), Play (transition to identity). Only `transform` animates; layout computed once. Powers shared-element/reorder/expand. GSAP **Flip** automates it; View Transitions is browser-native FLIP.

---

## §5. Micro-interactions & Motion Principles

- **Microinteractions (Dan Saffer):** Trigger → Rules → Feedback → Loops/Modes.
- **Easing:** ease-**out** entrances (fast→settle), ease-**in** exits, ease-in-out moves, **linear** only for continuous (marquee/spinner). Tune custom beziers (e.g. `cubic-bezier(0.16,1,0.3,1)`), store as CSS vars.
- **Spring physics:** stiffness (snappiness), damping (settle/bounce), mass (weight). Natural because they carry velocity and are interruptible. Use for direct-manipulation/interruptible UI; duration+easing for deterministic choreography.
- **Staggering:** 30–80ms per item, total cascade < 600ms; `from:'center'|'edges'|'random'`.
- **Orchestration:** one focal point, lead the eye, overlap (next starts before previous ends), consistent motion voice.
- **12 Principles of Animation → UI:** squash&stretch (button squish), anticipation (wind-up), staging (dim bg for modal), straight-ahead vs pose-to-pose, follow-through/overlap (stagger, overshoot), **slow in/out (easing — most important)**, arcs (curved paths), secondary action, timing (mass), exaggeration (sparingly), solid drawing (consistent depth), appeal (brand personality).
- **Material motion:** Emphasized vs Standard easing sets; M3 Expressive (2025) moved to spring physics; container-transform/shared-element = FLIP/View-Transitions.
- **States:** skeleton/shimmer (perceived speed; static under reduced motion); **optimistic UI** (`useOptimistic` in React 19 — only for likely-success, cheap-rollback actions); design **empty/loading/error** deliberately.
- **Haptics:** Vibration API (`navigator.vibrate`) mobile/Android; short meaningful bursts; never haptic-only.
- **Don Norman:** affordance (what's possible), signifier (perceivable cue), feedback (≤100ms response), mapping (control↔effect correspondence).
- **Timing defaults:** hover/press/toggle 120–200ms; reveal/small move 200–300ms; modal/page 300–450ms; ceiling ~500ms; respond to input ≤100ms. "Motion should be felt, not seen."
- **Reduced motion (mandatory):** detect via `@media (prefers-reduced-motion: reduce)` + `matchMedia`; **reduce, don't always nuke** — keep opacity fades/shortened durations, remove large movement/parallax/scroll-jack/marquees/overshoot; provide non-motion signifiers.

---

## §6. Typography

- **Modular scale:** base × ratio^n. Ratios: 1.2 (UI conservative), **1.25 (web UI workhorse)**, 1.333 (marketing), 1.5 (bold), 1.618 (golden/dramatic). Use type-scale.com. **Fewer sizes (5–7) = more consistent.**
- **Variable fonts:** axes `wght`/`wdth`/`slnt`/`ital`/`opsz` (registered, lowercase) + custom (UPPERCASE). High-level (`font-weight:550`, `font-optical-sizing:auto`) cascades; `font-variation-settings` does NOT inherit per-axis (all-or-nothing) → store each axis in a CSS var and recompose. One file replaces many weights; animate numeric axes.
- **Kerning/tracking/leading:** `letter-spacing` in `em`; `line-height` **unitless**. Tracking inversely scales with size (display `-.02em` to `-.04em`; small-caps `+.05em` to `+.1em`). Leading: body 1.5–1.7, display 0.9–1.1.
- **Fluid type:** `clamp(min, intercept_rem + slope*100vw, max)`. slope=(max−min)/(maxVw−minVw); intercept=min−slope×minVw (rem). **Keep a `rem` term** so zoom works (pure `vw` fails WCAG 1.4.4). Use utopia.fyi (ratio can differ at each breakpoint).
- **Pairing:** contrast of role + harmony of mood; superfamily pairing safest (IBM Plex, Source); display + body + mono; limit 2–3 families. Tools: Fontjoy, Fontpair, Typewolf.
- **OpenType:** prefer `font-variant-*` (cascades): `tabular-nums slashed-zero` (tables), `oldstyle-nums` (prose), `all-small-caps` (real small caps, not `text-transform`), ligatures; `font-feature-settings:"ss01" 1` for stylistic sets. `dlig` display only.
- **Foundries:** free quality — **Fontshare** (Satoshi, General Sans, Clash Display), Google Fonts (Inter, Geist), Pangram Pangram. Premium — Klim (Söhne, Tiempos), Grilli Type (GT America/Sectra), ABC Dinamo (Diatype). "Expensive" = large optical ranges, real small caps + figure styles, restrained distinctive grotesques.
- **"Expensive" recipe:** 1–2 families; body line-height 1.5–1.7, display 1.0–1.1; tight display tracking; ratio ≥1.25; measure 60–75ch; body 16–20px; OpenType on; restraint.

---

## §7. Color

- **Schemes:** complementary (max contrast), analogous (calm), triadic (vibrant/balanced), split-complementary (safe contrast), monochromatic, duotone.
- **Spaces:** HSL lies about lightness (same L% ≠ same perceived brightness → uneven ramps). **OKLCH** (Oklab cylindrical) is perceptually uniform, P3-capable, hue-stable. `oklch(L C H / a)` — L 0–1, C 0→~0.37, H 0–360. Relative color: `oklch(from var(--c) calc(l + .1) c h)`. ~92%+ support.
- **Tokens/ramps:** primitive (`blue-50…950`) + **semantic** (`--bg`/`--text`/`--primary`/`--danger` referencing primitives — theming/dark mode remaps semantics). Build perceptually-even ramps in OKLCH: fix H, sweep L evenly 0.97→0.20, curve C (peak mid ~500). **Radix 12-step** roles: 1 app bg, 2 subtle bg, 3–5 component bg (normal/hover/active), 6 subtle border, 7 border/focus, 8 strong border, 9 solid (purest — buttons), 10 solid hover, 11 low-contrast text, 12 high-contrast text.
- **Contrast:** ship **WCAG 2.2 AA** — 4.5:1 text, 3:1 large/UI (WebAIM checker). **APCA** (perceptual, directional, size/weight-aware; Lc 90 body / 75 min / 60 / 45 headlines / 30 floor) is better for dark mode but **not yet a conformance target** — design with it, certify with 2.x.
- **Gradients:** interpolate in OKLCH (`linear-gradient(in oklch, blue, yellow)`) for clean midpoints; hue methods `shorter`/`longer`/`increasing`/`decreasing` (`longer hue` for rainbows). Add noise/dithering to kill banding.
- **Tools:** Coolors (ideation), Adobe Color (wheel + contrast/colorblind), **Realtime Colors** (preview on a real layout), Huemint (AI, context-aware), Tailwind (OKLCH ramps), Radix Colors (12-step), Open Color, Leonardo (contrast-target ramps), uicolors.app (hex → 50–950).
- **Recipes:** muted = low chroma (.03–.08); monochrome + 1 saturated accent; **60-30-10**; dark mode needs accents **desaturated ~10–15%** (full saturation vibrates on dark).

---

## §8. Layout & Composition

- **Mental model:** **Flexbox = 1D content-out** (navs, toolbars, card internals, wrapping); **Grid = 2D layout-in** (page templates, dashboards, bento); **Subgrid** (Baseline Mar 2026) inherits parent track lines → align card internals across siblings.
- **Grid setup:** 12-col `repeat(12,1fr)` + gap + spans; `grid-template-areas` for app shells (each area must be rectangular, redefine per breakpoint); baseline grid via disciplined spacing multiples.
- **Intrinsic sizing:** `min-content`/`max-content`/`fit-content(x)`/`minmax(min,max)`. The no-media-query responsive grid: `grid-template-columns: repeat(auto-fit, minmax(250px, 1fr))` (auto-fit collapses empty tracks; auto-fill keeps them).
- **Container queries** (Baseline 2023): `container-type:inline-size` + `@container (min-width:400px)` → component adapts to *its container*, not viewport → truly portable components. Units `cqw/cqi/cqmin`. Style queries newer.
- **Viewport units** (Baseline 2025): **`svh`** for hero/full-screen (smallest, no clip on first paint), `lvh` (largest), `dvh` (live, can reflow during scroll — use for overlays).
- **Spacing:** **8-point grid** (multiples of 8; viewport widths divide cleanly) with 4pt sub-unit for tight gaps; named scale tokens; `aspect-ratio:16/9` reserves proportion (prevents CLS).
- **Whitespace** — the #1 premium signal. Macro (between sections → airy/structured) + micro (line-height, padding → legibility). Start with too much, then remove.
- **Hierarchy:** size, weight, color, position, contrast → one dominant focal point; one accent = the CTA.
- **Composition:** rule of thirds (focal points), golden ratio (proportions), **F-pattern** (text-dense — top + left), **Z-pattern** (sparse/landing — logo TL, CTA TR then BR).
- **Gestalt → UI:** proximity (group by spacing — cheapest tool), similarity (consistent button styles), closure (skeletons, peeking carousel card), continuity (aligned fields guide scan), figure/ground (modal + scrim), common region (cards/sections — stronger than proximity), focal point (the one accent CTA).
- **Asymmetry / broken grid** — intentional imbalance balanced by visual weight; energy + editorial feel; not random.
- **Page structure:** above-the-fold communicates value + primary CTA; hero sized `min-height:100svh` (often less); reserve media with `aspect-ratio`.

---

## §9. Design Systems & Component Libraries

- **shadcn/ui** — copy-paste **source into your codebase** (not an npm dep) via CLI + registry; headless primitive (Radix *or* Base UI) + Tailwind + CSS-variable theme tokens; `cva` variants, `cn()` merge. You own the code → unlimited customization, no version lock, no bloat. The current greenfield default. Tradeoff: you maintain copied code (re-pull for fixes); it's a starting point, not a finished system.
- **Radix UI** — Primitives (unstyled, accessible, the WAI-ARIA reference) vs Themes (pre-styled). Huge adoption but **dev slowed post-WorkOS** (why Base UI rose).
- **Base UI** — unstyled accessible primitives by the **MUI team**, Radix-like API, **v1 Dec 2025**. Actively developed, smaller bundle — strong new default headless layer; shadcn supports it.
- **Tailwind v4** — utility-first, zero-runtime. CSS-first config (`@import "tailwindcss"; @theme {}`), Oxide (Rust) engine (~5×/100×+ faster), native CSS vars, OKLCH, container queries built in. Migration from v3 is breaking.
- **Headless UI** (Tailwind team) — small set of accessible interactive primitives (Menu, Combobox, Dialog, Tabs) for React/Vue.
- **Animated kits** (pair with shadcn, marketing pages): **Aceternity UI** (most wow, most overused), **Magic UI** (landing blocks), **Motion Primitives**, **Cult UI** (AI-app patterns), **HextaUI**. Tradeoff: heavier (Motion/WebGL), sameness, check reduced-motion.
- **Batteries-included** (enterprise/data-heavy, fast teams, no designer): **MUI** (+ MUI X DataGrid/charts), **Ant Design** (richest free data components), **Mantine** (DX champion, 120+ components + hooks — great SaaS default), **Chakra** (style-props, now Ark/Panda-based).
- **Emil Kowalski trio** (best-in-class, win on feel + a11y): **Vaul** (drawer/bottom-sheet physics), **Sonner** (toast — imperative `toast()`, promise states), **cmdk** (⌘K command palette).
- **Others:** Origin UI (Tailwind blocks), **Ark UI** (headless, state-machine/Zag.js, multi-framework), **Park UI** (styled Ark for Panda/Tailwind), **Panda CSS** (typed zero-runtime CSS-in-JS), **Tremor** (dashboards/charts).
- **Storybook 9** — component workshop now testing-centric: interaction tests (Vitest), a11y tests (axe), visual regression, Testing Widget.
- **Design tokens:** **W3C DTCG spec v2025.10** (vendor-neutral JSON). Three tiers: primitive → **semantic (carries brand + enables theming)** → component. **Style Dictionary v4** transforms tokens → CSS vars/SCSS/JS/iOS/Android. Flow: Figma variables → DTCG JSON → Style Dictionary → CSS vars → Tailwind `@theme` / shadcn theme.

**Default 2026 stack:** Next/Vite + Tailwind v4 + shadcn (Base UI or Radix) + Sonner/Vaul/cmdk + Storybook 9; DTCG → Style Dictionary if a design team exists. Marketing: + Aceternity/Magic UI (watch perf). Enterprise/data: Ant Design or MUI+MUI X or Mantine. Dashboard: Tremor. Cross-framework: Ark/Park UI.

---

## §10. Design & Prototyping Tools

- **Figma** — industry standard. Auto Layout, Variants, **Variables + modes** (design tokens with theme switching), Dev Mode (IDE-like). Config 2025 expansion: **Figma Make** (prompt→app/code), **Figma Sites** (publish live sites), **Figma Slides**, **First Draft / Figma AI** (in-canvas generate), Grid layout (clean CSS Grid/Flex output). End-to-end idea→production pipeline.
- **Framer** — publishes real animated production sites; native React, code components, Workshop (AI components). Fast/visual marketing sites.
- **Webflow** — strongest CMS + interactions + scalability; Code Components; award winners use it as a shell + layer WebGL/Rive on top.
- **Spline** — no-code 3D + AI prompt-to-scene; exports React/glTF/USDZ; the on-ramp to 3D-on-web.
- **Penpot** — open-source Figma alt on web standards (SVG/CSS); picked for cost, data ownership/self-hosting, git-versionable designs.
- **Rive** — interactive animation; **State Machines** + tiny `.riv`; replacing Lottie for interactive motion. **After Effects → Lottie** (LottieFiles added its own state machines + AI).
- **Protopie/Principle** — hi-fi interaction prototyping (Protopie the survivor). **Origami Studio** (Meta) — node-based, advanced. **Sketch** — eclipsed. **Adobe XD** — deprecated/EOL.
- **AI design→code (2025):** **v0** (UI + best image-to-code, shadcn+Tailwind), **Lovable** (full-stack MVP + Supabase), **Bolt.new** (in-browser WebContainers), **Cursor** (IDE-grade), + Figma Make. The handoff stage is collapsing.

---

## §11. Inspiration & Curation Sources

- **Awwwards** — SOTD/SOTM/SOTY, scored Design/Usability/Creativity/Content. The flashy maximalist end; cutting-edge interaction/WebGL reference (aspirational, not production-realistic).
- **Godly** — video-based showcases with animated thumbnails (captures *motion*, not static shots). Best Awwwards alternative for motion.
- **Mobbin** — largest UI/UX reference; **real app flows** (onboarding, paywalls, settings, edge cases). The research tool.
- **Dribbble/Behance** — aspirational concept shots (much is non-functional design fiction). Behance = fuller case studies.
- **Land-book / SaaS Landing Page / Lapa Ninja** — landing/marketing structure. **Refero** — real product screenshots; **Page Flows / UI Sources** — recorded flows.
- **Httpster / siteInspire (clean/editorial) / Minimal Gallery / The FWA (experimental)** — curated showcases. **CodePen** — runnable technique demos. **Cosmos / Savee / Are.na** — mood-board curation. **Typewolf** — typography in the wild / pairings.
- **Studios + their technique:** Active Theory (immersive WebGL/installations), Resn (playful surreal WebGL), Locomotive (smooth-scroll, polished scroll sites), Obys (bold editorial type + motion), Cuberto (fluid cursor/gooey), Unseen Studio (refined motion+type), Aristide Benoist (WebGL/shaders), **Codrops** (the tutorial engine of the scene).

**What's actually winning now (live):** SOTY 2025 = Lando Norris site by **OFF+BRAND** — the representative stack: **Webflow shell + WebGL 3D + Rive motion + scroll-driven cinematic transitions + Lenis**. Trend toward **faux-3D** (image sequences / shader tricks) to dodge WebGL perf cost. Motion *is* the product on award sites.

---

## §12. Learning Resources

- **Codrops (tympanus)** — *the* advanced animation/WebGL tutorial source; read the last 10 posts to see what's hot.
- **The Book of Shaders** — GLSL fragment shaders (shapes, noise, patterns). **Three.js Journey** (Bruno Simon) — definitive WebGL course (+ R3F, Blender). **Awwwards Academy / SuperHi** — creative-dev courses.
- **Refactoring UI** (Wathan + Schoger) — **the most important practical UI book.** "Design with tactics, not talent." Core: start with too much whitespace then remove; hierarchy via size/weight/**color** (de-emphasize with lighter gray, not just bigger primary); don't use gray text on colored bg (tint it); define a constrained system upfront (spacing scale + type scale + full palette incl. ~10 shades, avoid pure black); few font weights; line length 45–75ch; depth via soft layered shadows; **work in grayscale first**; supercharge empty states; design with real content.
- **Laws of UX:** Hick's (more choices = slower), Fitts's (big + near targets), Jakob's (match conventions), Miller's (~7±2 chunks), **Aesthetic-Usability** (pretty = perceived usable), **Peak-End**, **Doherty (<400ms response)**, Gestalt laws, Tesler's (irreducible complexity), Postel's, Serial Position, Von Restorff, Zeigarnik, Goal-Gradient.
- **NN/g 10 Usability Heuristics:** system status visibility, match real world, user control/freedom, consistency/standards, error prevention, recognition over recall, flexibility/shortcuts, aesthetic/minimalist, error recovery, help/docs.
- **Material Design / Apple HIG** — platform ground truth. **Josh Comeau** — intuitive CSS/animation mental models (Whimsical Animations). **Emil Kowalski "Animations on the Web"** — *the* motion-craft course (why an animation feels right; easing, timing, when *not* to animate, a11y). **Hover.dev** — copy-paste animated components. **12 Principles of Animation** — the motion backbone.

---

## §13. Performance & Accessibility

**Rendering pipeline:** Style → Layout → Paint → Composite. The property you animate decides how far back the browser rewinds each frame:

| Type | Examples | Cost |
|---|---|---|
| Composite-only | `transform`, `opacity` | **Cheap** (GPU reuses texture) |
| Layout (reflow) | `width/height/top/left/margin/font-size` | **Expensive** (recompute geometry → repaint) |
| Paint | `color/background/box-shadow/border-radius` | Moderate (re-raster) |

- **Frame budget:** 16.67ms @60Hz (~10ms yours), 8.33ms @120Hz. Consistent frames > peak FPS.
- **Layout thrashing:** reading geometry (`offsetWidth`, `getBoundingClientRect`) after a write forces sync reflow. **Batch reads, then writes**; schedule visual writes in `requestAnimationFrame`.
- **Layers:** `will-change:transform` (or legacy `translateZ(0)`) promotes to a GPU layer — but layers cost memory; promote *only* frequently-animated elements, set `will-change` just before and remove after. Don't blanket it.
- **Threading:** main thread (JS/Style/Layout/Paint) vs compositor thread (scroll, compositor animations). **CSS/WAAPI animations of transform/opacity run off main thread** — stay smooth under JS load. Biggest reason to prefer them over JS rAF tweening.
- **Loading:** native `loading="lazy"` (never the LCP image — eager + `fetchpriority="high"`), code splitting + dynamic import + tree-shaking, rAF-throttle scroll/resize/mousemove + `{passive:true}`, AVIF→WebP with `srcset`/`sizes` + `width`/`height`, fonts `font-display:optional` (no mid-session swap) + preload + subset + metric-matched fallback, CDN/Brotli, `content-visibility:auto` for offscreen sections.
- **Core Web Vitals (p75 field):** **LCP ≤ 2.5s** (preload/eager the LCP resource, fast TTFB, no render-blocking), **CLS ≤ 0.1** (size media, reserve ad/embed space, animate only transform/opacity, `font-display:optional`), **INP ≤ 200ms** (most-failed — break long tasks >50ms, `await scheduler.yield()` (Chrome/FF, fallback `setTimeout`), yield after the visible update, avoid thrashing, shrink DOM, compositor animations). Tools: Lighthouse/PSI (lab), **CrUX/RUM** (field — decide on these).

**Accessibility (target WCAG 2.2 AA):**
- **`prefers-reduced-motion`** — opt INTO motion (ship static, add motion in `@media (prefers-reduced-motion: no-preference)`); JS gate via `matchMedia(...).addEventListener('change',...)`. Reduce (don't blanket-disable): remove parallax/scroll-jack/spin/big slides, keep opacity fades. (WCAG 2.3.3.)
- **WCAG 2.2** adds 9 criteria — notably **Target Size ≥ 24×24px (2.5.8)**, **Focus Not Obscured (2.4.11)**, **Dragging Movements have a single-pointer alternative (2.5.7)**, **Accessible Authentication (3.3.8 — allow paste/password managers)**. WCAG 3.0 is far off; **APCA not yet a conformance target**.
- **Semantic HTML first:** native `<button>`/`<a href>`/`<nav>`/`<dialog>` over ARIA (first rule of ARIA: don't use ARIA if HTML does it). Landmarks, logical non-skipping headings (one `h1`), accessible names on every interactive element (icon buttons need `aria-label`).
- **Focus/keyboard:** never bare `outline:none`; use `:focus-visible` with a thick high-contrast ring; logical tab order (no positive `tabindex`); modals → move focus in, **trap**, `Esc` closes, restore on close (prefer native `<dialog>`+`showModal()`); skip link first.
- **Color:** text ≥4.5:1 (3:1 large), UI/icons/focus ≥3:1; never color alone.
- **Screen readers:** correct `alt` (`alt=""` for decorative), `aria-live="polite"`/`role="status"` (or `assertive`/`alert`) for async updates; **canvas/WebGL is inaccessible** → provide DOM/table/text alternative.
- **Motion-specific:** auto-motion >5s needs pause/stop/hide (2.2.2); **never flash >3×/sec** (seizure risk, 2.3.1/2.3.2); gate parallax/scroll-jack.

---

## §14. Master decision logic

| Goal | Reach for |
|---|---|
| Scroll storytelling / pin / scrub / parallax | GSAP ScrollTrigger (+ Lenis, + ScrollSmoother) |
| SVG morph / draw / motion path / text split | GSAP (MorphSVG/DrawSVG/MotionPath/SplitText) |
| React component anim, gestures, enter/exit, layout/shared-element | Motion |
| Smallest WAAPI tween | Motion mini (~2.3KB) |
| Free lightweight general timeline | Anime.js v4 |
| Designer-authored decorative motion | Lottie / dotLottie |
| Interactive, stateful, data-bound graphics | Rive |
| Effortless list/accordion motion | Auto-Animate |
| Bespoke 3D, max ecosystem | Three.js (WebGPURenderer + TSL, WebGL2 fallback) |
| 3D in React | R3F + Drei |
| Game / physics / editor | Babylon.js 8 |
| High-perf 2D at scale | PixiJS v8 |
| No-code 3D hero | Spline (lazy-load) |
| DOM image hover/scroll distortion | gpu-curtains (WebGPU) / OGL |
| Smooth scroll | Lenis (wired to gsap.ticker) |
| Page transitions | View Transitions API (Barba/Swup for bespoke) |
| Layout/shared-element morph | FLIP / GSAP Flip / View Transitions |
| Component library (greenfield) | shadcn (Base UI or Radix) + Tailwind v4 |
| Enterprise/data-heavy | Ant Design / MUI+MUI X / Mantine |
| Dashboard/charts | Tremor |
| Drawer / toast / command palette | Vaul / Sonner / cmdk |
| One-shot reveal | IntersectionObserver + CSS class (no lib) |

---

## §15. Expensive vs. cheap (the cross-cutting truth)

**Reads as expensive:** Swiss-grid restraint; generous *active* whitespace; a distinctive non-default typeface with hard scale contrast; a whisper of grain; perceptual (OKLCH/LCH) dark themes with elevation-by-lightness; one disciplined low-saturation accent; real grid/baseline discipline; purposeful, sparse motion; refraction/liquid as a single earned moment.

**Reads as cheap (AI-slop tells):** pure `#000` + low-contrast grey text; default Inter/Playfair/Roboto with no scale; glassmorphism on everything; the purple→blue gradient + frosted card combo; uniform-size bento boxes; two-stop "mesh" gradients; neon glow as one blurry shadow; constant glitch/warp; neumorphism; visible tiled-PNG noise.

**Always-elevates techniques (any aesthetic):** (1) grain via SVG `feTurbulence` at low opacity; (2) generous active whitespace; (3) restraint — one accent, one hero moment, one technique done correctly; (4) a typeface with a point of view; (5) perceptual color + a real token system; (6) **execute the system, not the surface** — a real grid, a real light source, a real type scale, a real color system.

**The two worlds — know which you're building for:**
- **Awards/portfolio:** maximal WebGL, kinetic type, scroll choreography, custom cursors. Motion is the product. Accept the perf/a11y cost.
- **Production/business:** bento grids, restraint, real content, performance, accessibility, sub-400ms responsiveness. The flashy trends often *don't ship* here.

---

## §16. Pre-ship gates (a beautiful site isn't done until it passes these)

**Performance (field p75):** LCP ≤2.5s, CLS ≤0.1, INP ≤200ms (CrUX/RUM); animate only transform/opacity; reads batched before writes; scroll/resize rAF-throttled + passive; no long tasks >50ms (split with `scheduler.yield`); `will-change` sparing; LCP image eager + `fetchpriority`; below-fold `loading="lazy"`; AVIF/WebP + dimensions; fonts preload+subset+`font-display:optional`; heavy animation compositor/WAAPI-driven.

**Accessibility (WCAG 2.2 AA):** `prefers-reduced-motion` in CSS *and* JS (opt-in to motion); no flashing >3×/sec; auto-motion >5s has pause/stop/hide; semantic HTML + landmarks + heading order; visible `:focus-visible` everywhere (no bare `outline:none`); modals trap + `Esc` + restore (native `<dialog>`); targets ≥24×24px; drag has tap alternative; contrast text ≥4.5:1, UI ≥3:1, never color-alone; correct `alt` + `aria-live`; canvas/WebGL has a DOM alternative; tested keyboard-only + screen reader + automated scan.

---

## How to use this knowledge

Foundations first (Refactoring UI, type scale, OKLCH color, whitespace, Gestalt, UX laws) — they make *everything* better. Then layer the flashy tools (GSAP, Three.js, shadcn) only after the system underneath is sound. Use §3's named aesthetics as search vocabulary, §11's galleries to reverse-engineer the masters, §15 as the taste filter, and §16 as the non-negotiable gate. Always decide which of the two worlds (§15) you're building for before you start.
