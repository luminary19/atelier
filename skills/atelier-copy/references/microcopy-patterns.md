# Microcopy patterns — by string type

Each interface string type has a job and a shape. Behavior (when these render, input preservation, locale
formatting) is **`atelier-harden`**; this is the wording.

## Actions / CTAs

- **Verb + object, specific:** "Create account", "Save changes", "Add payment method", "Start free trial".
- **Avoid:** "Submit", "OK", "Click here", "Continue" (when a specific verb fits), "Learn more" ×5 on one page.
- **1-3 words** for primary actions; they must fit one line at every breakpoint (a wrapping button is broken).
- **One intent → one label, reused.** Don't phrase the same action three ways across the page.
- **Pair destructive with neutral:** "Delete" next to "Cancel" (not "Delete" / "OK").

## Form labels & helper text

- **Label above the input, persistent.** Placeholder ≠ label — placeholders disappear on focus and are
  poor for a11y. Use a placeholder only for a *format example* ("name@company.com").
- **Helper text** for requirements ("8+ characters, 1 number"), shown before and during entry — not only
  as an error after failure.
- **Optional vs required:** mark the rarer one. If most fields are required, mark "(optional)"; don't
  asterisk everything.
- **Input-level errors** sit next to the field, name the fix, and are tied via `aria-describedby`.

## Error messages — the formula

> **What happened · why (if useful) · how to fix.** Human, specific, blameless, no raw codes alone.

| Bad | Good |
|---|---|
| "Error: null" | "We couldn't load your projects. Check your connection and retry." |
| "Invalid input" | "Card number should be 16 digits — yours has 15." |
| "Access denied" | "You don't have permission to edit this. Ask an admin for access." |
| "Something went wrong" | "Our server hiccuped saving that. We kept your draft — try again." |

- Never blame the user ("You entered it wrong"); never leak a stack trace or internal code as the whole message.
- Preserve their input (behavior: `atelier-harden`); offer the recovery action in the message.

## Empty states

Three parts: **what this is**, **the value when it's populated**, **one clear next action (CTA)**.

> Bad: a blank panel, or "No data."
> Good: "No projects yet. Projects keep your work organized and shareable. **[Create your first project]**"

First-run empties are prime onboarding real estate (`atelier-ux` patterns) — treat them as a feature, not a void.

## Loading / progress

- Honest and specific where possible ("Importing 248 contacts…") beats a bare spinner.
- Don't lie about speed; don't show a fake progress bar that stalls at 90%.
- Skeletons usually need no words; long operations get a short status line.

## Confirmations & destructive dialogs

- **Name the consequence + object + reversibility:** "Delete 3 projects? This permanently removes them and
  their files. This can't be undone."
- **Button says the action, not "OK":** "Delete projects" / "Cancel". The destructive button is visually
  distinct.
- Only confirm when the action is destructive or expensive — confirmation fatigue is real; don't gate
  reversible actions.

## Tooltips, hints, notifications

- **Tooltip:** supplementary only (it's hidden on touch + from keyboards) — never the only place
  task-critical info lives. Put that in helper text.
- **Toast/notification:** one idea, past-tense result ("Changes saved", "Invite sent"), with an action if
  reversible ("Undo"). Auto-dismiss success; persist errors until acknowledged.
- **Onboarding lines:** one benefit-led sentence per step; never a wall of text in a tooltip tour.

## Nav & system labels

- Short, distinct, parallel grammar, the user's vocabulary ("Billing", "Settings", "Team") — never the
  internal/DB name. Don't be clever over clear in navigation.
