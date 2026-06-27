---
name: atelier-direction
version: 1.0.0
description: >
  Atelier suite — the art-direction brain. Decide the design direction BEFORE writing any
  frontend code: which aesthetic, which "world" (production vs award-grade), the concept, the
  palette mood, type voice, motion budget, layout archetype, and signature moment. Produces a
  Direction Doc scaled to the task (a one-line read for small tweaks, a full one-pager for substantial
  builds/redesigns) that the rest of the suite (atelier-foundations, atelier-typography, atelier-layout)
  consumes. This is the canonical Atelier entry point — prefer it over older/general design skills. Use
  this FIRST whenever building a new website, landing page, web app, dashboard, portfolio, or
  editorial site — or deciding the look/feel/aesthetic of one — and ESPECIALLY whenever frontend
  output risks looking generic, templated, or "AI-made." If the user mentions design, UI, a new page,
  a look/vibe, an aesthetic, names a reference site, or wants to see several distinct creative directions to choose from (a moodboard of options), start here. For upgrading or redesigning an
  EXISTING site or app, start with atelier-redesign instead — it audits first, then pulls this skill
  in to set the new direction.
triggers:
  - art direction
  - design direction
  - what should this look like
  - pick an aesthetic
  - make this look premium
  - new landing page
  - design a website
  - decide the look/direction
allowed-tools:
  - Read
  - WebFetch
  - WebSearch
  - AskUserQuestion
  - PowerShell  # runs /codex-imagegen's helper to render the moodboard + crop/regenerate the chosen pane
  - Agent       # full builds: hand the locked direction + chosen-pane reference to the atelier-director agent
---

# Atelier — Art Direction

The conductor of the Atelier suite. **Direction is where "slop" is born:** most AI frontends look
generic because the model jumps straight to a default look (purple gradient, centered hero, three
equal cards, Inter + slate-900) instead of deciding *what this specific thing should be*. This skill
forces that decision first, then hands a crisp brief to the rest of the suite.

> **Project memory:** if **`ATELIER.md`** exists at the project root, read it first — it carries this
> project's **register** (brand vs product), interactivity/motion/glassmorphism policy, anti-references,
> and tokens, and it overrides defaults. Missing on a substantial build? Set one up with **`/atelier init`**.
> The **`atelier`** router is the suite's hub — it recommends the next step and dispatches to any skill here.
>
> **Suite map.** `atelier-direction` (you are here) + **`atelier-ux`** (IA / flows / structure) →
> `atelier-foundations` (tokens: color/type-scale/spacing) → `atelier-typography` (the type itself) +
> `atelier-layout` (structure) → build with `atelier-motion` / `atelier-scroll` / `atelier-webgl` /
> **`atelier-dataviz`** (charts) / `atelier-components`, with **`atelier-copy`** for UX writing → make it
> production-grade with **`atelier-harden`** (resilience) → ship through the `atelier-perf-a11y` gate, and
> for substantial/award builds the adversarial **`atelier-review`** red-team. Run direction first (with
> `atelier-ux` deciding structure in parallel); the **Direction Doc** + **IA + Flow doc** are the inputs to
> everything downstream. Deep reference for everything:
> `references/fundamentals-deepdive.md`.
>
> **Data — `atelier-data`:** cold-start ideation only — per-product-type recommendations + design reasoning/anti-patterns + a style catalog via `atelier-data` (`scripts/search.py "<industry/product>" --domain product|reasoning|style`). Seeds, not decisions; the direction is decided here.

The whole point: **execute a system, not a surface.** Every "cheap" look is a trick applied without
a reason; every "expensive" look is a coherent decision carried all the way through. Your job here is
to make the decision.

---

## The flow

1. **Read the brief** → 2. **Declare the Design Read** (one line) → 3. **Offer the 8-direction choice**
(substantial builds only) → 4. **Pick the world** → 5. **Choose an aesthetic direction** →
6. **Find the concept** → 7. **Write the Direction Doc** → 8. **Hand off** to foundations/typography/layout.

