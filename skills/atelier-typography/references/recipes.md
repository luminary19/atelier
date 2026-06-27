# Type recipes — fluid, OpenType, variable fonts

## Fluid type (zoom-safe clamp)
`clamp(MIN, intercept_rem + slope·vw, MAX)`. **Always keep the `rem` intercept** — a pure-`vw` size
doesn't respond to browser text-zoom and fails WCAG 1.4.4 (locks out low-vision users).

**Derive from two breakpoints** — work in px, then convert the intercept to rem:
```
slope     = (maxPx − minPx) / (maxVw − minVw)   // px of size per px of viewport
vw coeff  = slope × 100                          // the number before `vw`
interceptPx = minPx − slope × minVw   →  interceptRem = interceptPx / 16
size = clamp(MIN_rem, interceptRem + (slope×100)vw, MAX_rem)
```
**Worked:** 16→32px, 320→1440px → slope = 16/1120 = 0.014286; vw coeff = 1.4286;
intercept = 16 − 0.014286·320 = 11.43px = 0.714rem → `clamp(1rem, 0.714rem + 1.43vw, 2rem)`.
Or use **utopia.fyi** (lets the ratio itself differ between min/max contexts) and paste the output.

Display scale wants high contrast — let the top steps grow far on large screens (reserve `--text-4xl`
for the hero). A timid scale where everything is near body size is a slop tell.

## Tracking / leading / measure (the craft layer)
```css
.display { font-size: var(--text-3xl); line-height: 1.0; letter-spacing: -0.02em; }
.h2      { font-size: var(--text-2xl); line-height: 1.1; letter-spacing: -0.015em; }
.body    { font-size: var(--text-base); line-height: 1.6; max-width: 66ch; }
.eyebrow { font-size: var(--text-sm); letter-spacing: 0.08em; text-transform: uppercase; }
```
- Tracking inversely with size: large display tighter (−0.02 to −0.04em), small caps/labels looser
  (+0.05 to +0.1em). Leading: body 1.5–1.7, display 0.95–1.1, **always unitless**. Measure 60–75ch.
- **Line-wrapping:** `h1,h2,h3,.lead { text-wrap: balance; }` (Baseline 2024 — even last lines, no JS
  balancer); `p { text-wrap: pretty; }` (Chrome/Safari 26, **not Firefox** ~82% — gate with `@supports`).
  Both degrade to normal wrapping. Optional cap-height align: `text-box: trim-both cap alphabetic`
  (Chrome 133 + Safari 18.2, not Firefox — progressive enhancement).

## OpenType — prefer high-level `font-variant-*` (it cascades)
```css
:root { font-optical-sizing: auto; }                          /* opsz — auto-tunes by size */
.prose  { font-variant-ligatures: common-ligatures;
          font-variant-numeric: oldstyle-nums proportional-nums; } /* figures sit like lowercase */
td.num  { font-variant-numeric: tabular-nums slashed-zero; }   /* columns align; clear zero */
.label  { font-variant-caps: all-small-caps; }                 /* REAL small caps, not text-transform */
.recipe { font-variant-numeric: diagonal-fractions; }
.brand  { font-feature-settings: "ss01" 1, "ss03" 1; }         /* stylistic sets (no high-level prop) */
```
- **Gotcha:** `font-feature-settings` is all-or-nothing — listing one feature *disables the font's
  defaults* (you can silently lose `liga`/`kern`). Only reach for it for features with no
  `font-variant-*` longhand (stylistic sets `ss01–ss20`, character variants `cv01`); re-add
  `"liga" 1, "kern" 1` if you must hand-roll the string.
Tags: `liga` common, `dlig` discretionary (display only), `tnum/pnum`, `onum/lnum`, `zero`, `frac`,
`smcp/c2sc`, `ss01–ss20`, `kern`, `opsz`. Tabular figures in any data table/dashboard is a quiet
quality signal.

## Variable fonts
One file, continuous axes — animate or fine-tune weight/width/optical size.
- Registered axes (lowercase): `wght`, `wdth`, `slnt`, `ital`, `opsz`. Custom axes UPPERCASE (`GRAD`,
  `CASL`).
