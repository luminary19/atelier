# Setup — Next/Vite + Tailwind v4 + shadcn + Storybook

## Project + Tailwind v4
```bash
# Next.js (recommended for marketing + app)
npx create-next-app@latest my-app --ts --app --eslint
cd my-app
npm install tailwindcss @tailwindcss/postcss
```
Tailwind v4 is CSS-first — no `tailwind.config.js`. In your global CSS:
```css
@import "tailwindcss";
@theme {
  /* paste the atelier-foundations @theme tokens here (colors in oklch, spacing, fonts, radii) */
}
```
(Vite: `npm create vite@latest` + `@tailwindcss/vite` plugin instead of postcss.)

## shadcn/ui init
```bash
npx shadcn@latest init           # pick Base UI (modern, MUI team) or Radix (broadest set)
npx shadcn@latest add button card dialog dropdown-menu input label sonner
```
- `components.json` controls paths + style; with v4 it leaves `tailwind.config` blank and
  `cssVariables: true`.
- shadcn copies component **source** into `components/ui/` — you own + edit it.
- Helpers it installs: `lucide-react` (icons), `class-variance-authority` (cva, for variants),
  `clsx` + `tailwind-merge` exposed as `cn()`.

```ts
// lib/utils.ts
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
export const cn = (...i: ClassValue[]) => twMerge(clsx(i));
```

## Token wiring → shadcn (do this immediately after init)
Map shadcn's semantic vars to the atelier-foundations OKLCH tokens so every component inherits the system.
Put this in global CSS (see foundations' `tokens-and-output.md` for the full block):
```css
:root {
  --background: var(--color-bg); --foreground: var(--color-text);
  --primary: var(--color-primary); --primary-foreground: oklch(0.985 0 0);
  --card: var(--color-surface); --muted-foreground: var(--color-text-muted);
  --border: var(--color-border); --ring: var(--color-primary); --radius: 0.625rem;
  /* ...rest of the mapping... */
}
.dark { /* dark-mode token values from foundations' dark-mode-and-depth.md */ }
```
Dark-mode toggle: `next-themes` (`<ThemeProvider attribute="class">`) toggles `.dark` on `<html>`.

## cva variant pattern (custom components)
```ts
import { cva, type VariantProps } from "class-variance-authority";
const badge = cva("inline-flex items-center rounded-full px-2.5 py-0.5 text-xs font-medium", {
  variants: { tone: { neutral: "bg-muted text-foreground", brand: "bg-primary/10 text-primary",
                      danger: "bg-destructive/10 text-destructive" } },
  defaultVariants: { tone: "neutral" },
});
```

## Storybook 9 (only for reusable component libraries)
```bash
npx storybook@latest init     # auto-detects Vite/Next
```
v9 is testing-centric: interaction tests (Vitest), a11y tests (axe across all stories), visual
regression, a Testing Widget. Write a story per component state; the a11y addon flags contrast/roles/names
automatically. Skip Storybook for one-off pages — it's overhead you don't need there.

## Fonts (premium foundries are first-class — see atelier-typography)
- Google/Fontshare/self-host: `next/font/local` or `next/font/google`, expose as `--font-display/-sans/-mono`
  and reference them in `@theme`.
- Premium foundry webfont kits: host per license, declare `@font-face`, wire the same CSS vars. Preload the
  critical face; subset; `font-display: swap` with a metric-matched fallback (or `optional`).