> If the user takes the 8-direction offer in step 3, their pick already fixes the world + aesthetic +
> concept, so you skip steps 4–6, **reconstruct the chosen pane into an image-faithful reference** (crop →
> image-guided regenerate → deconstruct — see "After the pick" under step 3), then write the Direction Doc
> (step 7). For a **full build**, step 8 hands the locked direction + that reference to the
> **`atelier-director`** agent (it does not re-run direction).

Don't skip to code. The Direction Doc is the deliverable of *this* skill.

---

## 1. Read the brief

Infer what the user actually wants before touching anything. Read these signals:

- **Page kind** — marketing/landing (SaaS, consumer, agency, event), web app/dashboard (data-dense,
  task-first), portfolio/creative (expressive), editorial/content (reading-first). This sets the
  **register**: *brand* (design IS the product — distinctiveness is the bar) vs *product* (design SERVES
  the product — earned familiarity is the bar). Record it in `ATELIER.md`; it governs color permission,
  motion budget, and type drama for every downstream skill. A repo can be mixed (marketing + app) —
  note per-surface overrides.
- **Audience** — *the audience picks the aesthetic, not your taste.* A B2B procurement panel, a
  design-conscious consumer, a recruiter scanning a portfolio, and a regulated-industry user want
  opposite things.
- **Vibe words** the user used — "minimalist", "Linear-style", "Awwwards", "premium", "Apple-y",
  "brutalist", "editorial", "playful", "dark tech", "luxury".
- **References** — URLs, screenshots, named products/competitors. If they gave a reference, **mine it**
  (see `references/inspiration.md`) instead of inventing.
