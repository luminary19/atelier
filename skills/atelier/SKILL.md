---
name: atelier
version: 2.0.0
description: >
  Atelier suite — the entry point, router & orchestrator. START HERE when you're not sure which Atelier
  skill to reach for, want the suite to take a project from where it is to where it should be, or want to
  set up / read this project's design memory. With no argument it probes project state, decides which
  skills the situation needs, then RUNS them end-to-end by invoking each skill explicitly with the Skill
  tool (full `atelier-*` name) — pausing only for a skill's own creative input (tone, audience, the
  8-direction pick), never for step-by-step permission.
  `/atelier <verb> [target]` dispatches to a specific atelier-* skill; `/atelier init` writes the
  project's ATELIER.md design memory; `/atelier help` shows the full stage-organized menu. Use when the
  user says "use Atelier", "set up Atelier", "what should I do next on this design", "build this for me",
  "which atelier skill do I use", or invokes /atelier directly. For a concrete single task the specific
  atelier-* skill still triggers on its own; this is the hub for when intent is broad, unknown, or "just
  make this good." Part of the Atelier suite.
triggers:
  - use atelier
  - set up atelier
  - atelier init
  - what should i do next
  - build this for me
  - which atelier skill
  - atelier help
  - where do i start
user-invocable: true
argument-hint: "[init | direction | ux | foundations | type | layout | motion | scroll | webgl | components | dataviz | copy | harden | perf | review | redesign | bolder | quieter | distill | help] [target]"
# No allowed-tools allowlist, on purpose: the hub now orchestrates and RUNS the whole pipeline, so it
# needs every tool the downstream skills use (Read/Write/Edit/Bash/PowerShell/WebFetch/WebSearch/Task/…).
---

# Atelier — Entry Point, Router & Orchestrator

The front door to the Atelier suite. The suite is **15 focused skills** (plus the `atelier-data`
reference library the others call); this hub keeps you from having to remember which one to invoke. It does four things: **orchestrate** — detect which skills the current repo/situation needs, then **actually run them end-to-end by invoking each one with the Skill tool (full `atelier-*` name)** — plus **dispatch** a verb to a specific skill, **init** the project's design memory (`ATELIER.md`), and show the **menu**.

> **Suite map (what this routes to).** Planning: **`atelier-direction`** (aesthetic) + **`atelier-ux`**
> (IA/flows). Foundation: **`atelier-foundations`** (OKLCH tokens) → **`atelier-typography`** +
> **`atelier-layout`**. Build: **`atelier-motion`** / **`atelier-scroll`** / **`atelier-webgl`** /
> **`atelier-dataviz`** / **`atelier-components`**, with **`atelier-copy`** for UX writing. Ship:
> **`atelier-harden`** (resilience) → **`atelier-perf-a11y`** gate → **`atelier-review`** (adversarial).
> Existing sites: **`atelier-redesign`** (audit-first front door). Reference data: **`atelier-data`**
> (a lookup library siblings call; not user-facing). Full sequence: **`references/pipeline.md`**.
>
> **Agent team (isolated-context orchestration).** For a full, from-scratch end-to-end build, hand broad
> "build me a website" intent to the **`atelier-director`** agent (`Agent(atelier-director)`) — it runs this
> same pipeline across **`atelier-design-lead`** → **`atelier-build-engineer`** → **`atelier-ship-reviewer`**
> in its own context. **When no direction is locked yet, route to `Skill(atelier-direction)` first** (the
> 8-direction moodboard pick); it reconstructs the chosen pane into a reference image and hands off to the
> director itself. This skill keeps scoped / in-place orchestration, single-skill dispatch, and `init`.
>
> **Project memory:** this skill owns **`ATELIER.md`** — the per-project design memory every other skill
> reads at the start of its work. Template + schema: **`references/project-memory.md`**.

---

## Setup — read project state first

Run the signal probe once (pure-Python stdlib, no network beyond localhost port checks):

```bash
python "$CLAUDE_CONFIG_DIR/skills/atelier/scripts/signals.py"
```

It reports: whether `ATELIER.md` exists, the detected stack, git-changed web files, and whether a dev
server is running. **It recommends nothing — you reason over the facts.** Add `--json` if you want to
parse it; pass `--root <dir>` to point at a specific project. If Python or git is unavailable, skip it
and reason from what you can see in the workspace; never block on the probe.

