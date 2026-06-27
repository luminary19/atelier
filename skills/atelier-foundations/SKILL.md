---
name: atelier-foundations
version: 1.0.0
description: >
  Atelier suite — the design-system engine. Build the token foundation that makes a frontend look
  coherent and "expensive": a perceptual OKLCH color system (ramps + semantic tokens + accessible
  dark mode), a modular + fluid type scale, an 8-point spacing scale, and depth (radii, shadows,
  grain). Outputs ready-to-use CSS custom properties, Tailwind v4 @theme (mapped to shadcn/ui theme variables), or W3C/DTCG design tokens.
  Use this whenever starting any frontend that needs a consistent visual system, when building a
  color palette / design tokens / chart & data-viz palettes / theme / dark mode, or when colors, spacing, or sizing feel
  inconsistent, muddy, or generic. Run after atelier-direction; before building components. (Choosing
  and setting the actual fonts → atelier-typography; scaffolding and building components → atelier-components.)
triggers:
  - design system
  - design tokens
  - color palette
  - color system
  - spacing scale
  - dark mode
  - theming
  - oklch
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Atelier — Design-System Foundations

The engine of the suite. **"Expensive" is not a trick — it's a system showing through.** Coherent
color, spacing, and type tokens are what separate bespoke-looking work from a pile of one-off values.
This skill turns a Direction Doc into a real, reusable token system that `atelier-typography` and
`atelier-layout` (and your components) consume.

> **Project memory:** if **`ATELIER.md`** exists, read it first and honor its register, palette mood, and
> anti-references. **Identity preservation wins:** if the project already has committed brand colors/tokens
> (existing CSS vars, a theme file, recognizable brand hexes), preserve them and build the system *around*
> them — don't regenerate a palette over a real brand. Capture the result back in `ATELIER.md`'s Tokens
> section. Set up memory with **`/atelier init`** (the **`atelier`** router).
>
> **Inputs:** the Direction Doc from `atelier-direction` (palette mood, type voice, density, light/dark).
> **Outputs:** tokens as CSS vars / Tailwind v4 `@theme` / DTCG JSON. Deep reference:
> `references/fundamentals-deepdive.md` (§7 Color, §8 Layout & Composition → spacing, §9 Design Systems → DTCG tokens).
>
> **Data — `atelier-data` (seed only):** per-product-type shadcn-token palettes via `scripts/search.py "<product>" --domain color`. These are raw Tailwind hex stops — use as a *starting* hue set, then rebuild the system here in OKLCH and re-check contrast before shipping.

---

## Token architecture (build in this order)

Three tiers, always. This is what makes theming and dark mode trivial later.

1. **Primitive / ramp** — raw values, no meaning: `--blue-50 … --blue-950`, `--space-1 … --space-12`.
2. **Semantic / alias** — intent, *referencing* primitives: `--bg`, `--surface`, `--border`, `--text`,
   `--text-muted`, `--primary`, `--danger`. **This tier carries the brand and enables theming** —
   dark mode = remap semantics, never touch components.
3. **Component** (optional) — component-scoped: `--button-bg`, `--card-padding`, referencing semantics.

Rule: components consume tier 2/3, **never hard-code a primitive**. Get this right and dark mode is a
20-line remap instead of a rewrite.

---

## 1. Color — build in OKLCH

Build the whole color system in **OKLCH**, not HSL/hex. HSL lies about lightness (same `L%` looks far
brighter for yellow than blue), so HSL ramps are perceptually uneven and dark themes go muddy. OKLCH is
perceptually uniform, hue-stable, and P3-capable. Full method, ready-to-tweak ramps, and the Radix
12-step role mapping are in **`references/color-oklch.md`**. The short version:

- **Brand ramp:** fix the hue `H`, sweep lightness `L` evenly from ~0.97 (step 50) to ~0.20 (step 950),
  and *curve* chroma `C` — low at the light end, peaking around step 500–600, tapering at the dark end.
  `oklch(L C H)`.
- **Neutrals:** a gray ramp with a *tiny* chroma tinted toward the brand temperature (`C ≈ 0.01–0.02`).
  Pure-gray neutrals read clinical; a whisper of brand tint reads designed.
