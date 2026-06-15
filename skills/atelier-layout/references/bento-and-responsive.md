# Bento, masonry & responsive

## Bento grid (Apple-keynote style)
Modular rounded tiles of *deliberately different sizes* — size contrast creates instant hierarchy. The
rule that makes it work: **one clear hero cell + purposeful variation, never a uniform box grid.**
```css
.bento {
  display: grid; grid-template-columns: repeat(4, 1fr); grid-auto-rows: 1fr; gap: var(--space-3);
}
.bento > * { border-radius: var(--radius-lg); background: var(--surface); padding: var(--space-5);
  display: flex; flex-direction: column; }     /* stretch fills the cell — no empty space */
.bento .hero { grid-column: span 2; grid-row: span 2; }
.bento .wide { grid-column: span 2; }
.bento .tall { grid-row: span 2; }
@media (max-width: 900px) { .bento { grid-template-columns: repeat(2, 1fr); } .bento .hero { grid-column: span 2; } }
@media (max-width: 560px) { .bento { grid-template-columns: 1fr; } .bento > * { grid-column: 1 / -1; grid-row: auto; } }
```
Rules: never leave empty cells (let cells stretch — keep default `align-items: stretch`); one consistent
radius + gap; one surface color; one idea per cell. **Avoid:** uniform equal boxes (kills hierarchy —
the whole point), cards-in-cards-in-cards, random spans with no compositional logic. It's a cliché when
overused — earn it with real hierarchy.

## Masonry / mosaic
For varied-height content (galleries, feeds). Native CSS masonry (`grid-template-rows: masonry`) is
still limited in support → for production use a columns approach or JS (or a CSS-grid `grid-auto-flow:
dense` approximation). Columns version:
```css
.masonry { columns: 3 280px; column-gap: var(--space-5); }
.masonry > * { break-inside: avoid; margin-bottom: var(--space-5); }
```
(Note: CSS `columns` flows top-to-bottom then across — fine for galleries, wrong if reading order matters.)

## Whitespace rhythm
- **Start with too much, then remove.** Cramped = cheap; spacious = expensive. The #1 premium signal.
- **Macro** (between sections) creates the airy, structured feel; **micro** (padding, gaps, line-height)
  creates legibility. Both off the 8-pt spacing tokens.
- Section vertical padding fluid: `padding-block: var(--section-y)` (`clamp(4rem, 8vw, 10rem)`). Keep all
  vertical spacing on the scale so rhythm stays consistent.

## Responsive essentials
- **Mobile heroes / full-screen:** `min-height: 100svh` (small viewport unit) so content isn't clipped
  under mobile browser UI on first paint. `lvh` = largest; `dvh` = live (use only for overlays/modals —
  it reflows during scroll and can jank). Avoid bare `100vh` on mobile.
- **Reserve media** to prevent layout shift (CLS): `img, video { aspect-ratio: 16/9; width: 100%;
  height: auto; }` and always set intrinsic `width`/`height` attributes.
- **Prefer intrinsic + container queries + `auto-fit/minmax`** over a thicket of width breakpoints.
- **Fluid everything:** `clamp()` for type, gaps, section padding; let the layout breathe between fixed
  breakpoints instead of snapping.
- Test the hero and any pinned/sticky sections at small laptop sizes — full-viewport heroes often push
  real content too far down; a hero rarely *needs* the whole screen.

## Page archetype skeletons (quick reference)
- **Marketing landing:** hero (asymmetric / giant-type) → logo strip → bento features (one hero cell) →
  alternating editorial rows → metrics/proof → testimonial → CTA → footer. Z-scan.
- **Dashboard:** app-shell grid (header/sidebar/main) → KPI row (equal cards OK here — it's data, not
  marketing) → main chart (large) + side panels (subgrid-aligned) → table (tabular figures).
- **Portfolio:** oversized type hero → broken-grid project tiles (varied sizes, overlap) → about (single
  measure column) → contact. Generous negative space.
- **Editorial:** title block → single 60–75ch measure with side-column captions/pull-quotes → related →
  footer. F-scan, intentional asymmetry around the measure.
