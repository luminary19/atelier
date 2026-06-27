# atelier-data — provenance & cleaning record

**Harvested:** 2026-06-18 · **By:** the adoption plan in `UI-UX-Pro-Max-Adoption-Report.md`.

## Source

- **Project:** UI/UX Pro Max v2.5.0 (npm `uipro-cli`, site uupm.cc; internally "Antigravity Kit")
- **Author / License:** © 2024 Next Level Builder — **MIT** (retained at `../../THIRD-PARTY-LICENSES/ui-ux-pro-max-MIT.txt`)
- **Repo:** https://github.com/nextlevelbuilder/ui-ux-pro-max-skill (snapshot commit 2026-04-03, merge PR #184)
- **Source of truth used:** the repo's `src/ui-ux-pro-max/{data,scripts}` (newer than the `cli/assets` copy; never the `.claude/skills` symlinks).
- The clone was temporary (`…/Projects/Personal/eval/ui-ux-pro-max-skill`); this skill is self-contained and does **not** depend on it.

## Attribution

Derived work under MIT. Any redistribution must retain the upstream copyright + license notice (kept in `THIRD-PARTY-LICENSES/`).

## What was copied as-is

`colors.csv` (161), `charts.csv` (25), `products.csv` (161), `ui-reasoning.csv` (161), `google-fonts.csv` (1,923), `react-performance.csv` (44); stacks `nextjs` (52), `react` (53), `shadcn` (60), `vue` (49), `threejs` (53). *(data-row counts)*

## What was filtered (and the exact rule)

| File | Rule | Result |
|---|---|---|
| `styles.csv` | drop rows where `Type == "Mobile"` (RN/SwiftUI APIs) | 84 → **67** |
| `typography.csv` | drop `No` ∈ {20, 39} — named Heading/Body font absent from the CSS `@import` (silent Fontshare substitution bug) | 73 → **71** |
| `ux-guidelines.csv` | keep `Platform ∈ {Web, All}` (drop Mobile + VisionOS) | 99 → **89** |
| `landing.csv` | strip uncited conversion claims in `Conversion Optimization` (e.g. `"35% higher conversion"` → `"higher conversion"`, `"time-on-page 3x"` → `"time-on-page"`); advice retained | 34 rows, **6 cells** de-fabricated |

CSVs were round-tripped with Python's `csv` module (list-based, to tolerate ragged rows exactly as the engine parses them), UTF-8 out.

## What was dropped entirely (with reason)

- `design.csv`, `draft.csv` — not real CSVs (free-text, 2 styles, bilingual; engine ignores them).
- `icons.csv` — un-vetted; Atelier covers icons. (`icons` domain removed from the engine.)
- `app-interface.csv` — iOS/Android/RN content (was the misnamed `web` domain). (`web` domain removed.)
- `stacks/html-tailwind.csv` — Tailwind **v3** idioms; would mislead a v4 stack. Atelier owns Tailwind v4.
- All native / non-used-web stacks: `react-native, flutter, swiftui, jetpack-compose, laravel, svelte, astro, nuxtjs, nuxt-ui, angular`. (Easy to re-harvest from source if ever needed.)
- `design_system.py` (the generator), the CLI (`cli/`), and the per-platform templates — generator output conflicts with `atelier-foundations` (raw hex / `--color-*` names / hardcoded CSS) and had a known style-selection defect.

## Engine patches (`scripts/core.py`, `scripts/search.py`)

- `tokenize()`: `len(w) > 2` → **`len(w) >= 2`** (2-char tokens like `ux`/`ai` were silently dropped).
- `CSV_CONFIG`: removed `icons` and `web` domains (their files were dropped); **added** a `reasoning` domain → `ui-reasoning.csv` (it was unsearchable upstream — only consumed by the dropped generator).
- `STACK_CONFIG`: trimmed to `react, nextjs, vue, shadcn, threejs`.
- `detect_domain()`: removed the `icons` and `web` keyword bags.
- `search.py`: removed the `design_system` import and the entire `--design-system/--persist/--page` machinery; fixed docs (`python` not `python3`; accurate domain/stack lists).
- `_load_csv` reads `utf-8-sig` (tolerates BOM). Stdlib only; **no network calls**.

## How to re-harvest or extend

Re-clone the source, then re-apply the table above (or add a dropped stack by copying `src/ui-ux-pro-max/data/stacks/<name>.csv` into `data/stacks/` and adding it to `STACK_CONFIG` in `core.py`). Keep colors as a seed only — always rebuild tokens in OKLCH via `atelier-foundations`.
