---
name: atelier-harden
version: 1.0.0
description: >
  Atelier suite — the production-resilience pass. Make a beautiful build survive the real world: text
  overflow and truncation at every breakpoint, internationalization (30-40% text expansion, RTL
  mirroring via logical properties, locale-aware number/date/currency formatting, pluralization), the
  full set of error states (per-HTTP-status, offline, timeout, partial failure, form validation), empty
  and edge-case data (zero / one / few / many / huge, null fields, long strings, broken images), and
  interaction resilience (double-submit guards, race conditions, AbortController cleanup, no memory
  leaks). Use whenever hardening or shipping to production, handling edge cases, adding error/empty
  states, fixing text overflow or i18n/RTL, or making a UI robust under real, messy, translated, or
  failing data. This owns the BEHAVIOR and markup of error/empty/edge states; the WORDS in them are
  atelier-copy. Runs after the build and before the atelier-perf-a11y gate. Part of the Atelier suite.
triggers:
  - harden
  - production ready
  - edge cases
  - error states
  - text overflow
  - i18n
  - internationalization
  - rtl
  - empty states
  - error state resilience
  - make it robust
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Atelier — Production Resilience (Harden)

A build that's beautiful on the happy path with seed data is not done — it's a demo. Production is
**long German strings, an API 500, a 1,500-row list, a double-tapped submit button, a screen reader on a
flaky connection.** This skill is the pass that makes the build survive all of it without breaking layout,
losing the user's work, or going blank. It sits between the build and the quality gate.

> **Project memory:** if **`ATELIER.md`** exists at the project root, read it first — its register and
> accessibility commitments scope this pass (a `product` admin tool hardens differently from a `brand`
> campaign page). Missing on a substantial build? Offer **`/atelier init`** (owned by the **`atelier`** router).
>
> **Suite map.** Runs after the build (**`atelier-components`**) and before the **`atelier-perf-a11y`**
> gate. **`atelier-ux`** *enumerates* the five screen-states (ideal/empty/loading/error/partial); this
> skill makes them production-grade. **`atelier-motion`** builds the skeleton/optimistic-UI mechanics;
> here we make them resilient (rollback, no stuck spinners). Error/empty *copy* is **`atelier-copy`**;
> overflow on display type loops back to **`atelier-typography`** (measure, `text-wrap`). For an existing
> site, **`atelier-redesign`** calls this before its final gate. Deep reference:
> `references/fundamentals-deepdive.md`.

---

## The flow

1. **Inventory** the surfaces + the real data shapes they render → 2. **Stress with extreme data** →
3. **Overflow & truncation** pass → 4. **i18n / RTL** pass → 5. **Error / empty / offline states** →
6. **Interaction resilience** (double-submit, races, cleanup) → 7. **Re-gate** (`atelier-perf-a11y`).

## 1. Inventory the data shapes

For each screen, list what's actually variable: which fields can be empty / null / very long; which lists
can be 0, 1, or 10,000 rows; which numbers can be huge or negative; which images can 404; which calls can
fail or be slow. You're cataloguing the inputs reality will throw at the happy-path UI.

## 2. Stress with extreme data (the core move)

Replace seed data with the worst realistic cases and look at every breakpoint. Full catalogue in
**`references/edge-cases-and-data.md`**. The essentials:
- **Collections:** zero (→ empty state), one, a few, and *many* (pagination / virtualization for long
  lists — a 1,500-item map will jank). Loading and stale/partial variants.
- **Strings:** a 60-character name, a no-spaces token, a missing/`null` field, emoji and combining marks,
  user-generated HTML (escape it). The viewport is part of the design — long content must not break it.
- **Numbers / dates:** very large, zero, negative, fractional; far-past/future dates; missing timestamps.
- **Media:** broken image (real `onerror` / fallback), slow image (dimensions reserved so no CLS),
  missing avatar (initials fallback).

## 3. Text overflow & truncation

The #1 way real data breaks a pretty layout. Patterns in `references/edge-cases-and-data.md`:
- **Flex/grid children need `min-width: 0`** (or `min-inline-size: 0`) to allow truncation — the default
  `auto` refuses to shrink and forces overflow. The single most common overflow bug.
