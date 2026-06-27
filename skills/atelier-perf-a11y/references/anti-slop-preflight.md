# Anti-slop pre-ship gate — the "AI Tells" checklist

The perf/a11y gate proves a build *works*. This proves it doesn't *read as AI-generated*. Run it over the
finished output, the same way you run the perf and a11y lists. Each item below is a **Tell** — a pattern
that marks a frontend as templated/LLM-default. A Tell in the shipped build is a fail.

> **`atelier-direction`'s `anti-slop.md` runs at DIRECTION time** (avoid cheap choices in the *plan*).
> **This runs at SHIP time** (catch cheap patterns in the *built output*). Both, every substantial build.

> **Stack-agnostic.** These are patterns, not Tailwind classes — they apply to vanilla CSS, React, or
> anything else. Where a rule cites a class, read the *pattern*.

## The one escape hatch: committed concept devices

A Tell is only a Tell when it's *unmotivated default*. If the Direction Doc's **concept** deliberately
adopts a pattern as a *system* — and it's applied consistently, with intent, across the whole build — it
is not a violation. Example: a "technical spec-sheet" concept may put a `[FIG.0X]` eyebrow on every
section *on purpose*; a brutalist concept may run a marquee as a signature. The test: **can you name the
concept reason in one sentence, and is it executed consistently?** If yes, keep it. If it's just there
because the model reached for it, it's a Tell — cut it.

---

## Layout & composition Tells
- [ ] **Eyebrow restraint.** Small uppercase wide-tracked labels above section headings ≤ **1 per 3
      sections** (hero counts as one) — *unless* eyebrows are a committed concept device. The default
      "tiny mono label above every headline" is the most-shipped AI rhythm. Otherwise: drop it, the
      headline alone is enough.
- [ ] **No split-header default.** "Big headline left + small explainer paragraph right" as a section
      header is banned unless the right column carries a real visual/interactive element. Otherwise stack
      headline-over-body (`max-width: ~65ch`).
- [ ] **Vary layout families.** A layout family (3-image-cards, full-width-quote, split-text-image…)
      appears at most ~once. An 8-section page uses ≥4 different families. **Zigzag cap:** ≤2 consecutive
      "image-left/text-right ↔ text-left/image-right" rows; the 3rd is a fail.
- [ ] **Marquee ≤ 1 per page** (unless the concept *is* kinetic marquees). Two scrolling strips reads as
      filler.
- [ ] **Bento has rhythm + the right cell count.** No empty cells (cells == content count); not one-sided
      repetition; ≥2–3 cells carry real visual variation (image / texture / tint), not all type-on-flat.
- [ ] **Anti-center bias** when the direction isn't editorial/manifesto: avoid centered-everything heroes;
      reach for asymmetry/split/broken-grid (governed by the Direction Doc).
