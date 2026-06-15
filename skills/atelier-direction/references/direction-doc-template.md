# Direction Doc — template

The one-page brief this skill produces for **substantial builds/redesigns** (for small tweaks, skip the
doc — just state the Design Read + the 2–3 decisions that matter). Keep it tight. Fill every field with a
*decision* (and a one-line why), not a menu of options. Output it to the user and carry it into
`atelier-foundations`, `atelier-typography`, and `atelier-layout`. Default build stack is **Tailwind v4
+ shadcn/ui** unless the project dictates otherwise.

```markdown
# Direction Doc — <project name>

**Design Read:** <one line: "a <page kind> for <audience>, with a <vibe> language, leaning toward
<aesthetic family>.">

**World:** Production | Award  — <why; where (if anywhere) the one award-grade signature moment lives>

**Aesthetic:** <named look, or pairing> — <one line on why it fits the audience/brand>

**Concept spine:** <the organizing idea the design expresses, one line>
**Signature moment:** <the single moment that embodies the concept>

**Palette mood:** <e.g. "ink dark-tech, one cool desaturated accent, tinted-cool neutrals, grain">
  → feeds atelier-foundations (it builds the OKLCH ramps + semantic tokens + dark mode)

**Type voice:** <e.g. "confident grotesque display + neutral variable body; tight display tracking;
  high scale contrast"> → feeds atelier-typography (it picks the actual families + sets them)

**Motion budget:** <none / restrained ≤300ms / award-grade scroll choreography> — <what may move, where>
  (carry the perf/a11y rules: transform+opacity only, prefers-reduced-motion, ≤300ms unless award world)

**Density:** airy | balanced | packed — <one line: where the page breathes vs. where it packs detail.
  "Airy" = art-gallery whitespace, few elements per view; "packed" = cockpit / data-dense / editorial-rich.
  Decide it explicitly; it governs spacing scale, section count, and how much lives in each viewport.>
  → feeds atelier-layout (whitespace + grid density) and atelier-foundations (spacing scale choice)

**Layout archetype:** <e.g. "asymmetric hero → bento features → editorial rows → CTA; Z-scan">
  → feeds atelier-layout (it builds the grid + composition + whitespace + responsive)

**Build stack:** Tailwind v4 + shadcn/ui  (or: <existing project stack, if it dictates otherwise>)

**References:** <URLs/products + the specific decisions mined from each — grid/type/color/motion>

**Constraints (override aesthetics):** <accessibility, perf budget, regulated industry, existing brand>

**Anti-slop guardrails for THIS project:** <the 2–3 specific cheap tells to avoid here, and the 2–3
  expensive levers to lean on>
```

## Worked example (filled)

```markdown
# Direction Doc — Northwind (developer infra SaaS)

**Design Read:** a B2B SaaS landing for technical buyers, with a Linear-style restrained language,
leaning toward dark-tech.

**World:** Production. One award-grade signature moment: the hero's animated topology/connection
graph (static poster fallback below the fold).

**Aesthetic:** Dark-tech + a restrained mesh-gradient hero backdrop + grain. Fits a technical,
trust-first audience that distrusts "marketing-y."

**Concept spine:** "infrastructure you can see." Signature moment: nodes that settle into a clean
graph on load, then go still.

**Palette mood:** ink charcoal base (not black), one cool teal accent desaturated ~12%, neutrals
tinted slightly cool, subtle grain. Elevation by lighter surfaces.

**Type voice:** neutral variable grotesque (e.g. Geist/General Sans) for body; a slightly tighter,
more characterful grotesque for display; tight display tracking; high H1↔body contrast; tabular
figures for the metrics band.

**Motion budget:** restrained ≤300ms for UI; the hero graph is the one award moment. transform+opacity
only; full prefers-reduced-motion fallback (static graph).

**Density:** balanced — generous whitespace around the hero and proof rows; the one packed moment is the
metrics band (tabular, dense by intent). Not airy (it's a product, not a gallery), not cockpit.

**Layout archetype:** asymmetric hero (giant headline left, graph right) → 2-3-2 bento feature grid
with one hero cell → alternating editorial proof rows → metrics band → CTA. Z-scan.

**References:** linear.app (elevation-by-lightness, hairlines, restraint), vercel.com (Geist, grain),
the user's existing logo/teal.

**Constraints:** WCAG 2.2 AA, LCP ≤2.5s (lazy-load the hero graph), keep the dashboard screenshots crisp.

**Anti-slop guardrails:** avoid #000 + grey text and the purple-gradient+glass-card cliché; lean on
generous whitespace, one teal accent, grain, and a real 12-col grid.
```
