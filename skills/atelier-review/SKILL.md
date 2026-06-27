---
name: atelier-review
version: 1.0.0
description: >
  Atelier suite — the adversarial pre-ship review. A full multi-step red-team of a FINISHED frontend
  build: fan out independent reviewers across dimensions (accessibility, performance, motion/reduced-
  motion, design-integrity/anti-slop, code quality), adversarially verify every finding to kill false
  positives, verify live in a real browser, synthesize a prioritized fix list, apply serially, and
  re-verify. Built to run with the ordinary Task/subagent tool — it does NOT require ultracode/Workflow.
  Use whenever a substantial build is "done" and needs a real audit before shipping, when asked to review
  / red-team / audit / "is this ready to ship" / find problems / pre-ship review a frontend. This is the
  heavyweight, adversarial counterpart to the atelier-perf-a11y self-checklist. Part of the Atelier suite.
triggers:
  - adversarial review
  - red team
  - review the build
  - audit the frontend
  - is this ready to ship
  - pre-ship review
  - find problems
  - review my site
  - critique the build
allowed-tools:
  - Read
  - Glob
  - Grep
  - Bash
  - Write
  - Edit
  - Task
# Step 4 (live verification) additionally requires the Playwright MCP browser tools
# (browser_navigate / browser_evaluate / browser_take_screenshot / browser_resize / browser_console_messages).
# allowed-tools can't enumerate MCP tools portably — ensure the Playwright MCP server is enabled in the session.
---

# Atelier — Adversarial Review

The builder is blind to their own work. This skill runs **independent, hostile reviewers** over a
finished build, makes each finding **survive an adversarial refutation**, confirms everything **live in a
real browser**, then applies fixes and re-checks. It is the structured, repeatable version of the
multi-agent audit — **without** needing ultracode: it orchestrates ordinary subagents (the `Task` tool),
which are always available.

