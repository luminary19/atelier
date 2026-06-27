# User flows & screen states

## Mapping a flow
A flow is the ordered path a user takes to complete one job. Write it as steps with branches — plain text is
enough (no tool required):
```
Goal: new user → first published project   (success metric: time-to-first-publish)
[Landing] → (CTA) → [Sign up] → ◇ email verified?
                                   ├ no  → [Check inbox] → … (resend path)
                                   └ yes → [Create project] → [Editor] → (Publish) → [Live ✓]
   ⤺ abandon paths: close at Sign up (→ resume email), close in Editor (→ autosave draft)
```
- `◇` = decision/branch, `[ ]` = screen/state, `( )` = action, `⤺` = the exit/abandon path you must also design.
- Map **one goal per flow**; the critical set is usually **signup → activation**, the **core task**, and
  **upgrade/checkout**. Three good flow maps beat a diagram of the whole app.

## The rules of a good flow
- **Minimize steps to value.** Count the steps to the first real payoff (*time-to-first-value*); cut fields,
  defer account creation until value is shown, pre-fill smart defaults, collapse optional steps.
- **No dead-ends.** Every screen has a next action; every error a recovery; every empty state a way forward.
  If a path can end with the user stuck, it's a bug in the flow.
- **Design the unhappy exits**, not just success: back, cancel, abandon, timeout, "not now". What happens to
  half-entered data? (Autosave a draft; confirm destructive loss.)
- **Plural entry points.** Users arrive mid-flow from search, deep links, emails, shared URLs — every landing
  screen must orient a cold arrival (where am I, what now). Don't assume they started at step 1.
- **Decision points are costs.** Each branch the user must reason about slows them; remove choices that don't
  matter, and make the recommended path obvious.

## Every screen has five states (the discipline AI skips)
For each key screen, enumerate **all** of these — the build skills implement them; ux makes sure none is forgotten:

| State | What it is | Don't ship |
|---|---|---|
| **Ideal** | populated, happy path | (the only one usually designed) |
| **Empty** | first-run / no data yet | a blank box — make it an onboarding moment + CTA |
| **Loading** | data in flight | a spinner over collapsing layout — use a skeleton at final size |
| **Error** | request/validation failed | a dead-end — give human cause + retry, preserve input |
| **Partial** | some/slow/stale/paginated, degraded perms, offline | pretending it's complete — badge it |

Plus, where relevant: **no-permission / locked** (paywall, role), **offline**, **success/confirmation**.
The *visual + motion* of these is `atelier-motion` (skeleton, optimistic UI, empty/error patterns) and the
markup is `atelier-components`; **ux owns the enumeration** — the matrix below travels with the screen so it's
built complete.

### State matrix (carry this per core screen)
```
Screen: Projects list
  ideal    → grid of project cards, sorted by recent
  empty    → "No projects yet" + [Create project] + a one-line why
  loading  → 6 skeleton cards (reserve grid height)
  error    → "Couldn't load projects" + [Retry] (keep the header/nav)
  partial  → paginated; "Showing 20 of 240"; stale badge if cache > 5m
  locked   → free plan capped → [Upgrade] inline, existing items still readable
```

## The IA + Flow doc (this skill's deliverable — scale to the task)
- **Small (a flow or a few screens):** sitemap sketch + the one flow map + its state list. Inline, no ceremony.
- **Substantial (a real product):**
  1. **Product frame** — primary user, top 3–5 jobs, success metric.
  2. **Sitemap** — the grouped IA tree (top-level ≤7) with screen ↔ route mapping.
  3. **Navigation model** — chosen model + labels + URL scheme (`references/ia-and-navigation.md`).
  4. **Key flows** — 2–4 flow maps with branches + abandon paths.
  5. **State matrix** — five states for each core screen.
  6. **Patterns** — the chosen onboarding / search / form / disclosure patterns (`references/ux-patterns-and-onboarding.md`).
  7. **Hand-off notes** — what `atelier-layout` builds (page structure), `atelier-components` builds (nav/forms),
     `atelier-dataviz` answers (dashboards), and the `atelier-perf-a11y` carry-forwards (landmarks, focus order,
     skip link, reduced-motion transitions).

Keep it a working brief, not a spec novel — enough that the build skills can act without re-deciding structure.
