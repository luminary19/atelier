---
name: atelier-layout
version: 1.0.0
description: >
  Atelier suite — premium layout & composition. Structure pages and sections so they read intentional
  and "expensive": choose the right layout archetype, build it with modern CSS (Grid, Subgrid, Flexbox,
  container queries), apply composition models (rule of thirds, F/Z patterns, asymmetry/broken grid),
  use Gestalt grouping and clear visual hierarchy, and deploy generous active whitespace. Use this
  whenever laying out a page or section, building a grid / bento / dashboard / hero, making something
  responsive, or when a layout feels cramped, flat, centered-and-boring, or templated. Run after
  atelier-direction (layout archetype) using atelier-foundations spacing tokens.
triggers:
  - layout
  - page structure
  - grid
  - bento grid
  - composition
  - whitespace
  - responsive layout
  - hero section
allowed-tools:
  - Read
  - Write
  - Edit
---

# Atelier — Layout & Composition

Layout is where "premium" is won quietly. **Generous active whitespace and clear hierarchy are the #1
signal that a design is bespoke**, not templated. The slop tells here: everything centered, three equal
cards, uniform bento boxes, cramped spacing, no focal point. This skill structures pages so the eye is
led and the page breathes.

> **Project memory:** if **`ATELIER.md`** exists, read it first and honor its register, density, and
> anti-references (set up via **`/atelier init`** — the **`atelier`** router).
>
> **Inputs:** the sitemap / screens / nav model from **`atelier-ux`**; layout archetype + world + **density**
> from the Direction Doc; spacing/radii tokens from `atelier-foundations`. Deep reference: `references/fundamentals-deepdive.md` (§8 layout).

---

## The flow

1. **Pick the archetype** → 2. **Choose the engine** (Grid/Flex/Subgrid/container) → 3. **Composition
model** → 4. **Gestalt + hierarchy** → 5. **Whitespace rhythm** → 6. **Responsive**.

## 1. Pick the layout archetype

