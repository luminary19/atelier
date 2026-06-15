# Token architecture & output formats

Three tiers (primitive → semantic → component). Components consume semantics, never primitives. Below:
the type-scale + spacing tokens, the fluid-type math, and copy-paste output in all three formats.

## Type scale (fluid clamp)
Modular ratio × base (16–18px), ~5–7 steps. Make each fluid with a `rem` term preserved (zoom-safe).

**Math:** for size `minPx`→`maxPx` across viewport `minVw`→`maxVw` (px). Work in px, then convert the
intercept to rem:
- `slope = (maxPx − minPx) / (maxVw − minVw)`   (px of size per px of viewport)
- **`vw` coefficient `= slope × 100`**   (the number before `vw`)
- `interceptPx = minPx − slope × minVw`  →  `interceptRem = interceptPx / 16`
- Result: `clamp(min_rem, interceptRem + (slope×100)vw, max_rem)`.

**Worked:** 16→32px from 320→1440px → `slope = 16/1120 = 0.014286`; `vw coeff = 1.4286`;
`interceptPx = 16 − 0.014286·320 = 11.43px = 0.714rem` → `clamp(1rem, 0.714rem + 1.43vw, 2rem)`.
(Or just use utopia.fyi and paste the output.)

```css
:root {
  /* fluid type scale (ratio ~1.25, base ~18px) */
  --text-xs:   clamp(0.75rem, 0.73rem + 0.10vw, 0.80rem);
  --text-sm:   clamp(0.875rem, 0.85rem + 0.12vw, 0.95rem);
  --text-base: clamp(1rem, 0.96rem + 0.20vw, 1.125rem);
  --text-lg:   clamp(1.20rem, 1.13rem + 0.35vw, 1.45rem);
  --text-xl:   clamp(1.50rem, 1.38rem + 0.60vw, 1.95rem);
  --text-2xl:  clamp(1.95rem, 1.74rem + 1.05vw, 2.85rem);
  --text-3xl:  clamp(2.50rem, 2.10rem + 2.00vw, 4.20rem);
  --text-4xl:  clamp(3.20rem, 2.50rem + 3.50vw, 6.50rem); /* hero only */
  --leading-tight: 1.05; --leading-snug: 1.25; --leading-normal: 1.6; --leading-relaxed: 1.75;
  --tracking-tight: -0.02em; --tracking-wide: 0.06em;
  --measure: 66ch;
}
```

## Spacing, radii, depth tokens
```css
:root {
  /* 8-pt scale (4px sub-unit) */
  --space-1: 0.25rem; --space-2: 0.5rem; --space-3: 0.75rem; --space-4: 1rem;
  --space-5: 1.5rem;  --space-6: 2rem;   --space-8: 3rem;    --space-10: 4rem;
  --space-12: 6rem;   --space-16: 8rem;  --space-20: 12rem;
  /* fluid section padding */
  --section-y: clamp(4rem, 8vw, 10rem);
  /* radii — pick one family */
  --radius-sm: 6px; --radius-md: 10px; --radius-lg: 16px; --radius-xl: 24px; --radius-full: 9999px;
  /* layered soft shadows (light mode) */
  --shadow-sm: 0 1px 2px oklch(0 0 0 / .06), 0 1px 1px oklch(0 0 0 / .04);
  --shadow-md: 0 4px 8px oklch(0 0 0 / .06), 0 2px 4px oklch(0 0 0 / .05);
  --shadow-lg: 0 12px 24px oklch(0 0 0 / .08), 0 4px 8px oklch(0 0 0 / .05);
}
```

> **Default = Output B (Tailwind v4 + shadcn).** Use Outputs A/C only when the project isn't Tailwind.

## Output A — CSS custom properties (portable fallback)
Wrap primitives + semantics in `:root`; put the dark remap in `[data-theme="dark"]` (see
`dark-mode-and-depth.md`). This works in any stack. Toggle with `document.documentElement.dataset.theme`.

