---
name: atelier-dataviz
version: 1.0.0
description: >
  Atelier suite — the data-visualization layer. Turn data into charts that read clear and premium, not
  rainbow slop: choose the right chart for the question, encode values honestly (position > length > color),
  build on the house stack (shadcn Charts/Recharts → Tremor → visx/D3 → ECharts), strip to signal
  (restrained axes/legends/grid, direct labels, tabular number formatting), and ship ACCESSIBLE charts
  (keyboard, data-table fallback, real alt/aria, reduced-motion) — because canvas/SVG is invisible to screen
  readers. Use whenever building or fixing a chart, graph, plot, sparkline, KPI/metric/stat, gauge, heatmap,
  or the data *inside* a dashboard — or when a visualization looks cluttered, misleading, 3-D, or generic.
  Pulls categorical/sequential/diverging palettes from atelier-foundations; the dashboard *shell* + KPI-card
  layout is atelier-components; gated by atelier-perf-a11y. This is the canonical home for charting craft —
  prefer it over reaching for a chart lib blindly. Part of the Atelier suite.
triggers:
  - data visualization
  - dataviz
  - chart
  - graph
  - plot a chart
  - dashboard charts
  - kpi / metric card
  - sparkline
  - visualize data
  - make this chart better
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Atelier — Data Visualization

Charts are where "data product" most reliably turns to slop: rainbow categorical palettes, 3-D pie charts,
dual-axis combos, truncated bars that lie, legends nobody reads, and chartjunk drowning the one number that
matters. The discipline here is the opposite of decoration: **the chart serves a question, encodes the data
honestly, and strips everything that isn't signal.** A clean bar chart beats a beautiful wrong one — and if
a table answers the question better, you ship the table.

> **Project memory:** if **`ATELIER.md`** exists, read it first and honor its register + tokens (set up via
> **`/atelier init`** — the **`atelier`** router).
>
> **Inputs:** the Direction Doc (aesthetic, density, light/dark) + **chart palettes from `atelier-foundations`**
> (`atelier-foundations/references/color-oklch.md` → categorical / sequential / diverging + the `--chart-N` tokens). **Default
> stack:** shadcn Charts (Recharts) → Tremor (dashboards) → visx / D3 (bespoke) → ECharts (heavy/real-time).
> **Defers:** the dashboard *shell*, KPI-card *layout*, and data-table component → `atelier-components`;
> animated counters → `atelier-motion` (`NumberFlow`); empty/error-state + axis-label copy → `atelier-copy`;
> real/empty/huge-data resilience → `atelier-harden`. **Gate:** `atelier-perf-a11y` is mandatory — charts
> are a top a11y and INP failure. Deep reference:
> `references/fundamentals-deepdive.md` (§7 Color, §9 Design Systems, §13 Perf & a11y).
>
> **Data — `atelier-data`:** chart-type → library / a11y guidance via `scripts/search.py "<data question>" --domain chart`. A quick cross-check; chart craft, palettes, and a11y are decided here.

---

## The flow

1. **Frame the question** → 2. **Pick the chart** (match the data relationship) → 3. **Choose the tool**
(layered stack) → 4. **Encode honestly** (channels + palette) → 5. **Strip to signal** (axes/legend/labels/
numbers) → 6. **States + accessibility** → gate with `atelier-perf-a11y`.

## 1. Frame the question (before any chart type)

A chart that doesn't answer a question is decoration. State, in one line, **what the viewer should learn**
("is revenue trending up?", "which region leads?", "how is latency distributed?"). That fixes the *data
relationship*, which fixes the chart:

| Relationship | The question | Default chart |
|---|---|---|
| **Trend over time** | how does X move? | line (continuous) / area (volume) / bar (few discrete periods) |
| **Comparison** | which is bigger? | **bar** (the workhorse — horizontal when labels are long) |
| **Part-to-whole** | what's the mix? | stacked bar / **100% stacked** / treemap — *rarely* a pie (≤4 slices only) |
| **Distribution** | how is it spread? | histogram / box / violin / strip |
| **Correlation** | does X relate to Y? | scatter / bubble (3rd dim = size) |
| **Single value vs target** | are we on track? | KPI/stat (number-first) / gauge / bullet |
| **Flow / hierarchy** | how does it move/nest? | sankey / treemap / funnel |
| **Geo** | where? | choropleth / symbol map |

If the answer is "a precise lookup of many exact values," the right "chart" is a **table** (→ `atelier-components`).

## 2. Pick the chart — and the anti-slop rules

Full selection guide + Recharts/shadcn recipes in **`references/chart-recipes.md`**. The non-negotiables:
- **Bars start at zero.** A truncated y-axis on a bar chart is a lie (line charts *may* crop to show variation).
- **No pie soup** — humans can't compare angles; >4 slices → bar or 100%-stacked. **No 3-D anything** (3-D
  distorts the encoding for style). **No dual-axis** combos (the crossover point is arbitrary/misleading).
- **One question per chart.** Two questions → two charts (small multiples), not one overloaded combo.
- **Small multiples beat a 9-series spaghetti line.** Repeat a small chart per category; shared scale.
- **Sparklines** for trend-at-a-glance inside tables/KPIs (no axes, ~3-line tall).

## 3. Choose the tool (the layered stack)

