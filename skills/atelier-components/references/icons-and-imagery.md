# Icons & imagery — implementation

Builds the visual-asset *language* decided in `atelier-direction/references/imagery-and-iconography.md`.
Generate real assets via **`/codex-imagegen`** (see this skill's SKILL.md §5); optimize and gate at
`atelier-perf-a11y` (CLS, contrast, `alt`).

## Icon system
- **Tree-shaken SVG components, not an icon font.** `lucide-react` (shadcn default) or `@phosphor-icons/react`
  import only the icons you use; an icon *font* ships the whole set and is a11y-hostile.
```tsx
import { Search, ArrowRight } from "lucide-react";
<Search className="size-4" />                          {/* size + color inherit via currentColor */}
<button aria-label="Search"><Search className="size-5" /></button>  {/* icon-only MUST have a name */}
```
- **One set, one style, one grid.** Don't mix libraries or filled+outline. Set a default stroke/size once
  (Lucide: `<LucideIcon strokeWidth={1.75} />` or a wrapper) so every icon matches the type weight + `--radius` feel.
- **`currentColor` + `size-*`** — icons follow text color and size; never hard-code icon color. Decorative
  icons get `aria-hidden="true"`; meaningful icon-only controls get `aria-label`.
- **Custom icons:** author as React SVG components on the same viewBox/grid (e.g. `0 0 24 24`,
  `stroke-width:2`, `stroke="currentColor"`); for many custom glyphs use one **SVG sprite** (`<svg><use href="/sprite.svg#id"/>`).
- **Animated icons:** CSS/Motion for micro (hover morph, menu↔close), **Rive**/**Lottie** for richer state
  (`atelier-motion`); always respect reduced motion.

## Responsive images
**Next.js — `next/image`** (handles srcset, lazy, formats, blur):
```tsx
import Image from "next/image";
// LCP hero — eager + priority; sized to its slot to avoid CLS
<Image src="/hero.webp" alt="" width={1536} height={1024} priority sizes="100vw"
       placeholder="blur" blurDataURL={blur} className="w-full h-auto object-cover" />
// below the fold — lazy by default; give real sizes so the right srcset is picked
<Image src={img} alt="Team reviewing a dashboard" fill sizes="(max-width:768px) 100vw, 50vw"
       className="object-cover" />   {/* parent needs position:relative + a sized box */}
```
**No framework — `<picture>` / `<img srcset>`:** AVIF → WebP → fallback, always `width`/`height` (CLS),
`loading="lazy"` + `decoding="async"` below the fold (**never** the LCP image — that's eager +
`fetchpriority="high"`), real `alt` (`alt=""` if decorative).
```html
<picture>
  <source type="image/avif" srcset="hero-800.avif 800w, hero-1536.avif 1536w" sizes="100vw" />
  <source type="image/webp" srcset="hero-800.webp 800w, hero-1536.webp 1536w" sizes="100vw" />
  <img src="hero-1536.jpg" width="1536" height="1024" alt="" fetchpriority="high" />
</picture>
```
- **Art-directed `<picture>`** (different *crop* per breakpoint, not just size) uses `<source media="(max-width:768px)" srcset="hero-portrait.webp">`.
- **Reserve the slot** with `aspect-ratio` + `object-fit: cover` so media never shifts layout (CLS) — pair
  with the `atelier-layout` slot.

## CSS image treatment (one house look across all imagery)
- **Scrim for text-over-image (a11y + craft):** never put text on a raw photo.
```css
.media-text { position: relative; }
.media-text::after { content:""; position:absolute; inset:0;
  background: linear-gradient(to top, oklch(0 0 0 / .6), transparent 60%); }  /* darken behind copy */
```
- **Duotone / grade to the palette** (unify mismatched photos): a `mix-blend-mode` color wash, or an SVG
  `feColorMatrix`/`feComponentTransfer` duotone filter mapped to two brand colors. Apply *consistently*.
- **Grain on photos:** the `atelier-foundations` `.grain` overlay over the image ties generated/stock imagery
  into the house texture. **Dither/halftone** for editorial (see the Dithering aesthetic).
- Keep treatments a *system* (same grade/scrim everywhere), not per-image whim — inconsistency is the tell.

## Favicon & OG / social-card pipeline (brand artifacts, not defaults)
- **Replace the framework default favicon.** Ship a real set (`favicon.ico` + `icon.svg` + `apple-touch-icon`
  + maskable PWA icons); Next App Router auto-wires `app/icon.*` / `app/apple-icon.*`.
- **Designed `og:image`** (1200×630) controls every shared link — generate it on the aesthetic via
  `/codex-imagegen` (logo + headline + brand bg), or build dynamic ones with `next/og` (`ImageResponse`):
```html
<meta property="og:image" content="/og.png"><meta property="og:image:width" content="1200">
<meta name="twitter:card" content="summary_large_image">
```
- **Never** ship the gray default OG card or a missing favicon — both are first-impression slop. Verify in the
  perf/a11y + anti-slop gate.
