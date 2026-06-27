# Atelier + Forge — premium frontend & 3D production suites for Claude Code

Two sibling [Claude Code](https://docs.claude.com/en/docs/claude-code) suites that take work from a
brief all the way to a shipped, audited result — and are engineered to avoid the generic, templated,
"AI-made" look.

- **Atelier** — a frontend design suite (17 skills + 4 agents). Direction → design system → type &
  layout → motion & components → scroll & 3D, gated by a hard performance/accessibility bar and finished
  with an adversarial pre-ship review.
- **Forge** — a headless, code-first, render-in-the-loop **3D production** suite (20 skills + 5 agents).
  Model → look-dev → rig/animate/sim → export/optimize, gated by an asset-validation pass.

They're **peers**, connected at exactly one seam: Atelier hands heavy 3D asset work down to Forge, and
Forge hands web-ready `.glb` + posters back up to Atelier. Use either on its own.

A small **image-generation** dependency (`codex-imagegen` + `codex-imagegen-taste`) is bundled because a
few skills/agents call it for moodboards and assets — it's **optional** and degrades gracefully.

The skills/agents are plain Markdown instruction sets, so they're editable and mostly OS-agnostic. The
machine-specific pieces are the helper **scripts** (image-gen and Forge tooling), which resolve their own
location at runtime — see [Path resolution & portability](#path-resolution--portability).

---

## What's inside

### Atelier — frontend design (17 skills)

| Skill | What it does |
|---|---|
| **atelier** | The hub/router. Probes project state and runs the right skills end-to-end; `/atelier <verb>` dispatches to one; `/atelier init` writes the project's `ATELIER.md` design memory. Start here when intent is broad. |
| **atelier-direction** | Decides the design *direction* before any code — aesthetic, "world" (production vs award), concept, palette mood, type voice, motion budget, layout archetype, signature moment. Emits a **Direction Doc** (and an 8-up moodboard pick). |
| **atelier-ux** | Planning-first IA & flows: content/feature inventory, sitemap, nav model, critical user flows, and the five screen-states. Produces an IA + Flow doc that layout/components realize. |
| **atelier-foundations** | The design-system engine. Perceptual **OKLCH** color ramps + semantic tokens + accessible dark mode, modular/fluid type scale, 8-pt spacing, depth. Outputs CSS vars, Tailwind v4 `@theme`, or W3C/DTCG tokens. |
| **atelier-typography** | Expensive type. Pairing with a point of view, fluid modular scale, tracking/leading/measure, OpenType + variable fonts, editorial detail, tasteful kinetic type. |
| **atelier-layout** | Premium layout & composition. Archetypes, modern CSS (Grid/Subgrid/container queries), composition models, Gestalt grouping, hierarchy, active whitespace. |
| **atelier-components** | Turns the system into real code. Scaffolds React/Next + Tailwind v4 + shadcn/ui, wires tokens into shadcn theme vars, installs best-in-class components (Vaul, Sonner, cmdk, Tremor), ships a copy-paste premium section-block library. |
| **atelier-motion** | The "feel" layer. Easing/spring defaults, durations, the 12 animation principles for UI, micro-interactions, and the often-skipped states (skeleton, optimistic UI, empty/loading/error). Default: Motion (`motion/react`). |
| **atelier-scroll** | Scroll choreography. Smooth scroll (Lenis), reveals, scrubbing, pinning, horizontal/sticky-stacking sections, parallax, CSS scroll-driven animations, View Transitions, marquees, magnetic buttons, custom cursors. Default: GSAP + ScrollTrigger + Lenis. |
| **atelier-webgl** | 3D, WebGL & shader craft. React Three Fiber + Drei, hand-written GLSL/TSL, WebGPU, Spline, faux-3D, image hover/scroll distortion — with lazy-load, static fallbacks, a11y. **Delegates heavy asset production to Forge.** |
| **atelier-dataviz** | Data-visualization craft. The right chart for the question, honest encoding, the house stack (shadcn Charts/Recharts → Tremor → visx/D3 → ECharts), accessible charts (keyboard, data-table fallback, real alt/aria). |
| **atelier-copy** | The UX-writing layer. Button/action labels, form & helper text, error/empty/loading copy, confirmations, tooltips, onboarding — clear, human, on-voice. Owns the *words* inside the interface. |
| **atelier-harden** | The production-resilience pass. Text overflow, i18n/RTL, the full set of error states, empty/edge-case data, interaction resilience (double-submit, race conditions, cleanup). Owns the *behavior* of error/empty/edge states. |
| **atelier-perf-a11y** | The quality gate every build passes. Compositor-safe animation, Core Web Vitals (LCP ≤2.5s, CLS ≤0.1, INP ≤200ms), `prefers-reduced-motion`, WCAG 2.2 AA, accessible canvas/WebGL fallbacks, the anti-slop "AI Tells" check. The canonical home for the perf/a11y rules others reference. |
| **atelier-redesign** | The front door for **existing** sites/apps. Audits brand/IA/stack, names the slop tells and missing "expensive" levers, scores gaps by impact vs risk, then applies the suite selectively without breaking functionality, SEO, or a11y. |
| **atelier-review** | The adversarial pre-ship review. Fans out independent reviewers (a11y, perf, motion, design-integrity, code quality), verifies every finding to kill false positives, checks live in a browser, synthesizes a prioritized fix list. Runs with the ordinary subagent tool. |
| **atelier-data** | On-demand reference **data** (searchable, BM25): per-industry palettes, font pairings, UI-style definitions, landing-page patterns, current framework do/don't tables. A lookup library the other skills cross-check against (not user-invoked directly). |

### Atelier — agents (4, all Opus)

| Agent | Role |
|---|---|
| **atelier-director** | Orchestrator + guardian of the image-first spine & anti-slop taste. Locks the style spec, delegates each phase with self-contained briefs, verifies every specialist against the spec. Invoke for a full from-scratch build. |
| **atelier-design-lead** | Direction · ux · foundations · typography · layout · copy. Owns the taste comps and derives the role-named token system; emits the spec packet the build engineer consumes cold. |
| **atelier-build-engineer** | Components · motion · scroll · webgl · dataviz + the screenshot-refine loop + photographic assets. |
| **atelier-ship-reviewer** | Hardening + the perf/a11y gate + the adversarial review. |

### Forge — 3D production (20 skills)

| Skill | What it does |
|---|---|
| **forge** | The hub/router. `/forge init` writes `FORGE.md`; routes to the right stage; `## Atelier handoff` hands assets back to the web suite. |
| **forge-brief** · **forge-standards** | Scope a 3D task + tool availability; the conventions/quality bar all stages follow. |
| **forge-model** · **forge-parametric** · **forge-procedural** · **forge-topology** · **forge-uv** | Geometry: direct/parametric (OpenSCAD)/procedural modeling, topology cleanup, UV unwrapping. |
| **forge-material** · **forge-texture** · **forge-light** · **forge-render** | Look-dev: PBR materials, texture/PBR baking, lighting, headless Cycles rendering. |
| **forge-rig** · **forge-animate** · **forge-sim** | Rigging, animation, simulation. |
| **forge-export** · **forge-optimize** · **forge-intake** | Pipeline: glTF/USD export, `gltf-transform` optimization (Draco/Meshopt/KTX2), intake/cleanup of external/generated meshes. |
| **forge-validate** | The asset gate — topology/manifold/scale/material checks before an asset ships. |
| **forge-data** | Searchable (BM25) reference library for 3D production (not user-invoked directly). |

### Forge — agents (5)

| Agent | Role |
|---|---|
| **forge-director** | Opus orchestrator. Fans out to the specialists; writes working files to `<projectRoot>/.forge-build/out/` and web handoffs to `public/forge/`. |
| **forge-modeler** · **forge-lookdev** · **forge-rigtech** · **forge-pipeline** | Geometry · materials/light/render · rig/animate/sim · export/optimize/convert. |

### Image generation (optional dependency)

| Skill | What it does |
|---|---|
| **codex-imagegen** | Generates/edits raster images by driving a locally-installed **OpenAI Codex CLI** (its built-in `image_gen` tool via your ChatGPT login — **no API key**). Used for moodboards, section assets, shader textures. |
| **codex-imagegen-taste** | A taste/anti-slop layer over `codex-imagegen` for premium, art-directed single-image comps (style anchors, not section copies). |

---

## The pipelines

```
ATELIER                       atelier  (hub / router)
                                 │
   atelier-direction ──(Direction Doc + moodboard pick)──┐   atelier-ux ──(IA + flows)──┐
                                                          ▼                              ▼
                       atelier-foundations · atelier-typography · atelier-layout   (structure)
                                                          │
                          ┌───────────────────────────────┼───────────────────────────────┐
                          ▼                                ▼                                ▼
              atelier-motion · atelier-components   atelier-scroll · atelier-webgl   atelier-dataviz
                          │                                │  (heavy 3D ↓ to Forge)
                          └──── atelier-copy · atelier-harden ────┐
                                                                  ▼
                                              atelier-perf-a11y  →  atelier-review
                                              (gate, mandatory)   (adversarial pre-ship)

   Existing site? Start at  atelier-redesign  → it pulls the rest of the suite in as needed.

FORGE        forge (hub) → brief/standards → model/parametric/procedural/topology/uv
             → material/texture/light/render → rig/animate/sim → export/optimize/intake → forge-validate (gate)

THE SEAM     atelier-webgl  ──(needs a real 3D asset)──►  forge / forge-director
             forge          ──(public/forge/<slug>-hero.glb + poster)──►  atelier-webgl
             Gate split: forge-validate = asset gate · atelier-perf-a11y = web-runtime gate
```

For an agent-driven build, invoke **`atelier-director`** (full website) or **`forge-director`** (a 3D
asset); each fans out to its specialists. For a single concrete task, the matching skill triggers on its
own.

---

## Requirements

- **[Claude Code](https://docs.claude.com/en/docs/claude-code)** — these are Claude Code skills & agents.
- **Atelier** has no other runtime dependency: it instructs Claude on *how* to build, using whatever
  stack your project uses (default: React/Next + Tailwind v4 + shadcn/ui).
- **Forge** is **Windows / PowerShell-first and headless**, and shells out to real DCC tooling. Install
  what the stages you use need (each skill self-documents the exact install — see
  `forge-brief/references/tool-availability.md` and `forge-export/references/install-windows.md`):
  - **Blender 4.2 LTS** (headless **Cycles** for render/bake) — required for most geometry/look-dev.
  - **Node.js + `gltf-transform`** — for `forge-optimize`.
  - **OpenSCAD** — for `forge-parametric`; **ImageMagick** — for poster generation; **PyMeshLab/trimesh** — for some `forge-validate`/`forge-intake` checks (optional).
- *Optional, both suites:* **OpenAI Codex CLI** for in-suite image generation — see
  [Image generation](#image-generation).

---

## Install

Claude Code loads personal skills from `~/.claude/skills/` and agents from `~/.claude/agents/` by
default — or from `$CLAUDE_CONFIG_DIR/skills` and `$CLAUDE_CONFIG_DIR/agents` if you set
`CLAUDE_CONFIG_DIR`. Copy both folders from this bundle into your Claude config dir.

**Windows (PowerShell)**
```powershell
$cfg = if ($env:CLAUDE_CONFIG_DIR) { $env:CLAUDE_CONFIG_DIR } else { "$env:USERPROFILE\.claude" }
New-Item -ItemType Directory -Force "$cfg\skills","$cfg\agents" | Out-Null
Copy-Item -Recurse -Force .\skills\* "$cfg\skills"
Copy-Item -Recurse -Force .\agents\* "$cfg\agents"
```

**macOS / Linux** (Atelier is fully cross-platform; Forge's helper scripts are Windows-shaped)
```bash
cfg="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
mkdir -p "$cfg/skills" "$cfg/agents"
cp -R skills/* "$cfg/skills/"
cp -R agents/* "$cfg/agents/"
```

> **Want just one suite?** Copy only the `atelier-*` (+ `codex-imagegen*`) folders, or only the `forge*`
> folders, and the matching agents. **Don't want image-gen?** Omit `codex-imagegen` + `codex-imagegen-taste`.
> **Project-scoped instead of global?** Copy into `<your-project>/.claude/skills/` and `…/.claude/agents/`.

Restart Claude Code afterward — skills and the agent registry load at startup. Verify with `/skills`
and `/agents`; you should see the `atelier-*` / `forge*` entries.

---

## Path resolution & portability

These skills shipped from another machine with **no hard-coded user paths** — every helper-script
reference resolves at runtime:

- **PowerShell image-gen calls** resolve as
  `$skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }`
  — so they work whether or not you set `CLAUDE_CONFIG_DIR`.
- **Forge tooling and a few Atelier scripts** (the signals probe, the perf/a11y detector, the data
  indexers) are referenced as `$CLAUDE_CONFIG_DIR/skills/…` (or `$env:CLAUDE_CONFIG_DIR\skills\…`).

**Recommended:** set `CLAUDE_CONFIG_DIR` to your Claude config dir (the parent of `skills/`), e.g.
`~/.claude`, so every script-invocation example resolves verbatim. If you install to the default
`~/.claude` and don't set it, the image generator still works (USERPROFILE fallback); the Forge command
examples assume `CLAUDE_CONFIG_DIR` is set.

---

## Usage

Skills trigger automatically from their descriptions — you usually don't invoke them by hand.

- **New frontend build:** describe it — *"design a premium landing page for a developer tool."*
  `atelier-direction` engages first, then the pipeline runs (or invoke `atelier-director` for the
  full agent-driven build).
- **Existing site:** *"make this look less generic / modernize this app"* → `atelier-redesign` audits
  first, then pulls in the rest.
- **A 3D asset:** *"model a low-poly hero object and give me a web-ready glb"* → `forge` (or
  `forge-director`) runs the model→look-dev→export→validate chain and hands the asset to `atelier-webgl`.
- **Pre-ship:** *"is this ready to ship? review it."* → `atelier-review` (frontend) / `forge-validate`
  (asset).

### The knowledge base (deepdive)

14 of the Atelier skills cite a 16-section **deepdive** (`fundamentals-deepdive.md`) — a
practitioner-grade reference on the current (mid-2026) frontend ecosystem (animation libs, OKLCH color,
Tailwind v4, shadcn, Core Web Vitals, WebGPU/TSL, the "expensive vs cheap" rules). A copy is **bundled
into each citing skill's `references/` folder**, so every skill is self-contained — nothing external to
wire up. (`atelier`, `atelier-review`, and `atelier-data` cite no deepdive.)

---

## Image generation

Several Atelier skills/agents (`atelier-direction`, `atelier-components`, `atelier-webgl`, the
design-lead/build-engineer agents) and `forge-texture` can generate imagery — direction moodboards, real
section assets, shader textures — via the bundled **`codex-imagegen`** (+ taste) skill. This is
**optional and degrades gracefully**: if it's unavailable, the skills skip image-gen and tell you to
drop in your own assets.

**To enable it (Windows):**
1. Install the Codex CLI: `npm i -g @openai/codex`
2. Log in with your ChatGPT Plus/Pro account: `codex login` (no OpenAI API key needed).
3. Keep `codex-imagegen` (+ `codex-imagegen-taste`) in your skills directory — the helper resolves its
   own path at runtime.

**On macOS / Linux, or without Codex:** the helper is a Windows PowerShell script, so it won't run
as-is. The design skills are unaffected — when image-gen is requested they substitute any generator you
have (an MCP/IDE tool, a hosted model, stock you provide) or leave clearly labelled asset slots.

---

## Folder layout

```
.
├── README.md                  ← this file
├── skills/
│   ├── atelier/  atelier-direction/  atelier-ux/  atelier-foundations/  …   (17 atelier skills)
│   ├── forge/  forge-model/  forge-render/  forge-validate/  …               (20 forge skills)
│   └── codex-imagegen/  codex-imagegen-taste/                                (image-gen)
└── agents/
    ├── atelier-director.md  atelier-design-lead.md  atelier-build-engineer.md  atelier-ship-reviewer.md
    └── forge-director.md  forge-modeler.md  forge-lookdev.md  forge-rigtech.md  forge-pipeline.md
```

Each skill is a standard Claude Code skill — a `SKILL.md` (with `name`/`description` frontmatter that
controls triggering) plus a `references/` folder (and `scripts/` where it shells out). Each agent is a
single Markdown file with frontmatter, invoked by `subagent_type`.

---

## Notes

- **Default frontend stack** is React/Next + Tailwind v4 + shadcn/ui, but Atelier adapts to whatever a
  project already uses (down to vanilla CSS). **Forge** standardizes on Blender **Cycles** for headless
  render and project-relative output paths.
- **Premium foundries / heavy libraries** (GSAP, Motion, Three.js/R3F) are treated as first-class.
- These are *taste* suites: they bias hard toward restraint, coherence, and one earned "signature
  moment" over piling on effects. Read `atelier-direction` (and `forge-standards`) first for the
  philosophy.
- No license is included — add one if you intend to redistribute.
```
