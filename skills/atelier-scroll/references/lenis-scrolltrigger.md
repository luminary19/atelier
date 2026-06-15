# Lenis + GSAP ScrollTrigger recipes

GSAP is fully free (incl. ScrollTrigger). Lenis is the smooth-scroll standard. Register plugins once:
`gsap.registerPlugin(ScrollTrigger)`.

## Lenis setup wired to GSAP (memorize this)
```js
import Lenis from "lenis";                 // npm i lenis  (+ import 'lenis/dist/lenis.css')
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

## Cleanup & refresh
- `ScrollTrigger.refresh()` after async content/layout changes; `invalidateOnRefresh: true` on
  width-dependent setups.
- React: create in `useGSAP(() => {...}, { scope })` (`@gsap/react`) so triggers auto-revert on unmount.
- Reduced motion: guard *all* of the above behind `if (!reduce)`; ship the static layout otherwise.
