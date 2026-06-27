# Upgrade playbook — add system, remove tricks, don't break it

Apply after the audit. The principle: a premium upgrade is **more discipline, not more effects.** Work in
a safe order, keep changes per-section (reviewable), and preserve everything that works.

## Safe order (most lift, least breakage)
1. **Tokens first (`atelier-foundations`).** Introduce OKLCH color ramps + semantic tokens, a modular/
   fluid type scale, and an 8pt spacing scale as CSS vars / Tailwind `@theme`. Replace scattered hardcoded
   hex/px with token references. *Highest coherence win, lowest visual risk* — often transforms the feel
   before you change a single layout.
2. **Typography (`atelier-typography`).** Swap default fonts for a typeface with a point of view (premium
   foundries are fair game); fix scale contrast, leading (1.5–1.7 body / 0.95–1.1 display), tracking, and
   measure (60–75ch). Cheap, huge perceived-quality jump.
3. **Layout & whitespace (`atelier-layout`).** Add macro whitespace, establish one focal point per view,
   introduce a real grid and intentional asymmetry, fix hierarchy. **Don't reflow the IA** — restructure
   visual layout, not information architecture.
4. **Components (`atelier-components`).** Where you're already touching them, align to the system (shadcn +
   token mapping) for consistency + accessibility. Don't rip out a working component lib wholesale unless a
   migration was requested. (On a shadcn codebase, `npx shadcn@latest add --diff <component>` previews what
   upstream changed before you re-pull — drift detection without overwriting your edits.) Modernizing is the moment to swap hand-rolled JS for now-Baseline native
   primitives — Popover API + Invoker Commands + anchor positioning (tooltips/menus/popovers), native
   `<dialog>` (modals), `<details name>` (exclusive accordions), `field-sizing: content` (auto-grow inputs):
   less code, free top-layer/focus/Esc a11y. Keep a fallback where a feature isn't fully cross-engine yet.
5. **Motion (`atelier-motion`).** Add restrained feedback + reveals (≤300ms, transform/opacity, reduced-
   motion-safe). Remove infinite-loop / excessive motion found in the audit.
6. **Scroll / WebGL (`atelier-scroll` / `atelier-webgl`).** Only if the new direction earns a signature
   moment. Never as decoration; always with fallbacks.

## High-ROI / low-risk fixes (do these first, almost always)
- Replace `#000` + grey text with charcoal + proper-contrast text (OKLCH, elevation-by-lightness in dark) —
  and desaturate the accent on dark (pull chroma down so it doesn't vibrate on charcoal); a saturated accent
  over `#000` is the #1 vibe-coded dark-theme tell.
- Default fonts → a real typeface; fix the scale.
- Add generous macro whitespace; create one clear focal point.
- One disciplined accent (kill rainbow/everything-colored); 60-30-10.
- Add a whisper of grain (SVG `feTurbulence`, opacity .03–.08) — kills banding, adds depth.
- Kill the slop combos: purple-gradient+frosted-card, glass-on-everything, uniform bento, two-stop "mesh."

## Preserve (the non-negotiables of a redesign)
- **Functionality & state** — forms, auth, data, interactions keep working.
- **IA & URLs** — don't move pages/routes; keep nav structure; protect SEO.
- **Semantics & headings** — preserve heading hierarchy and landmark structure (SEO + a11y).
- **Accessibility** — keep/improve alt text, ARIA, keyboard flows, focus, contrast. Never regress.
- **Brand equity** — recognizable logo/color/voice stay (anchor the Direction Doc to them).

## Safety practices
- **Per-section, reversible changes** — not one giant diff. Easier to review and roll back.
- **Before/after** on the changed sections and on Core Web Vitals.
- Introduce tokens alongside the old values first, migrate references, then remove the old — avoids a
  big-bang break.

## Verify (the gate), then red-team
Run **`atelier-perf-a11y`** (it owns the full list). A redesign isn't done until:
- Core Web Vitals are **no worse** (ideally better) at p75 (field/CrUX, not lab) — LCP ≤2.5s, CLS ≤0.1,
  INP ≤200ms (INP is the most-failed; offscreen sections `content-visibility: auto`, split long tasks with
  `scheduler.yield()` + a fallback since it's not in Safari).
- Keyboard + screen-reader pass on every changed flow; contrast ≥ AA; visible `:focus-visible` everywhere;
  interactive targets ≥24×24px (WCAG 2.2). OS preferences honored — `prefers-reduced-motion`, plus
  `prefers-contrast` / `prefers-reduced-transparency` / `forced-colors` don't break the new look (glass →
  solid, focus survives).
- Functionality + IA + SEO confirmed intact.
Measurably not worse on the fundamentals, clearly better on the craft = a successful redesign.

For a **substantial** redesign, escalate past the self-checklist to **`atelier-review`** — the adversarial
red-team (independent reviewers per dimension + live browser verification). A redesign is the canonical
"substantial build" case it's built for; the self-gate alone under-checks a full before→after.