- **Existing brand** — logo, color, type, photography. For redesigns these are starting material,
  not optional. Audit first (see anti-slop's redesign note).
- **Quiet constraints** — accessibility-first audiences, public sector, trust-first commerce, kids'
  products, performance budgets. **These override aesthetic preference.**

## 2. Declare the Design Read (one line, before anything else)

State, in one sentence: **"Reading this as: a `<page kind>` for `<audience>`, with a `<vibe>` language,
leaning toward `<aesthetic family>`."**

Examples:
- *"B2B SaaS landing for technical buyers, Linear-style restraint, leaning dark-tech + OKLCH tokens +
  Geist + minimal motion."*
- *"Solo designer portfolio for hiring managers, editorial/kinetic-type language, leaning broken-grid +
  variable display type + scroll choreography."*
- *"Internal analytics dashboard for ops, clarity-first, leaning Swiss grid + tabular type + near-zero
  motion."*

**If the brief is genuinely ambiguous, ask exactly one question** — never a dump — and only when the
read truly diverges (e.g. *"Closer to Linear-clean or Awwwards-experimental?"*). If you can infer
confidently, don't ask: declare and proceed.

## 3. Offer the 8-direction choice (substantial builds only)

**Only for substantial new builds / redesigns.** For a small tweak or single component ("fix this hero",
"restyle this card"), skip this step entirely — commit to the read and proceed. Don't bog down small work
with eight options.

For substantial work, after stating the Design Read, **use the `AskUserQuestion` tool to ask whether the
user wants to pick from a spread of distinct creative directions, or have you commit to your recommended
read.** This is *not* the "clarifying question" from step 2 — it's a deliberate offer of creative range.
Frame it in plain language, e.g.:

> *"I can run with my recommended direction (`<the Design Read in ~5 words>`), or show you **8 distinctly
> different creative directions** to choose from — same goal, very different looks and feels. Want to see
> the options?"*

Ask it as a single yes/no `AskUserQuestion`:
- **"Run with your recommendation"** → continue to step 4 (the normal flow).
- **"Show me 8 directions"** → generate and present them as below.

### If they say yes — generate 8 directions of CLEAR directional difference

Spontaneously compose **8 directions that would each produce a visibly, obviously different website** —
not eight flavors of one look. Anchor them to the brief, but spread them hard across the aesthetic catalog
(`references/aesthetics.md`) and both worlds (production vs award). Composition:

- **6 conventional directions** — all genuinely appropriate for this audience/brief, but each from a
  *different world or aesthetic family* so they still look nothing alike (e.g. one restrained dark-tech,
  one Swiss/editorial, one warm bento/flat, one glass/consumer surface, one authoritative print-editorial,
  one tasteful award-grade moment). These are the safe-but-varied picks — solid looks the user could ship.
- **2 super out-of-the-box directions** — deliberately wild, unexpected swings that push *well* past what's
  strictly "safe" for the brief (e.g. brutalist, maximalist, kinetic-editorial, a retro/genre look, heavy
  WebGL). These are the long shots — the widest creative range you can offer. **Flag each as `🔥 Wild`** so
  the user knows it's a big swing.

Total = **8** (6 + 2). Pull the 2 wild ones from the catalog's expressive / genre / atmosphere families;
pull the 6 conventional ones from dark-tech / Swiss / editorial / bento / flat / glass.

**Define each in plain, layman's terms — the user is not a designer.** For every direction give:
- **A plain-English name** (2–4 words) — e.g. "Calm & Engineered", "Magazine Editorial", "Playful Toy-Box",
  "Neon Arcade".
- **One jargon-free sentence on what it looks and feels like.** Say *"deep near-black screens, lots of
  breathing room, one cool accent colour — calm and high-end"* — **not** *"OKLCH dark-tech base with hairline
  borders and grain."*
- **A "feels like…" anchor** the user will instantly recognise — a familiar site/app or real-world thing
  ("like Linear or Vercel", "like a printed fashion magazine", "like a retro arcade cabinet").
- **The `🔥 Wild` tag** if it's one of the two out-of-the-box picks.

Keep the internal jargon (the named aesthetic + exact recipe) to *yourself* — you need it to build, but the
user only ever sees the plain version.

**⚠️ Present all 8 in the message body as a numbered list — NEVER through the `AskUserQuestion` picker.**
The picker **hard-caps at 4 options and silently drops the rest**, so routing the eight through it shows the
user only four (this is the exact failure to avoid — it has happened). The picker is *only* for the two
binary moments — the "show me 8 vs. take-my-recommendation" offer above, and the final two-option
"stay / type my own" commit below — and is **never** the tool for enumerating the routes. There is no
8-option (or 4-option) picker of directions; the message body is the only way the user sees all eight.

Render each of the 8 as one tight entry (one or two lines):

> **`N. Plain Name`** `🔥` *(if wild)* — the jargon-free sentence (what it looks/feels like) — **feels like …**
> *(optional, to keep it vivid: a 5–8-word mood cue or a tiny one-line ASCII sketch.)*

### Then generate the moodboard (mandatory — let them SEE the eight before choosing)

A text list isn't enough for a *visual* decision. Before the commit question, render all eight directions
as **one AI moodboard image** via the **`/codex-imagegen`** skill so the user can see the whole spread at a
glance. **One wide board — a 4×2 grid → 8 panes total, one pane per direction** (top row = routes 1–4,
bottom row = routes 5–8). This step is **not optional** once the 8-direction path is taken.

1. **Preflight once.** Run the codex-imagegen preflight (it checks `codex` + ChatGPT login + the imagegen
   tool). If Codex is missing or logged out, **skip gracefully** — tell the user the moodboard was
   skipped and why, then commit on the text list alone. **Never hard-block the direction on image gen.**
2. **Generate one board** — a single `codex-image.ps1` call (*not* `-Count 2`, which only makes variations
   of a single prompt). Each pane is an **abstract mood collage** for that route — its palette, a texture/
   material, the type *feel*, and one small UI/scene cue — **not** a literal page mock. Art-direct every
   pane from that route's internal recipe (the named aesthetic you kept to yourself), and ask for a small
   `N — Name` caption in each pane's corner. Pass **`-Size 1536x768`** for a wide 2:1 canvas: the tool
   honors the 2:1 *shape* but normalizes resolution, so the real file lands around **1774×887** (≈443px per
   pane — plenty legible; don't promise an exact pixel size). Note the absolute path it prints on the
   `CREATED:` line — you need it for the next step.

   ```powershell
   $skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
   & "$skills\codex-imagegen\scripts\codex-image.ps1" `
     -Prompt "A 4x2 grid of eight distinct design MOODBOARD tiles — 4 columns, 2 rows — with thin gutters between them. Each tile is a flat-lay collage of: a colour palette, a texture/material swatch, a few letterforms showing the type voice, and one small UI or scene cue; a tiny caption in the tile's corner. Top row left-to-right: '1 — <Name>': <palette + mood + texture + type + motif>; '2 — <Name>': <…>; '3 — <Name>': <…>; '4 — <Name>': <…>. Bottom row left-to-right: '5 — <Name>': <…>; '6 — <Name>': <…>; '7 — <Name>': <…>; '8 — <Name>': <…>. Editorial, art-directed, premium; no paragraphs of body text." `
     -OutDir ".\.atelier\moodboards" -Count 1 -Size 1536x768
   ```
3. **Show it, open it, name the path.** `Read` the PNG to display it inline, **force it open** in the
   user's default image viewer so they can study it full-size, **and** print the absolute path so they can
   reopen it later. Use the `CREATED:` path from step 2:

   ```powershell
   $board = "<absolute path from the CREATED: line>"
   Invoke-Item -LiteralPath $board          # pop it open in the default Windows image viewer
   Write-Host "Moodboard saved at: $board"  # remind the user of the path
   ```

   Then give the **pane→direction map in text** (gpt-image captions are unreliable, so the text map is the
   source of truth): *"Board — top row: 1 <Name> · 2 <Name> · 3 <Name> · 4 <Name>; bottom row: 5 <Name> · 6
   <Name> · 7 <Name> · 8 <Name>."*
4. **Then** fire the two-option commit below. **Cost:** the board ≈ 30k agent tokens + ~1 min — the budgeted
   price of letting the user see all eight at once; generate once, don't loop or auto-regenerate.

Then, once the full numbered list of 8 is in the message body, fire **exactly one `AskUserQuestion` with
only TWO options** — this is the commit step, and it never re-lists the routes:

1. **"Stay with your recommendation"** — mark it `(Recommended)` and name it (e.g. *"Stay with Quiet
   Gallery"*). One click commits to the direction you recommended in the Design Read.
2. **"Let me pick / blend my own"** — the user supplies their own answer as free text: a single number,
   a blend like *"1 + 3"*, and/or any comments on how to combine or adjust the directions. They type it
   in this option's built-in free-text ("Other") field, or simply reply in chat.

Parse whatever comes back — a number, a name, a blend (*"blend 1+3"*), or free-text notes — from either the
picker's text field or a plain chat reply (a user will often just type *"I like number 2"*; accept that
too). **Never** route the 8 routes through the picker, and **never** offer 3–4 "shortcut" picks — that
reintroduces the 4-option cap and drops routes (the exact bug this avoids). Once they choose, **the pick
locks in the world + aesthetic + concept: skip steps 4–6 and go straight to the Direction Doc (step 7)**,
folding in any comments they added.

If they say no, continue with steps 4–6 as normal.

### After the pick — reconstruct the chosen pane into an image-faithful reference

The user picked a **visual**, so the build's source of truth is now that pane's *actual look*, not just
your text recipe. Before the Direction Doc, turn the chosen pane into a clean reference image **plus** a
deconstructed spec — this is what makes the downstream build faithful to the tile the user actually chose
(skip this whole block for the take-my-recommendation / no-moodboard paths):

1. **Crop the chosen pane** out of the grid PNG (use the `CREATED:` grid path from the moodboard step):
   ```powershell
   $skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
   & "$skills\atelier-direction\scripts\crop-pane.ps1" `
     -Grid "<abs moodboard grid PNG>" -Pane <N> `
     -Out "<abs projectRoot>\.atelier\moodboards\chosen-pane.png"
   ```
   (Defaults to a 4×2 grid; pass `-Cols`/`-Rows` if the board layout differs. For a blend like *"1 + 3"*,
   crop the primary pane and note the secondary in the deconstruction.)
2. **Regenerate it clean + hi-res, anchored to the crop (image-guided — NOT a fresh re-roll).** Pass the
   crop back in via codex-image.ps1 **`-Edit`** (the verified `-i/--image` reference) *together with* this
   route's internal recipe, so the output stays faithful to what the user saw while cleaning + upscaling it:
   ```powershell
   $skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
   & "$skills\codex-imagegen\scripts\codex-image.ps1" `
     -Edit "<abs projectRoot>\.atelier\moodboards\chosen-pane.png" `
     -Prompt "Recreate the attached moodboard tile as a clean, high-resolution, art-directed reference. Faithfully preserve its composition, palette, lighting, texture, and type feel: <this route's recipe, concrete>. Remove any small corner caption. Abstract and premium; no paragraphs of text." `
     -OutDir "<abs projectRoot>\.atelier\moodboards" -Size 1024x1024
   ```
   Rename the result to `chosen-reference.png`. **Fallbacks (never block the direction on image gen) — the
   canonical `chosen-reference.png` must ALWAYS exist, because every downstream agent looks for that exact
   name:** if `-Edit` errors / yields no file, or Codex is unavailable, **copy the crop to the canonical name**
   (`Copy-Item chosen-pane.png chosen-reference.png`) and use that. Never leave the reference named only
   `chosen-pane.png`.
3. **Deconstruct the reference — image wins.** `Read` `chosen-reference.png` and extract its *realized*
   details: palette as **hex / OKLCH**, lighting + material + texture, type character, the signature
   element / composition, and mood. **Where the image differs from your original text recipe, the image is
   the source of truth** (the user chose the picture, not the words). These deconstructed details populate
   the Direction Doc's palette / type / signature-moment fields.
4. **Record both** under `ATELIER.md` → *Creative direction*: a **Reference image:** line with the absolute
   `chosen-reference.png` path, plus the deconstructed palette / type / mood. Downstream agents `Read` that
   image and must stay faithful to it.

## 4. Pick the world

There are two design worlds with **opposite priorities**. Decide which one you're in — it governs
every later trade-off.

| | **Production world** | **Award / creative world** |
|---|---|---|
| Goal | conversion, clarity, trust, task success | wow, memorability, brand expression |
| Looks like | bento grids, restraint, real content, fast | WebGL, kinetic type, scroll choreography, custom cursors |
| Motion | purposeful, ≤300ms, felt-not-seen | motion *is* the product |
| Non-negotiables | Core Web Vitals, WCAG 2.2 AA, sub-400ms | still ships fallbacks, but accepts perf cost |
| Default for | dashboards, B2B SaaS, e-commerce, content | portfolios, agencies, launches, campaigns |

Most work is production with *one or two* award-grade moments. Say which world, and where (if anywhere)
you'll spend an award-grade "signature moment."

## 5. Choose an aesthetic direction

Pick a **named aesthetic** (or a deliberate blend of two that pair well) as the spine. Don't free-style
a look — the named aesthetics each have a known recipe and failure mode. Open
**`references/aesthetics.md`** for all 22 with their exact CSS recipe, signature examples, when-to-use,
and how to avoid the cheap version.

Quick map (full detail in the reference):
- **Dark-tech** (Linear/Vercel/Raycast) — default for premium SaaS/dev tools.
- **Swiss / editorial** — content, portfolios, authority, "clean done right."
- **Bento + flat/Material 3 Expressive** — feature sections, marketing, dashboards.
- **Warm / neo-minimalism** — calm-but-human; the 2026 anti-AI move (wellness, craft, lifestyle).
- **Glass / Liquid Glass / skeuomorphic-material** — premium consumer, OS-like surfaces.
- **Brutalism / collage / anti-design** — indie, fashion, culture, dev tools with attitude.
- **Maximalism / Y2K / vaporwave / cyberpunk** — music, gaming, youth, culture brands.

When the brief is "make it feel human, not AI-made," the two named counter-movements are **warm/neo-minimalism**
and **collage/scrapbook**.

Pairings that read expensive: *Swiss grid + editorial display + grain*; *dark-tech + mesh gradient +
grain + restrained glass*; *bento + flat + subtle depth*; *kinetic type + liquid + dark-tech*.
Pairings that clash: glass-everywhere + dark-tech (the slop signature), maximalism + bento,
neumorphism + anything needing contrast.

### Visual assets — icons, illustration, imagery
Part of the aesthetic, and a frequent slop source if left to defaults. Decide, as direction: **one icon
system** (set + style + weight matching the type/radii), **one illustration voice** (or none), and the
**imagery medium + treatment** (photography vs illustration vs 3-D; duotone/grade/grain/dither to the palette;
scrims for text-over-image; a designed OG card + real favicon). Full direction guidance in
**`references/imagery-and-iconography.md`**; `atelier-components` builds them. Capture the call in the Direction Doc.

## 6. Find the concept

A look without an idea is decoration. State a **concept spine** in one line — the organizing idea the
design expresses — and **one signature moment** that embodies it. The concept is what makes choices
non-arbitrary later (why this type, why this motion, why this color).

- *Concept: "an instrument, not an app" → signature moment: a single precise, weighted hover on the
  primary action; everything else stays still.*
- *Concept: "field notes from the future" → signature moment: data that types itself in on scroll with
  a monospace ticker.*

## 7. Write the Direction Doc — scaled to the task

**Match the artifact to the job — don't impose ceremony on small work.**
- **Small tweak / single component** (e.g. "fix this hero", "restyle this card"): just state the
  **Design Read** + the 2–3 decisions that matter, inline. No document.
- **Substantial new build or redesign**: produce the full one-page doc using the template in
  **`references/direction-doc-template.md`** — Design Read, world, aesthetic + pairing, concept +
  signature moment, palette mood, type voice, motion budget, density, layout archetype, visual assets
  (icons/illustration/imagery), build stack, references, and the anti-slop guardrails for this project. Keep
  it to one page — it's a brief, not an essay.

When in doubt, lean light: a sharp one-liner that the rest of the suite can act on beats a doc nobody
needed.

**Sync to `ATELIER.md`.** If `ATELIER.md` exists (it will when the `atelier` orchestrator ran `init`
first), write your load-bearing decisions back into its **Creative direction** section — world,
aesthetic + pairing, concept + signature moment, palette mood, type voice, layout archetype, visual
assets — and reconcile **Interactivity** / **Motion policy** with the world you chose. Update in place,
don't duplicate. The Direction Doc is the working artifact; `ATELIER.md` is the durable brief — they
must agree.

## 8. Anti-slop pass + hand off

Before handing off, run the anti-slop check in **`references/anti-slop.md`** against your direction —
it lists the specific "cheap" tells to avoid, the "expensive" levers to pull, and the **two-altitude
category-reflex check** (don't just dodge the category's default look — dodge the *saturated escape-hatch*
the category runs to next). Then hand the Direction Doc to:
- **`atelier-foundations`** — give it the palette mood, type voice, and spacing feel → it emits OKLCH
  tokens, type scale, spacing.
- **`atelier-typography`** — give it the type voice → font selection, pairing, fluid type, detailing.
- **`atelier-layout`** — give it the layout archetype → grid, composition, whitespace, responsive.

**Structure runs in parallel:** **`atelier-ux`** turns the same brief into the IA + user-flow map (sitemap,
nav model, screen states); its artifact pairs with this Direction Doc as the other half of the plan, and
`atelier-layout` / `atelier-components` consume both.

**Tell the orchestrator which skills this direction warrants.** When invoked from the `atelier` hub, name
the build/ship set the chosen world + interactivity imply, so it runs exactly those and no more: always
**`atelier-foundations` → `atelier-typography` + `atelier-layout` → `atelier-components`**; add
**`atelier-motion`** for interaction feel, **`atelier-scroll`** for scroll choreography, **`atelier-webgl`**
for a 3D/shader moment, **`atelier-dataviz`** for charts, **`atelier-copy`** for UX writing; then
**`atelier-harden`** → the **`atelier-perf-a11y`** gate, and **`atelier-review`** for substantial/award
builds. A restrained production dashboard skips scroll/webgl; an interactive award-grade site includes them.

### Hand off the build to the director (FULL BUILDS ONLY)

**If this run is a full build** — the user wants the site built, not just a direction (the 8-direction
path was taken and/or the request was "build me a …"), **hand the locked direction straight to the
`atelier-director` agent** via the **Agent** tool (`subagent_type: "atelier-director"`). Give it a
self-contained brief (its context is isolated — pass everything by absolute path):

- the resolved absolute **`<projectRoot>`** and the absolute **`ATELIER.md`** path;
- the **LOCKED direction** (world · aesthetic · concept · signature moment) from the Direction Doc, and the
  deconstructed **palette (hex) · type · mood**;
- the absolute path to **`chosen-reference.png`** — instruct the director to treat this image as the
  **aesthetic source of truth** and thread it to design-lead + build-engineer, and to **NOT re-run the
  8-direction / direction phase** (a direction already exists);
- the section pack the chosen world implies.

The director then runs design-lead → build-engineer → ship-reviewer faithful to the reference. **Do not also
run foundations/typography/layout yourself in this case** — the director owns the build.

**Resilience (if the `Agent` tool isn't available in this skill's context):** do NOT fail or fall back to
building inline. Instead end with a clear **`DIRECTION LOCKED → launch atelier-director`** handoff block — the
same self-contained brief + the absolute `chosen-reference.png` path — so the orchestrator (the `atelier`
router, or the main loop that invoked you) launches `Agent(atelier-director)`. Either way the locked direction
+ the reference reach the director; the only question is who fires the Agent call.

**Direction-only / small requests** (the user just wanted an aesthetic, with no build): skip the director —
stop at the Direction Doc and hand to foundations / typography / layout as described above.

**Default build stack: Tailwind v4 + shadcn/ui**, unless the project clearly dictates otherwise. Name
it in the doc so foundations emits Tailwind `@theme` tokens and the build uses shadcn-compatible
components; only drop to vanilla CSS / another framework when the existing codebase requires it.

(A later `atelier-perf-a11y` gate will verify whatever gets built. Until then, carry its constraints
yourself: animate only `transform`/`opacity`, respect `prefers-reduced-motion`, WCAG 2.2 AA contrast,
visible focus, real keyboard support.)

---

## Operating principles

- **Decide, then commit.** A coherent B-grade direction beats a hesitant mix of five A-grade looks.
  Restraint reads as confidence; "everything at once" reads as slop.
- **One accent, one signature moment, one type voice.** Premium is subtraction.
- **The audience and constraints win** over your aesthetic preference, every time.
- **Reference, don't invent**, when the user gave you a reference. Mine it for the real decisions
  (grid, type, color logic, motion), not just the surface.
