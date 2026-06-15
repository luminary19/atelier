---
name: atelier-redesign
version: 1.0.0
description: >
  Atelier suite — audit & upgrade existing sites/apps to premium without breaking them. Audit-first:
  inventory the current brand/IA/stack, name the specific AI-slop tells and the missing "expensive"
  levers, score gaps by impact vs risk, then apply the Atelier suite (direction → foundations → type →
  layout → motion → components → scroll/webgl) selectively, preserving functionality, content, SEO, and
  accessibility, and verifying with the perf/a11y gate. Use whenever improving, modernizing, polishing,
  or redesigning an existing website or app, fixing a design that looks dated/generic/templated/cheap, or
  doing a UI audit. This is the front door for EXISTING-site work — start here rather than
  atelier-direction when the site/app already exists; it brings the rest of the suite (direction
  included) in as needed. Supersedes older redesign skills. Default stack: Tailwind v4 + shadcn. Part
  of the Atelier suite.
triggers:
  - redesign
  - audit this site
  - make this look better
  - modernize the UI
  - this looks generic
  - upgrade the design
  - polish the frontend
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - WebFetch
---

# Atelier — Redesign & Audit

Upgrading existing work is different from greenfield: you must **add system without breaking what works.**
The failure mode is "piling on more effects." The fix is the opposite — diagnose what *system* is missing,
add it, and remove the tricks. Audit before you touch anything.

> **Uses the whole suite:** `atelier-direction` (anti-slop lens), `atelier-foundations` (tokens),
> `atelier-typography`, `atelier-layout`, `atelier-motion`, `atelier-components`, `atelier-scroll`/
> `atelier-webgl` (only if earned), gated by `atelier-perf-a11y` and — for a substantial redesign —
> red-teamed by `atelier-review` (a redesign is the canonical "substantial build" case). Deep reference:
> `references/fundamentals-deepdive.md` (§15). **Supersedes** the older `redesign-existing-projects` skill.

---

## The flow

1. **Audit (don't touch yet)** → 2. **Name slop tells + missing levers** → 3. **Score by impact vs risk**
→ 4. **Re-direct** → 5. **Upgrade in safe order** → 6. **Verify (perf/a11y + regression)** → 7. **Adversarial
review** (substantial redesigns).

## 1. Audit first

Inventory before judging. Full method in **`references/audit.md`**: read the existing **brand** (logo,
color, type, photography — starting material, not noise), **IA / content / flows**, **stack** (so you
upgrade in-place, not rewrite), and the current **design system** (or absence of one): grid, type scale,
color logic, spacing rhythm, motion, perf, a11y. WebFetch the live site or read the codebase; ask for a
screenshot if it's JS-rendered/blocked.

## 2. Name the slop tells + the missing levers

Use the anti-slop lens from `atelier-direction`. Name the *specific* cheap tells present (e.g. `#000` +
grey text, default Inter, glass-on-everything, purple-gradient+frosted-card, uniform bento, no focal
point, cramped spacing) and the *specific* expensive levers missing (real grid, OKLCH tokens, generous
whitespace, a typeface with a point of view, grain, one accent). Be concrete — "this section, this value."

## 3. Score by impact vs risk

Not everything is worth changing. Rank fixes by **impact** (how much it lifts the look/UX) vs **risk** (how
likely it breaks functionality/IA/SEO/a11y). The high-ROI / low-risk set is almost always: **whitespace,
type, color tokens (OKLCH), one accent, grain, killing the slop combos.** Surface the plan before mass edits.

## 4. Re-direct

Produce a (scaled) Direction Doc via `atelier-direction` for the target state — but **anchored to the
existing brand** (preserve logo/equity/recognizable color where it works). Decide the world and the one or
two signature improvements. Don't impose an unrelated aesthetic on an established brand.

## 5. Upgrade in safe order (system first, tricks last)

Playbook in **`references/upgrade-playbook.md`**. The order that adds the most with the least breakage:
1. **Tokens** (`atelier-foundations`) — introduce OKLCH color, type scale, 8pt spacing as variables;
   replace scattered hardcoded values. Biggest coherence win, low visual risk.
2. **Typography** — escape default fonts, fix scale/leading/measure.
3. **Layout & whitespace** — add macro whitespace, fix hierarchy/focal point, real grid; don't reflow IA.
4. **Components** — align to the system (shadcn + token mapping) where you're already touching them.
5. **Motion** — add restrained feedback/reveals; respect reduced motion.
6. **Scroll/WebGL** — only if the new direction earns a signature moment; never as decoration.
7. **Imagery** — replace dated / stock / placeholder / low-res images with assets generated on the *new*
   direction via **`/codex-imagegen`** (`codex-image.ps1 -Prompt "…" -OutDir ".\public\img" -Size 1536x1024`;
   `-Transparent` for logos/icons). Preserve `alt`/SEO/dimensions, optimize to WebP/AVIF — and **keep**
   brand-equity photography you're meant to retain (it's starting material, not noise).
Remove the slop tricks as you go. Keep changes reviewable (per-section, not one giant diff).

## 6. Verify

- **Don't break functionality, IA, SEO, or accessibility** — preserve URLs, headings/structure, alt text,
  ARIA, keyboard flows, form behavior. A prettier site that regresses these is a failure.
- Run the **`atelier-perf-a11y`** gate. Compare before/after on Core Web Vitals (a redesign that tanks LCP/
  INP is a loss). Spot-check keyboard + screen reader on changed flows.

## 7. Adversarial review (substantial redesigns)

The perf/a11y gate is the self-check. For a substantial redesign — a real "before → after" with new
direction, tokens, and motion — escalate to **`atelier-review`**: it red-teams the upgraded build with
independent reviewers (a11y, perf, motion, design-fidelity), refutes each finding, and verifies live in a
browser, then applies fixes. A redesign is exactly the "substantial build" `atelier-review` exists for, so
don't stop at the self-checklist. (Skip it for a small touch-up — match the rigor to the change.)

---

## Operating principles
- **Audit before you touch.** Inventory brand/IA/stack/system first; the existing brand is starting
  material, not noise.
- **Add system, remove tricks** — the upgrade is more discipline (tokens, whitespace, real type/grid), not
  more effects.
- **Highest ROI is usually the cheapest:** whitespace, type, OKLCH color, one accent, grain.
- **Preserve what works** — functionality, IA, SEO, accessibility, brand equity. Reversible, per-section
  changes.
- **Gate it, then red-team it** — verify perf/a11y didn't regress (`atelier-perf-a11y`), and for a
  substantial redesign run the adversarial `atelier-review`. A redesign isn't done until it's measurably
  not worse on the fundamentals and clearly better on the craft.
