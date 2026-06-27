# ATELIER.md Extraction — Forge Brief Reference

## Contents
- §1. What forge-brief extracts and why
- §2. Sanction check (is 3D justified?)
- §3. Regex extraction patterns (Python)
- §4. Aesthetic → Forge look-dev direction table
- §5. OKLCH hue → material hue mapping
- §6. AskUserQuestion cap (4 options)
- §7. Edge cases and failure modes

---

## §1. What forge-brief extracts and why

`ATELIER.md` is the Atelier suite's persistent project memory. Every Atelier skill reads it
first. When Forge is invoked for a project that already has an ATELIER.md, the 3D look-dev
must harmonize with the web design system — not contradict it.

forge-brief is the **aesthetic bridge**: it reads ATELIER.md once, extracts the fields
relevant to 3D production, and writes them into FORGE.md's `## Atelier link` section. Every
downstream Forge skill (forge-material, forge-light, forge-render) then reads from FORGE.md
without needing to re-parse ATELIER.md.

**Fields extracted:**

| ATELIER.md location | Key | Maps to FORGE.md |
|---|---|---|
| `## Interactivity` section | `award-grade`, `webgl`, `canvas` keywords | Sanction flag (internal; not written to FORGE.md) |
| `**World:**` inline | `production` or `award` | `World: <value>` |
| `**Aesthetic:**` inline | Named aesthetic string | `Aesthetic: <value>` |
| `**Concept.*signature moment.*:**` | One-line description | `Signature moment: <value>` |
| First `oklch(... ... <H>)` in `## Tokens` | H channel float | `Primary OKLCH hue: <H>` |

---

## §2. Sanction check (is 3D justified?)

Before writing FORGE.md's Atelier link, check whether the 3D moment is sanctioned:

```
Sanctioned = Interactivity contains "award-grade" OR "webgl" OR "canvas"
```

**If sanctioned:** proceed — extract all fields and write `## Atelier link`.

**If not sanctioned (Interactivity = Static / Responsive / Choreographed):** PAUSE.
Authored 3D geometry (a real mesh with baked textures, a product viewer, a hero sculptural
form) carries real budget costs: Three.js engine weight, multi-MB assets, continuous rAF
loop, LCP impact, a11y opacity, and battery/thermal load on mobile. The project hasn't
budgeted for this.

Correct response:
1. Tell the user: "ATELIER.md shows Interactivity: [value] — a 3D production moment requires
   Award-grade to be sanctioned. Suggest running `Skill(atelier-direction)` to upgrade the
   project's budget."
2. Do NOT proceed to write FORGE.md or model geometry.
3. If the user explicitly overrides ("I know, build it anyway"), proceed with a warning note
   in FORGE.md: `## Note: 3D produced outside sanctioned Interactivity level.`

**If ATELIER.md is absent:** assume Production world unless the user explicitly states
Award-grade. Write FORGE.md without the `## Atelier link` section.

---

## §3. Regex extraction patterns (Python)

