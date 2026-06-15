# Performance — pipeline, animation, loading, Core Web Vitals

## The rendering pipeline
**Style → Layout → Paint → Composite.** The property you animate decides how far back the browser must
rewind each frame. Frame budget: 16.67ms @60Hz (~10ms yours), 8.33ms @120Hz. Consistent frames beat peak FPS.

| Property type | Examples | Triggers | Cost |
|---|---|---|---|
| Composite-only | `transform`, `opacity` | Composite | **Cheap** — GPU transforms an existing texture |
| Layout (reflow) | `width/height/top/left/margin/padding/font-size` | Layout→Paint→Composite | **Expensive** |
| Paint | `color/background/box-shadow/border-radius/outline` | Paint→Composite | Moderate (box-shadow/blur heavy) |

**Rule:** move with `transform: translate()` (not top/left), resize with `scale()` (not width/height),
fade with `opacity` (not visibility/display).

## Layout thrashing (forced synchronous reflow)
Reading geometry (`offsetWidth/Height/Top`, `getBoundingClientRect`, `scrollTop`, `getComputedStyle`)
*after* a write forces a synchronous layout. Interleaving read→write in a loop is a top INP/jank killer.
**Batch reads, then writes:**
```js
const widths = els.map(el => el.offsetWidth);          // all reads
els.forEach((el, i) => el.style.width = widths[i] + 10 + "px"); // all writes
```
Schedule visual writes in `requestAnimationFrame`. rAF-throttle scroll/resize/mousemove; add
`{ passive: true }` to scroll/touch listeners.

## Compositing layers
`will-change: transform` (or legacy `transform: translateZ(0)`) promotes an element to its own GPU layer
so transform/opacity run on the compositor. **Layers cost GPU memory** — promote only frequently-animated
elements; set `will-change` just before the animation and remove it after (`el.style.willChange = "auto"`).
Never blanket hundreds of elements (cripples mobile).

## Threading
Main thread: JS, Style, Layout, Paint. Compositor thread: scrolling + compositor animations (survives a
busy main thread). **CSS/WAAPI/Motion animations of transform/opacity run off the main thread** — the
single biggest reason to prefer them over JS rAF tweening. (Animating a layout/paint property via WAAPI
does NOT get off-main-thread.)

## Loading performance
- **Lazy-load** below-fold media (`loading="lazy"`) + IntersectionObserver for triggering. **Never** lazy
  the LCP image — eager + `fetchpriority="high"`.
- **JS diet:** code splitting + dynamic `import()`; tree-shaking (ESM, `sideEffects:false`). Big initial
  bundles = long startup tasks = bad INP during load.
- **Images:** AVIF → WebP → fallback; `<picture>` + `srcset`/`sizes`; always set `width`/`height` (CLS).
- **Fonts:** `font-display: optional` (no mid-session swap, best CLS) or `swap` + metric-matched fallback
  (`size-adjust`/`ascent-override`); preload critical face; subset (`unicode-range`).
- **`content-visibility: auto`** (+ `contain-intrinsic-size`) on heavy offscreen sections — cuts load +
  interaction cost.
- **CDN** + HTTP/2-3 + Brotli + immutable caching; ensure BFCache eligibility.

## Core Web Vitals (p75 field; thresholds current mid-2026)
**LCP ≤ 2.5s** (needs-improvement ≤4s): preload/eager + `fetchpriority="high"` the LCP resource, fast
TTFB (CDN/SSR), inline critical CSS, kill render-blocking JS/CSS, modern image formats.

**CLS ≤ 0.1** (≤0.25): set media dimensions / `aspect-ratio`; reserve ad/embed/iframe space;
`font-display: optional` + metric-matched fallback; only animate transform/opacity; never inject content
above existing content; BFCache.

**INP ≤ 200ms** (≤500ms) — replaced FID Mar 2024, most-failed CWV:
- Three parts: input delay (main-thread long tasks), processing duration (your handler JS), presentation
  delay (rendering the result).
- **Break long tasks > 50ms.** `await scheduler.yield()` (Chrome/FF; feature-detect, fallback
  `await new Promise(r => setTimeout(r))`). `scheduler.postTask()` for prioritized work; `requestIdleCallback`
  for non-urgent.
- Yield right after the UI-critical update; defer saving/analytics. Avoid handler thrashing. Shrink DOM;
  `content-visibility: auto`. Prefer compositor animations so motion doesn't compete with input.

## Tooling
Lighthouse / PageSpeed Insights = lab (debug). CrUX = field (28-day real Chrome users; affects ranking).
RUM (`web-vitals` lib / PerformanceObserver) = ground truth per cohort. **Decide on field data, debug
with lab.**