Match structure to page kind (per the Direction Doc's world):
- **Marketing/landing** — hero (asymmetric or giant-type, not always center) → bento feature grid →
  alternating editorial rows → social proof → CTA. Z-pattern scanning.
- **Web app/dashboard** — app shell (`grid-template-areas`: header/sidebar/main), data-dense modular
  grid, subgrid for aligned cards, container queries for portable panels. (Build the shell, tables, and
  forms with `atelier-components`; this skill sets their *structure*.)
- **Portfolio/creative** — broken grid, overlap, large media, asymmetry, generous negative space.
- **Editorial/content** — single strong column at 60–75ch, side-column captions/pull-quotes, F-pattern,
  intentional asymmetry around the measure.
- **Forms** (any kind) are their own structural archetype — single column, labels-above, grouped with
  `<fieldset>`, message row reserved, action bar at the bottom. Recipe in `references/grid-recipes.md`
  (validation logic → `atelier-components`; multi-step *flow* → `atelier-ux`).

## 2. Choose the engine

Mental model — *don't* treat these as competitors (full recipes in **`references/grid-recipes.md`**):
- **Flexbox = 1D, content-out** — navs, toolbars, tag rows, card internals (`margin-top:auto` to pin a
  footer), anything that should wrap.
- **CSS Grid = 2D, layout-in** — page templates, dashboards, bento, galleries. Use `grid-template-areas`
  for app shells (self-documenting, re-flowable per breakpoint).
- **Subgrid** (Baseline Widely Available 2026-03, ~95%+) — make card internals (image/title/body/footer)
  align *across* sibling cards regardless of content length: `grid-template-rows: subgrid`.
- **Container queries** (Baseline now) — `container-type: inline-size` + `@container` so a component
  adapts to *its container*, not the viewport → genuinely portable components. Use for anything reused
  in different-width slots. **Style queries** (`@container style(--variant: hero)`) are cross-browser too
  (Baseline after FF151) — fork on a custom-property value, not just size.
- **Anchor positioning** (Baseline early 2026 — Chrome 125 / Safari 26 / FF 147) — tether a popover/menu/
  tooltip to a reference element in pure CSS (`anchor-name` + `position-anchor` + `anchor()` / `position-area`;
  `@position-try` auto-flips on overflow). Pairs with the **Popover API** → the native replacement for
  Floating UI / Popper; reach for it before a JS positioning lib.
- **The no-media-query responsive grid:** `grid-template-columns: repeat(auto-fit, minmax(250px, 1fr))`.

## 3. Composition model

Avoid the default centered stack. Pick a model and break symmetry intentionally:
- **Rule of thirds** — place focal elements on the power points, not dead center.
- **F-pattern** (text-dense) — key info top + left. **Z-pattern** (sparse/landing) — logo TL, CTA TR
  then BR.
- **Asymmetry / broken grid** — offset, overlap, uneven columns for energy and an editorial feel —
  **balanced by visual weight** (a large element answered by whitespace or a cluster), never random.
- Details and when-to-use in **`references/composition-gestalt.md`**.

## 4. Gestalt + hierarchy

- **Hierarchy via** size, weight, color, position, contrast → one dominant focal point per view; the
  single accent color marks the primary CTA. De-emphasize secondary text with a lighter token, don't
  just enlarge the primary.
- **Gestalt grouping** (concrete UI applications in `references/composition-gestalt.md`): proximity
  (group by spacing — cheaper than borders), similarity (consistent component styles), common region
  (cards/sections), continuity (aligned fields guide the scan), figure/ground (modal + scrim).

## 5. Whitespace rhythm

- **Start with too much whitespace, then remove.** Cramped = cheap; spacious = expensive.
- **Macro** whitespace (between sections) creates the airy, structured feel; **micro** (padding,
  line-height, gaps) creates legibility. Both from the 8-pt spacing tokens.
- Section padding scales with viewport (`clamp()`); keep vertical rhythm on the spacing scale.
- **The Direction Doc's `density` sets the baseline reach:** *airy* → large gaps + wide `--section-y`,
  fewer elements per view (art-gallery); *balanced* → mid; *packed* → tighter gaps + denser grids, more
  per view (cockpit/editorial) — still on the 8-pt scale. The dashboard archetype is inherently *packed*;
  portfolio/editorial usually *airy*.

## 6. Responsive

- **Mobile heroes/full-screen:** use **`min-height: 100svh`** (small viewport unit) so content isn't
  clipped under mobile browser UI on first paint; `dvh` only for overlays (it reflows during scroll).
- **Reserve media** with `aspect-ratio` to prevent layout shift — **CLS + responsive are verified at the
  `atelier-perf-a11y` gate** (this is where layout meets the perf budget). Fill those media slots with
  **real generated assets at the slot's aspect ratio** (via `/codex-imagegen` → 1536×1024 / 1024×1024 /
  1024×1536, then WebP/AVIF), not text-on-gradient placeholders — an empty or faked media slot is the
  layout Tell that undoes the composition.
- Prefer intrinsic sizing + container queries + the `auto-fit/minmax` grid over a thicket of breakpoints.
- **`field-sizing: content`** lets a `<textarea>`/`<input>`/`<select>` auto-grow to its content (cap with
  `max-block-size`) — kills the JS auto-resize-textarea pattern and its jank. Now in all three engines
  (Chrome 123 / Safari 26.2 / FF 152), on the cusp of Baseline; degrades to fixed sizing on older engines.
- Bento, masonry, and responsive recipes in **`references/bento-and-responsive.md`**.

---

## Operating principles

- **Whitespace and hierarchy first.** They do more for "premium" than any effect.
- **One focal point per view; break symmetry on purpose.** Centered-everything is the default that
  reads as templated.
- **Grid for 2D structure, Flex for 1D flow, subgrid/container-queries for real reuse.** Reach for
  `grid-template-areas` on app shells.
- **Visual order ≠ DOM order (a11y).** Flex `order`/`row-reverse`, `grid-auto-flow: dense`, and explicit
  grid placement move the *visual* layout but not keyboard/screen-reader order → a jumpy focus path
  (WCAG 2.4.3 / 1.3.2). Keep DOM order == reading order; `reading-flow`/`reading-order` is a fix but
  Chromium-only, not Baseline. Verified at the `atelier-perf-a11y` gate.
- **Bento needs hierarchy** — one hero cell and purposeful size variation, never a uniform box grid.
- **Default stack: Tailwind v4 + shadcn.** The CSS recipes here translate directly to Tailwind utilities
  (`grid`, `grid-cols-12`, `gap-*`, `@container`, `aspect-video`, `min-h-svh`); use shadcn for interactive
  components and the spacing/radius tokens from `atelier-foundations`. Drop to plain CSS only when the
  project isn't Tailwind.