Default low, escalate only when the data demands it. Install/usage in **`references/chart-recipes.md`**.
- **shadcn Charts (Recharts) — DEFAULT.** `npx shadcn@latest add chart` gives you `ChartContainer` +
  `ChartConfig` + `ChartTooltip`/`ChartLegend` over Recharts; colors come from your `--chart-N` tokens via
  `var(--color-<key>)`, so charts inherit the design system. **Recharts 3 ships the a11y layer on by
  default** (keyboard + ARIA). You own the code. Best for standard line/bar/area/scatter/pie.
- **Tremor** — fastest premium *dashboards* (KPI cards, charts, tables in one kit; Vercel/MIT). Reach for it
  when you want a whole analytics surface fast and less low-level control. (Already curated in `atelier-components`.)
- **visx + D3** — when you need a chart Recharts doesn't ship or pixel-level control (bespoke/award-grade):
  visx = D3 math + React rendering. Most code, highest ceiling. **Observable Plot** for fast exploratory/custom.
- **ECharts (or Chart.js)** — canvas engines for **huge datasets, real-time streams, or finance** (candlesticks,
  10k+ points) where SVG would choke. Accept the bundle + the canvas-a11y cost (table fallback is mandatory).

> **Render target matters:** SVG (Recharts/visx) is inspectable + stylable + somewhat AT-reachable; canvas
> (ECharts/Chart.js) is faster for big N but **opaque to assistive tech** → always pair a table.

## 4. Encode honestly (map data → visual channels)

The channel you choose decides how accurately people read the value. Full guidance + the palette wiring in
**`references/color-and-encoding.md`**.
- **Accuracy order:** position > length > angle/slope > area > **color/saturation** (least accurate). Put the
  most important variable on the most accurate channel; never encode magnitude by hue alone.
- **Color is for category, lightness is for quantity.** Pull palettes from `atelier-foundations`:
  **categorical** (rotate hue at fixed L/C — the `--chart-N` tokens), **sequential** (one hue, sweep L — heatmaps),
  **diverging** (two hues, neutral midpoint — +/−). Cap categorical at **~6–8**; past that, group or direct-label.
- **Colorblind-safe is mandatory:** vary lightness *and* hue, add a second channel (shape, dash, direct label).
  Verify in a deuteranopia simulator. (1.4.1 — never color alone.)

## 5. Strip to signal (the restraint that reads premium)

Most "premium chart" work is subtraction. Recipes in `references/color-and-encoding.md`:
- **Direct-label the data** (line ends, bar tips) and **drop the legend** where you can — a legend is a lookup tax.
- **Kill chartjunk:** no heavy gridlines (faint or none), no chart borders, no background fills, no drop
  shadows on bars, no redundant axis titles. One faint baseline beats a full grid.
- **Numbers like a typographer:** `tabular-nums` + `slashed-zero` on every value/axis (from `atelier-typography`);
  format with **`Intl.NumberFormat`** (compact `1.2M`, currency, %, locale) — never raw floats. Animated
  counters use **`NumberFlow`** (`atelier-motion`), not a hand-rolled odometer.
- **Annotate the insight:** a single threshold line, target marker, or "+12% YoY" callout does more than another series.

## 6. States + accessibility (the part everyone skips)

A chart is a component — it needs every non-happy state, and a non-visual path. Patterns in
**`references/dashboards-and-accessible-charts.md`**.
- **States:** loading = **skeleton at the chart's final dimensions** (reserve height → no CLS; shimmer from
  `atelier-motion`, static under reduced motion); **empty / no-data** = a labeled message + next action, never a
  blank box or `0`-line; **error** = human cause + retry, keep the axes; **partial/stale** = badge it.
- **Accessibility (non-negotiable — gate at `atelier-perf-a11y`):**
  - **Provide the data as a table.** Canvas is invisible to AT; even SVG charts should ship a visually-hidden
    `<table>` (or a toggle) carrying the same numbers — this is the real fallback, not `alt` text.
  - **Keyboard + ARIA:** Recharts 3's `accessibilityLayer` is on by default (arrow-key datapoint nav, roles);
    add a concise `aria-label`/figure caption stating the takeaway ("Revenue by month, trending up 12%").
  - **Reduced motion:** chart entrance/scrub animations are decorative — under `prefers-reduced-motion` render
    the final state immediately (no draw-on, no count-up).
  - **Not color alone, contrast ≥3:1** for series vs background, and don't put meaning only in a hover tooltip
    (touch + keyboard users can't reliably reach it).
- **Perf:** SVG degrades past a few thousand nodes → switch to canvas (ECharts) or downsample/aggregate;
  virtualize/decimate real-time streams; heavy continuous redraws inflate INP — throttle and pause offscreen.

---

## Operating principles
- **The chart serves the question.** If a table or a single big number answers it better, ship that.
- **Encode honestly:** position over color, bars from zero, no 3-D / dual-axis / pie-soup. The encoding is the ethics.
- **Restraint is the premium move** — direct labels, no chartjunk, tabular figures, one annotated insight.
- **Every chart needs a non-visual path** — a real data table + aria, because canvas/SVG is opaque to AT.
- **Default to shadcn/Recharts on your tokens;** escalate to Tremor / visx / ECharts only when the data demands.
- **Inherit the system:** chart colors are `--chart-N` tokens from `atelier-foundations`, numbers are
  `tabular-nums`, motion respects the budget — so charts look designed, not bolted on.
