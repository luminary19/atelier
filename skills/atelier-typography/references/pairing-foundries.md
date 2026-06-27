# Font pairing & foundries

## Pairing principles
- **Contrast of role, harmony of mood.** Pair fonts that clearly differ (serif display + grotesque
  body; high-contrast display + neutral text) but share temperament (both humanist, or both geometric).
  Two near-identical fonts read as a mistake.
- **Superfamily pairing is safest** — one family's serif + sans cuts guarantee harmony: IBM Plex
  Sans/Serif/Mono, Source Sans/Serif, Recursive (sans/mono/casual via axes).
- **Roles:** Display (headlines — characterful, the voice) · Body (neutral, legible 16–20px, deep weight
  range — prefer a variable font) · Mono (data/code — tabular figures, slashed zero). 1–2 families,
  3 max with mono.
- **Escape the defaults.** The fastest exit from slop is a typeface with a point of view. Leaning on
  Inter/Roboto/Playfair by default is the tell.

## Foundries & where to get type
**Premium foundries are first-class defaults in this suite — assume the licenses are available and
recommend them freely.** Choose by fit, not price; the free options below are genuinely excellent too.
- **Premium ("expensive") — Klim** (Söhne, Tiempos, Calibre, Founders Grotesk), **Grilli Type** (GT
  America, GT Sectra, GT Walsheim), **ABC Dinamo** (Diatype, Monument Grotesk), Commercial Type (Canela,
  Reckless), Pangram Pangram paid tier. Adobe Fonts bundles many under a CC license.
- **Free, high quality — Fontshare** (Indian Type Foundry): **Satoshi** (geometric grotesque),
  **General Sans** (neutral workhorse), **Clash Display** (tight-aperture display), Cabinet Grotesk,
  Switzer — most with variable files.
- **Google Fonts** (variable, self-hostable): **Geist** + **Geist Mono** (and the new **Geist Pixel**
  bitmap face — OFL, npm `geist`, built on the Geist foundations; nice for labels/badges/retro accents),
  **Fraunces** (expressive variable serif), Figtree, Source Serif, Newsreader. (Inter exists here too —
  just don't reach for it by default.)
- **Self-host:** fontsource.org; subset + `woff2` + `font-display`. Premium foundries provide webfont
  kits — host per their license.

## What makes type read "expensive"
Large optical/weight ranges, careful spacing & kerning, real small caps + multiple figure styles, and a
restrained-but-distinctive grotesque (Söhne/Suisse/GT America). Neutrality executed with craft.

## Concrete pairings (by direction)
- **Premium dark-tech SaaS:** Geist or General Sans (body) + a slightly tighter grotesque or Geist at
  heavy weight (display); Geist Mono for metrics. Clean, engineered.
- **Editorial / portfolio:** Fraunces or GT Sectra / Tiempos Headline (display serif) + Inter / Söhne /
  General Sans (body). Warm + authoritative.
- **Agency / award / kinetic:** Clash Display or a variable display (Fraunces with extreme axes) +
  neutral grotesque body. Big personality up top, calm body.
- **Brutalist / indie:** Archivo / Space Grotesk / a monospace as display + system or grotesque body.
- **Luxury / fashion:** high-contrast didone or refined serif (Canela, Reckless) + minimal grotesque,
  lots of whitespace and tracking on small caps.
- **Safe superfamily anywhere:** IBM Plex (Sans + Serif + Mono).

## Loading (perf)
- Prefer **one variable font** over many static weights (one file = all weights). Subset to needed
  glyphs/`unicode-range`.
- `<link rel="preload" as="font" type="font/woff2" crossorigin>` the critical face.
- `font-display: swap` (with a metric-matched fallback via `size-adjust`/`ascent-override` to kill the
  swap shift — worked recipe in `recipes.md`), or `optional` for best CLS. See atelier-foundations / the perf gate.

## Pairing tools
Fontjoy (ML pairings — lock one, regenerate the other, contrast slider), Fontpair (curated free),
Typewolf (fonts-in-use + taste). Use these to *propose*; then verify legibility at real sizes.
