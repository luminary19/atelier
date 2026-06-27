# Encoding, color & number craft

## Visual channels — accuracy order (Cleveland–McGill)
How precisely people decode a value depends on the channel. Spend the most accurate channel on the most
important variable:

**position (common scale) > position (non-aligned) > length > angle/slope > area > volume > color hue/saturation**

Consequences: a **bar** (length from a zero baseline) is read more accurately than a **pie** (angle); a
**dot plot** (position) beats a heatmap (color) for exact comparison; **never encode magnitude by hue alone**
— color is the *least* accurate channel, so reserve it for *category*, and use lightness for ordered quantity.

## Palettes — wire from atelier-foundations (don't invent per chart)
The three families live in `atelier-foundations/references/color-oklch.md`; consume them here.
- **Categorical** (distinct, unordered series) → the **`--chart-1 … --chart-N`** tokens (hue rotated at fixed
  L/C so no series dominates). In shadcn charts, map them in `chartConfig` and reference `var(--color-<key>)`.
  **Cap at ~6–8**; beyond that, group "Other", facet into small multiples, or direct-label.
- **Sequential** (ordered, one hue: heatmap, choropleth, density) → sweep `L` along a single hue. OKLCH keeps
  the steps perceptually even, so equal data steps look equal — the whole reason to build in OKLCH.
- **Diverging** (a meaningful midpoint: profit/loss, above/below target) → two hues meeting at a neutral
  middle, **equal `L` range each arm**. Anchor the midpoint at the real zero, not the data median.
- **Highlight palette:** most series muted grey, the focal series in the brand accent — the cheapest way to
  give a chart a focal point. Semantic encodings stay fixed (success=green, danger=red) and must *also* carry
  a non-color cue.

```ts
// derive an N-step categorical set at runtime if you need more than the tokens
const cat = (n: number, i: number) => `oklch(0.70 0.15 ${(i * 360) / n})`;
```

## Colorblind-safe (mandatory for data — WCAG 1.4.1)
~8% of men can't separate red/green. Rules:
- Vary **lightness as well as hue** between series (so they survive greyscale).
- Add a **second channel**: direct labels, distinct markers/dash patterns, or icons — never color as the only key.
- Avoid the red→green ramp for diverging; prefer blue↔orange / purple↔teal.
- Test in a deuteranopia/protanopia simulator (DevTools → Rendering → Emulate vision deficiencies) and at greyscale.

## Strip to signal (subtraction = premium)
- **Direct-label over legend.** Put the series name at the line's end / on the bar; drop the legend when you
  can (a legend forces a back-and-forth lookup). When a legend is needed, order it to match the data.
- **Chartjunk to delete:** heavy gridlines (→ faint or none; keep only the axis the eye needs), chart borders,
  background fills, gradients-for-decoration, bar drop-shadows, redundant axis titles, value labels *and* a y-axis
  (pick one). Data-ink ratio: maximize ink that encodes data.
- **Gridlines:** horizontal-only for column charts, faint (`--border` at low alpha), behind the data.
- **Annotate the insight:** one threshold line, target marker, or "+12% YoY" callout beats another series.

## Number craft (charts are typography too)
- **`tabular-nums slashed-zero`** on every axis tick, tooltip, and value label (from `atelier-typography`) so
  digits don't jitter and zeros are unambiguous.
- **Format with `Intl.NumberFormat`**, never raw floats:
```ts
const compact = new Intl.NumberFormat("en", { notation: "compact", maximumFractionDigits: 1 }); // 12_400 → "12.4K"
const money   = new Intl.NumberFormat("en", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
const pct     = new Intl.NumberFormat("en", { style: "percent", maximumFractionDigits: 1 });
// Recharts: <YAxis tickFormatter={compact.format} />   <ChartTooltip ... valueFormatter />
```
- **Animated counters** (KPIs, totals) → **`NumberFlow`** (`@number-flow/react`, from `atelier-motion`):
  accessible, `Intl`-aware, respects reduced motion. Never a hand-rolled odometer.
- **Axis honesty:** bar/column y-axis **starts at zero**; line charts may crop to show variation but say so;
  keep tick counts low (4–6), round to human numbers, and label units once (axis title or suffix), not per tick.