- [ ] **Mobile collapse is explicit** per multi-column section (don't assume the grid "just works").
- [ ] **No numbered section markers as scaffolding.** `01 / 02 / 03` above every section is the eyebrow
      trope one tier deeper — reached for because "landing pages do this." Numbers earn their place only
      when the section genuinely *is* an ordered sequence (a real 3-step process). One deliberate numbered
      sequence is voice; numbered eyebrows site-wide is AI grammar.
- [ ] **No side-stripe accent borders.** A `border-left`/`border-right` thicker than 1px used as a colored
      accent on cards, callouts, or alerts is never intentional — it's the default "make it pop" reflex.
      Use a full border, a background tint, a leading icon/number, or nothing. (Flagged by `scripts/detect.py`.)

## Hero discipline (the most-failed section)
- [ ] **Hero fits the initial viewport** — primary CTA visible without scrolling.
- [ ] **Headline ≤ 2 lines** at desktop; a 4-line headline is a font-size error, not a copy problem.
- [ ] **Subtext ≤ ~20 words / ≤ 4 lines.**
- [ ] **≤ 4 text elements total** (optional eyebrow · headline · subtext · CTAs). Trust-strip, tagline-
      under-CTA, pricing teaser, feature bullets, avatar row → move to sections *below* the hero.
- [ ] **Top padding not excessive** — hero content shouldn't float halfway down the viewport.

## CTA & copy Tells

> UX writing is owned by **`atelier-copy`** (errors, labels, empty-state copy, voice/tone); this is the
> ship-time *tell* check on the rendered words.

- [ ] **CTA text fits one line at desktop** — a wrapping button is broken. 1–3 words for primary CTAs.
- [ ] **No duplicate CTA intent.** "Get in touch" + "Contact us" + "Let's talk" = one intent → one label,
      used everywhere. Same for signup / view-work intents.
- [ ] **Copy self-audit.** Re-read *every* visible string (headlines, eyebrows, buttons, body, captions,
      alt, footer, errors). Cut/rewrite anything grammatically broken, with unclear referents, or
      AI-cute (forced wordplay, mock-poetic micro-meta, fake-craftsman labels). Plain functional copy
      beats clever-wrong copy.
- [ ] **No fake-precise numbers.** `92%`, `4.1×`, `13.4 lb`, invented stats — either real (from the
      brief/brand), explicitly labelled mock, or cut. Don't fake precision the brand doesn't claim.
- [ ] **No AI prose cadence.** Em-dash overuse (the detector flags >6/file), the "Not X. Just Y."
      aphoristic pivot, triadic "X, Y, and Z" auto-pilot, and buzzword filler (seamless/robust/elevate/
      empower) are LLM-writing tells. Vary structure; say the specific thing. (Craft: `atelier-copy`.)
- [ ] **No placeholder-as-label** in forms; labels sit above inputs.

## Color, shape, theme consistency
- [ ] **One accent, locked page-wide.** No surprise second accent in section 7. (Verify in *both* themes —
      an accent that passes on dark can fail as text on light; see the a11y contrast rule.)
- [ ] **One radius scale** (all-sharp / all-soft / all-pill, or a documented per-role rule followed
      everywhere). Round buttons in a square system is broken.
- [ ] **One theme — sections don't invert.** No warm-paper section sandwiched in a dark page (unless a
      deliberate one-time color-block device). Tints within the same family are fine.
- [ ] **No AI-default palette by reflex:** purple/blue gradient-on-white; or the premium-consumer
      beige+brass+espresso cliché. Use them only if the brand explicitly calls for it. (The cream/sand/
      beige body-bg band + its token names are covered at token time in `atelier-foundations` and flagged
      by `scripts/detect.py`.)
- [ ] **No ghost cards.** A near-invisible hairline border + a wide, soft, diffuse drop-shadow on a flat
      white card (the "floating nothing") reads as a generated default. Commit to a real border *or* a real
      elevation shadow with intent — not a faint both.

## Asset Tells (→ owned by `atelier-components` "Real assets")
- [ ] **No div-based fake screenshots.** Hand-built `<div>` "dashboards / task lists / terminal windows /
      product previews" are a Tell. Use a generated image (image-gen-first — on this machine `/codex-imagegen`, then optimized to WebP/AVIF + `width`/`height` + real `alt`), a real screenshot, a real
      mini-component, or editorial photography — or leave a labelled TODO slot. (Our own first pass shipped
      CSS "blueprint" placeholders — that's this Tell; real generated images replaced them.)
- [ ] **Hero has a real visual** — text + a gradient blob is a placeholder, not a hero. Even minimalist
      sites need 2–3 real images.
- [ ] **Real logos for social proof** (Simple Icons / generated marks), not styled text wordmarks; logos
      only, no category labels underneath.
- [ ] **No hand-rolled icon SVGs** — use one icon family; standard stroke width.

## Type Tells (defer detail to `atelier-typography`)
- [ ] **No default Inter/Roboto/Arial** as the display face unless the brief asks for neutral/system.
- [ ] **No unjustified serif** as the "creative = serif" reflex; emphasis inside a headline uses
      italic/bold of the *same* family, not a random second family.

---

> Mechanical where possible: count eyebrows (`uppercase tracking` labels) vs `ceil(sections/3)`; count
> marquees; count consecutive zigzag rows; grep the build for `<div>`-faked UI previews. **Run the
> deterministic detector first** — `python scripts/detect.py <changed files>` (see `detector.md`) — it
> mechanizes the source-detectable subset of these tells (gradient-text, cream tokens, side-stripe,
> pure-black/white, glass-default, bounce easing, buzzwords) so this pass can focus on the rendered-output
> judgments a regex can't make. Anything over the cap, or any unchecked box, is a draft — not shippable.
> **Beauty + speed + access + no-tells, or it isn't premium.**