## Routing rules

1. **No argument (often with a build prompt)** → the user wants the suite to move the project forward
   ("build this", "just make this good"). **For a full, from-scratch end-to-end WEBSITE build, branch on
   whether `ATELIER.md` already holds a locked Creative direction:**
   - **No locked direction yet** → run **`Skill(atelier-direction)`** first so the user picks from the
     8-direction moodboard. On the pick, `atelier-direction` reconstructs the chosen pane into an
     image-faithful reference (`chosen-reference.png`) and hands off to **`Agent(atelier-director)`** itself.
     **Safety-net:** if it instead returns a `DIRECTION LOCKED → launch atelier-director` handoff (a skill
     context couldn't spawn the agent), **you** launch `Agent(atelier-director)` with that brief + the
     reference. If the director already ran, do **not** double-launch.
   - **Direction already locked** (a filled Creative direction in `ATELIER.md`) → hand straight to
     **`Agent(atelier-director)`**, passing the recorded `chosen-reference.png` + tokens; it skips its own
     direction phase.

   Either way the director owns the image-first design-then-code pipeline across the specialist team
   (design-lead → build-engineer → ship-reviewer) in an isolated context. Use THIS skill's inline
   orchestration for **scoped / in-place work on an existing project**:
   read the signals, decide the **pipeline the situation needs** (logic below), and **run it via the
   orchestration loop by invoking each skill with the Skill tool** — don't hand back a list, and don't just
   name skills in prose. For such a scoped run, `init` inline, then the matching skills in order. Pause only
   for a skill's own creative questions — never for permission to advance a stage. Scale it: a one-surface
   fix is a single-skill run, not the whole pipeline.
2. **First word is a verb in the dispatch table** → invoke that skill via the **Skill tool** by its exact
   `atelier-*` name (pass anything after the verb as its target), and let it run — don't just narrate it.
3. **First word is `init`** → run the memory-setup flow below.
4. **First word is `help`** → print the stage menu.
5. **Verb doesn't match but intent maps to one skill** (e.g. "fix the spacing" → layout, "the copy is
   vague" → copy) → invoke that skill via the **Skill tool** by its exact name and let it run. If two fit,
   ask once which.

### Dispatch table (verb → skill)

| Verb(s) | Routes to | For |
|---|---|---|
| *full from-scratch website build* (broad "build me a website") | **`Agent(atelier-director)`** *(agent)* | End-to-end image-first build via the specialist team |
| `direction`, `aesthetic`, `look`, `vibe` | **`atelier-direction`** | Decide the look/world/concept (new work) |
| `ux`, `ia`, `flow`, `structure`, `sitemap` | **`atelier-ux`** | Information architecture, flows, screen-states |
| `foundations`, `tokens`, `color`, `theme`, `dark` | **`atelier-foundations`** | OKLCH token system, dark mode |
| `type`, `typography`, `fonts` | **`atelier-typography`** | Font choice/pairing, scale, detailing |
| `layout`, `grid`, `spacing`, `whitespace` | **`atelier-layout`** | Composition, grid, rhythm, responsive |
| `motion`, `animate`, `transition` | **`atelier-motion`** | Micro-interactions, states, feel |
| `scroll`, `parallax`, `pin` | **`atelier-scroll`** | Scroll choreography, page transitions |
| `webgl`, `3d`, `shader` | **`atelier-webgl`** | 3D / generative / shader work — for **authored 3D geometry** (models, look-dev, baked assets) it delegates to the **`forge`** suite |
| `forge`, `blender`, `model`, `mesh`, `geometry`, `glb`, `look-dev`, `hdri` | **`forge`** *(Forge suite)* | Authored 3D production pipeline: mesh/parametric/procedural modeling, UV, PBR look-dev, rig/anim/sim, headless render, GLB/USD export → web handoff |
| `components`, `build`, `scaffold` | **`atelier-components`** | Scaffold + build the component layer |
| `comp`, `mockup`, `image`, `render` | **`codex-imagegen-taste`** (sibling) | Premium one-image-per-section website / hero / landing comps — calls `/codex-imagegen`; the moodboard stays bare |
| `dataviz`, `charts`, `graph` | **`atelier-dataviz`** | Charts, dashboards data layer |
| `copy`, `clarify`, `microcopy`, `errors` | **`atelier-copy`** | UX writing: labels, errors, empty-state copy |
| `harden`, `resilience`, `i18n`, `edge` | **`atelier-harden`** | Production resilience: overflow/i18n/error/edge |
| `review`, `audit`, `red-team`, `ship-check` | **`atelier-review`** | Adversarial pre-ship review |
| `perf`, `a11y`, `gate`, `lighthouse` | **`atelier-perf-a11y`** | Perf + accessibility quality gate |
| `redesign`, `improve`, `modernize` | **`atelier-redesign`** | Audit + upgrade an existing site/app |
| `bolder` | **`atelier-redesign`** → `references/tonal-dials.md` (§Bolder) | Amplify a too-safe/bland design |
| `quieter` | **`atelier-redesign`** → `references/tonal-dials.md` (§Quieter) | Calm a too-loud/busy design |
| `distill` | **`atelier-redesign`** → `references/tonal-dials.md` (§Distill) | Strip to essence; remove what doesn't earn its place |

### Orchestration logic — which skills the situation needs (reason over signals; there is no score)

- `memory.hasAtelierMd` **false** and there's real code/intent → **`/atelier init`** first (capture
  register + policies so every other skill stays on-brief), or `/atelier redesign` if it's an existing
  site you're improving.
