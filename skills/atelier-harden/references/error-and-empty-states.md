# Error, empty & offline states

`atelier-ux` enumerates *which* states a screen has; this makes them production-grade. The *words* in
every state are **`atelier-copy`**'s job — this file is the behavior and structure.

## Per-status error UI (stop shipping one generic "Something went wrong")

| Status | Meaning | What the UI should do |
|---|---|---|
| **400 / 422** | Bad input | Send the user back to the field; show *what* to fix inline. Not a full-page error. |
| **401** | Not authenticated | Prompt sign-in; preserve where they were going (return URL). |
| **403** | Authenticated, not allowed | Explain it's a permission issue; offer "request access" / contact, not "retry". |
| **404** | Gone / never existed | Helpful not-found: search, recent items, a way back. Never a dead end. |
| **409** | Conflict | Surface the conflict (e.g. "edited elsewhere"); offer reload/merge. |
| **429** | Rate-limited | Show the retry-after window; disable the action until then; don't hammer. |
| **500 / 502 / 503** | Our fault | Apologize plainly, offer **Retry**, preserve their input/draft, log it. |

## Network reality

- **Offline:** detect (`navigator.onLine` + `online`/`offline` events) and show a non-blocking banner;
  queue or block writes with a clear message.
- **Timeout:** every fetch needs a timeout (`AbortSignal.timeout(ms)`); a request that never resolves
  must not leave a permanent spinner.
- **Partial failure:** when a page is several independent regions and one fails, **degrade that region**
  (inline error + retry in the widget) — don't blank the whole page. Wrap major regions in an **error
  boundary** (React: a boundary per route/section; a thrown render must not white-screen the app).
- **Retry with backoff** for transient failures; cap attempts; make manual retry always available.

## Empty states (an onboarding moment, never a blank)

Every empty state has three parts: **what this is**, **why it's empty / the value once it's not**, and
**one clear next action** (the primary CTA). A blank panel or a lone "No data" string is a fail. First-run
empty states are the highest-leverage onboarding surface — treat them as such (`atelier-ux` patterns).
Structural primitive: shadcn's `Empty` / `EmptyMedia` / `EmptyTitle` / `EmptyContent` family is a ready
markup target (→ `atelier-components/references/curated-components.md`).

## Forms (where input gets lost)

- **Validate** on blur and on submit; show errors **inline**, next to the field, tied with
  `aria-describedby`; set `aria-invalid`. shadcn's `Field` / `FieldError` primitive renders exactly this
  (de-duped messages, `role="alert"`) — see `atelier-components/references/curated-components.md`.
- **Preserve input on failure** — never clear a form because one field was wrong or the request 500'd.
- **Focus management** — move focus to the first error on a failed submit; announce a summary via a live
  region for screen readers.
- **Pending + guard** — disable submit and show progress the instant it fires (double-submit guard);
  re-enable on resolve/reject.
- **Destructive actions** — confirm with the *consequence and object* named ("Delete 3 projects? This
  can't be undone."), not a bare "Are you sure?". Copy is `atelier-copy`.

## Loading

- **Skeletons at final dimensions** (reserve space → no CLS); static under reduced motion. Spinner only
  for short, indeterminate waits. `atelier-motion` builds these.
- **Optimistic UI** for likely-success, cheap-to-reverse actions only — and it **must have a rollback
  path** on failure. Never optimistic for irreversible/financial actions.

## Checklist

- [ ] Errors are differentiated by cause (auth / permission / not-found / rate-limit / server), each with
      a real recovery — no blanket "Something went wrong".
- [ ] Offline, timeout, and partial-failure are handled; a thrown component can't white-screen the app.
- [ ] Every empty state is an onboarding moment with a CTA; no blank panels.
- [ ] Forms preserve input, validate inline + accessibly, guard double-submit, and confirm destructive ops.
