# Timing, easing & the 12 principles

## Duration defaults
| Interaction | Duration |
|---|---|
| Hover / press / toggle / focus ring | 120–200ms |
| Reveal / fade-in / small move | 200–300ms |
| Modal / drawer / dropdown / page transition | 300–450ms |
| Hard ceiling for standard UI | ~500ms |
| Respond to *any* input (press/ripple/scale) | ≤100ms (even if the full transition runs longer) |

Distance & size scale duration: bigger/farther elements take slightly longer; small elements snap.

## Easing by intent
```css
:root {
  --ease-out:    cubic-bezier(0.16, 1, 0.30, 1);   /* entrances: fast in, gentle settle */
  --ease-in:     cubic-bezier(0.4, 0, 1, 1);        /* exits: accelerate away */
  --ease-in-out: cubic-bezier(0.4, 0, 0.2, 1);      /* moves between two on-screen states */
  /* linear: continuous only (spinner, marquee, progress) */
}
```
- **ease-out** for things arriving (the responsive, "it came to me" feel) — the default for most UI entrances.
- **ease-in** for things leaving.
- **ease-in-out** / Material "standard" for repositioning visible elements.
- Avoid the browser default `ease` for important UI; use tuned curves stored as tokens.

## Springs (physical, interruptible)
- **stiffness** — snappiness (higher = faster). **damping** — settle/bounce (lower = more oscillation).
  **mass** — weight (higher = slower, more overshoot).
- Why springs: they carry current velocity, so an interrupted/redirected animation continues naturally
  instead of restarting — ideal for drag, sheets, toggles, anything direct-manipulation.
- Motion presets: snappy `{ type:"spring", stiffness:300–500, damping:30–40, mass:1 }`; playful = lower
  damping; Motion also exposes intuitive `{ type:"spring", duration, bounce }`.
- Use **duration+easing** instead for deterministic, choreographed sequences (you need exact timing).

## Stagger & orchestration
- Per-item stagger **30–80ms**, total cascade **< 600ms** (cap large lists or use distance-based stagger).
- Orchestrate with **overlap** (next starts before previous ends) for fluidity; one focal point; consistent
  motion "voice"; never multiple competing simultaneous motions in production UI.

## When motion helps vs hurts
- **Helps:** shows state change; feedback (<100ms); guides attention/spatial mapping; masks latency
  (skeleton/optimistic); continuity between states (shared-element); brand expression in moderation.
- **Hurts:** blocks/delays the user; fires on every scroll tick; competes with content; gates function on
  pointer-only/JS-only behavior; continuous looping; anything >~500ms or that the user waits on.

## The 12 Principles of Animation → UI
1. **Squash & stretch** — button press squish, rubber-band overscroll, elastic toggles.
2. **Anticipation** — a control dips/winds up before launching a menu; loaders gather before resolving.
3. **Staging** — direct attention: dim background for a modal; one focal animation at a time.
4. **Straight-ahead vs pose-to-pose** — procedural/physics vs keyframed; most UI is pose-to-pose, springs
   are straight-ahead-ish.
5. **Follow-through & overlapping action** — trailing elements, stagger, spring overshoot/settle.
6. **Slow in & slow out (easing)** — the single most important principle: ease-out entrances, ease-in exits.
7. **Arcs** — move along curved paths, not dead-straight (FABs, shared-element transforms feel organic).
8. **Secondary action** — supporting motion (icon rotates as a panel slides) that doesn't distract.
9. **Timing** — duration conveys mass/urgency; heavy things move slower.
10. **Exaggeration** — slightly amplified success/celebration states — use rarely, for delight.
11. **Solid drawing** — consistent depth, z-order, perspective, light direction across transitions.
12. **Appeal** — charisma; brand-distinct motion that earns attention.
