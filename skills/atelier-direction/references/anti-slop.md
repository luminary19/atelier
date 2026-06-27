# Anti-slop: expensive vs. cheap

The single filter that lifts every output. **Cheap = a surface trick with no system behind it.
Expensive = a coherent system showing through.** Run this against your Direction Doc before handoff,
and against any built UI before you call it done.

## The cheap tells (AI-slop fingerprints — avoid by default)
- The **purple→blue gradient + frosted glass card** combo (the #1 vibe-coded signature).
- Pure `#000` background + low-contrast grey text.
- **Default Inter / Roboto / Playfair** at random sizes with no scale.
- Glassmorphism on *everything*.
- Centered hero over a dark mesh; three equal feature cards.
- Uniform-size "bento" boxes (no hierarchy).
- Two-stop linear gradient passed off as "mesh."
- Neon glow as a single blurry drop-shadow.
- Constant glitch/warp; infinite-loop micro-animations everywhere.
- Neumorphism used as a system.
- Visible tiled-PNG noise that repeats.
- Cramped spacing; no focal point; everything the same weight.

> Dated tells specifically: neumorphism, literal-texture skeuomorphism (leather/wood), glass-on-everything,
> flat-purple-blob "mesh," constant-glitch cyberpunk. When the brief is "make it feel human, not AI-made,"
> the named 2026 counter-movements are **warm/neo-minimalism** and **collage/scrapbook** (see `aesthetics.md`).

## The category-reflex check (two altitudes)

Slop is a *reflex*. Run this twice before committing a direction — the second altitude catches what the
first one misses:

- **First-order:** could someone guess the theme + palette from the *category alone*? ("Fintech dashboard
  → navy + a blue accent." "AI tool → dark + purple." "Wellness → clinical blue + rounded sans.") If yes,
  it's the first training-data reflex — rework the scene sentence and color strategy until the answer isn't
  obvious from the domain.
- **Second-order:** could someone guess the aesthetic *family* from *category + the obvious anti-reference*?
  ("AI tool that's *not* dark-purple → editorial-typographic." "Fintech that's *not* navy → terminal-dark."
  "Wellness that's *not* clinical-blue → warm-beige-minimal.") This is the trap one tier deeper: you dodged
  the default and landed in the **saturated escape-hatch** everyone else who dodged it also landed in.
  Rework until **both** answers are non-obvious.

**Currently-saturated escape-hatch lanes (the second-order traps of 2026)** — don't default *into* one just
because it's "not the obvious thing":
- **Editorial-typographic** (giant serif headline + lots of whitespace + a thin rule) — the default
  "tasteful" escape from SaaS-cream.
- **Warm-beige / "cozy minimal"** (oat/sand bg + a character serif + grain) — the default escape from
  clinical-blue.
- **Terminal / monospace-dark** (mono everything + green-on-black + a grid) — the default escape from
  corporate-navy.
- **Brutalist-lite** (one huge type size + hard borders + a single acid accent) — the default escape from
  "boring corporate."

One of these *chosen on purpose, expressing a concept* is a real direction. One reached for *because it's
the non-default default* is just slop one level up. Name the concept reason, or pick again.

## The expensive levers (pull these)
- **Generous *active* whitespace** — start with too much, then remove. The cheapest premium signal.
- **A typeface with a point of view** — escape the defaults; spend your one bold type choice.
- **A whisper of grain** (SVG `feTurbulence`, opacity .03–.08, `overlay`).
- **Perceptual color** (OKLCH ramps), **tinted neutrals**, **one disciplined accent**.
- **Elevation by lightness** in dark mode (not muddy shadows).
- **Real grid + baseline discipline**; intentional asymmetry balanced by visual weight.
- **One signature moment**, motion that's *felt not seen* (≤300ms, `transform`/`opacity`).
- **Refraction/liquid/3D as a single earned moment**, never as wallpaper.

## The core test
For every choice ask: **"What system is this part of, and why this value?"** If the answer is "it's the
default" or "it looked cool," it's probably slop. If it's "it's step 9 of the brand ramp / it's on the
8-pt scale / it expresses the concept," it's probably right.

## The "always elevates" shortlist (works under any aesthetic)
1. Grain. 2. Generous whitespace. 3. Restraint (one accent, one hero moment, one technique done right).
4. A typeface with a point of view. 5. Perceptual color + a real token system. 6. Execute the system,
not the surface.

## Redesign / audit note
If this is a redesign, **audit before you touch anything**. Inventory the existing brand (logo, color,
type, photography) — these are starting material, not noise. Then name the specific slop tells present
(from the list above) and the specific expensive levers missing. Upgrade by *adding system* (tokens,
scale, whitespace, a real type choice) and removing tricks — not by piling on more effects. Don't break
working functionality, IA, or accessibility in the name of looks.

## Two-worlds reminder
The bar for "expensive" differs by world (see the SKILL.md table). Production work earns it through
restraint, system, performance, and accessibility. Award work earns it through a bold concept and a
signature moment — but still ships fallbacks. Know which you're in before you judge an output.
