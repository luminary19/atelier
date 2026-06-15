---
name: codex-imagegen
version: 1.0.0
description: |
  Generate and edit raster images by driving the locally-installed OpenAI Codex CLI
  headlessly and invoking its FIRST-PARTY built-in `image_gen` tool (gpt-image) — using
  the ChatGPT Plus/Pro login Codex is already authenticated with, NO OpenAI API key, no
  reverse-engineered routes. Use when asked to "generate an image", "make a logo/icon/
  texture/mockup", "edit this PNG", "use codex to create an image", or "/codex-imagegen".
  Wraps `codex exec` and parses output via a PowerShell helper so files are reliably found.
triggers:
  - codex-imagegen
  - generate an image with codex
  - codex image generation
  - make an image
  - edit this image
  - create a logo / icon / texture / mockup
allowed-tools:
  - Bash
  - PowerShell
  - Read
  - Write
  - Glob
---

# /codex-imagegen — image generation via the local Codex CLI (no API key)

Generate or edit raster images by driving the **already-installed, already-logged-in**
OpenAI Codex CLI and triggering its **built-in `image_gen` tool**. This piggybacks on the
user's **ChatGPT Plus/Pro session tokens** that Codex stores in `auth.json` — there is
**no `OPENAI_API_KEY`** and **no manual HTTP / internal-route work**. The image model under
the hood is OpenAI's `gpt-image` (gpt-image-2).

## How this actually works (read once)

- Codex ships two image paths. **(1) the built-in `image_gen` tool** — server-side, runs on
  whatever auth Codex has (ChatGPT login *or* key), **needs no key**. **(2) a Python fallback
  CLI** (`image_gen.py`) — needs `OPENAI_API_KEY`. **This skill uses path (1) only** and must
  steer the agent away from path (2).
- We invoke it through `codex exec "<prompt>"` (non-interactive). The prompt instructs the
  Codex agent to call the built-in `image_gen` tool and generate N images.
- **Where files land:** the built-in tool has **no path argument** — it writes to
  `$CODEX_HOME\generated_images\<session-id>\ig_*.png`. The agent's own "now copy it to your
  folder" step is **unreliable and frequently hallucinated** (it prints `DONE` + a fake path
  while the real PNG sits in `generated_images`). So **the helper script does the copy itself**:
  it snapshots `generated_images` before the run, finds the new file after, and copies it into
  `-OutDir` with a friendly name. Never trust the agent's claimed save path.
- **Critical gotcha:** a model reading a SKILL.md does **not** run the bash inside it verbatim
  (it tries to pre-evaluate `$(...)`). So **all the real logic lives in `scripts/codex-image.ps1`**
  — you (Claude) just call that one script. Do not hand-assemble the `codex exec` line.
- The user is on **native Windows 11, PowerShell, no WSL**. Codex here has no OS sandbox, so we
  run with approvals/sandbox bypassed (safe: it only ever writes into the chosen output dir).

## Preflight (run once per session, via the PowerShell tool)

```powershell
$ch = $env:CODEX_HOME
$ok = (Get-Command codex -ErrorAction SilentlyContinue) -and (Test-Path "$ch\auth.json") `
      -and (Test-Path "$ch\skills\.system\imagegen")
if (-not $ok) { "PREFLIGHT FAILED — see notes" } else {
  $a = Get-Content "$ch\auth.json" -Raw | ConvertFrom-Json
  "codex: $((Get-Command codex).Source)"
  "auth mode: " + ($(if ($a.tokens) {'chatgpt-login (no key needed)'} elseif ($a.OPENAI_API_KEY) {'api-key'} else {'unknown'}))
  "imagegen tool present: yes"
}
```

If preflight fails:
- `codex` missing → tell the user to install it (`npm i -g @openai/codex`) and `codex login`.
- no `tokens` in `auth.json` → they aren't logged into ChatGPT; have them run `codex login`
  (or `codex login --device-auth` on a headless box). Don't proceed.
- imagegen skill missing → their Codex is too old or trimmed; `npm i -g @openai/codex@latest`.

## Generate — the happy path

Call the helper. **Always prefer the script over a raw `codex exec`.**

```powershell
# Resolve your Claude skills dir (this skill lives under it):
$skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
& "$skills\codex-imagegen\scripts\codex-image.ps1" `
    -Prompt "A cozy alpine cabin at dawn, soft volumetric light, photographic" `
    -OutDir ".\codex-images" `
    -Count 1 `
    -Size 1024x1024
