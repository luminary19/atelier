---
name: atelier-ux
version: 1.0.0
description: >
  Atelier suite — the UX architecture & flows layer (planning-first). Decide how a product is STRUCTURED
  before any page is styled: the information architecture (content/feature inventory, grouping, sitemap,
  labels in the user's words), the navigation model (top-nav / sidebar / tab-bar / hub-and-spoke, URL
  structure, breadcrumbs, search), the critical user flows (signup → activation, the core task, checkout)
  with their dead-ends and decision points, and the five states every screen must handle (ideal / empty /
  loading / error / partial). Produces an IA + Flow artifact — analogous to the Direction Doc — that
  atelier-layout realizes as page structure and atelier-components builds. Use whenever structuring a new
  app/product/site, deciding what pages or screens exist and how they connect, designing a user flow,
  journey, navigation model, sitemap, onboarding/activation, or progressive disclosure — or when a product
  feels confusing, disorganized, or full of dead-ends. Runs right after atelier-direction: ux owns
  structure, direction owns aesthetic, layout owns the visual grid. Part of the Atelier suite.
triggers:
  - information architecture
  - user flow
  - sitemap
  - navigation model
  - app structure
  - what pages do i need
  - user journey
  - onboarding flow
  - ux structure
  - screen states
allowed-tools:
  - Read
  - Write
  - Edit
  - AskUserQuestion
  - WebFetch
---

# Atelier — UX Architecture & Flows

The gap between "pretty pages" and "a product that makes sense" is structure. AI builds beautiful screens
on top of incoherent architecture — navigation that doesn't match the user's mental model, flows with
dead-ends, and screens that only handle the happy path. This skill decides the **structure and flow before
the pixels**: what screens exist, how they connect, how a user moves through them, and every state each
screen must handle. It is **planning-first** — it produces an artifact the rest of the suite builds; it does
not render UI.

