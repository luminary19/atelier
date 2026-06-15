---
name: atelier-perf-a11y
version: 1.0.0
description: >
  Atelier suite — the performance & accessibility gate. The cross-cutting quality bar every Atelier build
  passes before it ships: animate only compositor-safe properties, hit Core Web Vitals (LCP ≤2.5s, CLS
  ≤0.1, INP ≤200ms), respect prefers-reduced-motion, meet WCAG 2.2 AA (contrast, focus, keyboard, target
  size, semantics, screen readers), and give canvas/WebGL accessible fallbacks. Use whenever finishing or
  reviewing a frontend, optimizing performance / Core Web Vitals / Lighthouse, fixing jank or layout
  shift, doing an accessibility/a11y audit, handling reduced motion, or running a pre-ship check. This is
  the canonical home for the perf/a11y rules the other Atelier skills reference. Part of the Atelier suite.
triggers:
  - performance
  - core web vitals
  - lighthouse
  - accessibility
  - a11y
  - wcag
  - reduced motion
  - layout shift
  - jank
  - pre-ship check
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Atelier — Performance & Accessibility Gate

The line between an amateur "beautiful" build and a professional one. **A beautiful site is not done
until it passes these gates.** This skill is both a *reviewer* (run it over finished work) and the
*reference* the rest of the suite points to for its perf/a11y rules — when those skills say "respect
reduced motion" or "animate only transform/opacity," the full how lives here.

> **Applies to everything** from `atelier-motion`, `atelier-scroll`, `atelier-webgl`, `atelier-components`.
> Deep reference: `references/fundamentals-deepdive.md` (§13, §16). Numbers below are current (mid-2026).

---

## How to use this skill

Two modes:
1. **As you build** — the other skills cite the relevant rule; pull the matching detail from the
   references here (don't re-derive it).
2. **Before you ship** — work **The quality ladder** (below): the two self-checklists (perf+a11y, then
   anti-slop), and for substantial builds escalate to the adversarial `atelier-review`. Fix every miss.

## Performance (the mental model)

Browser pipeline: **Style → Layout → Paint → Composite.** The property you animate decides how far back
the browser rewinds each frame — this one fact governs animation perf. Full detail in
**`references/performance.md`**:
- **Animate only `transform` and `opacity`** (composite-only, GPU, off main thread). Animating
  `width/height/top/left/margin` forces Layout every frame; `box-shadow/background` forces Paint.
- **No layout thrashing** — batch DOM reads before writes; rAF-throttle scroll/resize/mousemove + use
  `{ passive: true }`.
- **`will-change` sparingly** — only on frequently-animated elements; layers cost GPU memory.
- **Prefer CSS/WAAPI/Motion animation** (off main thread) over JS rAF tweening of layout props.
- **Loading:** lazy-load below-fold (never the LCP image — eager + `fetchpriority="high"`); code-split +
  tree-shake; AVIF/WebP + `srcset` + dimensions; fonts preload + subset + `font-display: optional`;
  `content-visibility: auto` for heavy offscreen sections; CDN/Brotli.

### Core Web Vitals (p75 field — the targets)
- **LCP ≤ 2.5s** — render time of the largest in-viewport element. Preload/eager it; fast TTFB; no
  render-blocking CSS/JS.
- **CLS ≤ 0.1** — unexpected layout shift. Set image/video dimensions or `aspect-ratio`; reserve
  ad/embed space; `font-display: optional`; animate only transform/opacity.
- **INP ≤ 200ms** — interaction latency (replaced FID; most-failed). Break long tasks >50ms
  (`scheduler.yield()` + `setTimeout` fallback); yield after the visible update; avoid thrashing; shrink
  the DOM. Heavy continuous JS animation directly inflates INP — move it to the compositor or gate it.
Measure with **CrUX/RUM** (field) for decisions; Lighthouse/PSI (lab) for debugging.

## Accessibility (WCAG 2.2 AA)

Full detail in **`references/accessibility.md`**. The essentials:
- **`prefers-reduced-motion`** — default-safe: ship static, add motion inside `@media (prefers-reduced-
  motion: no-preference)`; in JS branch on `matchMedia(...)` / `useReducedMotion()`. **Reduce, don't
  blanket-nuke** — keep opacity fades, remove large movement/parallax/scroll-jack/spin. Provide non-motion
  signifiers.
- **Semantic HTML first** — native `<button>/<a href>/<nav>/<dialog>` over ARIA (first rule of ARIA:
  don't use it if HTML does the job). Landmarks, logical heading order (one `h1`), accessible names on
  every interactive element.
- **Focus & keyboard** — never bare `outline: none`; use `:focus-visible` with a thick high-contrast ring;
  logical tab order; modals trap focus + `Esc` + restore (prefer native `<dialog>`); skip link.
- **WCAG 2.2 new** — target size **≥ 24×24px**; focus not obscured by sticky UI; dragging has a single-
  pointer alternative; auth allows paste/password managers.
- **Color** — text ≥ 4.5:1, large/UI/icons/focus ≥ 3:1; never color alone. (Design with APCA, certify with
  2.x — APCA isn't a conformance standard yet.)
- **Screen readers** — correct `alt` (`alt=""` decorative); `aria-live`/`role=status|alert` for async
  updates; **canvas/WebGL is invisible to AT → provide a DOM/table/text alternative**.
- **Motion a11y** — auto-motion >5s needs pause/stop/hide; **never flash >3×/sec**.

## The quality ladder

Three layers, escalating rigor — **same rubrics throughout** (nothing is duplicate work, just re-checked
with more independence):

1. **perf-a11y self-checklist** — `references/preflight-checklist.md`. Core Web Vitals + WCAG 2.2 AA.
   **Every build.**
2. **anti-slop self-checklist** — `references/anti-slop-preflight.md`. The "AI Tells" pass on the *rendered
   output* (eyebrow overuse, split-header, duplicate-CTA, div-faked screenshots, marquee/zigzag repetition,
   fake-precise numbers, copy audit, accent/theme locks). **Every build.** (The *plan*-stage version of the
   same Tells — checked against the Direction Doc, not the build — is `atelier-direction`'s
   `references/anti-slop.md`. Same Tells, different artifact; the overlap is intentional — catch one that
   slipped from plan to pixels.)
3. **`atelier-review` — adversarial.** Independent reviewers per dimension + refutation of each finding +
   live in-browser verification, then fixes. **Substantial / redesign / award builds.** Uses ordinary
   subagents (no ultracode/Workflow needed).

Layers 1–2 are you checking your own work; layer 3 is independent reviewers trying to break it.

**How to test (all layers):** keyboard only; a screen reader; DevTools (Rendering → emulate reduced motion;
Performance/Lighthouse); an automated scan (axe); field data (CrUX/RUM) to confirm the perf numbers at p75.

---

## Operating principles
- **It's not done until it passes.** Beauty that janks or excludes users is unfinished work, not a trade-off.
- **`transform`/`opacity` only** is the single highest-leverage perf rule.
- **Reduce motion, don't remove meaning** — keep the information, drop the movement.
- **Semantic HTML + visible focus + real contrast** cover most of accessibility before ARIA ever enters.
- **Canvas/WebGL always needs a DOM alternative** — it's opaque to assistive tech.
