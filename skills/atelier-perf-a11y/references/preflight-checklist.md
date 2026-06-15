# Pre-ship checklist — the gate

Run this over the finished build. Fix every miss. A beautiful site isn't done until it passes.

## Performance (validate at p75 in CrUX/RUM, not just Lighthouse)
- [ ] **LCP ≤ 2.5s** — LCP element eager + `fetchpriority="high"`, not lazy-loaded; fast TTFB; no
      render-blocking CSS/JS; modern image formats.
- [ ] **CLS ≤ 0.1** — every image/video/iframe/embed has dimensions or `aspect-ratio`; `font-display:
      optional` (or metric-matched fallback); no content injected above existing content.
- [ ] **INP ≤ 200ms** — no long tasks > 50ms during load/interaction (split with `scheduler.yield()` +
      `setTimeout` fallback); handlers yield after the visible update; no layout thrashing.
- [ ] **Animations use only `transform`/`opacity`** — audit for animated `top/left/width/height/margin/
      box-shadow`.
- [ ] Scroll/resize/mousemove handlers are **rAF-throttled** + `{ passive: true }`; reads batched before writes.
- [ ] **`will-change` used sparingly** (only frequently-animated elements; removed when idle) — no
      hundreds of layers.
- [ ] Below-fold media `loading="lazy"`; `content-visibility: auto` on heavy offscreen sections.
- [ ] Images AVIF/WebP + `srcset`/`sizes`; fonts preloaded + subset; CDN + Brotli; BFCache eligible.
      **Generated images (e.g. `/codex-imagegen` PNGs) are converted to WebP/AVIF + sized before ship, never raw.**
- [ ] Heavy/continuous animation is compositor/WAAPI-driven (off main thread), not JS rAF tweening.
- [ ] WebGL/3D: lazy-loaded, DPR clamped ≤2, paused offscreen/when tab hidden, static poster fallback.

## Accessibility (WCAG 2.2 AA)
- [ ] **`prefers-reduced-motion` honored in BOTH CSS and JS** (opt-in to motion; reduce, don't remove meaning).
- [ ] No flashing > 3×/sec; auto-motion > 5s has pause/stop/hide; no scroll-jacking; parallax gated + subtle.
- [ ] Semantic HTML + landmarks + logical heading order (one `h1`); native elements over ARIA; ARIA correct
      where used.
- [ ] **Visible `:focus-visible` on everything** (no bare `outline: none`); logical tab order; skip link present.
- [ ] Modals: focus moved in, trapped, `Esc` closes, focus restored (prefer native `<dialog>`); focus never
      obscured by sticky UI.
- [ ] Interactive **targets ≥ 24×24px** (or spaced); drag actions have a tap/click alternative; auth allows
      paste/password managers.
- [ ] Contrast: text ≥ 4.5:1, UI/icons/focus ≥ 3:1; **never color alone**.
- [ ] All images have correct `alt` (`alt=""` decorative); async updates use `aria-live`/`role=status|alert`.
- [ ] **Canvas/WebGL has a real text/DOM/table alternative**; essential content/nav never WebGL-only.
- [ ] Forms: every input has a `<label htmlFor>`; errors are inline + `role="alert"`, preserve input.

## Design integrity (anti-slop — full list in `anti-slop-preflight.md`)
A build can pass perf + a11y and still read as AI-generated. Catch the Tells (a committed, consistent
concept device is exempt — see the full ref):
- [ ] **Eyebrows ≤ 1 per 3 sections**; no split-header default; layout families varied (zigzag ≤ 2 in a row).
- [ ] **Hero fits the viewport** — headline ≤ 2 lines, subtext ≤ ~20 words, CTA visible, ≤ 4 text elements.
- [ ] **CTA fits one line**, no wrap; **no duplicate CTA intent** (one label per intent, page-wide).
- [ ] **One accent locked page-wide** (verified in both themes); one radius scale; one theme (sections don't invert).
- [ ] **No div-based fake screenshots / gradient-blob heroes** — real generated/photographic assets; real logos.
- [ ] **Marquee ≤ 1 per page**; bento cells == content (no empty cells), with visual variation.
- [ ] **Copy self-audit done** — no AI-cute/broken strings; **no fake-precise numbers** (real, labelled mock, or cut).
- [ ] No default Inter/Roboto as display; no unjustified serif; no reflex purple-gradient / beige-brass palette.

## How to test
- **Keyboard only** — tab through the whole page; can you reach + operate everything; is focus always visible.
- **Screen reader** — VoiceOver/NVDA pass on key flows; headings/landmarks/names make sense.
- **DevTools** — Rendering panel: emulate `prefers-reduced-motion: reduce`; Performance/Lighthouse for
  jank + CWV lab; emulate slow CPU/network.
- **Automated** — axe (or Lighthouse a11y) clean; then a manual review (automation catches ~30–40%).
- **Field** — confirm CWV at p75 in CrUX/RUM after release.

> If any box is unchecked, the build isn't shippable yet — it's a draft. Beauty + speed + access together,
> or it's not premium.
