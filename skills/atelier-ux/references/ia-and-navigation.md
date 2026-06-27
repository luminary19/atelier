# Information architecture & navigation

## Inventory → group → name (the IA method)
1. **Inventory** every piece of content / feature / action the product has (a flat list — don't structure yet).
2. **Group** by the **user's mental model** (card-sort logic): what they'd expect to find together, not how
   your database is shaped. The classic failure is mirroring the org chart or the data schema.
3. **Name** each group in **the user's vocabulary** — "Billing", not "SubscriptionManager"; "Your work", not
   "Entities". Test labels against what a user would *say*.
4. **Validate** with a quick reverse test: pick 5 top tasks, confirm each has an obvious home and one path.

## Breadth vs depth
- **Top-level groups: ~5–7.** Navigation is working memory; past ~7 the user stops scanning and starts hunting.
- **Shallow beats deep.** Every extra level halves the chance content is found. Prefer flat (more on a page,
  fewer clicks) unless volume forces a taxonomy. Most AI-built IAs are *too deep* (a folder for everything).
- **Polyhierarchy:** a thing can live in two places (a doc in "Recent" *and* "Projects") — duplicate the
  *link*, not the content; let search + filters cut across.

## Navigation models (match to product type + depth)
| Model | Best for | Notes |
|---|---|---|
| **Top nav (horizontal)** | marketing / content, ≤7 destinations | the default for sites; add a sticky condensed variant on scroll |
| **Sidebar (vertical)** | apps/dashboards with many sections | collapsible; group with headings; the `atelier-components` app-shell |
| **Tab bar (bottom)** | mobile apps, 3–5 core areas | thumb-reachable; icons + labels; never >5 |
| **Hub-and-spoke** | task launchers, mobile utilities | a home that spokes out to single-task screens |
| **Hierarchical + breadcrumbs** | deep catalogs, docs, commerce | breadcrumbs show depth + offer escape up |
| **Search-first** | large content / commerce / media | search *is* the primary nav; faceted filters refine |
| **Command palette (⌘K)** | power/keyboard apps | *augments*, never replaces, visible nav (`atelier-components` cmdk) |

- **One primary nav.** Demote the rest to footer, overflow menu, or the command palette. Two competing primary
  navs = the user doesn't know where to look.
- **Mobile is the forcing function.** If the IA doesn't collapse into a tab bar + a menu, it's too wide —
  simplify the top level, don't cram.
- **Persistent + predictable:** nav stays put across screens; the current location is always marked
  (`aria-current="page"` + visual). Wayfinding ("where am I, where can I go, how do I get back") is non-negotiable.

## Labels
- **Short, distinct, parallel.** One register and grammar ("Dashboard / Projects / Settings", not "Dashboard /
  Your projects / Configure"). Distinct enough that two labels never feel interchangeable.
- **Clarity over cleverness.** A clever label that needs a second of decoding is a tax paid on every visit.
  Standard words win ("Pricing", "Docs", "Sign in") — recognition beats recall.
- **Icons need text** in primary nav (icon-only is a memory test and an a11y problem); icon-only is fine for a
  universally-understood, labeled-on-hover toolbar.

## URLs are IA made durable
- **Readable + hierarchical + stable:** `/settings/billing`, `/projects/atlas/issues` — they mirror the IA,
  and they're shareable, bookmarkable, deep-linkable, and SEO. Slugs over IDs where possible.
- **Don't break them.** URLs are a contract; on a redesign, **301-redirect** old paths (`atelier-redesign`
  preserves these). State lives in the URL where it should be shareable (filters, tabs, search query).
- **Map screens ↔ routes** in the IA doc so `atelier-layout`/`atelier-components` build the router from the
  same source of truth (Next App Router segments, etc.).

## Search & filtering (when search is part of nav)
- **Faceted filters** for structured catalogs (category, price, status); persistent and **reflected in the
  URL** so a filtered view is shareable. Show active filters as removable chips; offer "clear all".
- **Empty results ≠ dead end:** suggest broader terms, recent/popular, or a reset (→ states reference).
- Scope, autocomplete, and recent searches turn search from a fallback into primary nav for large products.
  (The *component* build — combobox, cmdk — is `atelier-components`.)
