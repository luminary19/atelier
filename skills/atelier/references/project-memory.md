# ATELIER.md — the project design-memory file

`ATELIER.md` lives at the **project root** and is the persistent brief every Atelier skill reads before
it works. It is the suite's answer to "the model forgets the design decisions between sessions." One
combined file: the **strategic brief** (who/what/voice/policies) + the **visual system** (tokens). The
`atelier` router's `init` flow writes it; `atelier-foundations` fills/links its Tokens section;
everything else reads it and stays on-brief.

> **Strictly Atelier.** This is Atelier's own format — plain Markdown the model reads directly, no
> external tool or schema required. The structure below is **universal scaffolding**; the values are
> **your project's taste**. Carry the headings; fill the content fresh per project — never inherit
> another project's palette, fonts, or anti-references.

## How skills use it

- **Read at boot.** Each skill's intro says: *if `ATELIER.md` exists, read it first and honor it.* The
  **Register**, **Interactivity**, **Motion policy**, **Glassmorphism policy**, and **Anti-references**
  sections override that skill's defaults.
- **Register routes decisions.** `brand` (design IS the product — marketing, landing, portfolio,
  campaign) vs `product` (design SERVES the product — app, dashboard, tool). It changes color permission,
  motion budget, type drama, and density. A repo can be mixed — record per-surface overrides.
- **Write once, update deliberately.** `init` creates it; re-running `init` *updates* (never silently
  overwrites). `atelier-direction` writes the **Creative direction** section once the look is decided;
  `atelier-foundations` writes the **Tokens** section; `atelier-redesign` reconciles it with an existing
  codebase.

## The template

```markdown
# ATELIER — <Project> design memory

## Register
<brand | product>
<!-- Per-surface overrides, if mixed: e.g. "/ , /about = brand; /app/* , /dashboard = product" -->

## Users
<Who, specifically — role, context, frequency. For product: their primary task/workflow.
 For brand: their state of mind on arrival. Not "users".>

## Purpose
<What this does and why it exists. Success from the user's perspective.>

## Personality
<Three words (voice traits, not visual): e.g. "calm, precise, human". Then one line on how it speaks.>

## Anti-references
<NAMED things to avoid, not adjectives. Name specific sites/patterns/aesthetics you reject.
 e.g. "generic SaaS: purple gradient on white + glass cards + neon accents"; "every-section eyebrow +
 three equal cards". Anti-references stop reflexes better than references set direction.>

## Principles
<3-5 STRATEGIC principles (not visual rules). e.g. "Show, don't tell"; "Restraint reads as confidence".>

## Interactivity
<One of: Static | Responsive | Choreographed | Award-grade.
 Static = functional feedback only. Responsive = transitions + feedback, ~150-250ms, no choreography.
 Choreographed = orchestrated entrances, scroll sequences. Award-grade = WebGL/canvas moments, uncapped.
 Note per-surface overrides (e.g. "product overall; the marketing hero is award-grade").>

## Motion policy
<The library trigger, not just permission. e.g.
 - CSS: all single-element hover/state transitions under 300ms.
 - Motion (motion/react): React component/gesture/exit/layout animation (the suite default).
 - GSAP / Lenis: scroll choreography (via atelier-scroll).
 - anime.js: light vanilla/non-React timelines and stagger.
 - Easing: ease-out (exponential) for entrances; no bounce, no elastic.
 - Reduced motion: required everywhere — reduce, don't strip meaning.>

## Glassmorphism policy
<Your stance, as a rule with a threshold. e.g. "Eligible only over real depth (image/video/canvas),
 to communicate layering, blur() <= 16px, never a card or section background, never over flat color.">

## Accessibility
<WCAG level (2.2 AA is the suite floor; state if higher). Reduced-motion commitment. Contrast method
 (verified from rendered pixels at ship, not eyeballed). Visible focus on every interactive element.>

## Creative direction   <!-- atelier-direction writes/updates this once the look is decided -->
- **World:** <production | award — and where any award-grade "signature moment" lives>
- **Aesthetic:** <named aesthetic or a deliberate pairing — the spine>
- **Concept + signature moment:** <the organizing idea in one line + the one moment that embodies it>
- **Palette mood / type voice / layout archetype:** <the briefs foundations + typography + layout consume>
- **Visual assets:** <icon system; illustration voice or none; imagery medium + treatment>

## Tokens   <!-- the visual system — atelier-foundations writes/links this; stub until then -->
- **Color:** <OKLCH brand ramp + tinted neutrals + one accent; semantic mapping; dark mode if any.
  Link the token file (e.g. `app/globals.css @theme`) once it exists.>
- **Type:** <display / body / mono families; modular ratio; key sizes. (atelier-typography owns choice.)>
- **Spacing / radii / depth:** <8-pt scale reach for the density; one radius family; elevation approach.>
- **Components:** <key recurring decisions — button shape, card treatment, input style.>

## Forge 3D assets   <!-- forge-director writes this once a 3D moment is built; the Atelier <-> Forge seam -->
- **GLB:** `public/forge/<slug>-hero.glb` (DRACO+Meshopt; <size>KB)
- **Poster:** `public/forge/<slug>-hero-poster.webp` (<size>KB; also the reduced-motion / no-WebGL fallback)
- **Scene description:** <one-line description for the canvas DOM-alternative / alt text>
- **DRACO decoder path:** `/draco/` (local) or CDN (specify which)
- **Forge pipeline log:** `.forge-build/export/<slug>-log.txt`

## Do / Don't
### Do
- <specific visual prescriptions with values>
### Don't
- <anti-references from above, echoed verbatim, + project-specific visual guardrails>
```

## Universal scaffolding vs. your taste

**Carry unchanged (the structure that produces coherence):** the section set and order; Register as the
first decision; the four-level Interactivity taxonomy; "library trigger, not just permission" for motion;
glassmorphism written as a thresholded rule; anti-references named (not adjectives) and echoed into
Don't; strategy in the top half, the visual system in Tokens.

**Fill fresh per project (never inherit):** the palette, the fonts, the Creative concept, the
anti-references, the motion/glass policy values. The structure is universal; the content is this
project's alone.

## Scale to the task

A one-component tweak doesn't need an `ATELIER.md`. Create one for **substantial builds and redesigns** —
anything that will span more than one session or where staying on-brief matters. For tiny work, the
inline Direction Read from `atelier-direction` is enough.
