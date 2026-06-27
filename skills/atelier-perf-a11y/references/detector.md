# The atelier detector — `scripts/detect.py`

A native, **regex-tier** static checker that mechanizes Atelier's own tells. It scans source text
(CSS / HTML / JSX / TSX / Vue / Svelte / Astro / MD) and reports findings in the five buckets from the
suite's quality model. **Strictly Atelier** — it enforces the `anti-slop-preflight.md` checklist and the
`atelier-foundations` / `atelier-typography` numeric thresholds; it is not a port of any third-party tool,
and it has no external dependencies (Python stdlib only).

> **Honest scope.** This sees what's in *source*. It does **not** parse the DOM, run layout, resolve
> computed styles, or compute real contrast — so it cannot judge rendered geometry or color pairs. It is a
> cheap first net that **complements, never replaces**, the LLM anti-slop self-check and `atelier-review`'s
> live, pixel-computed verification. Treat WARN/SUGGEST as prompts to look, not verdicts.

## Run it (Windows: `python`, not `python3`)

```bash
cd <project>
python "$CLAUDE_CONFIG_DIR/skills/atelier-perf-a11y/scripts/detect.py" src/
python ".../detect.py" src/ --json            # machine-readable (for atelier-review to parse)
python ".../detect.py" src/ --category cliche  # one bucket
python ".../detect.py" src/ --severity warn    # warn + block only (drop suggest)
python ".../detect.py" src/ --strict           # exit 2 if any BLOCK finding (CI)
```

## The rules, by bucket

| Bucket | Rules | Default severity |
|---|---|---|
| **a11y** | `img-no-alt`, `positive-tabindex`, `outline-none-no-focus` (block); `div-onclick`, `tiny-font` (warn) | block / warn |
| **layout** | `magic-zindex` (warn); `viewport-height-unit` (100vh→dvh) (suggest) | warn / suggest |
| **drift** | `important-overuse`, `hardcoded-color-drift` (suggest) | suggest |
| **cliche** | `gradient-text`, `cream-token-name`, `pure-black-white`, `bounce-elastic-easing`, `glassmorphism-default`, `side-stripe` (warn); `buzzword-copy`, `em-dash-overuse` (suggest) | warn / suggest |
| **subjective** | `justified-text` (suggest) | suggest |

Severity → action: **block** = a real defect (a11y/layout) — fix it, and it fails CI under `--strict`.
**warn** = a probable issue or a strong AI tell — advisory; weigh against the Direction Doc. **suggest**
= low-confidence or a matter of taste — never blocks. This is the dive's "a11y/layout block; clichés
warn; aesthetics never fail CI" policy made concrete.

## Three ways to use it (and which to prefer)

1. **Manual audit (default — best for a solo workflow).** Run it before shipping, or point it at the files
   you just changed. Intentional, no passive noise. `atelier-review` runs it automatically in its flow.
2. **CI gate (optional, quality-only).** Run `--strict` so only **block** findings (a11y/layout defects)
   fail the pipeline. **Never gate on cliché/subjective findings** — aesthetic tells are context-dependent
   and a committed concept device is not a tell; a CI that fails on taste produces false-positive fatigue.
3. **PostToolUse hook (opt-in, quiet).** `scripts/detect_hook.py` fires after a UI-file edit and surfaces
   block/warn findings as a nudge. It always exits 0, never blocks, and drops `suggest` noise.

## Enabling the opt-in hook

The hook is **built but not wired** — a global `PostToolUse` hook runs on every edit in every repo, so
enabling it is your call. To turn it on, add this to `settings.json` → `hooks.PostToolUse` (a new matcher
object alongside the existing entries):

```json
{
  "matcher": "Edit|Write|MultiEdit",
  "hooks": [
    {
      "type": "command",
      "command": "python \"$env:CLAUDE_CONFIG_DIR\\skills\\atelier-perf-a11y\\scripts\\detect_hook.py\""
    }
  ]
}
```

- Disable temporarily without editing settings: set env `ATELIER_DETECT_OFF=1`.
- The wrapper self-scopes to **UI-certain** extensions (`.css/.scss/.sass/.less/.html/.htm/.jsx/.tsx/.vue/.svelte/.astro`)
  — it deliberately skips `.py`/`.md`/configs **and bare `.js`/`.ts`** (often backend/scripts) so it stays
  non-disruptive on non-frontend work. Manual `detect.py` runs and `atelier-review` keep full `.js/.ts/.md` coverage.
- Cost note: a global `PostToolUse` hook's interpreter starts on every `Edit/Write/MultiEdit` to self-filter
  (~50-100ms); for zero overhead on non-frontend repos, add it to a frontend project's local
  `.claude/settings.json` instead of the global one.
- If you don't want passive checks at all, skip this entirely — modes 1 and 2 cover the workflow.

## How the suite calls it

- **`atelier-perf-a11y`** lists it as **Layer 0** of the quality ladder (the deterministic pre-pass before
  the two LLM self-checklists).
- **`atelier-review`** runs `detect.py --json` in its boot/scope step and folds the findings into the
  DESIGN + A11Y reviewers' inputs (a finding is a lead to verify live, not an automatic finding).

## Extending it

Add a rule to `LINE_RULES` in `detect.py` (id, category, severity, extension-set, compiled regex, message,
optional numeric test), or a special-case function for anything multi-line / file-level. Keep new rules
**source-detectable and low-false-positive** — anything needing the DOM belongs in `atelier-review`'s live
pass, not here. Mirror any new design rule into `anti-slop-preflight.md` so the checklist and the detector
stay in sync.
