---
name: atelier-copy
version: 1.0.0
description: >
  Atelier suite — the UX-writing & microcopy layer. The words inside the interface are part of the
  design: button and action labels, form labels and helper text, error messages, empty-state and
  loading copy, confirmation and destructive-action dialogs, tooltips, onboarding lines, and notifications.
  Write copy that's clear, human, specific, and on-voice — verb-first actions, errors that say what
  happened + why + how to fix it, empty states that onboard, no jargon-as-label, no duplicate CTA
  intents, no fake-precise numbers, no AI-cute wordplay. Use whenever writing or fixing interface copy,
  microcopy, error/empty/loading text, labels, button text, or when the wording feels generic, confusing,
  robotic, or off-brand. This owns the WORDS only — which screens/states exist is atelier-ux, their
  production behavior (overflow, locale, validation) is atelier-harden, and the markup is atelier-components.
  Part of the Atelier suite.
triggers:
  - ux writing
  - microcopy
  - copy
  - error message
  - button label
  - empty state copy
  - confusing wording
  - rewrite this text
  - tone of voice
  - labels
allowed-tools:
  - Read
  - Write
  - Edit
---

# Atelier — UX Writing & Microcopy

The fastest way to make a polished interface feel cheap is the words. A pixel-perfect form with the
label "Submit", an error that says "Error: null", and an empty state that says "No data" reads as
unfinished — because it is. This skill treats copy as design: every visible string is a decision, on the
project's voice, doing a job.

> **Project memory:** if **`ATELIER.md`** exists at the project root, read its **Personality** (the voice
> traits) and **Register** first — they set the voice this copy must hold. Missing on substantial work?
> Offer **`/atelier init`** (owned by the **`atelier`** router).
>
> **Suite map.** **`atelier-ux`** decides the flows and *which* screen-states exist; this writes the words
> in them. **`atelier-components`** builds the markup the copy lives in (labels, errors, empty states) and
> calls here for the strings. **`atelier-harden`** owns the *behavior* of error/empty/form states and
> locale formatting; this owns their *words*. The **`atelier-perf-a11y`** anti-slop gate runs the "copy
> self-audit" Tell (and points here); **`atelier-review`**'s CODE/COPY reviewer checks against this skill.
> Deep reference: `references/fundamentals-deepdive.md`.

---

## The flow

1. **Lock the voice** (from `ATELIER.md` / Direction) → 2. **Inventory every visible string** →
3. **Fix the high-stakes copy** (errors, empty, destructive, primary CTAs) → 4. **Labels & microcopy** →
5. **Terminology consistency** pass → 6. **Self-audit** (cut AI-cute, fake-precise).

## 1. Lock the voice

Voice is constant; tone flexes by moment. Pull the three personality words + register from `ATELIER.md`
(or the Direction Doc). Full method in **`references/voice-and-tone.md`**. The rule: **voice is who you
are** (calm, expert, warm — set once); **tone is how you read in context** (an error is plain and
reassuring; a success is brief; an upsell is light). One register per surface — don't slip between playful
and formal in the same flow.

## 2. Inventory every visible string

List them by type — they have different jobs and rules: **actions/CTAs**, **form labels + helper text**,
**errors + validation**, **empty / loading / partial states**, **confirmations / destructive dialogs**,
**tooltips / hints**, **notifications / toasts**, **onboarding lines**, **nav labels**, **alt text**,
**footer / legal**. You can't fix what you haven't enumerated.

## 3. Fix the high-stakes copy first

The strings that decide trust and task success (patterns in `references/microcopy-patterns.md`):
- **Errors: what happened + why + how to fix.** Human language, never a raw code or "null" alone, never
  blame the user. "We couldn't save — you're offline. We'll retry when you reconnect." Preserve their input
  (behavior is `atelier-harden`).
- **Empty states: onboard, don't apologize.** Name the value + one clear first action. Never a bare "No
  data" or blank panel.
- **Destructive confirmations: name the consequence + the object + reversibility.** "Delete 3 projects?
  This can't be undone." Not "Are you sure?".
- **Primary CTAs: verb + object, specific.** "Create account", "Save changes", "Start free trial" — not
  "Submit", "OK", "Click here".

## 4. Labels & microcopy

- **Labels above inputs, always** — a placeholder is **not** a label (it vanishes on focus, fails a11y).
  Use placeholders only for format examples; put requirements in persistent helper text.
- **Verb-first, specific, parallel** — actions are verbs; sibling actions share grammar ("Edit / Duplicate
  / Delete", not "Edit / Duplication / Remove item").
- **Sentence case** for UI text by default (easier to read than Title Case); reserve Title/UPPER for brand
  moments decided in direction.
- **Helper > tooltip** for anything required to complete a task (tooltips hide on touch and from keyboards).

## 5. Terminology consistency (one word per concept)

Pick one term per concept and use it everywhere — "Projects" is not sometimes "Workspaces" or "Boards".
Match the **user's vocabulary**, not the database's ("Billing", not "SubscriptionEntity"). Keep a tiny
glossary for the project; it prevents the slow drift that makes a product feel incoherent.

## 6. Self-audit (the anti-slop pass on words)

Re-read **every** visible string out loud and cut:
- **AI-cute copy** — forced wordplay, mock-poetic micro-meta ("Let's craft magic ✨"), fake-craftsman
  labels. Plain functional copy beats clever-wrong copy every time.
- **Fake-precise numbers** — `92%`, `4.1×`, `13.4 lb` invented for effect. Real (from the brand), an
  explicitly-labelled mock, or cut.
- **Duplicate CTA intents** — "Get in touch" + "Contact us" + "Let's talk" = one intent → one label,
  reused. (This is an `atelier-perf-a11y` anti-slop Tell too.)
- **Marketing slop** — "seamless", "robust", "elevate", "empower", "unlock", "supercharge", "delve",
  "in today's fast-paced world". Say the specific thing instead.
- **Jargon / unclear referents / broken grammar** — anything a first-time user wouldn't parse.

---

## Operating principles
- **Copy is design.** A polished UI with placeholder words ships as slop. Every visible string is a decision.
- **Clarity over cleverness, always.** The plain version that one-shots comprehension beats the witty one
  that needs a second read.
- **Errors are a trust moment** — say what happened, why, and how to fix it; never blame, never leak a stack trace.
- **One voice, one term per concept** — drift in either is what makes a product feel incoherent.
- **Cut AI tells in words too** — no fake precision, no forced whimsy, no duplicate CTAs, no buzzword filler.
