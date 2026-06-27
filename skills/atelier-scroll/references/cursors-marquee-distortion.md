# Magnetic buttons, custom cursors, marquee, hover distortion

All of these are **pointer-only enhancements** — they must never gate function (keyboard/touch users get
nothing) and must disable under `prefers-reduced-motion`.

## Magnetic button
Element drifts toward the cursor within its bounds, eases back on leave. Transform only; small magnitude
(4–12px) so it doesn't cause mis-clicks.
```js
import { gsap } from "gsap";
const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
document.querySelectorAll(".magnetic").forEach((el) => {
  if (reduce) return;
  const xTo = gsap.quickTo(el, "x", { duration: 0.4, ease: "power3" });
  const yTo = gsap.quickTo(el, "y", { duration: 0.4, ease: "power3" });
  el.addEventListener("pointermove", (e) => {
    const r = el.getBoundingClientRect();
    xTo((e.clientX - (r.left + r.width / 2)) * 0.3);
    yTo((e.clientY - (r.top + r.height / 2)) * 0.3);
  });
  el.addEventListener("pointerleave", () => { xTo(0); yTo(0); });
});
```
Already on Motion? **Motion+ `Cursor`** (magnetic / zoning / morph-to-target follower) ships this off the
shelf — buy-vs-build it instead of hand-rolling.

## Custom cursor (lerped follower)
Hide the native cursor, render a follower that lags toward the pointer; grow/label on interactive hover.
**Keep visible focus states for keyboard users; never remove the cursor for them.**
```js
const dot = document.querySelector(".cursor");
let mx = 0, my = 0, x = 0, y = 0, rafId = 0;
addEventListener("pointermove", (e) => { mx = e.clientX; my = e.clientY; }, { passive: true });
function loop() {
  x += (mx - x) * 0.15; y += (my - y) * 0.15;
  dot.style.transform = `translate3d(${x}px, ${y}px, 0)`;   // transform ONLY → compositor-safe; this is the
  rafId = requestAnimationFrame(loop);                       // allowed exception to "no JS-rAF of layout props"
}
if (matchMedia("(pointer: fine)").matches && !matchMedia("(prefers-reduced-motion: reduce)").matches) {
  rafId = requestAnimationFrame(loop);
  document.addEventListener("visibilitychange", () => {       // don't burn frames in a hidden tab
    if (document.hidden) cancelAnimationFrame(rafId); else rafId = requestAnimationFrame(loop);
  });
}
// teardown (SPA route change / unmount): cancelAnimationFrame(rafId);
/* CSS: body { cursor: none } only when the custom cursor is active and pointer is fine */
```
Gate behind `(pointer: fine)` so touch devices keep the native behavior.

## Infinite marquee
CSS-only, seamless (duplicate the content once so a -50% translate wraps cleanly), pausable:
```css
@media (prefers-reduced-motion: no-preference) {
  .marquee { display: flex; gap: 3rem; width: max-content; animation: marquee 24s linear infinite; }
  .marquee:hover { animation-play-state: paused; }
}
@keyframes marquee { to { transform: translateX(-50%); } }
```
```html
<div class="overflow-hidden"><div class="marquee"><Logos/><Logos aria-hidden="true"/></div></div>
```
`aria-hidden` the duplicate so screen readers don't read it twice. GSAP version (for velocity tied to
scroll, drag, variable-width items): `gsap.to(track, { xPercent: -50, repeat: -1, duration, ease: "none" })`
and modulate `timeScale` by scroll velocity. Or **Motion+ `Ticker`** — an infinite marquee that fixes the
CSS-marquee seam/gotchas (drag, velocity coupling) if you're already on Motion.
Auto-motion running >5s must be pausable (WCAG 2.2.2) — hover-pause only covers pointer users, so also
provide a keyboard/touch-reachable pause control (or stop entirely under reduced motion).

## WebGL hover / image distortion → atelier-webgl
Shader-based ripple/liquid/bulge distortion on images (flowmap, displacement) lives in **`atelier-webgl`**
(OGL / gpu-curtains + GSAP-driven uniforms). Always lazy-init, provide a plain `<img>` fallback (SEO /
no-WebGL / reduced motion), and keep `alt` on the underlying DOM.

## Reduced-motion summary
Disable magnetic + custom cursor (restore native), pause marquees, and skip any distortion. None of these
carry information, so removing them loses nothing — that's the test for a pure enhancement.