> **Project memory:** if **`ATELIER.md`** exists, read it first — the DESIGN reviewer checks fidelity to
> its register, policies, and anti-references (not just the Direction Doc). Set up via **`/atelier init`**.
>
> **Inputs:** a built, runnable site/app + the **Direction Doc** (to check fidelity, via `atelier-direction`).
> **Rubrics it reviews against** (cite cross-skill refs fully-qualified): `atelier-perf-a11y/references/
> preflight-checklist.md`, `…/anti-slop-preflight.md`, `…/accessibility.md`, `…/performance.md`, `…/detector.md`
> (the deterministic pre-pass), plus the domain refs under `atelier-motion`, `atelier-scroll`,
> `atelier-webgl`, `atelier-typography`, `atelier-layout`, `atelier-foundations`, `atelier-dataviz`,
> `atelier-ux`, `atelier-copy` (UX-writing rubric), and `atelier-harden` (resilience checklist). Reviewer +
> verifier prompt templates and the findings contract:
> **`references/reviewer-prompts.md`** (this skill's own ref). Live in-browser playbook:
> **`references/live-verification.md`** (this skill's own ref).
>
> **Supplementary data — `atelier-data`:** the DESIGN / A11Y reviewers may also consult its web UX heuristic list (`atelier-data/scripts/search.py "<topic>" --domain ux`) as a *breadth* prompt to catch overlooked patterns. It is curated-opinion, **not** a compliance source — the `atelier-perf-a11y` rubrics above remain authoritative.

## Where this sits — the quality ladder
Four layers, escalating rigor — **same rubrics throughout**, just re-checked with more independence:
0. **deterministic detector** (`atelier-perf-a11y/scripts/detect.py`) — a fast regex-tier pre-pass on
   source. Run it before everything else and feed its hits in as leads. Every build (seconds).
1. **perf-a11y self-checklist** (`atelier-perf-a11y/references/preflight-checklist.md`) — Core Web Vitals +
   WCAG 2.2 AA. Every build.
2. **anti-slop self-checklist** (`atelier-perf-a11y/references/anti-slop-preflight.md`) — the "AI Tells"
   pass on the rendered output. Every build.
3. **this skill — adversarial** — independent reviewers per dimension + refutation + live browser
   verification. Substantial / redesign / award builds.

Layers 0–2 are you checking your own work; **this** is independent reviewers trying to break it. So:
- **Quick build / single component** → just the layer-1/2 self-checklists. Don't over-process.
- **Substantial build, redesign, or award-grade work** → run **this**; it assumes the builder (you) missed
  things and pays independent reviewers to find them.

## The dimensions (one reviewer each — scale to the task)
- **A11Y** — WCAG 2.2 AA: contrast in *every* theme, focus-visible, keyboard, landmarks/heading order,
  reduced-motion completeness, target size, canvas/WebGL + chart text/table alternative, marquee pause.
- **PERF** — Core Web Vitals (field/p75 gate: LCP ≤2.5s, CLS ≤0.1, INP ≤200ms), lazy/`will-change`/
  `content-visibility`, font + asset strategy, compositor-only animation, offscreen pausing.
- **MOTION** — every motion path traced incl. the *reduced* path; breakpoint gates match the CSS; pin/
  scrub/marquee/cursor correctness; dispose/cleanup; cross-browser (svh, blend modes, oklch, iOS).
- **DESIGN** — anti-slop Tells (`anti-slop-preflight.md`) + **fidelity to the Direction Doc and
  `ATELIER.md`** (register, world, concept, signature moment, one-accent/theme/radius discipline,
  interactivity/glass policy, anti-references) + light/dark correctness + polish + **placeholder / fake /
  missing imagery** (div-fakes, gradient-blob heroes, stock-looking filler) + chart honesty/clutter
  (`atelier-dataviz`) + IA/flow coherence and missing screen-states (`atelier-ux`). Run a **5-persona pass**
  (power user · first-timer · screen-reader user · mobile user · stress-tester), naming the element-level
  failure each one hits.
- **CODE/COPY** (add when the build is large) — dead/duplicate code, contract drift, broken/AI-cute copy,
  fake-precise numbers. Judge copy against **`atelier-copy`**: errors say what happened + why + how to fix;
  labels verb-first; no duplicate CTA intents; no buzzword filler; placeholders aren't labels.
- **RESILIENCE** (add for production apps) — exercise the non-happy paths against **`atelier-harden`**: text
  overflow at every breakpoint, long / empty / huge data, per-status error states, offline / timeout,
  i18n / RTL + locale formatting, double-submit + cleanup. A demo-data happy-path build fails this even when
  it looks finished.

## The flow

1. **Boot & scope.** Identify the build's files and how to run it. Start it (a no-cache static server for
   vanilla; the dev server otherwise). Load it once — **console errors/warnings are findings**. List the
   files each reviewer needs. **Run the deterministic detector first** —
   `python atelier-perf-a11y/scripts/detect.py --json <built/changed files>` — and hand its hits to the
   DESIGN + A11Y reviewers as *leads to verify live*, not automatic findings (it's regex-tier; it can't see
   rendered geometry or real contrast).
2. **Fan-out review (parallel, READ-ONLY).** Spawn one subagent per dimension *in a single message* so
   they run concurrently. Each is a **hostile specialist** — "assume this build is flawed; find the real
   problems" — reads its files + the matching Atelier rubric, and returns findings in the fixed contract
   (`{severity, file, location, problem, fix, confidence}`). **Reviewers never edit** — they return
   findings only. (Prompts: `references/reviewer-prompts.md`.)
3. **Adversarial verification.** Every non-trivial finding must survive a refutation. Spawn verifier
   subagents (parallel) prompted to **prove the finding wrong** — not real, already handled, or the fix
   would break something — *defaulting to "refuted" when uncertain*. For findings that can fail multiple
   ways, use distinct lenses (correctness / does-it-repro / side-effects) rather than identical skeptics.
   Drop anything refuted by the majority. This is what kills the plausible-but-wrong finding (e.g. a
   contrast "failure" measured against the wrong background).
4. **Live verification (you, in the browser).** Static review is not enough. **Requires the Playwright MCP
   browser tools** (`browser_navigate`/`browser_evaluate`/`browser_take_screenshot`/…) — if they aren't
   available in the session, say so and fall back to a manual/devtools pass rather than skipping it. Drive
   the *running* app: console clean; screenshots at desktop **and** mobile;
   emulate `prefers-reduced-motion`; tab through with the keyboard; and **compute contrast from rendered
   pixels** (don't trust a token value or a string). Confirm/refute findings here. (Playbook:
   `references/live-verification.md`.)
5. **Synthesize + score.** Merge static + live + verdicts, dedupe, drop refuted. Tag each surviving finding
   **P0–P3** (P0 = blocker / ship-stopper · P1 = high · P2 = medium · P3 = low) and sort by it. State a
   **per-dimension verdict** (ship-ready · ship-with-risks · blocked) and an overall **ship-readiness** call
   with the P-counts (e.g. "blocked — 2×P0, 5×P1"). **Persist a snapshot** to `.atelier/review-snapshot.md`:
   the date, overall verdict, P0–P3 counts, and the open findings grouped by dimension. A re-run reads the
   last snapshot as its backlog and reports the trend (P-counts down = the fixes landed) — so the loop in
   step 7 is measurable, not vibes.
6. **Apply — serially, in the main thread.** Fix the surviving findings yourself, one coherent pass. **Do
   NOT fan out the fixes** — parallel edits to shared files (one CSS, one HTML) collide. Reviewers fan out;
   fixes do not. Asset findings (placeholder / fake / missing imagery) are remediated here by generating
   real assets on the Direction Doc's aesthetic via **`/codex-imagegen`** and wiring them in optimized
   (WebP/AVIF + `width`/`height` + `alt`).
7. **Re-verify & loop.** Re-run the live checks against the fixes. Loop steps 4→6 until only acceptable
   lows remain. Report what was found, fixed, and consciously deferred.

## How to run it WITHOUT ultracode (the point of this skill)
- **Primary — subagents via the `Task` tool.** It's a core capability (no opt-in, unlike Workflow). Launch
  K reviewers by issuing K `Task` calls **in one message** (they run in parallel); collect their findings;
  launch the verifier round the same way; then apply yourself. One level of fan-out is enough — subagents
  can't nest, and a review doesn't need them to.
- **Fallback — sequential self-review** (no subagent tool, or a small build): play each reviewer in turn,
  writing findings to a scratch list (`review-findings.md`); then a separate **skeptic pass** over your
  own list (refute each); then live-verify. Slower and less independent, but keeps the adversarial shape.
- **Scale to the task.** Quick: 3 reviewers, single-vote verify, one viewport. Thorough/award: 5–6
  reviewers, 3-lens adversarial verify, full desktop+mobile+reduced-motion+both-themes matrix. Say what
  you scaled to.

## Hard-won rules (from real runs)
- **Reviewers read; the main thread writes.** The single most important rule — it's why fixes are coherent
  and conflict-free.
- **Live-verify in the main thread**, never in subagents — they'd each need their own browser and would
  fight over one shared session and the server lifecycle.
- **Trust pixels, not strings.** `getComputedStyle` returns `oklch()`/`oklab()`; paint the color to a 1×1
  canvas and read sRGB to compute real WCAG contrast. Wait for theme/transition to *settle* before reading.
- **A finding isn't real until it survives refutation.** Most one-shot audits over-report; the verify
  round is what makes this trustworthy.
- **A "Tell" can be a committed concept device.** Check `atelier-perf-a11y/references/anti-slop-preflight.md`'s
  escape hatch before flagging an intentional system as slop.

---

## Operating principles
- **Assume it's broken.** A review that confirms the build is fine has done nothing; reviewers are paid to break it.
- **Independent beats thorough-solo.** Separate hostile reviewers + a refutation round catch what one self-pass can't.
- **Verify live, not on paper.** The browser is the source of truth; computed pixels over token values.
- **Fan out the finding, serialize the fix.** Parallel reviewers, single-threaded edits.
- **Don't depend on ultracode.** This is the always-on adversarial review; Workflow is a bonus, not a requirement.
