---
name: atelier-motion
version: 1.0.0
description: >
  Atelier suite — motion & micro-interactions (the "feel" layer). Add animation that reads premium, not
  gimmicky: correct easing/spring defaults, the right durations, the 12 animation principles applied to
  UI, component/gesture/layout/exit animation with Motion (motion/react), micro-interactions (buttons,
  toggles, likes), and the often-skipped states (skeleton/shimmer, optimistic UI, empty/loading/error).
  Use whenever adding or fixing UI animation, transitions, hover/press feedback, loading states, or when
  motion feels janky, abrupt, excessive, or cheap. Default stack: Motion for React UI; defer scroll-driven
  work to atelier-scroll and pre-ship checks to atelier-perf-a11y. Part of the Atelier suite.
triggers:
  - animation
  - micro-interaction
  - transition
  - hover effect
  - loading state
  - skeleton
  - make it feel smooth
  - motion
allowed-tools:
  - Read
  - Write
  - Edit
---

# Atelier — Motion & Micro-interactions

Motion is what separates a premium interface from a static one — and bad motion (too slow, too much,
wrong easing, animating the wrong property) instantly reads cheap. The rule that governs everything
here: **motion should be felt, not seen.** If the user consciously waits on an animation, it's too slow
or too big.

> **Inputs:** the Direction Doc's *motion budget* (none / restrained / award-grade). **Default stack:**
> Motion (`motion/react`) for component/gesture/layout/exit animation; GSAP for complex sequencing;
> **scroll-driven motion → `atelier-scroll`**; **the perf/a11y gate → `atelier-perf-a11y`** (animate
> only `transform`/`opacity`, respect reduced motion); **where these hooks mount in a real component tree
> → `atelier-components`.** Deep reference: `references/fundamentals-deepdive.md`
> (§1, §5).

---

## The flow

1. **Set the budget** (from the Direction Doc) → 2. **Pick durations + easing** → 3. **Choose the tool**
→ 4. **Build the interaction** → 5. **Add the missing states** → 6. **Gate it** (reduced motion + perf).

## 1. Motion budget

Match motion to the world (Direction Doc):
- **Production** — purposeful only: feedback (<100ms), state changes, attention guidance, latency masking.
  Durations ≤300ms, one thing moving at a time. Restraint reads as confidence.
- **Award/creative** — motion is part of the brand; bigger gestures, choreography, signature moments.
  Still ships reduced-motion fallbacks.
When in doubt, do less. The most common slop tell is *too much* motion (infinite-loop micro-animations
everywhere), not too little.

## 2. Durations & easing (defaults to internalize)

Full table + cubic-beziers + spring params in **`references/timing-easing.md`**. The essentials:
- **Hover / press / toggle: 120–200ms.** Reveal / small move: 200–300ms. Modal / drawer / page:
  300–450ms. **Ceiling ~500ms.** Respond to input **≤100ms** always (immediate press/scale).
- **Easing by intent:** ease-**out** for entrances (fast→settle, feels responsive); ease-**in** for
  exits; ease-in-out for moves between two on-screen states; **linear only** for continuous (spinner,
  marquee, progress).
- **Springs for direct manipulation / interruptible UI** (drag, sheets, toggles) — they carry velocity
  and feel physical. Duration+easing for deterministic, choreographed sequences.
- Distance/size scale duration (bigger/farther → slightly longer).

## 3. Choose the tool

- **Motion (`motion/react`)** — the default for React UI: declarative `animate`/`whileHover`/`whileTap`/
  `whileInView`, `AnimatePresence` for exit animations, `layout`/`layoutId` for shared-element "magic
  move", springs, gestures. Recipes in **`references/motion-react.md`**.
- **GSAP** — reach for it for complex timelines, SVG morph/draw, or when you need a single engine for an
  intricate sequence. (Scroll-driven motion **and** pointer-driven flourishes — magnetic buttons, custom
  cursor, infinite marquee — live in `atelier-scroll`, not here.)
- **Native CSS** — transitions and keyframes are perfect for simple hover/toggle/state changes with zero
  JS; prefer them when they suffice (they're cheap and run off the main thread).
- **Auto-Animate** — one-line FLIP for list add/remove/move when you want zero config.

## 4. Build the interaction

Use the patterns in `references/motion-react.md`. Core moves: variants with `staggerChildren` for lists,
`AnimatePresence` for mount/unmount, `layout` for size/position changes, `useReducedMotion()` to branch.
Keep to `transform`/`opacity`. Stagger 30–80ms/item, total cascade <600ms.

## 5. Add the missing states (the part everyone skips)

A premium feel is mostly about the *non-happy* states. Patterns in
**`references/microinteractions-states.md`**:
- **Skeleton / shimmer** loaders (perceived speed > spinner; static under reduced motion).
- **Optimistic UI** — `useOptimistic` (React 19): update instantly, reconcile/rollback. Only for
  likely-success, cheap-to-reverse actions (likes, toggles, list adds) — never irreversible/financial.
- **Empty / loading / error** states designed deliberately (empty = onboarding + CTA; error = human
  language + cause + recovery, preserve input).
- **Micro-interactions** — button press/scale, toggle, like, copy-confirm, input focus; tie a clear
  signifier to every action (Don Norman: affordance → signifier → feedback ≤100ms).
- **Haptics** — `navigator.vibrate` on mobile for confirmations; short, meaningful, never haptic-only.

## 6. Gate it

- **Reduced motion is mandatory.** `useReducedMotion()` (Motion) or `@media (prefers-reduced-motion:
  reduce)`. **Reduce, don't always nuke** — keep opacity fades and shortened durations; remove large
  movement, parallax, spin, springy overshoot. Provide non-motion signifiers so no info is lost.
- **Perf:** animate only `transform`/`opacity`; prefer CSS/WAAPI/Motion (off main thread) over JS rAF
  tweening **of layout/paint props**. A transform-only rAF loop (e.g. a lerped custom cursor in
  `atelier-scroll`) is fine — the rule targets `width/top/box-shadow`, not `transform`. Run the full
  **`atelier-perf-a11y`** gate before shipping.

---

## The 12 principles → UI (mental backbone)
Squash&stretch (press squish), anticipation (wind-up), staging (dim bg for modal), follow-through/
overlap (stagger, spring settle), **slow in/out = easing (the most important)**, arcs (curved paths),
secondary action, timing (conveys weight), exaggeration (sparingly, for delight), appeal (brand
personality). Full mapping in `references/timing-easing.md`.

## Operating principles
- **Felt, not seen.** Subtle + fast by default; reserve big gestures for one signature moment.
- **One thing moving at a time** in production UI; orchestrate with overlap, not chaos.
- **Springs for manipulation, easing for choreography.**
- **Design the empty/loading/error states** — that's where perceived quality actually lives.
- **Always reduced-motion + `transform`/`opacity` only.** Beauty ≠ inaccessible or janky.
