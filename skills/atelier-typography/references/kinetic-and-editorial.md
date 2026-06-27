# Editorial detailing & kinetic type

## Editorial detailing (content / portfolio / magazine)
The print-craft details that make a page read art-directed instead of "blog template."

```css
/* Drop cap */
.article > p:first-of-type::first-letter {
  float: left; font-family: var(--font-display); font-size: 4.5em; line-height: 0.8;
  padding: 0.05em 0.1em 0 0; font-weight: 600;
}
/* Pull quote — distinct face, short measure, hairline rule */
.pullquote {
  font-family: var(--font-display); font-size: var(--text-xl); line-height: 1.2;
  max-width: 22ch; border-top: 1px solid var(--border); padding-top: var(--space-3);
  letter-spacing: -0.01em;
}
/* Kicker / eyebrow */
.kicker { font-size: var(--text-sm); letter-spacing: 0.08em; text-transform: uppercase; color: var(--text-muted); }
```
Plus: a strong measure column (60–75ch), side-column captions, intentional asymmetry around the
measure, and hard scale contrast (giant headline vs calm body). Avoid centered-everything and a single
default serif — those are the editorial slop tells.

## Kinetic type (AWARD / CREATIVE WORLD ONLY)
Use only when the Direction Doc's world + motion budget call for it. Type is the moving hero.

**Stack:** GSAP + ScrollTrigger + **SplitText** (now free) + **Lenis** (smooth scroll) + variable fonts.
Non-negotiables: animate `transform`/`opacity` only; mask line reveals with `overflow:hidden`; **always
ship a `prefers-reduced-motion` fallback** (kinetic type is a top a11y + SEO + screen-reader risk);
never on transactional/utility flows.

### Setup — Lenis wired to GSAP (so ScrollTrigger reads virtual scroll)
```js
import Lenis from "lenis";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { SplitText } from "gsap/SplitText";
gsap.registerPlugin(ScrollTrigger, SplitText);

const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;
let lenis;
if (!reduce) {
  lenis = new Lenis({ lerp: 0.1 });
  lenis.on("scroll", ScrollTrigger.update);
  gsap.ticker.add((t) => lenis.raf(t * 1000));
  gsap.ticker.lagSmoothing(0);
}
```

### Line reveal (masked stagger) — modern `SplitText.create()` API
SplitText was rewritten when GSAP went fully free; prefer `SplitText.create()` (built-in masking, a11y,
and responsive re-splitting) over the old `new SplitText()` constructor + a manual `overflow:hidden` wrapper.
```js
// Split only AFTER fonts load — otherwise lines re-flow and the split is wrong:
document.fonts.ready.then(() => {
  SplitText.create(".headline", {
    type: "lines",
    mask: "lines",        // wraps each line in an overflow-clip mask — no manual .line CSS needed
    aria: "auto",         // a11y: aria-label on the parent + aria-hidden on the split units
    autoSplit: true,      // re-split on resize / font swap…
    onSplit: (self) => {  // …and re-run the reveal each time (the returned tween → auto cleanup + time-sync)
      if (reduce) return; // reduced-motion: leave text visible, no animation
      return gsap.from(self.lines, {
        yPercent: 100, opacity: 0, duration: 0.9, ease: "power4.out", stagger: 0.06,
        scrollTrigger: { trigger: ".headline", start: "top 80%" },
      });
    },
  });
});
/* CSS: .headline { font-kerning: none; text-rendering: optimizeSpeed; }  ← avoids per-char kerning shift.
   Don't combine SplitText with `text-wrap: balance` — the re-wrap fights the split. */
```
`aria:"auto"` is the key a11y win: without it, splitting a headline into per-line/char spans makes a
screen reader read it letter-by-letter. The old `new SplitText(...)` constructor still works, but you own
masking, re-splitting on resize, and aria yourself — `create()` does all three.

### Horizontal scroll section (vertical drives horizontal)
```js
if (!reduce) gsap.to(".track", {
  x: () => -(document.querySelector(".track").scrollWidth - innerWidth),
  ease: "none",
  scrollTrigger: { trigger: ".track", pin: true, scrub: true, end: "+=2000", invalidateOnRefresh: true },
});
```

### Variable-font weight morph on scroll
```js
if (!reduce) gsap.to(".word", {
  "--wght": 800, ease: "none",
  scrollTrigger: { trigger: ".word", start: "top 80%", end: "top 30%", scrub: true },
});
/* CSS: .word { --wght:300; font-variation-settings:"wght" var(--wght); } */
```

### Infinite marquee (CSS-only, pausable)
```css
@media (prefers-reduced-motion: no-preference) {
  .marquee { display: flex; gap: 3rem; width: max-content; animation: scroll 22s linear infinite; }
  .marquee:hover { animation-play-state: paused; }
}
@keyframes scroll { to { transform: translateX(-50%); } }
/* duplicate the content once so the -50% wrap is seamless; aria-hidden the duplicate */
```

### Timing / easing defaults for type
Entrances ease-out (`power4.out` / `cubic-bezier(0.16,1,0.3,1)`); reveals 0.6–0.9s; per-line stagger
0.05–0.08s (total < 0.8s); never block reading. "Motion should be felt, not seen."

### The fallback is mandatory
Wrap every effect in the `reduce` guard (JS) or `@media (prefers-reduced-motion: no-preference)` (CSS).
The reduced state must show the final, readable text immediately — no missing content, no broken layout.
