# Lenis + GSAP ScrollTrigger recipes

**GSAP is now 100% free, including every formerly-paid Club plugin** (ScrollTrigger, ScrollSmoother,
SplitText, Flip, MorphSVG, DrawSVG, MotionPath, Inertia, Observer, GSDevTools, …) after Webflow's
acquisition — install them all from the public `gsap` npm package. Never emit an auth-token `.npmrc`, the
private `npm.greensock.com` registry, or a "sign up for Club GSAP" step (that advice is outdated). Import
each plugin from `gsap/<Plugin>` and `gsap.registerPlugin(...)` once. Lenis is the smooth-scroll standard.

## Lenis setup wired to GSAP (memorize this)
```js
import Lenis from "lenis";                 // npm i lenis  (v1.3.x; + import 'lenis/dist/lenis.css')
// legacy @studio-freight/lenis is deprecated, frozen at 1.0.42 — migrate to bare `lenis` / `lenis/react`
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
gsap.registerPlugin(ScrollTrigger);

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
let lenis;
if (!reduce) {
  lenis = new Lenis({ lerp: 0.1 });                 // or { duration: 1.2, easing }
  lenis.on("scroll", ScrollTrigger.update);
  const raf = (t) => lenis.raf(t * 1000);           // capture so it's removable
  gsap.ticker.add(raf);                             // GSAP ticker drives Lenis; *1000 s→ms
  gsap.ticker.lagSmoothing(0);
}
// Teardown (SPA route change / HMR — else a second ticker callback leaks on re-init):
//   gsap.ticker.remove(raf); lenis?.destroy();
```
**React** — `autoRaf:false` disables Lenis's own loop, so you MUST drive `raf` from the ticker and
**remove it on cleanup** (the verified `lenis/react` pattern):
```jsx
import { ReactLenis } from "lenis/react";  // + import 'lenis/dist/lenis.css'
import { gsap } from "gsap";
import { useEffect, useRef } from "react";

function SmoothScroll({ children }) {
  const lenisRef = useRef(null);
  useEffect(() => {
    function update(time) { lenisRef.current?.lenis?.raf(time * 1000); }
    gsap.ticker.add(update);
    gsap.ticker.lagSmoothing(0);
    return () => gsap.ticker.remove(update);        // cleanup — no leaked loop
  }, []);
  return <ReactLenis root options={{ autoRaf: false }} ref={lenisRef}>{children}</ReactLenis>;
}
```
Key options: `lerp` (0–1, ~0.1) **or** `duration`+`easing` (pick one feel); `smoothWheel`, `syncTouch`.

