# Imagery, iconography & illustration — direction

The decisions here are *art direction*, not implementation. Pick a coherent visual-asset language as part
of the Direction Doc; **`atelier-components/references/icons-and-imagery.md`** builds it (icon system,
responsive `<img>`/`next/image`, CSS treatment, favicon/OG pipeline). Generated assets come from
**`/codex-imagegen`**, art-directed on the chosen aesthetic.

## Iconography — pick ONE system
Mismatched icons (two libraries, mixed weights, some filled some outline) are a quiet but unmistakable slop
tell. Decide:
- **One family, one style.** Outline *or* filled *or* duotone — not a mix. Stroke weight and corner radius
  should echo the type weight and the `--radius` system (sharp icons for Swiss/brutalist; rounded for
  soft/premium). Pick a default by fit:
  - **Lucide** — clean, neutral outline; the shadcn default. Safe premium default.
  - **Phosphor** — six weights (thin→fill) from one set; great when you want weight as a system.
  - **Heroicons** (outline+solid pair), **Tabler** (huge outline set), **Radix Icons** (tiny, UI-focused),
    **Iconoir**. Match the set's personality to the aesthetic.
- **Custom icons for brand-critical glyphs** (logo-mark, signature features) — drawn on the same grid (e.g.
  24px, 1.5–2px stroke) so they sit with the library set. Don't redraw the whole set; extend it.
- **One size grid + `currentColor`** so icons inherit text color/size and stay optically consistent.
- **Avoid:** emoji as UI icons; a 500-glyph icon *font* (ships the whole set, a11y-hostile) when tree-shaken
  SVG components do the job; decorative icons with no label on icon-only controls (→ a11y gate).

## Illustration — one voice or none
An illustration style is a strong brand lever — but only if it's *one* voice, used with intent.
- **Choose the medium per world/aesthetic:** clean line, flat-geometric, isometric, grain-textured, 3-D/clay,
  or collage-cutout (pairs with the Collage aesthetic). Premium brands commit to a single illustration
  language and repeat motifs.
- **Illustration vs photography vs 3-D vs abstract** — decide deliberately: illustration for concepts/
  abstract/playful and to dodge stock-photo slop; photography for trust/people/product; 3-D/render for
  flagship/product showcases (→ `atelier-webgl`); abstract gradient/shader for atmosphere.
- **Sources:** commission for a true brand set; **generate on the aesthetic** via `/codex-imagegen`
  (`-Transparent` for spot art / cut-outs) for consistency with the palette; libraries (Open Peeps, Humaaans,
  Blush, unDraw) only if restyled to one palette — raw unDraw is a recognizable AI-era tell.
- **Avoid:** mixing illustration styles on one surface; a single restyled stock illustration with nothing
  else committed; corporate-Memphis "big-hand" clip-art.

## Imagery — art-direction & treatment (not just "an image")
Generating an image is `atelier-components`' job; *directing* it is yours. A page with a faked text-on-gradient
"hero" or raw stock is slop; art-directed imagery is an "expensive" lever.
- **Art-direct every asset:** subject, **palette-on-aesthetic**, lighting, composition, negative space (for
  text), and crop/aspect for the slot. Write that into the codex-imagegen prompt; don't accept defaults.
- **Treatment as a system** (so all imagery feels like one brand): grade/duotone photos toward the palette,
  add the house **grain** (see the Grain aesthetic + `atelier-foundations`), or a **dither/halftone** pass for
  editorial/print-heritage (see the Dithering aesthetic) — applied consistently, not per-image whim.
- **Text-over-image always needs a scrim/treatment** for contrast (gradient overlay, darken, or a color wash) —
  decide it here; it's both a craft and an a11y requirement.
- **OG / social card + favicon are brand artifacts**, not afterthoughts: a designed `og:image` (on the
  aesthetic, with the logo + a headline) controls how every shared link looks; a real favicon/app-icon set
  (not the framework default) is part of the first impression. Spec them in the Direction Doc.
- **Avoid:** generic stock people pointing at laptops; mismatched photo treatments across sections; div-faked
  "screenshots" (an explicit Tell — use a real shot or a generated image, per `atelier-components`).

## Carry into the Direction Doc
Add a **Visual assets** line: the icon set + style, the illustration voice (or "none"), the imagery medium +
treatment, and the OG/favicon intent. That single decision keeps icons, illustration, and imagery coherent
across the whole build.