> **Project memory:** if **`ATELIER.md`** exists, read its **register** + **Users**/**Purpose** first and
> honor them (set up via **`/atelier init`** — the **`atelier`** router).
>
> **Runs with `atelier-direction`** (direction = the *look*; ux = the *structure* — both are planning).
> **Output:** an **IA + Flow doc** consumed by `atelier-layout` (realizes structure as page layout),
> `atelier-components` (builds nav / shell / forms), `atelier-motion` (state & route transitions),
> `atelier-dataviz` (what a dashboard answers), `atelier-copy` (the *words* in flows and states), and
> `atelier-harden` (makes the five states production-grade). **For existing products, `atelier-redesign`
> calls this to audit IA first.** **Gate:** `atelier-perf-a11y` (nav landmarks, focus order, skip links,
> reduced-motion route transitions). Deep reference:
> `references/fundamentals-deepdive.md` (§8 Layout & Composition, §14 Master decision logic, §15 Expensive vs cheap).
>
> **Data — `atelier-data`:** product-type recommendations (`--domain product`) + design reasoning incl. anti-patterns (`scripts/search.py "<product>" --domain reasoning`) and landing-page section/CTA patterns (`--domain landing`). Reference inputs for planning; the IA + flows are decided here.

The boundary, stated once: **ux decides *which* screens exist and how they connect + behave; `atelier-layout`
decides how *one* screen is composed (grid/whitespace); `atelier-components` builds the actual nav/forms.**

---

## The flow

1. **Frame the product** → 2. **Inventory & group (IA)** → 3. **Choose the navigation model** → 4. **Map the
key user flows** → 5. **Map every screen's states** → 6. **Pattern the hard parts** → 7. **Write the IA +
Flow doc** → hand off to layout/components.

## 1. Frame the product

Before structure, get the job. State in one or two lines: **the primary user, their top 3–5 tasks (jobs to
be done), and the one success metric.** Structure follows tasks — an IA optimized for the org chart instead
of the user is the #1 cause of "I can't find anything."
- **If genuinely ambiguous, ask exactly one question** (`AskUserQuestion`) — e.g. *"Is the primary job
  monitoring (dashboard-first) or doing work (task-first)?"* Otherwise infer and proceed.
- Product type sets the default shape: **content site** (browse/read), **marketing** (convince → convert),
  **app/SaaS** (recurring tasks), **commerce** (find → buy), **dashboard/admin** (monitor → act).

## 2. Inventory & group (information architecture)

Method in **`references/ia-and-navigation.md`**. List every piece of content/feature, then **group by the
user's mental model**, not your data model (card-sort logic): related things together, named in **the user's
words** (label "Billing", not "SubscriptionEntity"). Keep top-level groups to **~5–7** (navigation is
working memory). Decide depth — flat (few sections, more per page) vs deep (taxonomy) — by volume; most
products are too deep.

## 3. Choose the navigation model

Match the model to product type + depth (full matrix + labeling/URL rules in `references/ia-and-navigation.md`):
- **Top nav** — marketing/content, ≤7 destinations. **Sidebar** — app/dashboard with many sections.
  **Tab bar** — mobile app, 3–5 core areas. **Hub-and-spoke** — task launchers / mobile utilities.
  **Hierarchical + breadcrumbs** — deep catalogs. **Search-first** — large content/commerce.
- **URLs are IA made durable** — readable, hierarchical, stable (`/settings/billing`); they're shareable,
  bookmarkable, and SEO. **Labels:** short, distinct, user's vocabulary, parallel grammar; never clever over clear.
- One **primary** nav; demote the rest to footer/overflow/command-palette (`atelier-components` cmdk). Mobile
  is the forcing function — if it doesn't fit a tab bar + a menu, the IA is too wide.

## 4. Map the key user flows

A screen is a step in a journey, not an island. For each critical path (**signup → activation**, the **core
task**, **checkout/upgrade**), write the step sequence and mark **decision points, branches, and dead-ends**.
Method + notation in **`references/user-flows-and-states.md`**.
- **Minimize steps to value** (time-to-first-value): cut fields, defer account creation, smart defaults.
- **No dead-ends:** every screen offers a next action; every error offers a recovery; every empty state offers
  a way forward. Map the **back/cancel/abandon** paths, not just success.
- **Entry points are plural** — users arrive mid-flow from search/links/deep-links; each landing screen must
  orient them.

## 5. Map every screen's states (where products actually fail)

The discipline AI most often skips: **every screen has five states**, not one. For each key screen, specify:
- **Ideal** (data, happy path) · **Empty** (first-run / no-data — an onboarding moment + CTA, never a blank) ·
  **Loading** (skeleton at final dimensions — reserve space) · **Error** (human cause + recovery, preserve
  input) · **Partial** (some data, slow, paginated, stale, degraded permissions/offline).
- Detail + the state matrix template in **`references/user-flows-and-states.md`**. The *visual/motion*
  implementation of these is `atelier-motion` (skeletons, optimistic UI) and `atelier-components` (the markup);
  the *words* in them are **`atelier-copy`**; making them survive real/failing/translated data (per-status
  errors, overflow, i18n, edge cases) is **`atelier-harden`**. ux's job is to **enumerate which states exist**
  so none ships missing.

## 6. Pattern the hard parts

Reach for known-good patterns instead of inventing (catalog in **`references/ux-patterns-and-onboarding.md`**):
**onboarding & activation** (progressive setup, empty-state-as-onboarding, defer friction), **progressive
disclosure** (show what's needed, reveal complexity on demand), **search & filter** (faceted, persistent,
shareable), **forms as flow** (chunk long forms, one idea per step, save progress), **error recovery**,
**notifications/feedback**, **permissions/paywalls/auth gates** (where they interrupt the flow).

## 7. Write the IA + Flow doc — scaled to the task

Match the artifact to the job (template in `references/user-flows-and-states.md`):
- **Small (a few screens / one flow):** a sitemap sketch + the one flow + its state list, inline. No ceremony.
- **Substantial (a real product):** the full doc — **sitemap**, **navigation model + labels + URL scheme**,
  **2–4 key user-flow maps**, a **state matrix** for the core screens, and the chosen **patterns**.

Then hand off: **`atelier-layout`** (turn the sitemap/screens into page structure), **`atelier-components`**
(build the nav model, shell, forms, command palette), **`atelier-motion`** (state + route transitions),
**`atelier-dataviz`** (what each dashboard answers). Carry the `atelier-perf-a11y` constraints forward: nav
landmarks, logical focus/reading order == DOM order, a skip link, reduced-motion route transitions.

---

## Operating principles
- **Structure before surface.** IA decides whether a product makes *sense*; aesthetics decide whether it's *liked*. Both, in that order.
- **Match the user's mental model, not the org chart** — group and label in their words; clarity over cleverness.
- **Every screen has five states** — design the empty/loading/error/partial ones; that's where products fail.
- **Flows, not just pages** — a screen is a step; kill dead-ends, map the back/abandon paths, minimize time-to-value.
- **Planning-first** — this skill *decides* the structure; `atelier-layout`/`atelier-components` *build* it. Don't render here.
- **Don't over-architect** — a 5-page site needs a sitemap, not a taxonomy. Scale the artifact to the product.
