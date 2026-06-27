---
name: codex-imagegen-taste
version: 1.0.0
description: |
  Premium, anti-slop DESIGN layer over /codex-imagegen: turn a brief into an
  art-directed, one-image-per-section website comp (landing page, hero, full mockup,
  design reference) by injecting a taste preamble + a locked house style into EACH
  call of the codex-imagegen helper. This is the BRAIN (what to draw, how, anti-slop);
  /codex-imagegen stays the HANDS (renders key-free via the local Codex CLI and finds
  the PNG). Use when asked for a "landing page mockup", "full website comp", "hero
  image", "premium UI mockup", "design reference image", or "make a nice <page> image".
  DEFER to bare /codex-imagegen for a quick moodboard, a single abstract sketch, a
  simple icon/texture/logo, or atelier-direction's 8-direction board - those do NOT
  need the taste layer.
triggers:
  - landing page mockup
  - full website comp
  - website design comp
  - hero image
  - premium UI mockup
  - design reference image
  - make a nice landing page image
  - codex-imagegen-taste
  - taste image
user-invocable: true
allowed-tools:
  - Bash
  - PowerShell
  - Read
  - Write
  - Glob
---

# /codex-imagegen-taste - taste + anti-slop layer over /codex-imagegen

Produce a PREMIUM website comp - an art-directed, one-image-per-section design
reference a developer can build from - by wrapping the bare image generator in real
art direction. Bare `/codex-imagegen` knows how to make Codex render a PNG; it has no
taste. This skill supplies the taste and drives the bare helper concretely.

- **BRAIN (this skill):** decide section count, hero scale, the combinatorial look,
  the locked palette/type/CTA/treatment, the per-section composition - and the
  anti-slop rules. Full reasoning in `references/taste-ruleset.md`.
- **HANDS (`/codex-imagegen`):** render each prompt key-free through the local Codex
  CLI's built-in `image_gen` tool and find the file. This skill never re-implements
  `codex exec` and never talks to Codex directly - it calls the real helper.

## When to FIRE vs DEFER (the boundary)

**FIRE this skill for** a landing-page mockup, a full website comp, a hero image, a
premium UI mockup, or any "make a nice <page> image" design reference - anything where
the output must look art-directed and premium and read as one coherent site.

**DEFER to bare `/codex-imagegen`** (do NOT load the taste layer) for:
- a quick **moodboard** - including **atelier-direction's 8-direction board** (that
  step calls `codex-image.ps1` directly at 1536x768 with abstract collage tiles, on
  purpose; it must stay lightweight and is out of scope here);
- a single **abstract sketch**, a one-off **texture/pattern**, a **logo / icon**, an
  **OG card**, or refining one existing asset with `-Edit`.

Rule of thumb: multi-section, premium, "this is the design" -> here. Single, quick,
exploratory, or a lone asset -> bare `/codex-imagegen`.

## How it works (read once)

- **One section = one call.** Plan N sections, then call the wrapper once per section.
  Never ask for the whole page in one frame; never use `-Count N` to fake sections
  (that only makes variations of a single prompt).
- **The wrapper injects taste on every call.** `scripts/taste-image.ps1` reads
  `references/taste-preamble.md`, prepends it + the LOCKED style spec + this section's
  art direction, and passes the composed prompt to the real `codex-image.ps1`. So the
  taste reaches Codex structurally - it is not left to memory.
- **The helper owns rendering + file discovery.** `codex-image.ps1` forces the built-in
  `image_gen` tool (no `OPENAI_API_KEY`), does the before/after filesystem diff, and
  copies the PNG into `-OutDir`. Never trust the agent's claimed save path; trust the
  helper's `CREATED:` lines. Exit codes pass through: `0` created, `2` none found
  (surface the agent message), `1` preflight/error.

## The method

1. **Plan.** Infer the site type + primary conversion goal. Choose the section count
   (defaults: landing/product/portfolio = 6, full website = 8; a lone hero = 1) and
   **announce it out loud** ("Generating N images, one per section").
2. **Lock the look once.** Pick the hero scale (Giant / Mid / Mini) and the
   combinatorial combination (theme, type, hero architecture, section system, 2 motion
   cues, narrative spine, one second-read moment), then write a single **LOCKED STYLE
   SPEC** string: palette (1 primary + 1 secondary + 1 accent + neutrals) + type family
   + CTA family + image treatment + radius language. This same string threads through
   every section call - it is what makes the frames read as one site.
