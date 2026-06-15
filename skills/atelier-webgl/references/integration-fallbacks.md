# Integration, faux-3D, fallbacks & the honest cost

## The honest cost of WebGL heroes (read before committing)
- **Perf:** big engine (Three core ~150KB+ gzip; Babylon/Spline more) + multi-MB assets/HDRIs + shader
  compile + a continuous rAF loop → hurts **LCP** (large blocking payload), **INP** (main-thread parse/
  compile + per-frame work), and battery/thermals on mobile. Spline scenes are especially LCP-hostile.
- **Accessibility:** canvas is **opaque to assistive tech** — not focusable, not screen-reader-readable;
  WebGL text fails zoom/contrast/selection; animation can trigger vestibular issues.
- **Verdict:** worth it when the experience *is* the product (portfolio/agency/product showcase/launch),
  engineered with fallbacks. A net negative as decorative background on content/conversion sites — use a
  grainy CSS/SVG gradient (atelier-foundations) or faux-3D instead.

## Faux-3D (the look without the cost) — try this first
- **Image sequence on scroll** — pre-render a 3D turntable to ~60–120 frames; swap on scroll (canvas 2D or
  `<img>`). Codrops-style "3D without a 3D model." Cheap, no WebGL runtime, easy fallback (a single frame).
- **CSS 3D transforms** — `perspective` + `rotateX/Y` + `translateZ` for parallax depth and card tilt.
- **Single fullscreen fragment shader** (OGL, ~tens of KB) — a mesh-gradient / noise / dither hero with no
  scene graph. Far lighter than a full Three scene.
Prefer these unless real geometry/interaction (orbit a product, configurator) is genuinely required.

## Spline (no-code 3D)
```tsx
import dynamic from "next/dynamic";
const Spline = dynamic(() => import("@splinetool/react-spline"), { ssr: false, loading: () => <Poster/> });
<Spline scene="https://prod.spline.design/XXX/scene.splinecode" />
```
Fast for designers; **heavy multi-MB payload** → lazy-load (dynamic import, below fold), self-host the
`.splinecode` (dodge CORS + control caching), show a poster while loading. Query objects via
`findObjectByName`. Export glTF if you outgrow the runtime.

## DOM image hover / scroll distortion
Turn real `<img>`/`<video>` into shader-distortable WebGL planes (ripple/liquid/bulge on hover, warp on
scroll). Tools: **OGL** (tiny), **gpu-curtains** (WebGPU; curtains.js is legacy WebGL), driven by
GSAP-tweened uniforms (e.g. a decaying flowmap of cursor velocity). Lives at the border with
`atelier-scroll`. Always: lazy-init, keep a plain `<img>` with real `alt` underneath (SEO / no-WebGL /
reduced motion), and skip entirely under `prefers-reduced-motion`. **Generate that source `<img>` (and any
matcap / displacement texture) on the Direction Doc's aesthetic via `/codex-imagegen`** — e.g.
`codex-image.ps1 -Prompt "…" -OutDir ".\public\tex" -Size 1024x1024` — rather than stock-grabbing; the same
file doubles as the no-WebGL / reduced-motion poster.

## Lazy-load + pause + fallback pattern (non-negotiable)
```tsx
// 1. Lazy-load the whole 3D bundle so it never blocks first paint
const Hero3D = dynamic(() => import("./Hero3D"), { ssr: false, loading: () => <HeroPoster /> });

// 2. Only mount when near viewport (IntersectionObserver), pause when offscreen/tab hidden
// 3. Respect reduced motion + no-WebGL → render the poster instead
function Hero() {
  const reduce = useReducedMotion();
  const webgl = useMemo(() => !!document.createElement("canvas").getContext("webgl2"), []);
  if (reduce || !webgl) return <HeroPoster />;   // static image fallback
  return <Hero3D />;
}
```
Inside the scene: `frameloop="demand"` or pause the loop via IntersectionObserver + `document.hidden`;
clamp `dpr={[1,2]}`; compress assets (DRACO/Meshopt/KTX2); dispose on unmount.

## Accessibility (mandatory)
- **Never put essential content or navigation only in the canvas.** Provide the real content as DOM
  (headline, copy, links) layered over or beside the canvas, and a `<canvas>…fallback DOM…</canvas>` /
  adjacent text or table for anything the visualization conveys.
- Keyboard users can't tab into a canvas — keep all controls as real focusable DOM.
- Honor `prefers-reduced-motion` (static poster) and provide a pause control if motion runs > 5s.

## The gate
Run `atelier-perf-a11y` — this layer is where LCP/INP and accessibility most often fail. Confirm: lazy-
loaded, paused offscreen, DPR ≤ 2, assets compressed, static poster + DOM alternative present, reduced-
motion respected, CWV still green at p75.
