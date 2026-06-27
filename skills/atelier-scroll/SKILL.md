---
name: atelier-scroll
version: 1.0.0
description: >
  Atelier suite — scroll choreography & advanced interaction. Build award-grade scroll experiences:
  smooth/inertia scroll (Lenis), scroll-triggered reveals, scrubbing, pinning, horizontal sections,
  sticky-stacking cards, parallax, native CSS scroll-driven animations, page/route transitions (View
  Transitions API), infinite marquees, magnetic buttons, and custom cursors. Use whenever adding
  scroll-based animation or storytelling, smooth scrolling, parallax, pinned/horizontal sections, page
  transitions, marquees, or custom/magnetic cursors — or when scroll feels static, abrupt, or janky.
  Default stack: GSAP + ScrollTrigger + Lenis, with native CSS scroll-driven animations as progressive
  enhancement. Honors prefers-reduced-motion. Part of the Atelier suite.
triggers:
  - scroll animation
  - smooth scroll
  - parallax
  - scroll trigger
  - pinned section
  - horizontal scroll
  - page transition
  - marquee
  - custom cursor
  - magnetic button
allowed-tools:
  - Read
  - Write
  - Edit
---

# Atelier — Scroll Choreography

Scroll is the canvas for award-grade web. Done well it's cinematic; done badly it's scroll-jacking that
fights the user. The discipline: **choreograph scroll, never hijack it.** Lenis keeps the *real* scroll
position (so keyboard, anchors, sticky, and assistive tech keep working) while making it smooth.

> **Project memory:** if **`ATELIER.md`** exists, read its **Interactivity** level + **Motion policy** first
> and honor them (set up via **`/atelier init`** — the **`atelier`** router).
>
> **Inputs:** the Direction Doc's motion budget + signature moment. **Default stack:** GSAP +
> ScrollTrigger + Lenis; native CSS scroll-driven animations where supported. **Gate:** every effect runs
> through `atelier-perf-a11y` (reduced motion, off-main-thread, no scroll-jacking). Easing/duration
> vocabulary → `atelier-motion/references/timing-easing.md` (keep reveals consistent with component
> motion); React wiring (`ReactLenis` / `useGSAP`) → `atelier-components`; WebGL hover/scroll distortion →
> `atelier-webgl`; production resilience (instance cleanup, offline + reduced-motion fallbacks) →
> `atelier-harden` before the gate. Deep reference: `references/fundamentals-deepdive.md` (§4).

---

## The flow

1. **Check the budget** → 2. **Smooth scroll base (Lenis)** → 3. **Pick the technique** → 4. **Prefer
native where it fits** → 5. **Page transitions** → 6. **Gate (reduced motion + perf).**

## 1. Budget check

Scroll choreography is an **award/creative-world** investment. In the production world, keep it to subtle
reveals + maybe one pinned/scrubbed signature moment. Don't scroll-jack content/utility sites — it costs
conversions and accessibility. Confirm the Direction Doc actually called for this.

## 2. Smooth scroll base — Lenis

Lenis is the current standard because it modifies the real scroll position (unlike old fake-container
libs). Set it up and wire it into the GSAP ticker so ScrollTrigger reads the virtual scroll. Full setup +
React (`ReactLenis`) in **`references/lenis-scrolltrigger.md`**. Don't initialize it under reduced motion.
(Or GSAP **ScrollSmoother** if you're already all-in on GSAP — pick one engine.) In SSR / Next App Router
keep init client-side and `ScrollTrigger.refresh()` after fonts/images settle; gate responsive setups with
**`gsap.matchMedia()`** — recipes in the reference.

## 3. Pick the technique (GSAP + ScrollTrigger)

Recipes in `references/lenis-scrolltrigger.md`:
- **Reveals** — one-shot → IntersectionObserver + a CSS class (no lib); progress-tied → ScrollTrigger
  (many elements → `ScrollTrigger.batch()`, one shared observer instead of one trigger each).
- **Scrub** — `scrollTrigger: { scrub: true|<sec> }` ties progress to scroll (numeric = smoothing).
- **Pin** — `position: sticky` first (cheap, accessible); ScrollTrigger `pin: true` only when sticky
  can't express the choreography (independent duration, scrubbed timeline).
- **Horizontal section** — pin + translate a wide track on X (`invalidateOnRefresh`).
- **Sticky-stacking cards**, **parallax** (`data-speed` / transform on scroll).

> **Image sources** for reveals / parallax / distortion should be **real assets generated on the Direction
> Doc's aesthetic via `/codex-imagegen`** (then WebP/AVIF + set `width`/`height`), at the right aspect for
> the slot — animating a text-on-gradient placeholder is still slop, just slop in motion.

## 4. Prefer native where it fits

Native **CSS scroll-driven animations** (`animation-timeline: scroll()` / `view()` + `animation-range`)
run off the main thread and need no JS — use them for reveals/parallax/progress where supported (Chromium
+ Safari; not Firefox → feature-detect and fall back to ScrollTrigger). Also **CSS `scroll-snap`** for
sectioned scrolling (prefer `proximity` over `mandatory`); **scroll-state container queries**
(`@container scroll-state(stuck/snapped/scrollable)`, Chrome 133+) to style sticky/snapped elements with
zero JS instead of a scroll listener; and **CSS carousels** (`::scroll-button` / `::scroll-marker`, Chrome
135+) for zero-JS prev/next + dot markers. All Chromium-only → feature-detect and keep the JS/IO fallback.
Details in **`references/native-and-transitions.md`**.

## 5. Page / route transitions

Default to the **View Transitions API**: SPA `document.startViewTransition(() => updateDOM())` with
`view-transition-name` for shared elements; MPA `@view-transition { navigation: auto; }` (zero JS). Use
Barba.js/Swup only for bespoke control or legacy support. Recipes + framework notes (Next, Astro) in
`references/native-and-transitions.md`.

## 6. Advanced interaction (cursors, marquee, distortion)

In **`references/cursors-marquee-distortion.md`**: magnetic buttons, custom cursors (lerped follower),
infinite marquees (CSS + GSAP, pause-on-hover, velocity-linked), and WebGL hover distortion (delegated to
`atelier-webgl`). All pointer-only effects must never gate function and must respect reduced motion.

## 7. Gate

- **Reduced motion:** don't init Lenis; replace scrubbed/pinned/parallax/horizontal with static or simple
  fades; pause marquees; disable magnetic/custom cursor. Provide non-motion equivalents.
- **Perf:** animate `transform`/`opacity` only; `invalidateOnRefresh` on resize-dependent setups; lazy-
  init heavy effects; never block the main thread. Run `atelier-perf-a11y`.

---

## Operating principles
- **Choreograph, never hijack.** Lenis keeps native scroll behavior intact; true scroll-jacking is a last
  resort with an escape and a fallback.
- **Sticky before pin; native before JS.** Reach for the cheaper, more accessible primitive first.
- **Scroll choreography is an award-world spend** — in production, a few reveals + one signature moment.
- **Everything degrades** to a readable, navigable, reduced-motion page. No exceptions.