## Output B (DEFAULT) — Tailwind v4 + shadcn/ui
Tailwind v4 has no `tailwind.config.js` by default — define tokens in CSS with `@theme`. The names become
utilities (`bg-bg`, `text-primary`, `p-section`, `text-2xl`, `rounded-lg`).

```css
@import "tailwindcss";
@theme {
  --color-bg: oklch(0.985 0.003 255);
  --color-surface: oklch(0.967 0.004 255);
  --color-border: oklch(0.922 0.006 255);
  --color-text: oklch(0.205 0.007 255);
  --color-text-muted: oklch(0.556 0.012 255);
  --color-primary: oklch(0.600 0.205 255);
  --color-primary-hover: oklch(0.512 0.190 255);
  --color-danger: oklch(0.58 0.21 25);
  --font-display: "Clash Display", sans-serif;
  --font-sans: "General Sans", system-ui, sans-serif;
  --font-mono: "Geist Mono", ui-monospace, monospace;
  --text-2xl: clamp(1.95rem, 1.74rem + 1.05vw, 2.85rem);
  --spacing-section: clamp(4rem, 8vw, 10rem);
  --radius-lg: 16px;
}
```

**shadcn mapping.** shadcn components read a fixed set of semantic CSS variables — point them at your
tokens (in `:root` + `.dark`) so the whole component layer inherits the system. Use OKLCH values
directly (shadcn supports any CSS color since the Tailwind-v4 update); set `--radius` once.

```css
:root {
  --background: var(--color-bg);          --foreground: var(--color-text);
  --card: var(--color-surface);           --card-foreground: var(--color-text);
  --popover: var(--color-surface);        --popover-foreground: var(--color-text);
  --primary: var(--color-primary);        --primary-foreground: oklch(0.985 0 0);
  --secondary: var(--color-surface);      --secondary-foreground: var(--color-text);
  --muted: var(--color-surface);          --muted-foreground: var(--color-text-muted);
  --accent: var(--color-surface);         --accent-foreground: var(--color-text);
  --destructive: var(--color-danger);     --destructive-foreground: oklch(0.985 0 0);
  --border: var(--color-border);          --input: var(--color-border);
  --ring: var(--color-primary);           --radius: 0.625rem;
}
.dark { /* repeat with the dark-mode token values from dark-mode-and-depth.md */ }
```

## Output C — DTCG / W3C design tokens (when a design team / multi-platform pipeline exists)
Author tokens as JSON (W3C DTCG, stable spec 2025.10), transform with **Style Dictionary v4** → CSS
vars / SCSS / JS / iOS / Android. Three-tier structure; semantics `$value` reference primitives via
`{...}`.

```json
{
  "color": {
    "blue": { "600": { "$type": "color", "$value": "oklch(0.600 0.205 255)" } },
    "neutral": { "900": { "$type": "color", "$value": "oklch(0.205 0.007 255)" } }
  },
  "semantic": {
    "primary": { "$type": "color", "$value": "{color.blue.600}" },
    "text":    { "$type": "color", "$value": "{color.neutral.900}" },
    "bg":      { "$type": "color", "$value": "{color.neutral.50}" }
  },
  "space": { "4": { "$type": "dimension", "$value": "1rem" } }
}
```
Pipeline: Figma variables → DTCG JSON → Style Dictionary → CSS vars (then Tailwind `@theme` or shadcn
theme can consume them). This is the framework-neutral source of truth for cross-platform/teamed work.

## Choosing the output
- **Default → Tailwind v4 `@theme` + shadcn mapping** (Output B). This is the house stack; reach for it
  unless the repo says otherwise.
- Vanilla / non-Tailwind framework → **CSS custom properties** (Output A).
- Design team or React Native + web → **DTCG + Style Dictionary** (Output C).
Emit **one** source of truth (don't hand-roll a `:root` set *and* an `@theme` block — pick one) and have
components reference only semantic names.