```python
import re, pathlib

def read_atelier_brief(root: str) -> dict:
    """
    Extract Forge-relevant fields from ATELIER.md.
    Returns a dict with keys:
      sanctioned: bool
      world: str ("production" | "award" | "unknown")
      aesthetic: str
      signature_moment: str
      primary_oklch_hue: float | None
    """
    p = pathlib.Path(root) / "ATELIER.md"
    if not p.exists():
        return {
            "sanctioned": False,
            "world": "production",
            "aesthetic": "",
            "signature_moment": "",
            "primary_oklch_hue": None,
        }

    text = p.read_text(encoding="utf-8")

    # ─── Sanction check ───
    interactivity_m = re.search(
        r"##\s*Interactivity\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL | re.IGNORECASE
    )
    sanctioned = False
    if interactivity_m:
        val = interactivity_m.group(1).lower()
        sanctioned = any(kw in val for kw in ("award-grade", "award grade", "webgl", "canvas"))

    # ─── World ───
    world_m = re.search(r"\*\*World:\*\*\s*(.+?)(?:\n|$)", text)
    world = world_m.group(1).strip() if world_m else "unknown"
    # Normalize to "production" or "award"
    if "award" in world.lower():
        world = "award"
    elif "production" in world.lower():
        world = "production"

    # ─── Aesthetic ───
    aes_m = re.search(r"\*\*Aesthetic:\*\*\s*(.+?)(?:\n|$)", text)
    aesthetic = aes_m.group(1).strip() if aes_m else ""

    # ─── Signature moment ───
    # Matches "**Concept / signature moment:**" or "**Concept + signature moment:**"
    sig_m = re.search(
        r"\*\*Concept.*?signature\s+moment.*?\*\*[:\s]+(.+?)(?:\n|$)",
        text, re.IGNORECASE
    )
    signature = sig_m.group(1).strip() if sig_m else ""

    # ─── Primary OKLCH hue ───
    # Extracts H value from the first oklch(...) token in ## Tokens section
    tokens_m = re.search(r"##\s*Tokens\s*\n(.+?)(?=\n##|\Z)", text, re.DOTALL | re.IGNORECASE)
    hue = None
    if tokens_m:
        # oklch(lightness chroma hue) — H is the 3rd number
        oklch_m = re.search(
            r"oklch\(\s*[\d.]+%?\s+[\d.]+\s+([\d.]+)",
            tokens_m.group(1)
        )
        if oklch_m:
            try:
                hue = float(oklch_m.group(1))
            except ValueError:
                hue = None
    # Fallback: search entire file if Tokens section not found
    if hue is None:
        oklch_m = re.search(r"oklch\(\s*[\d.]+%?\s+[\d.]+\s+([\d.]+)", text)
        if oklch_m:
            try:
                hue = float(oklch_m.group(1))
            except ValueError:
                hue = None

    return {
        "sanctioned": sanctioned,
        "world": world,
        "aesthetic": aesthetic,
        "signature_moment": signature,
        "primary_oklch_hue": hue,
    }
```

**Usage in forge-brief flow (pseudocode):**
```python
brief = read_atelier_brief(project_root)

if not brief["sanctioned"]:
    # PAUSE — do not proceed with 3D build
    print("ATELIER.md Interactivity is not Award-grade — 3D moment not sanctioned.")
    # Suggest: Skill(atelier-direction)
else:
    # Write ## Atelier link block into FORGE.md
    atelier_block = f"""## Atelier link
World: {brief['world']}
Aesthetic: {brief['aesthetic']}
Signature moment: {brief['signature_moment']}
Primary OKLCH hue: {brief['primary_oklch_hue'] if brief['primary_oklch_hue'] is not None else 'unknown'}
"""
```

---

## §4. Aesthetic → Forge look-dev direction table

When `forge-material` and `forge-light` ask "what should this asset look like?", they read
the aesthetic from FORGE.md `## Atelier link`. This table maps named Atelier aesthetics to
concrete Blender look-dev defaults:

| ATELIER.md Aesthetic | Blender material | Lighting rig | HDRI / env | Render notes |
|---|---|---|---|---|
| Dark-tech (Linear / Vercel / Raycast) | Matte/brushed metal; dark base color; minimal emission; strong rim light | Strong backlight + rim; minimal fill | Dark studio / neutral overcast | Near-black background; high contrast |
| Glass / Liquid Glass | Principled BSDF: IOR ≈ 1.5, Transmission 1.0, thin | HDRI + point light for caustics | Bright studio / sky | Enable Cycles caustics; use denoiser |
| Warm / neo-minimalism | Soft baked SSS clay; Principled Subsurface ≈ 0.3; off-white | Warm directional (key) + soft fill | Golden-hour / warm HDRI | No chrome; muted palette |
| Swiss / editorial | White/grey matte; Roughness 0.8; zero Metallic | 3-point studio; sharp shadows | Neutral grey studio | High key; minimal shadows |
| Brutalism / collage | Low-saturation flat shading; Flat shader or very high Roughness | Hard single-source key; no IBL | Dark mono | Avoid IBL smoothness; raw industrial |
| Maximalism / Y2K | High Emission; saturated Base Color; Metallic 0.7–1.0 | Multiple colored rim lights; neon | Colorful studio | Bloom enabled; vivid palette |
| Organic / biomorphic | Principled SSS; low roughness; skin/wax tones | Soft wrap key + bounce fill | Warm neutral | Subsurface Color different from Base |
| Industrial / mechanical | Brushed metal; ORM bake from HP; Metallic 0.9–1.0 | Hard key + rim; spot lights | Neutral factory | Clear wear/edge scratches from curvature |
| Minimal / clean | Off-white matte; Roughness 0.9; zero emissive | Neutral 3-point or 2-point | Light grey studio | No bloom; near-white background |

---