- **Accent:** usually one. Monochrome + a single saturated accent is the safest "premium" move.
- **Avoid the cream/sand/beige default.** The warm-neutral band (OKLCH `L 0.84–0.97, C < 0.06, hue 40–100`)
  reads as paper/parchment no matter what you name it, and is *the* saturated AI body background of 2026.
  Token names like `--paper`, `--cream`, `--sand`, `--bone`, `--linen`, `--parchment`, `--ivory`, `--oat`
  are tells in themselves (the `atelier-perf-a11y` detector flags them). If the brief says "warm / editorial
  / cozy," carry the warmth in the **accent + type + imagery**, not the body bg: pick a saturated brand
  body, a true off-white at chroma ~0, or a clearly-branded mid-tone. Tint neutrals toward the brand hue by
  only `C ≈ 0.005–0.02`, *deliberately* — never "warm by default."
- **Map semantics** to ramp steps using the Radix 12-step roles (1 app bg → 9 solid/CTA → 12 high-
  contrast text). See the reference for the full table.
- **Relative color** for variants: `oklch(from var(--primary) calc(l - 0.08) c h)` for a hover state —
  keeps hue/chroma locked. Or **`color-mix(in oklch, …)`** (Baseline Widely Available Nov 2025) to derive state/tint
  ramps from a semantic token (`color-mix(in oklch, var(--primary) 12%, transparent)` for a scrim) — no
  Sass. Mix *in `oklch`*, not sRGB, or midpoints muddy.
- **Support:** base `oklch()` ~93%, relative-color syntax ~86% — both production-safe behind a
  plain-color fallback declaration. Keep the brand ramp inside sRGB; treat extra chroma as a P3 *opt-in*
  (`@media (color-gamut: p3)`), since out-of-gamut values gamut-map per-engine and can shift.
- **Data-viz palettes** — categorical (rotate hue at fixed L/C), sequential, diverging, and colorblind-safe
  rules + the `--chart-N` tokens live in `references/color-oklch.md`, built for **`atelier-dataviz`** to consume.

## 2. Type scale (tokens only — craft lives in atelier-typography)

Emit the *scale* here as tokens; `atelier-typography` picks the actual fonts and detailing.

- **Modular scale:** base 16–18px × a ratio (1.2 conservative UI, **1.25 web default**, 1.333+ marketing,
  1.618 dramatic). Keep it to ~5–7 steps — fewer sizes = more consistent.
- **Fluid:** make each step `clamp(min, intercept_rem + slope·100vw, max)`. **Always keep a `rem` term**
  in the preferred value or you break browser zoom (WCAG 1.4.4). The math + a generator is in
  `references/tokens-and-output.md`; or compute via utopia.fyi.
- Token names: `--text-xs … --text-5xl`, plus `--leading-tight/normal/relaxed` and `--tracking-tight`.

## 3. Spacing, radii, depth

- **Spacing: 8-point grid** (`--space-1: 4px` sub-unit, then 8/16/24/32/48/64…). Viewport widths divide
  cleanly by 8; it kills decision fatigue and gives consistent rhythm. Tight UIs may use the 4px sub-unit
  more.
- **Density (from the Direction Doc) sets where on the scale you live** + the `--section-y` macro rhythm:
  *airy* → bias to the larger steps, wide `--section-y` (`clamp` toward the top); *balanced* → mid;
  *packed* → lean on the 4px sub-unit and tighter steps. Same scale, different default reach.
- **Radii:** a small scale (`--radius-sm/md/lg/xl`, e.g. 6/10/16/24px). Pick one family and stick to it
  (sharp = brutalist/Swiss; large/continuous = soft/premium).
- **Depth:** elevation via **soft, layered, low-opacity shadows** (ambient + direct) in light mode; in
  **dark mode use lighter surfaces, not shadows** (shadows are nearly invisible on dark). See
  `references/dark-mode-and-depth.md`.
