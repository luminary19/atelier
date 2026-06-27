# Tonal dials — bolder · quieter · distill

Three corrective moves for when a *built* design points the wrong way on one axis. They're **occasional
modifiers, not pipeline steps** — reach for one when the work is technically fine but tonally off. Invoke
via `/atelier bolder | quieter | distill` (the router routes here). Each is diagnose-first: name what's
wrong before you turn the dial, and respect `ATELIER.md` (register, anti-references) and the Direction Doc
— a committed concept is not a fault to "fix."

> Pair rule: **bolder ↔ quieter are opposites** — if you're reaching for both, the real problem is an
> unclear Direction Doc; re-decide direction (`atelier-direction`) instead of dialing back and forth.

---

## Bolder — amplify a safe / bland / generic design

**Reach for it when:** the build is competent but forgettable — everything mid-weight, one timid type
size, a default palette, no focal point, no signature moment. "Looks fine" is the symptom.

**Diagnose:** where is it defaulting? Usually (1) type scale too flat (H1 barely bigger than body),
(2) no committed accent / all-neutral, (3) uniform spacing with no rhythm, (4) no signature moment,
(5) stock layout (centered hero + three equal cards).

**The moves (add conviction, not noise):**
- **Raise type contrast** — push the display step up (within the `clamp()` max ~6rem ceiling), tighten
  display tracking toward −0.04em, widen the H1↔body ratio. (`atelier-typography`.)
- **Commit the accent** — move from "restrained" toward "committed" on the color-strategy axis: let one
  saturated color carry more surface. (`atelier-foundations`.)
- **Create a focal point** — asymmetry, scale jump, one hero image or one bold block; kill the everything-
  equal grid. (`atelier-layout`.)
- **Spend one signature moment** — a single award-grade gesture (a real hover, a scroll reveal, a WebGL
  hero) the rest of the page stays calm around. (`atelier-motion` / `atelier-scroll` / `atelier-webgl`.)
- **Generous active whitespace + grain** — the cheapest premium signals. (`atelier-foundations`.)

**Guardrails:** bolder ≠ louder-everywhere. Add conviction in *one or two* places; if everything shouts,
nothing reads. Don't violate the absolute bans (gradient text, glass-on-everything, eyebrow on every
section) in the name of "impact." Re-run the `atelier-perf-a11y` gate — bigger type/motion must still pass
contrast + reduced-motion.

---

## Quieter — calm a loud / busy / overstimulating design

**Reach for it when:** the build is trying too hard — too many accents, competing focal points, motion
everywhere, heavy shadows/gradients/glass, no breathing room. It feels exhausting, not premium.

**Diagnose:** count the things fighting for attention. Usually (1) >1 accent, (2) motion on everything
(infinite loops, every section animating in), (3) over-decoration (glass + gradient + glow stacked),
(4) cramped spacing, (5) every element heavy-weight.

**The moves (subtract):**
- **One accent, locked page-wide** — remove the surprise second/third accent. (`atelier-foundations`.)
- **Cut motion to one or two intentional moments** — kill infinite loops and the uniform section-entrance
  reflex; keep what aids comprehension. (`atelier-motion`.)
- **Strip stacked decoration** — pick one technique (glass *or* gradient *or* glow), done well; drop the
  rest. Demote effects to where they carry meaning.
- **Add whitespace + lower weight** — increase section rhythm, lighten body weight, reduce shadow depth.
- **Re-establish hierarchy** — one clear focal point per section; everything else recedes.

**Guardrails:** quieter ≠ stripped-of-personality. Keep the concept and the one signature moment; remove
the *excess*, not the *idea*. Restraint reads as confidence — but a page with zero motion or zero accent
can read as unfinished; aim for *intentional calm*, not absence.

---

## Distill — strip to essence; remove what doesn't earn its place

**Reach for it when:** the design is complex rather than loud — too many features/options on screen,
redundant sections, duplicate CTAs, decorative elements with no function. Great design is simple; this is
the ruthless 80/20 pass across IA, content, layout, and code at once.

**Diagnose:** for every element ask the core test — **"what system is this part of, and why this value?"**
If the answer is "it's the default" or "it looked cool," it's a candidate to cut. Look for: duplicate CTA
intents, sections that repeat a point, ornament without function, options that could be progressive-
disclosed, copy that could be half as long.

**The moves (remove, merge, defer):**
- **Merge duplicate intents** — three CTAs that mean "contact us" become one label, reused. (`atelier-copy`.)
- **Cut sections that don't add information** — if two sections make the same point, keep the stronger.
- **Progressive disclosure** — move secondary options behind a click; show what's needed now. (`atelier-ux`.)
- **Halve the copy** — every visible string earns its place; cut filler and AI-cute lines. (`atelier-copy`.)
- **Remove ornament without function** — decoration that isn't expressing the concept goes.
- **Simplify the DOM/CSS** — fewer wrappers, retire dead styles; clarity in code mirrors clarity on screen.

**Guardrails:** distill ≠ delete content the user needs. Preserve functionality, IA, SEO, and accessibility
(this is `atelier-redesign`'s prime directive). Removing a real feature or a needed state is a regression,
not a simplification — cut *redundancy and ornament*, keep *substance*.

---

## After any dial

Run the **`atelier-perf-a11y`** gate (tonal changes touch type, motion, color, and markup), and for a
substantial change escalate to **`atelier-review`**. Record the new tonal stance in `ATELIER.md` if it
shifts the project's interactivity or color strategy, so the next session stays consistent.
