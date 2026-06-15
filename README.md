# Atelier — a premium frontend design skill suite

**Atelier** is a suite of 11 [Claude Code](https://docs.claude.com/en/docs/claude-code) skills that take a
frontend from *art direction* to *shipped, audited build* — and are engineered to avoid the generic,
templated, "AI-made" look. They encode a single opinionated pipeline (direction → design system →
type & layout → motion & components → scroll & 3D), gated by a hard performance/accessibility bar and
finished with an adversarial pre-ship review.

The skills are plain Markdown instruction sets, so they're OS-agnostic and editable. The only
machine-specific piece is one **optional** image generator (see [Image generation](#optional-image-generation)).

---

## What's inside

| Skill | What it does |
|---|---|
| **atelier-direction** | The entry point. Decides the design *direction* before any code — aesthetic, "world" (production vs award), concept, palette mood, type voice, motion budget, layout archetype, signature moment. Emits a **Direction Doc** the rest of the suite consumes. |
| **atelier-foundations** | The design-system engine. Perceptual **OKLCH** color ramps + semantic tokens + accessible dark mode, a modular/fluid type scale, an 8-pt spacing scale, depth (radii/shadows/grain). Outputs CSS custom properties, Tailwind v4 `@theme`, or W3C/DTCG tokens. |
| **atelier-typography** | Expensive type. Font pairing with a point of view, fluid modular scale, tracking/leading/measure, OpenType + variable-font features, editorial detail, tasteful kinetic type. |
| **atelier-layout** | Premium layout & composition. Layout archetypes, modern CSS (Grid/Subgrid/container queries), composition models, Gestalt grouping, hierarchy, active whitespace. |
| **atelier-components** | Turns the system into real code. Scaffolds React/Next + Tailwind v4 + shadcn/ui, wires tokens into shadcn theme vars, installs best-in-class components (Vaul, Sonner, cmdk, Tremor), and ships a copy-paste premium section-block library. |
| **atelier-motion** | The "feel" layer. Correct easing/spring defaults, durations, the 12 animation principles for UI, micro-interactions, and the often-skipped states (skeleton, optimistic UI, empty/loading/error). Default stack: Motion (`motion/react`). |
| **atelier-scroll** | Scroll choreography. Smooth/inertia scroll (Lenis), reveals, scrubbing, pinning, horizontal sections, sticky-stacking, parallax, native CSS scroll-driven animations, View Transitions, marquees, magnetic buttons, custom cursors. Default stack: GSAP + ScrollTrigger + Lenis. |
| **atelier-webgl** | 3D, WebGL & shader craft. React Three Fiber + Drei, hand-written GLSL/TSL, WebGPU via `WebGPURenderer`, Spline, faux-3D, image hover/scroll distortion — always with lazy-load, static fallbacks, and a11y. |
| **atelier-perf-a11y** | The quality gate every build passes. Compositor-safe animation, Core Web Vitals (LCP ≤2.5s, CLS ≤0.1, INP ≤200ms), `prefers-reduced-motion`, WCAG 2.2 AA, accessible canvas/WebGL fallbacks. The canonical home for the perf/a11y rules the other skills reference. |
| **atelier-redesign** | The front door for **existing** sites/apps. Audits brand/IA/stack, names the specific slop tells and missing "expensive" levers, scores gaps by impact vs risk, then applies the suite selectively without breaking functionality, SEO, or a11y. |
| **atelier-review** | The adversarial pre-ship review. Fans out independent reviewers across dimensions (a11y, perf, motion, design-integrity, code quality), verifies every finding to kill false positives, checks live in a browser, synthesizes a prioritized fix list. Runs with the ordinary subagent tool — no special setup. |

Bundled optional dependency:

| | |
|---|---|
| **codex-imagegen** | Generates/edits raster images by driving a locally-installed **OpenAI Codex CLI** (uses its built-in `image_gen` tool via your ChatGPT login — **no API key**). Atelier uses it for moodboards, real section assets, and shader textures. **Optional** — the suite works without it. |

### The pipeline

```
                          atelier-direction  ──(Direction Doc)──┐
                                                                │
              ┌───────────────┬───────────────┬────────────────┤
              ▼               ▼                ▼                ▼
     atelier-foundations  atelier-typography  atelier-layout   (build)
        (tokens)              (type)            (structure)
              │
              ├──────────────► atelier-motion + atelier-components
              │                        │
              └──────────────► atelier-scroll / atelier-webgl
                                       │
                          ┌────────────┴─────────────┐
                          ▼                           ▼
                   atelier-perf-a11y           atelier-review
                  (gate, mandatory)         (adversarial pre-ship)

  Existing site? Start at  atelier-redesign  → it pulls the rest of the suite in as needed.
```

---

## Requirements

- **[Claude Code](https://docs.claude.com/en/docs/claude-code)** (the skills are Claude Code skills).
- *Optional:* **OpenAI Codex CLI** for in-suite image generation — see [below](#optional-image-generation).

That's it. The 11 design skills have no other runtime dependencies; they instruct Claude on *how* to
build, using whatever stack your project uses (default: React/Next + Tailwind v4 + shadcn/ui).

---

## Install

Claude Code loads personal skills from your skills directory — `~/.claude/skills/` by default, or
`$CLAUDE_CONFIG_DIR/skills/` if you set `CLAUDE_CONFIG_DIR`. Copy each folder from `Atelier/skills/`
into it.

**macOS / Linux**
```bash
mkdir -p ~/.claude/skills
cp -R Atelier/skills/* ~/.claude/skills/
```

**Windows (PowerShell)**
```powershell
$skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
New-Item -ItemType Directory -Force $skills | Out-Null
Copy-Item -Recurse -Force .\Atelier\skills\* $skills
```

> Prefer it on a single project only? Copy the same folders into `<your-project>/.claude/skills/` instead.
> Don't want the image generator? Just omit the `codex-imagegen` folder.

Restart Claude Code afterward — skills are loaded at startup. Verify with `/skills` (or ask Claude
"what skills do you have?"); you should see the `atelier-*` entries.

---

## Usage

The skills trigger automatically from their descriptions — you usually don't invoke them by hand.

- **New build:** just describe what you want — *"design a premium landing page for a developer tool."*
  `atelier-direction` engages first and sets the direction, then hands off down the pipeline.
- **Existing site:** *"make this site look less generic / modernize this app."* Start with
  `atelier-redesign`; it audits first, then pulls in the rest.
- **Pre-ship:** *"is this ready to ship? review it."* → `atelier-review` runs the adversarial audit;
  `atelier-perf-a11y` is the lighter self-checklist.

You can also invoke any one explicitly, e.g. `/atelier-foundations`.

### The knowledge base (deepdive)

Each skill cites a 16-section **deepdive** (`fundamentals-deepdive.md`) — a practitioner-grade reference
on the current (mid-2026) frontend ecosystem: animation libs, OKLCH color, Tailwind v4, shadcn, Core
Web Vitals, WebGPU/TSL, and the "expensive vs cheap" rules. A copy is **bundled into every skill's
`references/` folder**, so each skill is fully self-contained — nothing external to wire up.

---

## Optional: image generation

Three skills (`atelier-direction`, `atelier-components`, `atelier-webgl`) can generate imagery —
8-up direction moodboards, real section assets, and shader textures/poster fallbacks — via the bundled
**`codex-imagegen`** skill. This is **optional and degrades gracefully**: if it's unavailable, the
skills skip the moodboard and tell you to drop in your own assets (or any other image generator).

**To enable it (Windows):**
1. Install the Codex CLI: `npm i -g @openai/codex`
2. Log in with your ChatGPT Plus/Pro account: `codex login` (no OpenAI API key needed).
3. Keep the `codex-imagegen` folder in your skills directory (the helper resolves its own path at
   runtime, so it works wherever you installed the suite).

**On macOS / Linux, or without Codex:** the image generator's helper is a Windows PowerShell script, so
it won't run as-is. The design skills are unaffected — when image-gen is requested they'll substitute
any image generator you have (an MCP/IDE tool, a hosted model, stock you provide) or leave clearly
labelled asset slots. Swap in your own generator wherever a skill says "generate on the Direction Doc's
aesthetic."

---

## Folder layout

```
Atelier/
├── README.md                  ← this file
└── skills/
    ├── atelier-direction/         SKILL.md + references/ (+ bundled deepdive)
    ├── atelier-foundations/
    ├── atelier-typography/
    ├── atelier-layout/
    ├── atelier-components/
    ├── atelier-motion/
    ├── atelier-scroll/
    ├── atelier-webgl/
    ├── atelier-perf-a11y/
    ├── atelier-redesign/
    ├── atelier-review/            (no deepdive — it cites no external reference)
    └── codex-imagegen/            optional image generator (SKILL.md + scripts/)
```

Each `atelier-*` skill is a standard Claude Code skill: a `SKILL.md` (with `name`/`description`
frontmatter that controls triggering) plus a `references/` folder of supporting Markdown the skill reads
on demand.

---

## Notes

- **Default stack** is React/Next + Tailwind v4 + shadcn/ui, but the skills adapt to whatever a project
  already uses (down to vanilla CSS).
- **Premium foundries / heavy libraries** (GSAP, Motion, Three.js/R3F) are treated as first-class —
  assume you have what your build needs.
- These are *taste* skills: they bias hard toward restraint, coherence, and one earned "signature
  moment" over piling on effects. Read `atelier-direction` first to get the philosophy.
- No license is included — add one if you intend to redistribute.