- **Grain:** the single highest-ROI "expensive" tactic — an SVG `feTurbulence` overlay at opacity
  0.03–0.08 with `mix-blend-mode: overlay`. Kills gradient banding, adds analog depth. Recipe in the
  depth reference.

## 4. Dark mode

If the direction is dark (or supports both), build it as a semantic remap, not a second palette:

- Base is **charcoal/ink, never `#000`** (`oklch(~0.16–0.22 …)` ≈ `#0a0a0f`–`#141416`). Pure black causes
  text halation and leaves no room to show elevation.
- **Elevation by lightness:** surfaces step *lighter* (`rgba(255,255,255,.03)` → `.06` → `.09` overlays,
  or stepped L), not by shadow.
- **Desaturate accents ~10–15%** — full-saturation brand colors vibrate on dark.
- Text: off-white (~`L 0.92`), muted ~`L 0.70`. Re-check contrast (APCA is better here than WCAG 2 ratios).
- **Authoring:** the cleanest way to express each semantic token is **`light-dark()`** (Baseline; needs
  `color-scheme: light dark` on `:root`) — `color: light-dark(<light>, <dark>)` follows the theme toggle
  with no `[data-theme]` media query.
- **Beyond dark:** the same semantic remap yields **multi-theme** for free — sub-brands, a first-class
  high-contrast variant, and a one-hue user-customizable accent. Recipes in `references/dark-mode-and-depth.md`.

## 5. Output

**Detect the stack first.** If the project already uses Tailwind (a `tailwindcss` dependency or
`@import "tailwindcss"`), **default to Tailwind v4 + shadcn/ui** (the suite's house stack) — emit tokens as
`@theme` in CSS and map them to shadcn's semantic token names so components inherit the system for free.
**If there's no Tailwind** (vanilla, Rails, Laravel, Django, Astro-no-Tailwind), default to **CSS custom
properties** instead — don't impose Tailwind on a codebase that isn't using it. Use DTCG JSON when a design
team / multi-platform pipeline exists. Full copy-paste templates in
**`references/tokens-and-output.md`**:
- **Tailwind v4 + shadcn** (DEFAULT) — `@theme { --color-…; --spacing-…; --font-… }` in CSS (v4 is
  CSS-first, OKLCH-native, no `tailwind.config.js`) + the shadcn `--background/--foreground/--primary/…`
  mapping.
- **CSS custom properties** (`:root` + `[data-theme="dark"]`) — portable fallback for vanilla / other
  frameworks.
- **DTCG / W3C design tokens** JSON (+ Style Dictionary) — when a design team / multi-platform pipeline
  exists.

## 6. Contrast gate (don't ship without it)

- **Conformance: WCAG 2.2 AA** — body text ≥ 4.5:1, large text & UI/icons/focus ≥ 3:1 (WebAIM checker).
- **Design with APCA** for fidelity, especially dark mode (Lc 90 body / 75 min / 45 headlines). APCA is
  not yet a conformance standard — certify with 2.x, tune with APCA.
- **Never rely on color alone** (pair with text/icon/shape). Verify the `--primary` solid and all text
  tokens against their backgrounds before handoff.
- For a *dynamic/data-driven* accent, let the browser pick the readable foreground:
  **`contrast-color(var(--brand))`** (Baseline Apr 2026) returns black or white — kills the "is white
  text readable on this accent?" guess for buttons/badges. Returns black/white only; provide a static
  `@supports` fallback for older engines.
- This is the *design-time* check; **`atelier-perf-a11y` re-verifies contrast at ship time** (computed
  from rendered pixels, in *every* theme) — the accent-as-text-on-light pair is the usual failure.

---

## Operating principles

- **Three tiers or it isn't a system.** Hard-coded hex/px scattered through components is the #1 cause of
  incoherent, cheap-looking UI.
- **OKLCH everywhere.** It's why the ramps look evenly stepped and the dark theme isn't muddy.
- **One accent, tinted neutrals, real grain.** These three quietly do most of the "expensive" work.
- **Default to Tailwind v4 `@theme` + shadcn token names**; drop to CSS custom properties or DTCG only
  when the project clearly isn't Tailwind. One source of truth either way — components reference
  semantic names, never primitives.