## §5. OKLCH hue → material hue mapping

The OKLCH H value extracted from ATELIER.md `## Tokens` is the primary brand hue in degrees
(0–360, perceptually uniform). Forge materials should harmonize with it, not clash.

**How to use the hue in Blender materials:**

OKLCH H → approximate RGB range (for orientation only; use proper OKLCH → sRGB conversion
for precision):

| OKLCH H range | Color family | Blender Base Color (approximate) |
|---|---|---|
| 0–30 or 330–360 | Red / red-pink | (0.8, 0.1, 0.1) area |
| 30–70 | Orange / amber | (0.8, 0.4, 0.05) area |
| 70–110 | Yellow / lime | (0.8, 0.8, 0.1) area |
| 110–160 | Green | (0.1, 0.7, 0.2) area |
| 160–220 | Cyan / teal | (0.05, 0.6, 0.7) area |
| 220–270 | Blue | (0.1, 0.2, 0.9) area |
| 270–310 | Purple / violet | (0.5, 0.1, 0.8) area |
| 310–330 | Magenta / pink | (0.8, 0.1, 0.6) area |

**Harmony rules:**
- A metallic material's Base Color should be a desaturated version of the brand hue
  (low Chroma, same H).
- A glass/transmission material's tint should use the hue at high Lightness (nearly white).
- An emissive accent should use the hue at high Lightness + boosted strength.
- A matte clay prop can be near-neutral with just a hint of the hue (+5–10 OKLCH Chroma).

---

## §6. AskUserQuestion option-cap (4 options)

The `AskUserQuestion` tool caps at **4 picker options** — any additional options are
silently dropped. This is a documented atelier-direction constraint.

**Impact for forge-brief:** Engine/target choices exceed 4 options (three.js/R3F, Unreal,
Unity, Godot, print, USD, render-only = 7).

**Correct pattern:**
1. List all options in the message body as a numbered Markdown list.
2. Use the picker with ≤ 4 options for the final commit (e.g., "Confirm my recommendation"
   vs "Let me choose a different engine").

```
Message body:
"Which delivery target?
1. three.js/R3F (web browser, GLB)
2. Unreal Engine 5 (FBX, Z-up, cm)
3. Unity / Godot 4 (FBX or GLB, Y-up, m)
4. 3D print (STL/3MF, mm, manifold required)
5. USD / Omniverse (USDC, Y-up, m)
6. Render-only (Blender .blend, no engine export)"

Picker options (max 4):
- "Use three.js/R3F (my recommendation)"
- "Use Unreal Engine 5"
- "Use Unity or Godot"
- "I'll specify the engine — it's not on this list"
```

---

## §7. Edge cases and failure modes

### ATELIER.md missing `**Aesthetic:**` line

Some older ATELIER.md files use `Aesthetic:` without bold markdown syntax.

Add a fallback regex:
```python
if not aesthetic:
    aes_m2 = re.search(r"(?:^|\n)Aesthetic:\s*(.+?)(?:\n|$)", text)
    aesthetic = aes_m2.group(1).strip() if aes_m2 else ""
```

### OKLCH token in HSL or HEX format (not OKLCH)

If the tokens section uses `hsl()` or `#rrggbb` instead of `oklch()`, the H extraction
returns None. In that case, fall back to writing `Primary OKLCH hue: unknown` in FORGE.md
and note it for `forge-material` to handle manually.

### Interactivity section spans multiple lines / has checkboxes

ATELIER.md sometimes encodes Interactivity as a checklist:
```
## Interactivity
- [ ] Static
- [ ] Responsive
- [x] Award-grade
```

The sanction regex handles this because it searches the full section text for the keyword,
not just the first line. No special case needed.

### FORGE.md already has a `## Atelier link` section

When updating an existing FORGE.md, use `Edit` (not `Write`) to replace only the
`## Atelier link` block. Never overwrite the whole file — `## Budgets` and `## Render`
may have been refined by downstream skills.

Pattern for the Edit tool:
- Find: the existing `## Atelier link\n...` block (from `## Atelier link` to the next `##`)
- Replace: with the freshly extracted content

### Project root disambiguation

"Project root" = the directory containing `FORGE.md` or the git repo root.
Use `git rev-parse --show-toplevel` to find it reliably:
```powershell
$root = git rev-parse --show-toplevel
```
Or look for `ATELIER.md`, `package.json`, or `pyproject.toml` walking up from the CWD.