```

The script:
1. snapshots existing images in both `-OutDir` and `$CODEX_HOME\generated_images`,
2. builds a prompt that forces the **built-in `image_gen`** tool (and bans the API-key fallback),
3. runs `codex exec --skip-git-repo-check -C <OutDir> --dangerously-bypass-approvals-and-sandbox -o <lastmsg>`,
4. finds the new PNG(s) the tool wrote under `generated_images` after the run started,
5. **copies them into `-OutDir`** with a prompt-derived filename, then prints `CREATED: <absolute path>`.

Relay the created file paths to the user. If you can display images, `Read` one to show it.
Exit code `0` = images created, `2` = none found (surface the agent message), `1` = preflight/error.

### Useful parameters

| Param | Meaning | Default |
|-------|---------|---------|
| `-Prompt` | what to draw (required unless `-Edit`) | — |
| `-OutDir` | where PNGs land (becomes Codex's working root) | `.\codex-images` |
| `-Count` | number of variations | `1` |
| `-Size` | `1024x1024`, `1536x1024`, `1024x1536`, or `auto` | `1024x1024` |
| `-Transparent` | request a transparent background (PNG) | off |
| `-Model` | force a Codex model (e.g. `gpt-5.1-codex`) | Codex default |
| `-Edit` | path to an input image → switches to **edit** mode | — |
| `-Sandbox` | `bypass`\|`workspace-write`\|`danger-full-access` | `bypass` |
| `-TimeoutSec` | hard cap per run | `420` |
| `-DryRun` | print the command without running | off |

## Edit an existing image

```powershell
& "...\scripts\codex-image.ps1" `
    -Edit ".\input.png" `
    -Prompt "Replace the background with a clean white studio backdrop; keep the subject sharp" `
    -OutDir ".\codex-images"
```

This attaches the source with `codex exec -i <file>` and asks the built-in tool to edit it.

## Batch / many variations

For several distinct prompts, call the script once per prompt (cleaner output discovery than
one mega-prompt). For N *variations of one* prompt, use `-Count N`.

## Reliability rules (so it doesn't silently no-op)

- **Force the right tool.** The prompt the script sends says, verbatim, *"Use your built-in
  `image_gen` tool. Do NOT use the python image_gen.py fallback and do NOT ask for or use an
  OPENAI_API_KEY."* Keep that — it's the difference between key-free success and a key prompt.
- **Never trust the agent's save path.** The agent routinely prints `DONE` and a path while the
  real PNG sits in `$CODEX_HOME\generated_images`. Truth = the filesystem diff the script does;
  the script tells the agent NOT to move files and copies them out itself. Don't "fix" this by
  asking the agent to save to a path — the built-in tool has no path argument.
- **No interactive hangs.** Headless runs must never wait on approval — that's why sandbox is
  bypassed. If a user insists on a sandbox, use `-Sandbox workspace-write` and the script adds
  `-c sandbox_workspace_write.network_access=true`.
- **Verify, don't assume.** If the script prints `CREATED:` lines, the files exist (it stat'd
  them). If it prints `NO IMAGES FOUND`, surface the agent's final message — usually it means
  the tool was disabled, auth expired, or the prompt was refused. Re-run `codex login` if auth.

## Failure modes & what they mean

- **"would need an API key" / asks for `OPENAI_API_KEY`** → the agent reached for the *fallback*
  CLI. Re-run; the forcing prompt usually fixes it. If persistent, the built-in tool may be off
  for that model — try `-Model gpt-5.1-codex` (a current Codex model that exposes the tool).
- **Auth/401-style errors** → ChatGPT session expired → `codex login`.
- **Hangs** → an approval prompt is blocking; ensure `-Sandbox bypass` (default) is used.
- **Zero files but "done"** → agent described an image instead of calling the tool; make the
  prompt more imperative ("call the image_gen tool now and save the file").
- **High token use** → each low-detail image turn can burn ~30k agent tokens; that's expected
  overhead of routing through an agent rather than a bare API call. Note it; don't loop blindly.

## Boundaries

- This is **not** an OpenAI API client and must not become one. If the user wants raw API image
  gen with a key, that's the `image_gen.py` fallback or the Images API — out of scope here.
- Don't attempt to read, copy, or transmit the ChatGPT tokens in `auth.json`. The whole point is
  that Codex uses them in-process; the skill never touches them.