**Alternative — GSAP ScrollSmoother** (free since GSAP went fully free): GSAP's own smooth-scroll, tightly
integrated with ScrollTrigger (no ticker wiring) with built-in `data-speed`/`data-lag` parallax —
`ScrollSmoother.create({ smooth: 1.2, effects: true })`, needs a `#smooth-wrapper > #smooth-content` shell.
Pick **one** engine: Lenis (lighter, framework-agnostic, the suite default) *or* ScrollSmoother (zero wiring
if you're already all-in on GSAP) — never both.

## Reveals
One-shot (lightest — no lib): IntersectionObserver toggles a class, CSS does the transition.
```js
const io = new IntersectionObserver((es) => es.forEach(e => {
  if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); }
}), { threshold: 0.15, rootMargin: "0px 0px -10%" });
document.querySelectorAll("[data-reveal]").forEach(el => io.observe(el));
/* CSS: [data-reveal]{opacity:0;transform:translateY(16px);transition:.6s cubic-bezier(.16,1,.3,1)}
        [data-reveal].in{opacity:1;transform:none} */
```
Progress-tied reveal (GSAP):
```js
gsap.from(".card", { y: 40, opacity: 0, duration: .8, ease: "power3.out", stagger: .08,
  scrollTrigger: { trigger: ".cards", start: "top 80%" } });
```
Many elements (one shared observer, not one trigger each) → `ScrollTrigger.batch()`:
```js
ScrollTrigger.batch(".card", { start: "top 85%",
  onEnter: (els) => gsap.from(els, { y: 40, opacity: 0, duration: .8, ease: "power3.out", stagger: .08 }) });
```

## Scrub (progress tied to scroll, reversible)
```js
gsap.to(".bar", { scaleX: 1, ease: "none",
  scrollTrigger: { trigger: ".section", start: "top top", end: "bottom top", scrub: true } });
// scrub: 0.5  → adds smoothing lag (buttery with Lenis)
```

## Pin — sticky first
```css
.panel { position: sticky; top: 0; }   /* cheap, accessible — breaks under ancestor overflow/transform */
```
ScrollTrigger pin only when sticky can't express it (independent duration / scrubbed timeline):
```js
gsap.timeline({ scrollTrigger: { trigger: ".stage", start: "top top", end: "+=1200",
  pin: true, scrub: true, anticipatePin: 1 } })
  .from(".stage h2", { yPercent: 30, opacity: 0 })
  .to(".stage .art", { scale: 1.1 }, "<");
```

## Horizontal section (vertical scroll drives X)
```js
const track = document.querySelector(".track");
gsap.to(track, {
  x: () => -(track.scrollWidth - innerWidth), ease: "none",
  scrollTrigger: { trigger: ".track-wrap", pin: true, scrub: true,
    end: () => "+=" + (track.scrollWidth - innerWidth), invalidateOnRefresh: true },
});
```
Provide arrows/keyboard affordance; users can otherwise get stuck.

## Sticky-stacking cards
Each card `position: sticky; top: 0` with increasing top offset, scaling/fading the outgoing one on a
scrubbed timeline; or native `view()` (next file) for the scale-on-leave with zero JS.

## Parallax
```js
gsap.utils.toArray("[data-speed]").forEach((el) => {
  gsap.to(el, { yPercent: (i, t) => -100 * (parseFloat(t.dataset.speed) - 1), ease: "none",
    scrollTrigger: { trigger: el, scrub: true } });
});
```
Keep displacement subtle; it's a top vestibular trigger.

## Responsive triggers — gsap.matchMedia()
Triggers set up at one width break at another. **`gsap.matchMedia()`** scopes setup to a media query and
auto-reverts when it stops matching (the modern replacement for deprecated `ScrollTrigger.matchMedia()`):
```js
const mm = gsap.matchMedia();
mm.add("(min-width: 768px)", () => {
  // desktop-only pin/scrub; auto-cleaned when the query stops matching
  gsap.to(".track", { x: () => -(track.scrollWidth - innerWidth), ease: "none",
    scrollTrigger: { trigger: ".track-wrap", pin: true, scrub: true, invalidateOnRefresh: true } });
});
mm.add("(prefers-reduced-motion: reduce)", () => { /* static fallbacks only */ });
// mm.revert() on teardown
```

## SSR / hydration (Next App Router, Astro islands)
ScrollTrigger and Lenis touch `window` — they must run client-side, after paint, against the *settled* layout:
- **`"use client"`** on any component that creates GSAP/Lenis/ScrollTrigger; never import them at module
  top-level in a Server Component.
- **Create inside `useGSAP`/`useEffect`** (post-mount). SSR markup has no triggers, so render content
  **visible by default and *enhance*** — never `opacity:0` in SSR CSS, or no-JS / pre-hydration users get a
  blank page (and LCP tanks). Add the hidden-until-revealed class from JS.
- **`ScrollTrigger.refresh()` after late layout shifts** — fonts swapping, images decoding, and lazy content
  move elements *after* triggers are computed, desyncing every `start/end`. Call `refresh()` on
  `document.fonts.ready` and after below-fold images load (or set their `width`/`height` so they don't shift —
  the `atelier-perf-a11y` rule). Re-`refresh()` on route change.

## Cleanup & refresh
- `ScrollTrigger.refresh()` after async content/layout changes; `invalidateOnRefresh: true` on
  width-dependent setups.
- React: create in `useGSAP(() => {...}, { scope })` (`@gsap/react`) so triggers auto-revert on unmount.
- Reduced motion: guard *all* of the above behind `if (!reduce)`; ship the static layout otherwise.

## ScrollTrigger discipline (do-not — the usual jank/desync bugs)
A short hardening checklist; most "scroll feels broken" reports are one of these:
- Put the ScrollTrigger on the **timeline or a top-level tween — never a child tween** of a timeline.
- **Never combine `scrub` with `toggleActions`** — scrub wins and `toggleActions` silently does nothing.
- On a **`containerAnimation`** (elements triggered as a horizontal/looping tween scrolls) the *driving*
  tween must be **`ease: "none"`**, or every child start/end drifts.
- Create triggers **top-to-bottom in DOM order**, or set **`refreshPriority`** so refresh order is correct.
- Call **`ScrollTrigger.refresh()`** after anything that changes layout *after* setup (font swap, image
  decode, async content) — better, fix the root cause (set image `width`/`height` so nothing shifts).
- A **non-Lenis / non-ScrollSmoother** smooth-scroll library needs **`ScrollTrigger.scrollerProxy()`** so
  ScrollTrigger reads its virtual scroll; Lenis (ticker-wired above) and ScrollSmoother do **not**.