- **Gotcha:** `font-variation-settings` does **not** inherit per-axis — re-declaring it overwrites
  *every* axis. Store each axis in a CSS var and recompose so you can change one without wiping others.
  **Scope it to a typographic root, never `*`** (the universal selector forces both axes onto icon
  fonts, pseudo-elements, and third-party widgets, and fights `font-optical-sizing: auto`):
```css
:root { --wght: 400; }
h1    { --wght: 720; }
/* recompose on the type elements only — and don't also set opsz here if you use
   font-optical-sizing:auto (the low-level setting wins and overrides the auto opsz) */
:where(body, h1, h2, h3, h4, h5, h6, p, li, blockquote, .type) {
  font-variation-settings: "wght" var(--wght);
}
```
- **Prefer the high-level properties** (`font-weight: 550`, `font-stretch: 75%`, `font-optical-sizing:
  auto`) for static values — they cascade and don't clobber other axes. Use the CSS-var + `font-variation-
  settings` recompose **only for animation or custom axes** (`GRAD`, `CASL`); don't mix both for the same
  axis on one element (`font-variation-settings:"opsz"` overrides `font-optical-sizing:auto`).
- Animate axes for hover/scroll effects (see `kinetic-and-editorial.md`); keep to `wght/wdth/opsz` and
  respect `prefers-reduced-motion`.

## Fallback-font metric matching (kill the swap shift)
`font-display: swap` shows a fallback first, then swaps — and if the fallback's metrics differ, the swap
*reflows* (a top CLS/LCP cause on big display type). Match the fallback's box to the web font so the swap
is invisible: override the metrics on a named local fallback, then list it right after the web font.
```css
@font-face {
  font-family: "Satoshi-fallback";
  src: local("Arial");
  size-adjust: 97%;        /* scale glyphs so x-height/advance match the web font */
  ascent-override: 92%;    /* lock the line box so vertical rhythm doesn't jump on swap */
  descent-override: 24%;
  line-gap-override: 0%;
}
:root { font-family: "Satoshi", "Satoshi-fallback", sans-serif; }
```
- Get the numbers automatically: **Fontaine** (`@capsizecss/...` / `fontaine`) or Next.js **`next/font`**
  (does this for you), or the *Automatic Font Matching* tool. Tune `size-adjust` until the swap is imperceptible.
- `font-display: optional` sidesteps the swap entirely (keeps the fallback for the first load if the font
  isn't ready) — best CLS, at the cost of a possible flash of fallback. Use `optional` for body, the matched
  `swap` for display you can't afford to flash. (The CLS/LCP gate is `atelier-perf-a11y`.)

## International type — RTL, non-Latin, expansion
A "premium" Latin setting that breaks in German or Arabic isn't premium. Three things to build in:
- **Text expansion:** translations run longer — German ~+35%, Russian ~+20%. Never fix a button/label
  width to the English string; size to content (`width: max-content`, sensible `min-width`) and allow wrap.
  Re-check that the type scale and `measure` still hold at +35%.
- **RTL (Arabic/Hebrew):** drive direction from `<html dir>` and use **logical properties everywhere**
  (`margin-inline-start`, `padding-inline`, `text-align: start`, `inset-inline`) so the layout mirrors for
  free — never `margin-left`. Obliques don't apply to Arabic; mirror direction-implying icons (arrows, chevrons).
- **Script-aware font stacks:** your display face likely has no Arabic/CJK/Devanagari glyphs — declare a
  per-script fallback (`unicode-range` `@font-face`, or a stack ending in a quality `Noto Sans <Script>`) so
  non-Latin text doesn't drop to ugly defaults. CJK has *no word spaces* and huge files — subset hard and
  set a higher `line-height` (~1.7). (Logical-property + RTL gate → `atelier-perf-a11y`.)

## Anti-slop type checklist
1–2 families · a font with a point of view (not a default) · ratio ≥1.25 with real H1↔body contrast ·
body line-height 1.5–1.7, display 0.95–1.1 · tight display tracking · measure 60–75ch · `tnum`+`zero`
in data · `font-optical-sizing: auto` · few sizes, consistent rhythm.
