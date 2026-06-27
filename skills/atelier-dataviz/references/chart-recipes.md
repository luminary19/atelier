# Chart recipes — selection + the layered stack

## Chart selection (relationship → chart → watch-outs)
| You want to show | Use | Avoid / watch |
|---|---|---|
| Trend over continuous time | **line** (area if volume matters) | don't bar-chart 60 days; don't crop a *bar* y-axis |
| Few discrete periods (≤~12) | **bar / column** | start at zero |
| Compare categories | **bar** (horizontal if labels long) | sort by value, not alphabetically |
| Part-to-whole, 1 moment | **100% stacked bar** / treemap | pie only ≤4 slices; never 3-D pie |
| Part-to-whole over time | **stacked area** / 100% stacked bar | >5 bands = mush → small multiples |
| Distribution | **histogram / box / strip** | a bar of averages hides the spread |
| Correlation | **scatter** (bubble = +size) | overplotting → opacity / bin / hexbin |
| One value vs target | **KPI number / bullet / gauge** | a gauge for >1 value wastes space |
| Many series | **small multiples** (one mini-chart per category, shared scale) | 9-line spaghetti |
| At-a-glance trend in a row | **sparkline** (no axes, ~3 lines tall) | — |
| Flow / funnel / nesting | sankey / funnel / treemap | label everything; they're easy to misread |

**Sort, don't alphabetize** categorical bars (rank reveals the story). **Highlight one series** with the
accent and mute the rest to grey — "one focal point" applies to charts too.

## shadcn Charts (Recharts) — the default
`npx shadcn@latest add chart` copies a `chart` wrapper (`ChartContainer`/`ChartTooltip`/`ChartLegend`) over
Recharts into your repo. Colors come from `--chart-N` tokens
(`atelier-foundations/references/color-oklch.md`), referenced as `var(--color-<configKey>)`. **Recharts 3 supports `accessibilityLayer`** (keyboard + ARIA) — shadcn's
chart examples pass it on every chart; keep it on.

```tsx
"use client";
import { Bar, BarChart, CartesianGrid, XAxis } from "recharts";
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from "@/components/ui/chart";

const data = [
  { month: "Jan", desktop: 186, mobile: 80 }, { month: "Feb", desktop: 305, mobile: 200 },
  { month: "Mar", desktop: 237, mobile: 120 }, { month: "Apr", desktop: 173, mobile: 190 },
];
const chartConfig = {                                   // labels + colors live here
  desktop: { label: "Desktop", color: "var(--chart-1)" },
  mobile:  { label: "Mobile",  color: "var(--chart-2)" },
} satisfies ChartConfig;

export function Visitors() {
  return (
    <ChartContainer config={chartConfig} className="min-h-[200px] w-full"> {/* reserves height → no CLS */}
      <BarChart accessibilityLayer data={data}>
        <CartesianGrid vertical={false} />              {/* one axis of faint grid, not a cage */}
        <XAxis dataKey="month" tickLine={false} axisLine={false} tickMargin={10} />
        <ChartTooltip content={<ChartTooltipContent />} />
        <Bar dataKey="desktop" fill="var(--color-desktop)" radius={4} />
        <Bar dataKey="mobile"  fill="var(--color-mobile)"  radius={4} />
      </BarChart>
    </ChartContainer>
  );
}
```
- **Line / Area:** swap `BarChart`→`LineChart`/`AreaChart`, `Bar`→`Line`/`Area` (`type="monotone"`, `dot={false}`
  for clean lines; for area, define a `<linearGradient>` fill that fades to transparent). Keep `<YAxis>` off
  when you direct-label or when the tooltip suffices — less ink.
- **Theming:** because fills are `var(--color-*)` → `--chart-N`, the chart re-themes with light/dark and any
  brand remap automatically. Never hard-code hex in a chart.
- **How it wires up:** the `chart` wrapper's `ChartStyle` injects each config key's color as a `--color-<key>`
  CSS var scoped to `[data-chart=<id>]`, so `var(--color-desktop)` resolves per chart instance and swaps with
  light/dark. `ChartTooltipContent` formats values with `tabular-nums` (no jitter); set its marker via
  `<ChartTooltipContent indicator="line|dot|dashed" />`.

## Sparkline (in a table cell / KPI)
A Recharts `LineChart` with everything stripped — no axes, grid, or tooltip, fixed tiny height:
```tsx
<ChartContainer config={cfg} className="h-8 w-24">
  <LineChart data={d}><Line dataKey="v" stroke="var(--chart-1)" dot={false} strokeWidth={2} /></LineChart>
</ChartContainer>
```

## Small multiples (beats a spaghetti line)
Render the same mini-chart per category on a **shared scale** (compute one `[min,max]` `domain` and pass it
to every `<YAxis>`), in a responsive grid (`atelier-layout`). The eye compares shapes, not 9 overlapping lines.

## Escalation — when shadcn/Recharts isn't enough
- **Tremor** (`npm i @tremor/react`, Vercel/MIT) — whole dashboards fast: `<AreaChart>`, `<BarList>`,
  `<Tracker>`, KPI `<Card>`/`<Metric>`. Theme via your CSS vars. Use for analytics surfaces where speed > control.
- **visx** (`@visx/*`) — D3 scales/shapes as React primitives; build the exact chart Recharts lacks (hexbin,
  chord, custom axes). **Observable Plot** (`@observablehq/plot`) for fast exploratory/grammar-of-graphics charts.
  Raw **D3** only when you need bespoke layouts (force, sankey, geo projections).
- **ECharts** (`echarts` + `echarts-for-react`) or **Chart.js** — canvas engines for **10k+ points, real-time
  streams, candlesticks/finance**. Decimate/aggregate the series; **ship a data-table fallback** (canvas is
  invisible to AT). `uPlot` if you need the lightest fast time-series.

Pick the lowest tier that answers the question; a Recharts bar on your tokens beats an ECharts dashboard nobody styled.