- Truncate deliberately: `text-overflow: ellipsis` (single line) or `-webkit-line-clamp` (multi-line);
  pair a truncated label with a `title`/tooltip so nothing is *lost*, only clipped.
- `overflow-wrap: anywhere` / `hyphens: auto` for long unbroken tokens (URLs, IDs).
- **Test headline copy at every breakpoint** — a long word + a big `clamp()` max + a narrow column
  overflows on tablet/mobile. Reduce the clamp max or rewrite the copy; the cap (`atelier-typography`) is
  display `clamp()` max ~6rem and measure 60-75ch.

## 4. Internationalization & RTL

Even English-only products benefit from these (they're really "don't hardcode layout to one string").
Method in **`references/i18n-and-rtl.md`**:
- **Budget +30-40% text expansion** — German/Finnish/Russian run long; never size a button to fit the
  English label exactly. Let containers grow; don't truncate critical actions.
- **Logical properties everywhere** (`margin-inline`, `padding-block`, `inset-inline-start`, `text-align:
  start`) so the layout mirrors for RTL by flipping `<html dir="rtl">`. No physical `left`/`right` in
  flow layout.
- **Format with `Intl`** — `Intl.NumberFormat`, `DateTimeFormat`, `RelativeTimeFormat`, `PluralRules`.
  Never concatenate translated fragments ("You have " + n + " items") — use full templated strings with
  interpolation and real plural categories.
- Declare script-aware font fallbacks (CJK, Arabic) so non-Latin glyphs don't tofu.

## 5. Error, empty & offline states

`atelier-ux` says *which* states exist; here they become real. Patterns in
**`references/error-and-empty-states.md`**:
- **Per-status error UI** — distinguish 400 (fix input) / 401-403 (auth/permission) / 404 (gone) / 429
  (rate-limit, show retry-after) / 500-503 (our fault, retry). Generic "Something went wrong" everywhere
  is a tell.
- **Network reality** — offline banner, request timeout, and **partial failure** (some widgets load, one
  fails — degrade that widget, don't blank the page). A React **error boundary** per major region so one
  thrown component doesn't white-screen the app.
- **Empty is an onboarding moment** — never a blank panel: explain the value + one clear next action.
- **Forms** — inline validation on blur/submit, error text tied via `aria-describedby`, **preserve the
  user's input** on failure, focus the first error. Copy for all of this is **`atelier-copy`**.

## 6. Interaction resilience

Where "works in the demo" diverges from "works in production":
- **Double-submit / double-tap** — disable + show pending on the action the instant it fires; guard
  idempotency. The classic duplicate-order bug.
- **Race conditions** — out-of-order async responses (type-ahead, tab switches): track the latest request,
  ignore stale ones; `AbortController` to cancel superseded fetches.
- **Cleanup = no leaks** — abort fetches, clear timers/intervals, disconnect observers
  (`IntersectionObserver`/`ResizeObserver`), remove listeners on unmount. A component that fetches on mount
  must cancel on unmount or it sets state on an unmounted tree.
- **Optimistic UI must roll back** — every optimistic update needs a reconcile/revert path on failure
  (`atelier-motion` builds the mechanic; ensure the failure branch exists).

## 7. Re-gate

Hardening changes markup and states — re-run the **`atelier-perf-a11y`** gate (new states need contrast,
focus, reduced-motion, and a11y too; long lists affect INP). For a substantial build, the
**`atelier-review`** red-team should exercise these states live (resize to mobile, kill the network,
tab through the error path).

---

## Operating principles
- **Beautiful + happy-path is a demo, not a product.** Resilience is the difference.
- **The viewport is part of the design** — if real copy overflows at any breakpoint, the design is wrong, not the data.
- **Every async path has four states** — loading, success, empty, error — and every error offers a recovery.
- **Preserve the user's work** — never lose input on a failure; never lose data on a double-tap.
- **Clean up everything you start** — fetches, timers, observers, listeners. No leaks, no stale state.
