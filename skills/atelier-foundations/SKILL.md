---
name: atelier-foundations
version: 1.0.0
description: >
  Atelier suite — the design-system engine. Build the token foundation that makes a frontend look
  coherent and "expensive": a perceptual OKLCH color system (ramps + semantic tokens + accessible
  dark mode), a modular + fluid type scale, an 8-point spacing scale, and depth (radii, shadows,
  grain). Outputs ready-to-use CSS custom properties, Tailwind v4 @theme, or W3C/DTCG design tokens.
  Use this whenever starting any frontend that needs a consistent visual system, when building a
  color palette / design tokens / theme / dark mode, or when colors, spacing, or sizing feel
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

> **Inputs:** the Direction Doc from `atelier-direction` (palette mood, type voice, density, light/dark).
> **Outputs:** tokens as CSS vars / Tailwind v4 `@theme` / DTCG JSON. Deep reference:
> `references/fundamentals-deepdive.md` (§7 color, §8 spacing, §9 tokens).

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
- **Map semantics** to ramp steps using the Radix 12-step roles (1 app bg → 9 solid/CTA → 12 high-
  contrast text). See the reference for the full table.
- **Relative color** for variants: `oklch(from var(--primary) calc(l - 0.08) c h)` for a hover state —
  keeps hue/chroma locked.

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

## 5. Output

**Default to Tailwind v4 + shadcn/ui** (the suite's house stack) — emit tokens as `@theme` in CSS and
map them to shadcn's semantic token names so components inherit the system for free. Support the other
formats when the project clearly isn't Tailwind. Full copy-paste templates in
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
