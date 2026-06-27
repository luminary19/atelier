# Grid recipes — Grid / Flex / Subgrid / container queries

Mental model: **Flexbox = 1D, content-out** (sizes from content, distribute leftover). **Grid = 2D,
layout-in** (define structure, items flow in). **Subgrid** inherits parent tracks. **Container queries**
make components adapt to their container. They cooperate — don't pick one religiously.

## 12-column grid (page scaffold)
```css
.grid12 { display: grid; grid-template-columns: repeat(12, 1fr); gap: var(--space-5);
  max-width: 80rem; margin-inline: auto; padding-inline: var(--space-5); }
.col-4  { grid-column: span 4; }   .col-6 { grid-column: span 6; }   .col-8 { grid-column: span 8; }
```

## App shell with grid-template-areas (dashboards)
Self-documenting and re-flowable per breakpoint without touching markup.
```css
.app {
  display: grid; min-height: 100svh;
  grid-template-columns: 248px 1fr;
  grid-template-rows: auto 1fr auto;
  grid-template-areas: "header header" "sidebar main" "footer footer";
}
.app > header { grid-area: header; } .app > nav { grid-area: sidebar; }
.app > main { grid-area: main; }     .app > footer { grid-area: footer; }
@media (max-width: 768px) {
  .app { grid-template-columns: 1fr; grid-template-areas: "header" "main" "footer"; } /* sidebar → drawer */
}
```
Each named area must be rectangular; use `.` for empty cells.

## The no-media-query responsive grid
```css
.cards { display: grid; gap: var(--space-5);
  grid-template-columns: repeat(auto-fit, minmax(min(260px, 100%), 1fr)); }
```
`auto-fit` collapses empty tracks so items stretch; `auto-fill` keeps phantom empty tracks. The
`min(260px, 100%)` floor prevents overflow on tiny viewports.

## Subgrid — align card internals across siblings
Cards with image/title/body/footer of varying length normally misalign. Subgrid fixes it — but the
**parent must define the shared row tracks**, or the card's `grid-template-rows: subgrid` has nothing to
inherit (the common mistake: a parent with only `grid-template-columns`):
```css
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  /* the 4 internal tracks the cards SHARE — defined on the PARENT so subgrid has rows to inherit */
  grid-auto-rows: auto auto 1fr auto;   /* media · title · body(fills) · footer */
  gap: var(--space-5);
}
.card {
  display: grid;
  grid-row: span 4;             /* occupy the parent's 4 internal rows */
  grid-template-rows: subgrid;  /* inherit them → media/title/body/footer align across the row band */
}
/* Alignment is per row-band: cards in the SAME row align to each other (the intended behavior). */
```

## Container queries — portable components
A component sized by *its container*, not the viewport — drop the same card in a sidebar vs a hero and
it adapts itself.
```css
.panel { container-type: inline-size; container-name: panel; }
.card { display: grid; gap: var(--space-3); }
@container panel (min-width: 480px) {
  .card { grid-template-columns: 160px 1fr; align-items: center; }
}
```
Container query units: `cqw`, `cqi` (inline), `cqmin`. Use for anything reused in different-width slots.

## Intrinsic sizing primitives
`min-content` / `max-content` / `fit-content(x)` / `minmax(min, max)`. `minmax(0, 1fr)` (the `0` floor)
stops flex/grid children with intrinsic min-width from blowing out the track. `clamp()` for fluid track
sizes and gaps.

## Form layout (a first-class archetype)
Forms are a layout problem before a validation one (validation logic → `atelier-components` rhf+zod;
target-size/focus a11y → `atelier-perf-a11y`; multi-step *flow* → `atelier-ux`). The structure that reads considered:
- **One column by default.** Multi-column forms break the vertical scan and the tab order; reserve two
  columns for genuinely paired fields (city/zip, first/last) via a nested grid that collapses to one:
  ```css
  .form  { display: grid; gap: var(--space-4); max-width: 40rem; }       /* ~a form's worth of measure */
  .field { display: grid; gap: var(--space-1); }                         /* label · control · help/error */
  .row-2 { display: grid; gap: var(--space-4);
           grid-template-columns: repeat(auto-fit, minmax(min(220px,100%), 1fr)); } /* pairs → 1 col on narrow */
  ```
- **Labels above the control** — fastest to scan, no width guessing, RTL-safe, best on mobile. Inline labels
  only for dense settings rows in a stable language.
- **Group with `<fieldset>`/`<legend>`** (semantic grouping = free a11y) and section headings; group with
  proximity/whitespace, not boxes.
- **Reserve the message row** so showing an error doesn't shift layout (`min-height` on the help/error line);
  every control ≥ the 24×24 target; vertical rhythm on the spacing scale.
- **Actions:** one primary (left-aligned to the form, or full-width on mobile) at the bottom; rest
  secondary/ghost. Sticky action bar for long or multi-step forms.

## Flexbox where it belongs
```css
.toolbar { display: flex; align-items: center; gap: var(--space-3); flex-wrap: wrap; }
.card    { display: flex; flex-direction: column; }
.card .cta { margin-top: auto; }   /* pin footer to bottom regardless of body length */
.center  { display: grid; place-items: center; }  /* shortest true centering */
```
Heuristic: layout defined by content in one direction → Flex; defined by a 2D structure → Grid;
cross-sibling alignment → Subgrid; reuse across widths → container queries.
