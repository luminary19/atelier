---
name: atelier-data
user-invocable: false  # a library the other atelier-* skills call via scripts/search.py, not a menu skill
description: On-demand reference DATA for the Atelier suite — a local, searchable (BM25) library of per-industry color palettes, font pairings, UI-style definitions, product-type design reasoning, landing-page patterns, chart guidance, and current Next.js / React / shadcn / Vue / Three.js do-and-don't tables. Use it to look up STARTING POINTS and cross-checks (e.g. "a starting palette/fonts/style for a fintech dashboard", "what does shadcn recommend for forms", "design reasoning for a SaaS product type", "search the design dataset"), or to feed a rubric into a review. It is a lookup tool, NOT a decision-maker: defer final craft to atelier-direction / atelier-foundations / atelier-typography / atelier-layout / atelier-components, and the compliance gate to atelier-perf-a11y / atelier-review. Do not use it as a token engine (it emits raw hex, not OKLCH) or as a code auditor (it cannot read your files).
---

# atelier-data — searchable design reference

A curated, **local** dataset + a tiny BM25 search engine. It answers "give me a vetted *starting point* / cross-check" fast, without spending model context on the whole corpus. It is the **data** layer of the Atelier suite; the other `atelier-*` skills remain the authorities that make the actual design decisions.

> **Provenance.** Harvested and cleaned from **UI/UX Pro Max v2.5.0** (© 2024 Next Level Builder, MIT). See `references/PROVENANCE.md` and `../../THIRD-PARTY-LICENSES/ui-ux-pro-max-MIT.txt`. Content is **curated-opinion** (some generated), not a cited standard — treat it as informed starting material, not ground truth.

## When to use (and when not)

**Use it for:** a fast per-industry palette/type/style *starting point*; product-type design reasoning (pattern + anti-patterns) during planning; a current do/don't lookup for Next.js / React / shadcn / Vue / Three.js while implementing or refactoring; a UX-heuristic rubric to hand a reviewer; a Google-Fonts metadata lookup.

**Do not use it for:** building the real token system (use **atelier-foundations** — its colors here are raw Tailwind hex stops, not OKLCH, and some fail AA); final font choice (use **atelier-typography** — this set still contains common defaults); auditing real code (use **atelier-review** — it cannot read your files); or as an always-on rule source (query it on demand only).

## How to query (Windows: use `python`, not `python3`)

```bash
cd $CLAUDE_CONFIG_DIR/skills/atelier-data/scripts
python search.py "<query>" --domain <domain> [-n 3]
python search.py "<query>" --stack <stack>  [-n 3]
python search.py "<query>"                     # auto-detect domain
```

Keep `-n` small (≤5) and avoid `--json` for large domains — results enter the model's context, and `--json` bypasses the per-field 300-char truncation. Python is stdlib-only; **no network calls**.

## Datasets → which Atelier skill owns the decision

| Domain / file | Gives you | Decision owner |
|---|---|---|
| `--domain product` → `products.csv` (161) | Per-product-type style / landing / dashboard recommendations | **atelier-direction**, **atelier-ux** (planning) |
| `--domain reasoning` → `ui-reasoning.csv` (161) | Per-product-type recommended pattern, style priority, color/type mood, key effects, **anti-patterns** | **atelier-direction**, **atelier-ux** (planning) |
| `--domain style` → `styles.csv` (67 web; Mobile rows removed) | Style definitions, CSS-var stubs, AI-prompt keywords, framework scores | **atelier-direction**, **atelier-components** |
| `--domain color` → `colors.csv` (161) | shadcn-token palette per product type — **scaffold only** | **atelier-foundations** (rebuild in OKLCH + re-check contrast) |
| `--domain typography` → `typography.csv` (71; broken rows removed) | Font pairings w/ ready `@import` + Tailwind config | **atelier-typography** (authority on escaping defaults) |
| `--domain google-fonts` → `google-fonts.csv` (1,923) | Font metadata: category, axes, subsets, popularity | **atelier-typography** |
| `--domain landing` → `landing.csv` (34; uncited stats stripped) | Section-order patterns, CTA placement, color strategy | **atelier-ux**, **atelier-layout** |
| `--domain chart` → `charts.csv` (25) | Chart-type → library/a11y guidance | **atelier-dataviz** |
| `--domain ux` → `ux-guidelines.csv` (89 web/all) | Do/don't UX + a11y heuristics w/ code examples | **atelier-perf-a11y**, **atelier-review** (rubric feed) |
| `--domain react` → `react-performance.csv` (44) | RSC / React 18+ / Next 15 perf patterns | **atelier-components** |
| `--stack nextjs\|react\|shadcn\|vue\|threejs` | Current per-stack do/don't tables w/ doc URLs | **atelier-components** (threejs → **atelier-webgl**) |

## Honest caveats (read before trusting a result)

- **Colors are Tailwind hex stops**, partially a11y-checked. Use as a *seed*, then rebuild in OKLCH via `atelier-foundations` and verify contrast via `atelier-perf-a11y`. Never paste `Secondary`/`Accent` as body text without a contrast check.
- **Typography** still includes common pairings (Inter/Playfair etc.). `atelier-typography` is the authority and deliberately steers away from defaults — treat rows as options, not endorsements.
- **`ui-reasoning` style picks can misfire** (its `Style_Priority` can override better matches; the `Decision_Rules` JSON is advisory, not executed). Sanity-check against `atelier-direction`.
- **`landing.csv` conversion %-claims were removed** (they were uncited). The section-order/CTA advice remains.
- Counts/labels in the source's own marketing were inflated; the numbers above are the **actual** cleaned row counts.

## What was deliberately left behind

The design-system **generator** (`design_system.py`), `colors→hardcoded-CSS` output, the MASTER.md/page-override generator, all **mobile-native** rows/stacks, `html-tailwind` (it was Tailwind v3), and the npm CLI — all conflicted with this stack or with Atelier. This skill is data + search only.
