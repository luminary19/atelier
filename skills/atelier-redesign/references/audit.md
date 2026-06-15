# Audit method

Inventory before judging. Goal: understand what exists (and what *system* is missing) so you upgrade
in-place without breaking it. WebFetch the live URL or read the codebase; request a screenshot if the page
is JS-rendered or blocked.

## 1. Inventory the brand (starting material, not noise)
- **Logo** — keep; build the palette/type to complement it.
- **Color** — what colors actually carry the brand? Which are equity (keep) vs arbitrary (replace)?
- **Type** — current families; are they defaults (Inter/Roboto/Playfair) or intentional?
- **Photography / illustration / iconography** — style, quality, consistency.
For redesigns, brand equity (recognizable color/logo/voice) is a constraint to preserve, not erase.

## 2. Inventory IA, content & flows
- Sitemap / nav structure, key pages, primary user flows, conversion paths. Note what must **not** move
  (URLs, IA, SEO-critical headings/content). Mobbin/Refero for how peers structure the same flows.

## 3. Inventory the stack (so you upgrade, not rewrite)
- Framework (Next/React/Vue/Astro/WordPress/etc.), CSS approach (Tailwind? CSS-in-JS? vanilla?), component
  lib, build. The Atelier default is Tailwind v4 + shadcn, but **work within the existing stack** unless a
  migration is explicitly wanted.

## 4. Inventory the design system (or its absence)
Score each — present + good / present + weak / absent:
- **Grid** — is there a real column/baseline grid, or arbitrary placement? Asymmetry intentional or accidental?
- **Type scale** — modular ratio + few sizes, or random sizes? Leading/measure/tracking controlled?
- **Color** — tokens + ramps + one accent, or scattered hex? Built in OKLCH/perceptual or HSL/hex?
- **Spacing** — an 8pt scale + rhythm, or ad-hoc px? Enough macro whitespace?
- **Hierarchy** — clear focal point per view, or flat/competing?
- **Components** — consistent, accessible, token-driven, or one-off and inconsistent?
- **Motion** — purposeful + reduced-motion-safe, or none / janky / excessive?
- **Perf** — Core Web Vitals (LCP/CLS/INP) — measure with Lighthouse + CrUX.
- **A11y** — contrast, focus, keyboard, semantics, alt text — quick axe pass + keyboard tab-through.

## 5. Name the AI-slop tells present (be specific: this section, this value)
Check for: pure `#000` + low-contrast grey text · default Inter/Roboto/Playfair, no scale ·
glassmorphism-on-everything · purple→blue gradient + frosted card · uniform-size "bento" boxes ·
two-stop "mesh" gradient · neon glow as one blurry shadow · constant glitch/warp / infinite micro-loops ·
neumorphism · visible tiled-PNG noise · cramped spacing · no focal point · everything centered ·
everything the same weight.

## 6. Name the missing "expensive" levers
Which are absent: generous active whitespace · a typeface with a point of view · a whisper of grain ·
perceptual OKLCH color + real tokens · tinted neutrals · one disciplined accent · elevation-by-lightness
(dark) · real grid/baseline discipline · intentional asymmetry · one purposeful signature moment.

## Output — the audit report
A short report: (a) brand/IA/stack summary, (b) the design-system scorecard above, (c) the specific slop
tells (with locations), (d) the missing levers, (e) measured perf/a11y baseline. This feeds the
impact-vs-risk prioritization and the (brand-anchored) Direction Doc. **Do not start editing until this
exists** — the diagnosis is what keeps the redesign from becoming "more effects."
