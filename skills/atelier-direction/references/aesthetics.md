# Aesthetics catalog

The 20 named looks — your search vocabulary and your spine. Each: **signature** (what the eye sees) ·
**recipe** (the concrete technique) · **examples** · **when** · **avoid** (the cheap version). Pick one,
or a deliberate pairing. The meta-rule for all: *execute the system, not the surface.*

## Contents
- Premium / clean: Dark-tech · Swiss/International · Editorial · Bento · Flat/Material/Material-You
- Surface / material: Glassmorphism · Skeuomorphism(modern) · Claymorphism · Neumorphism
- Expressive: Brutalism/Neo-brutalism · Maximalism · Anti-design
- Atmosphere: Aurora/Mesh gradients · Grain/Noise · Liquid/Metaball · Dithering/Halftone
- Retro/genre: Y2K/Frutiger Aero · Vaporwave/Synthwave · Cyberpunk/HUD · Kinetic typography

---

## Dark-tech (Linear / Vercel / Raycast)
- **Signature:** near-black charcoal canvas, elevation by lighter surfaces, one desaturated accent, sparse radial glow, hairline borders. Calm, engineered, expensive.
- **Recipe:** base `oklch(0.16–0.22 …)` not `#000`; surfaces step lighter via `rgba(255,255,255,.03→.06→.09)`; accent desaturated ~10–15%; text off-white `L≈0.92`; large soft `radial-gradient` glow behind hero; grain overlay.
- **When:** premium SaaS, dev tools, infra, B2B, long-session/low-light apps. The default premium choice.
- **Avoid:** pure `#000` + grey low-contrast text; muddy shadows faking elevation; **purple→blue gradient + frosted glass card** (the #1 slop tell); glowing everything.

## Swiss / International Typographic Style
- **Signature:** rigorous grid, flush-left grotesque on a baseline, asymmetric balance, active whitespace, black/white + one accent. The foundation of "clean."
- **Recipe:** real `repeat(12,1fr)` column grid + baseline-multiple spacing; Helvetica/Inter/Suisse/Söhne; ragged-right never justified; tight controlled tracking; strong size hierarchy.
- **When:** editorial, cultural, finance/legal authority, portfolios, info-dense layouts.
- **Avoid:** Helvetica + a red square but **no actual grid**; centered everything (Swiss is asymmetric); "minimal" as an excuse for empty pages.

## Editorial / Magazine
- **Signature:** oversized display type as graphic element, dramatic scale contrast, whitespace, pull quotes, drop caps, serif+sans, broken grid.
- **Recipe:** display `clamp(2.5rem,8vw,7rem); line-height:.95; letter-spacing:-.02em`; body `max-width:65ch; line-height:1.6`; drop cap via `::first-letter`; edge-bleed images, side-column captions.
- **When:** long-form, blogs/docs, brand storytelling, portfolios, fashion/culture/restaurant.
- **Avoid:** Playfair Display + centered headline + stock photo + no hierarchy (blog-template slop).

## Bento grids
- **Signature:** modular rounded tiles of *different* sizes, one hero cell; tight gaps; one idea per cell.
- **Recipe:** CSS Grid + spans; `gap:12px`; consistent `border-radius:~18px`; surface `#f5f5f7`/`#1a1a1a`; **never empty cells**; one clear hero cell (`grid-column/row: span 2`).
- **When:** feature overviews, marketing, dashboards, "what I do."
- **Avoid:** uniform equal boxes (kills hierarchy — the whole point), cards-in-cards, random spans.

## Flat / Material / Material You
- **Signature:** solid fills; Material adds paper elevation; Material You re-tints the whole UI from a seed color via tonal surface tint.
- **Recipe:** dynamic color from one seed (HCT → tonal palettes → role tokens); **tonal elevation** (semi-transparent primary overlay) over heavy shadows; M3 type/shape scales; 48dp targets.
- **When:** Android, cross-platform, dashboards, per-user theming.
- **Avoid:** generic indigo + oversized shadows + default Roboto + random FABs.

## Glassmorphism
- **Signature:** frosted translucent panels with a bright edge rim over a colorful backdrop.
- **Recipe:** `background:rgba(255,255,255,.10); backdrop-filter:blur(12px) saturate(160%); border:1px solid rgba(255,255,255,.18)`. Blur 8–15px. **`backdrop-filter` not `filter`**; never inside `overflow:hidden`; needs a busy backdrop.
- **When:** overlays, nav bars, modals, HUD controls over imagery/video. One or two surfaces max.
- **Avoid:** frosted-purple card on everything, no edge light, glass over a flat color (looks grey).

## Skeuomorphism (modern "rich material")
- **Signature:** real materials — liquid glass that refracts, specular edge highlights, context-aware legibility (Apple Liquid Glass, Vision Pro).
- **Recipe:** glass + `inset` specular rims (`inset 0 1px 1px rgba(255,255,255,.6)`) + SVG `feDisplacementMap` refraction + pointer/tilt parallax; always solve contrast.
- **When:** premium consumer OS/app surfaces, media-rich, AR/spatial.
- **Avoid:** photoreal textures glued everywhere (old slop) OR a flat translucent box with no edge light (new slop).

## Claymorphism
- **Signature:** puffy toy-like 3D, big rounded corners, pastels, inflated glow.
- **Recipe:** `border-radius:30px; box-shadow:0 35px 68px rgba(tint,.42), inset 0 -8px 16px <darker>, inset 0 8px 16px rgba(255,255,255,.6)`. Outer shadow is *tinted*, never black. 2–3 pastels, sparingly.
- **When:** playful/youthful brands, kids', casual apps, creative portfolios.
- **Avoid:** pure-black shadows; balloons everywhere; enterprise/finance/data contexts.

## Neumorphism / Soft UI
- **Signature:** same-color extruded/pressed elements via dual soft shadows.
- **Recipe:** `box-shadow:10px 10px 20px <dark>, -10px -10px 20px <light>` (bg shifted ±~12% L); `inset` = pressed.
- **When:** decorative accents, a single dial/toggle. **Rarely** — it inherently fails WCAG 3:1.
- **Avoid:** using it as a system, on anything interactive that must pass contrast (which is everything real).

## Brutalism / Neo-brutalism
- **Signature:** hard borders, zero-blur offset shadows, flat saturated/pastel fills, heavy grotesque type, exposed structure.
- **Recipe:** `border:3px solid #000; box-shadow:6px 6px 0 #000; border-radius:0`; loud fills; `font-family:Archivo/Space Grotesk`; press state translates + shrinks shadow.
- **When:** portfolios, indie/dev tools, anti-corporate, fashion/culture, content-first.
- **Avoid:** the border-kit applied without intent/strong content; half-brutalism that looks like a bug. Stay usable underneath.

## Maximalism
- **Signature:** curated chaos — dense overlapping layers, clashing saturated color, eclectic type at wild scales, texture/marquees/stickers.
- **Recipe:** `mix-blend-mode` layering; 8–12 fighting hues; type 12px–30vw; `conic-gradient` rainbows; recurring motifs + one anchor element so the eye rests.
- **When:** fashion, music, art, agencies, youth/culture brands.
- **Avoid:** "minimalism + 3 bright colors + a sticker"; random emoji decoration. Commit fully.

## Anti-design
- **Signature:** deliberate convention-breaking — default styles, clashing type, broken grids, "wrong" layouts.
- **Recipe:** strip the reset; default links/controls; Times/monospace; intentional overlap + arbitrary `rotate()`; clashing color. Needs intent + strong content.
- **When:** art/culture, portfolios, indie tools, counter-cultural brands.
- **Avoid:** bolting on the neo-brutalist kit and calling it anti-design; making it actually unusable.

## Aurora / Mesh gradients
- **Signature:** soft overlapping color blobs blending into an organic field (Stripe/Linear).
- **Recipe:** CSS — stack `radial-gradient()` spotlights + `blur(60–100px)` on a *wrapper* (keep foreground sharp). SVG — blurred `<circle>`s + `feBlend`. Shader for real-time motion. **Add grain** to kill banding.
- **When:** hero sections, marketing, dark-tech backdrops, abstract brand atmosphere.
- **Avoid:** two-stop linear "mesh"; lazy purple blob behind a centered hero.

## Grain / Noise
- **Signature:** fine film-grain over flat color/gradient; analog warmth, kills banding. Often near-subliminal.
- **Recipe:** SVG `feTurbulence` (`type=fractalNoise`, `baseFrequency:.6–.9`, `numOctaves:1–3`) as a fixed overlay at **opacity .03–.08** + `mix-blend-mode:overlay`. (Full snippet in `atelier-foundations/references/dark-mode-and-depth.md`.)
- **When:** almost anything — the highest-ROI "expensive" tactic. Pair with gradients especially.
- **Avoid:** visible/too-strong grain (dirty screen); tiled PNG that repeats.

## Liquid / Fluid / Metaball
- **Signature:** gooey morphing blobs; imagery warping/refracting; refractive "liquid glass."
- **Recipe:** 2D — SVG goo filter (`feGaussianBlur` + `feColorMatrix` alpha contrast on a container). Brand — WebGL SDF metaballs (`smin`) / refractive glass (snapshot → refract UVs → specular + chromatic aberration). CSS blur is fallback only (it can't refract).
- **When:** flagship/launch, agency reels, creative/entertainment, luxury hardware.
- **Avoid:** generic purple goo behind a centered hero; warping everything (nausea); confusing glass with true refraction.

## Dithering / Halftone
- **Signature:** images/gradients as luminance-driven dot/pixel patterns; tactile, print-y, retro-digital.
- **Recipe:** CSS (`radial-gradient` dots + `mask`), SVG filters, canvas (sample luminance), or WebGL Bayer-matrix shader (real-time). Monochrome/duotone.
- **When:** editorial, music/poster, print-heritage, anti-slick texture, image treatments.
- **Avoid:** flat halftone PNG overlay at low opacity on everything; dithered body text (unreadable).

## Y2K / Frutiger Aero
- **Signature:** Y2K = chrome/holographic/blobjects; Frutiger Aero = glossy aqua + bokeh + nature photography, hopeful.
- **Recipe:** glossy button = high radius + `::before` top-half white→transparent shine + inner glow + grounded drop shadow; gradients behave like *light* (diagonal, with specular highlight). Chrome text = metallic gradient + bevel.
- **When:** nostalgia brands, eco/wellness/water/nature, retro-tech, playful consumer.
- **Avoid:** flat color + one fake gloss stripe; mixing gloss with sharp flat icons.

## Vaporwave / Synthwave / Retrowave
- **Signature:** synthwave = sincere 80s (neon grid, sunset, chrome); vaporwave = ironic/glitch/pastel + statues + katakana.
- **Recipe:** layered neon glow (white core → colored bloom via stacked `text-shadow`); perspective grid floor (`perspective(200px) rotateX(45deg)` + animated `background-position`); gradient sun.
- **When:** music (electronic), gaming, nightlife, retro-tech, creative portfolios.
- **Avoid:** flat purple→pink + one grid PNG + Orbitron; mixing vaporwave irony with synthwave sincerity.

## Cyberpunk / Sci-fi HUD
- **Signature:** near-black + neon, mono type, glitch (chromatic aberration), subtle scanlines, notched HUD frames, telemetry.
- **Recipe:** glitch = duplicate text in `::before/::after` offset cyan/magenta, clip-banded, `steps()` stutter; scanlines = `repeating-linear-gradient(0deg, transparent 0 2px, rgba(0,247,255,.07) 3px 4px)`; `clip-path:polygon()` notched corners.
- **When:** gaming, dev tools, hacker/security, sci-fi, web3, dramatic heroes.
- **Avoid:** neon-green Courier + constant glitch loop; scanlines too strong; long-form reading.

## Kinetic typography
- **Signature:** type performs — char/line reveals, horizontal scroll, weight/width morph, marquees. Type is the hero.
- **Recipe:** GSAP + ScrollTrigger + SplitText + Lenis + variable fonts; `clamp()` sizing; `transform`/`opacity` only; line masks via `overflow:hidden`. (Full recipes in atelier-typography.)
- **When:** agency/portfolio, brand campaigns, launches, fashion/culture/editorial heroes.
- **Avoid:** generic char-stagger on every heading with a default font; no reduced-motion fallback; kinetic type on checkout/forms/docs.