- `memory.hasAtelierMd` false and the user wants something brand-new → **`/atelier direction`** (+ `ux`).
- `git.changedWebFiles` cluster on one surface → scope **`/atelier review <those files>`** or the matching
  fix verb (spacing → `layout`, vague copy → `copy`, flat palette → `foundations`).
- `devServer.running` true → live verification in **`atelier-review`** step 4 is available; mention it.
- Build looks finished (components exist, no obvious gaps) → **`/atelier harden`** then the
  **`atelier-perf-a11y`** gate, and **`/atelier review`** for substantial work.
- Nothing built yet → the planning pair: **`/atelier direction`** + **`/atelier ux`**.
- User wants a **premium image / mockup / hero / full landing comp** (a design-reference image, not code) →
  **`codex-imagegen-taste`** (calls `/codex-imagegen` under the hood, one image per section). The quick
  **8-direction moodboard stays on bare `/codex-imagegen`** in `atelier-direction` — never route it here.

These bullets compose the **plan** — the ordered set of skills you run, not a list handed back. Pick the
**shortest pipeline that actually moves this project forward**; finalize the build/ship half only once
`direction` has set the world + interactivity.

### The orchestration loop (how it actually runs)

You have full tool access — including the **Skill tool**, which is the ONLY way you actually run a
downstream skill.

> **Running a skill = calling the Skill tool with its exact name. Nothing else counts.** Writing "next:
> direction" or "now apply foundations" in prose runs NOTHING — that narration is the exact bug this loop
> exists to kill. To run a stage you MUST call the **Skill tool** with the full skill name, e.g.
> `skill: "atelier-direction"` (shorthand below: `Skill(atelier-direction)`), then `Skill(atelier-ux)`,
> `Skill(atelier-foundations)`, and so on — always the full `atelier-*` name, never a bare word. `init` is
> the one exception: it's a mode of THIS skill, so run its flow inline; there is no `atelier-init` skill.

Run the pipeline as one continuous flow:

1. **Invoke → carry forward.** Run each stage by calling the Skill tool with its exact name; let it execute
   its FULL flow — its own `AskUserQuestion` rounds, its `/codex-imagegen` moodboard, its build steps. Its
   output (ATELIER.md edits, Direction Doc, tokens, components…) feeds the next stage. Never paraphrase,
   summarize, or skip a skill's interactive steps in place of actually invoking it.
2. **`ATELIER.md` is the shared, living brief.** `init` writes it; `atelier-direction` writes its
   **Creative direction** section; `atelier-foundations` writes **Tokens**. Each stage reads it first.
3. **Let each skill ask its own questions — multiple rounds across stages are expected and fine.**
   `atelier-direction`'s 8-direction offer + moodboard, a foundations either/or, and so on: surface every
   one in full; never collapse, batch away, or skip them. The only thing you never pause for is permission
   to advance a stage.
4. **Direction sets the build list.** After `Skill(atelier-direction)`, the world + interactivity it locked
   decide which build/ship skills are warranted (it names them in its hand-off). Invoke each of those next,
   by name, in order — no "proceed?" gate between stages.
