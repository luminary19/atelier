# The Atelier pipeline — idea to production

The order the suite runs in, and where each skill fits. The `atelier` router recommends entry points
into this; you rarely run all of it. **Scale to the task** — a one-component tweak skips most stages.

## The spine

```
SET UP    atelier (init → ATELIER.md)         one-time per project; the persistent brief
   │
PLAN      atelier-direction   +   atelier-ux  aesthetic (Direction Doc)  ‖  structure (IA + Flow doc)
   │                                          run in parallel — they feed everything downstream
FOUND     atelier-foundations                 OKLCH tokens, scale, spacing, dark mode  → writes ATELIER.md Tokens
   │           │
   │      atelier-typography  +  atelier-layout   the type itself  ‖  grid / whitespace / composition
   │
BUILD     atelier-components                  scaffold + assemble the real component layer
              ├─ atelier-motion               micro-interactions, states, feel
              ├─ atelier-scroll               scroll choreography, page transitions
              ├─ atelier-webgl                3D / shaders (only if earned)
              ├─ atelier-dataviz              charts / dashboard data layer
              └─ atelier-copy                 UX writing: labels, errors, empty-state copy
   │
SHIP      atelier-harden                      resilience: overflow, i18n/RTL, error states, edge data
   │
          atelier-perf-a11y                   the quality gate (perf + a11y + anti-slop) — every build
   │                                          its detector (scripts/detect.py) mechanizes the tells
          atelier-review                      adversarial multi-agent red-team — substantial/award builds
```

## Existing sites

```
atelier-redesign   audit-first front door → pulls direction/foundations/type/layout/motion/components
                   selectively, preserving brand equity + IA + SEO + a11y → perf-a11y gate → review
                   tonal nudges live here too: references/tonal-dials.md (bolder / quieter / distill)
```

## How the stages hand off

- **`atelier` init** writes `ATELIER.md` (register, policies, anti-refs). Every later skill reads it.
- **Direction + UX** produce the **Direction Doc** + **IA + Flow doc** — the two planning artifacts.
- **Foundations** turns the Direction Doc's palette/type/density into tokens and writes them into
  `ATELIER.md`'s Tokens section; **typography** and **layout** consume the scale.
- **Components** assembles using foundations tokens + ux structure + type + layout, wiring in **motion**,
  **scroll**, **webgl**, **dataviz**, and **copy** as the build needs them.
- **Harden** makes it survive real data, translation, and failure; the **perf-a11y** gate proves it works
  and doesn't read as AI-generated; **review** red-teams it.

## Modifiers (occasional, not pipeline steps)

These are corrections you reach for when one axis is off — not default stages:

- **Tone:** `bolder` (too safe) / `quieter` (too loud) / `distill` (too complex) → `atelier-redesign/references/tonal-dials.md`.
- **Single dimension:** type off → `atelier-typography`; spacing off → `atelier-layout`; flat palette →
  `atelier-foundations`; motion janky → `atelier-motion`; copy vague → `atelier-copy`; slow → `atelier-perf-a11y`.

## Reference data

**`atelier-data`** (a Python BM25 lookup the skills call via `scripts/search.py`) supplies cold-start
starting points and do/don't cross-checks at any stage. It's a library, not a stage — it never decides.
