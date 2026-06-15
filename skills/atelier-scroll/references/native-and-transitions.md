# Native scroll-driven animations & page transitions

Prefer native where supported — it runs off the main thread and needs no JS. Always feature-detect and
fall back.

## CSS scroll-driven animations
Two timelines: `scroll()` (progress over a scroll container) and `view()` (progress while an element
crosses the viewport). Support: Chromium + Safari; **not Firefox** (~85%) → progressive enhancement only.

```css
@supports (animation-timeline: view()) {
  @media (prefers-reduced-motion: no-preference) {
    .reveal {
      animation: reveal linear both;
      animation-timeline: view();
      animation-range: entry 0% cover 30%;   /* play as it enters */
    }
    @keyframes reveal { from { opacity: 0; transform: translateY(24px); } to { opacity: 1; transform: none; } }
  }
}
/* default (no support / reduced motion): element is just visible */
```
Scroll progress bar with zero JS:
```css
.progress { position: fixed; top: 0; left: 0; height: 3px; background: var(--primary);
  transform-origin: left; animation: grow linear both; animation-timeline: scroll(root); }
@keyframes grow { from { transform: scaleX(0); } to { transform: scaleX(1); } }
```
Scale-down-on-leave (sticky-stacking cards), parallax via translate keyframes — all expressible with
`view()`/`scroll()`. Use these instead of ScrollTrigger when the effect is simple and you're OK with the
Firefox fallback.

## CSS scroll-snap (sectioned scrolling, accessible)
```css
.snap { scroll-snap-type: y proximity; }      /* proximity is gentler/safer than mandatory */
.snap > section { scroll-snap-align: start; scroll-padding-top: 4rem; }
```
`scroll-snap-stop: always` forces a stop per item. GPU-free and keyboard-friendly — prefer over JS snapping.

## Page / route transitions — View Transitions API
The browser snapshots old/new DOM and animates between them.

### Same-document (SPA)
```js
function navigate(update) {
  if (!document.startViewTransition) return update();      // fallback: instant
  document.startViewTransition(update);
}
/* shared element morph: give both old & new the same name */
.card-hero { view-transition-name: hero; }
::view-transition-old(hero), ::view-transition-new(hero) { animation-duration: .35s; }
```
Support: Chrome/Edge 111+, Firefox 133+, Safari 18+ (Baseline Oct 2025).

### Cross-document (MPA) — zero JS
```css
@view-transition { navigation: auto; }
/* customize via ::view-transition-group/old/new; persistent elements keep a view-transition-name */
```
Support: Chrome/Edge 126+, Safari 18.2+, Firefox 144+. Degrades to normal navigation elsewhere.

### Framework notes
- **Next.js (App Router):** wrap router updates in `startViewTransition` (or use the experimental
  `ViewTransition` support); name shared elements (e.g. a thumbnail → detail hero).
- **Astro:** built-in `<ClientRouter />` (view transitions) — add `transition:name` to shared elements.
- **Barba.js / Swup:** still useful for fully bespoke choreography or broad legacy support; you supply
  GSAP transitions and they manage the persistent shell.

### Reduced motion
```css
@media (prefers-reduced-motion: reduce) {
  ::view-transition-group(*), ::view-transition-old(*), ::view-transition-new(*) { animation: none !important; }
}
```
The page still navigates correctly — only the animation is removed.
