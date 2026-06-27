# Dashboards & accessible charts

## Dashboard composition (the data hierarchy, not the shell)
The *shell* (sidebar/topbar grid) and the *KPI-card* markup are `atelier-components`
(`atelier-components/references/blocks-app.md`); the *grid* is `atelier-layout`. This file is about what goes **inside**: the
information hierarchy that makes a dashboard read in seconds, not minutes.
- **Inverted pyramid:** the one answer first (the headline KPI, biggest), supporting trends next, granular
  tables last. A dashboard is a sentence — lead with the verb.
- **Five-second test:** a user should grasp the single most important state in five seconds. If everything is
  the same size, nothing is important — apply "one focal point per view" (`atelier-layout`).
- **Group by question, not by chart type.** Cluster the cards that answer one decision; separate with
  whitespace/`<section>` + a heading, not boxes-in-boxes.
- **KPI cards:** number-first and huge (`font-display`, `tabular-nums`), label above, one delta with
  direction + a *non-color* arrow (↑/↓) and color, optional sparkline. Never a KPI that's just a number with
  no comparison — "1,284" means nothing without "vs last week".
- **Density from the Direction Doc:** dashboards are inherently *packed* — tighter gaps, more per view — but
  still on the 8-pt scale (`atelier-foundations`). Restraint in color (one accent + greys) is what stops a
  dense dashboard reading as chaos.
- **Filters & cross-filter:** put global controls (date range, segment) top-right as a segmented control /
  select (`atelier-components`); reflect the active filter in every title ("Revenue — last 30 days").

## Chart states (a chart is a component — design all of them)
```tsx
if (isLoading) return <Skeleton className="h-[240px] w-full rounded-xl" />;  // RESERVE final height → no CLS
if (error)     return <ChartError onRetry={refetch} />;                       // human cause + retry, keep the frame
if (!data.length) return <ChartEmpty cta="Connect a source" />;              // labeled message + next action, not a blank box
return <RevenueChart data={data} />;
```
- **Loading = skeleton at the chart's final dimensions** (shimmer from `atelier-motion`; static under reduced
  motion). A spinner over a collapsing box causes layout shift and reads cheap.
- **Empty / no-data ≠ zero.** "No deployments yet" + a CTA is onboarding; a flat `0` line is a bug-looking dead end.
- **Error** keeps the axes/frame and offers retry; **partial / stale / sampled** data gets a visible badge
  ("Live", "Sampled", "Updated 2m ago") — silent staleness is a trust failure.

## Accessible charts (the gate — `atelier-perf-a11y`)
Canvas/SVG is **invisible or opaque to assistive tech**. `alt` text alone is not access. Provide the data:
- **Data-table fallback (the real fix):** ship the same numbers as a `<table>` — visually hidden, or behind a
  "View as table" toggle (a premium, sighted-user feature too). This is the screen-reader path *and* the
  reduced-data/print path.
```tsx
<figure role="group" aria-labelledby="rev-cap">
  <figcaption id="rev-cap">Revenue by month, 2026 — up 12% over the period.</figcaption>
  <RevenueChart data={data} aria-hidden="true" />     {/* the visual */}
  <table className="sr-only">                          {/* the accessible equivalent */}
    <caption>Monthly revenue, USD</caption>
    <thead><tr><th>Month</th><th>Revenue</th></tr></thead>
    <tbody>{data.map(d => <tr key={d.month}><th scope="row">{d.month}</th><td>{money.format(d.value)}</td></tr>)}</tbody>
  </table>
</figure>
```
- **Caption states the takeaway**, not just "a chart": "Revenue by month, trending up 12%" — the insight a
  sighted user gets at a glance.
- **Keyboard + ARIA:** Recharts 3 `accessibilityLayer` (on by default) gives arrow-key datapoint navigation and
  roles; verify Tab reaches the chart and focus is visible. Don't bury data only in a hover **tooltip** —
  touch and keyboard users can't reliably trigger hover; mirror key values as labels or in the table.
- **Not color alone** (1.4.1) and **≥3:1** series-vs-background contrast (1.4.11); distinguish series by
  marker/dash too. Direct labels survive colorblindness and greyscale printing.
- **Reduced motion:** draw-on, scrub, and count-up animations are decorative — under `prefers-reduced-motion`
  render the final chart immediately. (`atelier-motion` / `atelier-perf-a11y`.)

## Real-time & large data
- **Decimate before you draw:** aggregate/downsample to ~screen-width points; nobody reads 50k SVG nodes.
- **Switch render target by N:** SVG (Recharts/visx) up to a few thousand nodes; **canvas (ECharts/uPlot)**
  beyond, for streams/finance. Canvas → table fallback is mandatory.
- **Throttle updates** to animation frames; pause/disconnect when the tab is hidden or the chart is offscreen
  (IntersectionObserver) — continuous redraws inflate **INP** and drain battery. Verify at the perf gate.