3. **Art-direct each section.** For each section pick a **composition anchor** + a
   **background mode** + a **CTA variation**, varied across the page (>= 3 anchors
   appear; never the same anchor twice in a row; don't reflex to left-text/right-image).
   Write that as the section's `-SectionPrompt`.
4. **Render the loop.** Call the wrapper once per section (below), labelling each
   `Section X of N: <name>`. `Read` a couple of the returned PNGs to show them.
5. **Continuity + clarity.** Keep palette/type/CTA-identity/treatment/radius identical
   across all frames (only anchor/background/density/second-read vary). Run the clarity
   check in `references/taste-ruleset.md` (sec. 8) before declaring done; regenerate any
   missing section.

## Concrete invocation

Run `/codex-imagegen`'s **preflight once** first (it checks `codex` + ChatGPT login +
the `image_gen` tool - see that skill's SKILL.md). Then render **one section per call**,
threading the SAME `-StyleSpec` through every call. Use `-DryRun` first to see the exact
composed prompt; drop it to actually render.

```powershell
$skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
& "$skills\codex-imagegen-taste\scripts\taste-image.ps1" `
  -Section "1 of 6: Hero" `
  -StyleSpec "Deep dark mode; ink + graphite neutrals, one electric-cyan accent; Neue-Montreal-like grotesk, tight tracking; primary CTA = solid cyan pill; 12px radius; matte surfaces, low-chroma tonal depth" `
  -SectionPrompt "Mid Editorial hero; bottom-left text over a full-bleed graded product render; short 6-word headline; one cyan primary pill + a ghost secondary; generous negative space" `
  -OutDir ".\.atelier\comps" `
  -Size 1536x1024 `
  -DryRun
```

On a real run the wrapper prints `CREATED: <absolute path>` per section (via the
helper). Loop it for sections 2..N with the **same** `-StyleSpec` and a new `-Section`
/ `-SectionPrompt` each time.

### Wrapper parameters

| Param | Meaning | Default |
|-------|---------|---------|
| `-SectionPrompt` | the art-directed brief for THIS section (required) | - |
| `-OutDir` | where PNGs land (required) | - |
| `-Section` | label only, e.g. `"3 of 8: Features"` | `""` |
| `-StyleSpec` | the LOCKED shared style spec (thread it through every call) | `""` |
| `-PreambleFile` | override the taste preamble | this skill's `references/taste-preamble.md` |
| `-Size` | `1536x1024` (landscape comp), `1024x1536`, `1024x1024`, `auto` | `1536x1024` |
| `-Model` | force a Codex model (e.g. `gpt-5.1-codex`) | Codex default |
| `-Transparent` | request a transparent background | off |
| `-TimeoutSec` | hard cap per run (passed through) | `420` |
| `-DryRun` | print the composed command + injected preamble, do not render | off |

## Reliability & guardrails

- **Key-free only.** The helper uses the ChatGPT login; never introduce
  `OPENAI_API_KEY`. If the agent asks for a key it reached for the fallback - re-run.
- **ASCII-only on the generation path.** `taste-image.ps1` and `taste-preamble.md` are
  ASCII on purpose (the preamble is embedded into the Codex prompt; non-ASCII risks
  encoding breakage on PowerShell 5.1). Keep them that way.
- **Lead with the medium.** The preamble opens every prompt with "UI mockup / website
  design comp, no people, no stock photography unless asked" - gpt-image drifts to
  photography for UI asks otherwise. Don't strip that.
- **Token-aware.** Each image costs ~30k agent tokens. Generate once per section; do not
  loop or auto-regenerate. If `NO IMAGES FOUND` (exit 2), surface the agent message and
  re-run deliberately, not blindly.
- **Self-sanitizing prompt.** The wrapper normalizes the composed taste prompt (any
  double-quote -> single quote, whitespace flattened) so it passes safely as one native
  arg through the npm `codex` shim regardless of the helper version; `-DryRun` prints the
  exact normalized taste prompt (the helper then wraps it in its own forcing instructions).
- **Per-section files don't collide.** Each section lands in its own subfolder of `-OutDir`
  named from `-Section` (e.g. `-OutDir .\comps` + `-Section "3 of 8: Features"` ->
  `.\comps\3-of-8-features\`), because the helper derives filenames from the prompt (which
  shares the leading preamble across sections).
- **Don't reimplement the hands.** All Codex orchestration + file discovery lives in
  `codex-image.ps1`. This skill only composes prompts and calls it.

## References

- `references/taste-ruleset.md` - the full design brain (variation engine, anti-slop
  catalogue, palette/material rules, section packs, the clarity check). Read to plan.
- `references/taste-preamble.md` - the distilled, codex-ready slice injected into every
  render. Edit here to tune what rides along on every call.

## Atelier integration

The Atelier suite reaches for this skill (via the Skill tool) when the deliverable is a
**premium final image / mockup / hero / full landing comp** - e.g. from
`atelier-components` (the "real assets - images" step) or a direct "mock this page as an
image" request. The lightweight **8-direction moodboard in `atelier-direction` stays on
bare `/codex-imagegen`** and is never routed here. Honor `ATELIER.md` (palette, type
voice, register) when it exists: fold the project's tokens into the LOCKED STYLE SPEC so
the comp matches the rest of the build.