5. **Stop conditions.** Stop when the pipeline is done, a skill hits a real blocker (missing dependency,
   failing build), or the user steers. Then report what ran and what's left.

**Worked example — `/atelier` + "build an interactive creative site for an artist" in an empty repo:**
signals show no `ATELIER.md` + new repo → run **`init`** inline (interview → writes `ATELIER.md`) →
**`Skill(atelier-direction)`** (Design Read → 8-direction list + `/codex-imagegen` moodboard → on the pick,
writes the Creative direction section into `ATELIER.md`) → **`Skill(atelier-ux)`** → then, per direction's
hand-off for an interactive award-grade site: **`Skill(atelier-foundations)`** → **`Skill(atelier-typography)`**
→ **`Skill(atelier-layout)`** → **`Skill(atelier-components)`** → **`Skill(atelier-motion)`** →
**`Skill(atelier-scroll)`** → (**`Skill(atelier-webgl)`** if a 3D moment was chosen) → **`Skill(atelier-copy)`**
→ **`Skill(atelier-harden)`** → **`Skill(atelier-perf-a11y)`** → **`Skill(atelier-review)`**. Each runs
end-to-end; you only stop for a skill's own creative questions.

## `init` — write the project's design memory

`/atelier init` creates **`ATELIER.md`** at the project root: the persistent brief every skill reads.
Full template, schema, and the universal-vs-taste split are in **`references/project-memory.md`** — load
it, then:

1. **Probe + read.** Run `signals.py`; if `ATELIER.md` already exists, read it and offer to *update* (don't
   silently overwrite). If code exists, skim one representative file (CSS/tokens/a component) so the doc
   reflects reality.
2. **Interview (scaled to the project).** Use `AskUserQuestion` for the load-bearing choices — **register**
   (brand vs product) first, then interactivity level, motion-library policy, and glassmorphism policy.
   Infer users/purpose/personality/anti-references from the brief and confirm; don't interrogate.
3. **Write `ATELIER.md`** from the template. Leave the **Tokens** section as a stub linked to
   `atelier-foundations` (it fills/links it once the token system exists). Echo anti-references into the
   Do/Don't block.
4. **Continue, don't hand back — invoke the next skill, don't name it.** When `init` runs as part of an
   orchestration, flow straight on: after writing `ATELIER.md`, immediately call **`Skill(atelier-direction)`**
   (then **`Skill(atelier-ux)`**) and keep going down the pipeline. Actually call the Skill tool — saying
   "now direction" does nothing. `ATELIER.md` is the brief each stage reads, so `direction` builds the
   aesthetic *on top of* the register/policies you just set (no need to re-ask those), runs its full
   8-direction flow, then writes its decisions back into the file. (If the user invoked `/atelier init` on
   its own, just confirm the file and name the next step.)

`init` is the first move on any substantial project; everything downstream reads what it writes.

## `help` — the stage menu

```
PLAN      /atelier direction   ·  /atelier ux
FOUND     /atelier foundations ·  /atelier type   ·  /atelier layout
BUILD     /atelier motion · scroll · webgl · dataviz · components · copy
SHIP      /atelier harden  →  /atelier perf  (gate)  →  /atelier review  (adversarial)
EXISTING  /atelier redesign   ·  tonal: /atelier bolder | quieter | distill
SET UP    /atelier init        (writes ATELIER.md — do this first)
```

---

## Operating principles

- **Decide and run — don't just recommend.** Probe state, choose the skills the situation needs, then
  execute the pipeline end-to-end with full tool access. There is no "proceed?" gate between stages; the
  only pauses are for a skill's own creative questions.
- **Run = call the Skill tool.** Naming a skill in prose ("next: direction") runs nothing. Every stage is
  an explicit `Skill(atelier-<name>)` invocation by full name — zero ambiguity, no narration in its place.
- **`init` first on substantial work.** A persisted `ATELIER.md` is what keeps every later skill on-brief
  across sessions — it's the suite's memory; `direction` and `foundations` write back into it as they go.
- **Dispatch, don't duplicate.** This hub routes and runs; the real craft lives in the 15 focused skills.
  Don't re-explain a skill's method here — load it and follow it.
- **Scale to the task.** A one-line tweak is a single-skill run, not the whole pipeline — and doesn't need
  init. Match the pipeline length to what the project actually needs.
