# UX patterns — onboarding, disclosure, flows

Known-good patterns for the hard parts. Reach for these instead of inventing; the *build* is
`atelier-components` / `atelier-motion`, the *enumeration* is here.

## Onboarding & activation (get to value fast)
The goal is **activation** — the user reaching first real value — not a tour of features.
- **Defer friction.** Show value before asking for signup/payment/profile where possible; ask for the minimum,
  enrich later (progressive profiling). Every field before value costs conversions.
- **Empty state *is* the onboarding.** The first screen with no data is your best teaching moment: one clear
  primary action + a one-line "why", optionally sample/demo data to remove the blank-canvas freeze. (Markup →
  `atelier-components` empty states; this is why "empty" is a designed state, not an afterthought.)
- **Progressive setup / checklist** for multi-part activation ("Create project · Invite team · Connect repo")
  with visible progress — but make the product usable before it's complete; never a wall of required setup.
- **Contextual hints over a modal tour.** Teach a control when the user reaches it (a tooltip/coachmark in
  context) instead of a carousel nobody remembers. One tip at a time, dismissible, never blocking.
- **First-run ≠ every-run.** Gate onboarding to new users; don't re-teach returning ones.

## Progressive disclosure (manage complexity)
- **Show what most users need; reveal the rest on demand.** Advanced settings behind "Advanced", optional
  fields collapsed, power features discoverable but not in the way. Defaults should be right for the 80%.
- **Layer depth:** summary → detail (drill-in), overview → focus, basic → advanced. Each layer is a deliberate
  step, not everything at once. (`<details>`, popovers, drawers, "show more" — built in `atelier-components`.)
- **Avoid the opposite failure:** burying a *core* task one level too deep to look "clean". Disclose by
  frequency-of-use, not by tidiness.

## Forms as flow
- **Chunk long forms.** One idea per step (multi-step wizard) or grouped sections with a visible step indicator;
  show progress and remaining effort. Save/resume so a refresh or a return doesn't lose work.
- **Ask only what you need, when you need it.** Defer optional fields; explain why anything sensitive is asked.
- **Validation timing:** validate on blur / submit, then live-revalidate a field once it's errored — not
  aggressively on first keystroke. Errors inline at the field, in human language, with the fix; summarize at top
  for long forms and focus the first error. (Build: rhf + zod in `atelier-components`; *layout* in `atelier-layout`.)
- **Confirmation & destructive actions:** confirm only the irreversible (type-to-confirm for the truly
  dangerous); make the rest **undoable** (a Sonner toast with Undo beats a confirm dialog). Optimistic UI for
  cheap-to-reverse actions (`atelier-motion`).

## Search & filter (interaction)
- **Faceted, persistent, shareable** (state in the URL — `references/ia-and-navigation.md`); active filters as
  removable chips + "clear all"; autocomplete + recent/scoped search for large sets.
- **Empty results recover:** broaden suggestions, popular/recent, spelling tolerance, a reset — never a flat
  "0 results" dead-end.

## Feedback & notifications
- **System status, always** (Nielsen #1): every action gets feedback within ~100ms — a state change, toast, or
  inline result. Silence reads as broken.
- **Right channel for the message:** transient success → toast (Sonner); needs action → inline / banner;
  background events → a notification center; urgent/blocking → a dialog (sparingly). Don't toast errors that
  require a decision.
- **Notification center / inbox:** read/unread, grouping, mark-all, deep-link to the source; don't badge-spam.

## Gates in the flow (auth, permissions, paywalls)
- **Place the gate where value is clear, not before it.** Soft-gate (preview then prompt) beats a hard wall at
  the door. State *why* and *what unlocks it*; keep already-earned content readable.
- **Permission/empty-by-role** states are real screens (see the state matrix); design the "you don't have
  access — request it" path, not a raw 403.
- **Auth UX:** allow paste + password managers + passkeys, social + email options, clear recovery; never a
  cognitive puzzle (WCAG 3.3.8 — gated by `atelier-perf-a11y`).
