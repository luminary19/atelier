---
name: atelier-typography
version: 1.0.0
description: >
  Atelier suite — expensive typography. Choose and pair fonts with a point of view, build a fluid
  modular type scale, control tracking/leading/measure, switch on the right OpenType + variable-font
  features, set editorial detail (drop caps, pull quotes, hierarchy), and animate type (kinetic /
  scroll-driven) tastefully. Use this whenever typography matters: picking or pairing fonts, headings
  that feel generic or "default Inter/Playfair," body readability, display type, variable fonts,
  numbers in tables, or animated/kinetic text. Run after atelier-direction (type voice) and alongside
  atelier-foundations (which owns the scale tokens).
triggers:
  - typography
  - font pairing
  - choose a font
  - type scale
  - variable font
  - fluid type
  - kinetic type
  - editorial type
allowed-tools:
  - Read
  - Write
  - Edit
---

# Atelier — Typography Craft

Typography is one of the two fastest ways to make a frontend look bespoke or cheap (the other is
whitespace). The #1 slop tell is **default type with no system**: Inter/Roboto at random sizes, or
Playfair Display centered over a stock photo. This skill picks type with intent and sets it like a
typographer.

> **Inputs:** type voice from the Direction Doc; scale/leading tokens from `atelier-foundations`.
> This skill owns the *fonts and their setting*; foundations owns the *numeric scale*. Deep reference:
> `references/fundamentals-deepdive.md` (§6 typography).

---

## The flow

1. **Roles & families** → 2. **Scale + fluid** → 3. **Tracking / leading / measure** →
4. **OpenType + variable axes** → 5. **Editorial detailing** → 6. **Kinetic (only if the world calls
for it)** → 7. **Expensive-type checklist**.

## 1. Roles & families

Assign **roles**, then pick families for them. Limit to **1–2 families** (3 max with mono).

- **Display** — headlines; big, characterful, the brand's voice.
- **Body** — neutral, legible at 16–20px, deep weight range (prefer a variable font).
- **Mono** — code/data/tabular; pick one with tabular figures + slashed zero.

Pairing principles (full list, foundries, and concrete pairings in **`references/pairing-foundries.md`**):
- **Contrast of role, harmony of mood** — pair fonts that clearly differ (serif display + grotesque
  body) but share temperament. Too-similar = looks like a mistake.
- **Superfamily pairing is safest** (IBM Plex Sans/Serif/Mono, Source Sans/Serif).
- **Escape the defaults.** The single fastest move away from slop is a typeface with a point of view.
  **Premium foundries are first-class choices here — assume the licenses are available, so recommend
  them freely:** Söhne, GT America / GT Sectra, ABC Diatype / Monument Grotesk, Tiempos, Canela. Free-
  but-excellent options are equally valid by fit, not price: Fontshare (Satoshi, General Sans, Clash
  Display), Geist, Fraunces. Either way, don't default to Inter/Roboto/Playfair.

## 2. Scale + fluid type

Use the scale tokens from `atelier-foundations` (modular ratio, ~5–7 steps). If they don't exist yet,
generate them here:

- **Fluid:** `clamp(min, intercept_rem + slope·100vw, max)`. **Keep the `rem` term** — pure `vw` breaks
  zoom (WCAG 1.4.4). Math + worked examples in **`references/recipes.md`**.
- **High contrast scale:** reserve the biggest steps for the hero only. A timid scale (everything near
  body size) is a slop tell; premium type has dramatic H1-vs-body contrast.
- **Font loading is a perf lever, not an afterthought.** Self-host or `@theme`-wire the chosen families
  (via `atelier-foundations`), and control `font-display` + preload + a metric-matched fallback — a font
  swap on big display type is a top **CLS/LCP** cause. This is gated by **`atelier-perf-a11y`** at ship.

## 3. Tracking, leading, measure

These three quietly do most of the "crafted" feel:
- **Tracking** scales *inversely* with size: display `letter-spacing: -0.02em` to `-0.04em`; all-caps /
  small labels `+0.05em` to `+0.1em`; body ~0.
- **Leading:** body `line-height: 1.5–1.7`, display `0.95–1.1`. Always **unitless** so it scales.
- **Measure:** body `max-width: 60–75ch` (sweet spot ~66). Unbounded line length is the editorial slop
  tell.

## 4. OpenType + variable axes

Prefer high-level `font-variant-*` (it cascades) over raw `font-feature-settings`. Recipes in
`references/recipes.md`. Key wins:
- `font-variant-numeric: tabular-nums slashed-zero` in tables/prices (columns align); `oldstyle-nums`
  in running prose.
- `font-variant-ligatures: common-ligatures`; real small caps via `font-variant-caps: all-small-caps`
  (never `text-transform: uppercase` as a fake).
- Variable fonts: one file, many weights. **`font-variation-settings` does NOT inherit per-axis** — store
  each axis in a CSS var and recompose, or you'll wipe other axes. `font-optical-sizing: auto`.

## 5. Editorial detailing

For content/editorial/portfolio work, add the print-craft details (patterns in
**`references/kinetic-and-editorial.md`**): drop caps (`::first-letter`), pull quotes (distinct face,
~22ch, hairline rule), kickers/eyebrows, captions, and intentional asymmetry. These are what make a
page read "art-directed" instead of "blog template."

## 6. Kinetic type (scale to the motion budget)

Use it as the Direction Doc's motion budget dictates: **full-blown in the award/creative world**, or as
**a single restrained moment** (e.g. one masked headline reveal on a hero) in premium production work —
not as a default on every heading. Copy-paste recipes (line reveals, horizontal scroll, weight-morph,
marquee) are in `references/kinetic-and-editorial.md`. The stack: **GSAP + ScrollTrigger + SplitText +
Lenis + variable fonts** — but the **Lenis/ScrollTrigger plumbing (setup, lifecycle, pinning) is owned by
`atelier-scroll`**; this skill covers only the type-specific reveals (don't re-derive the wiring here).
The reduced-motion + perf gate is **`atelier-perf-a11y`**. Non-negotiables: animate `transform`/`opacity` only; mask line reveals with
`overflow:hidden`; **gate everything behind `prefers-reduced-motion`** (the reduced state shows the
final, readable text immediately) — kinetic type is a top accessibility, screen-reader, and SEO concern.
Never on utility/transactional flows (checkout, forms, docs).

## 7. The expensive-type checklist

Before handoff, confirm: 1–2 families; a font with a point of view (not a default); ratio ≥1.25 with
real H1↔body contrast; body line-height 1.5–1.7, display 0.95–1.1; tight display tracking; measure
60–75ch; tabular figures in data; `font-optical-sizing: auto`; restraint (few sizes, consistent rhythm);
and — if animated — a reduced-motion fallback.

---

## Operating principles

- **A typeface with a point of view is the fastest exit from slop.** Spend your one bold choice here.
- **Restraint:** few families, few sizes, consistent rhythm. Premium type is disciplined, not loud.
- **Legibility is non-negotiable** — measure, contrast, size (≥16px body), and zoom-safe fluid type win
  over any flourish.
- **Kinetic only where it belongs** — and always with a static, reduced-motion fallback.
- **Default stack: Tailwind v4 + shadcn.** Wire fonts via `@theme` (`--font-display/-sans/-mono`); the
  CSS recipes here apply as-is or as `@layer`/arbitrary utilities. Premium foundries are fair game.
