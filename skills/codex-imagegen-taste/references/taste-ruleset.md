# Taste ruleset - the full design brain (reference knowledge)

This is the complete art-direction ruleset the skill reasons over when it PLANS a
comp. It is the brain; the distilled, codex-ready slice that actually rides along on
every render is `taste-preamble.md`. Read this to plan; inject the preamble to render.

Ported and adapted from the open-source design skill `imagegen-frontend-web`
(github.com/Leonxlnx/taste-skill). Reformatted to ASCII and to the Atelier house
conventions; nothing load-bearing dropped.

---

## 0. Output rule (the spine)

Generate ONE separate horizontal image PER section. Always.
- 1 section = 1 image; 4 sections = 4 images; 8 = 8; 12 = 12.
- Never combine multiple sections into one frame. Never return a single tall image
  of the whole page. Never return one "best" image and skip the rest.
- Render sequentially, one call per section, labelled "Section X of N: <name>".
- Announce the count out loud before rendering ("Generating N images, one per section").

Default section counts when the brief is silent:
- "hero" -> 1; "landing page" / "product page" / "portfolio" -> 6;
  "full website" / "site template" / "marketing site" -> 8.

## 1. Baseline dials (adapt from the brief; the brief always overrides)

- DESIGN_VARIANCE 8 (1 rigid/symmetric -> 10 artsy/asymmetric)
- VISUAL_DENSITY 4 (1 airy -> 10 packed)
- ART_DIRECTION 8 (1 safe commercial -> 10 bold statement)
- IMPLEMENTATION_CLARITY 9 (1 loose moodboard -> 10 very codeable)
- IMAGE_USAGE_PRIORITY 9 (1 typographic -> 10 image-led)
- SPACING_GENEROSITY 8 (1 tight -> 10 very breathable)
- LAYOUT_VARIATION 8 (1 same anchor repeats -> 10 bold variety)
- CONVERSION_DISCIPLINE 8 (1 pure art -> 10 clear funnel + premium balance)

Conditional steering: "clean" -> lower density, higher clarity. "crazy creative" ->
raise variance + art direction. "premium SaaS" -> clarity high, art direction
controlled. "minimalist/swiss/typography-only" -> Mini hero, solid surfaces, skip
full-bleed, stacked-center, lots of negative space. "editorial/magazine/fashion" ->
Mid or Giant hero, duotone/atmospheric image, off-grid, strong type contrast.
"cinematic/luxury/bold" -> Giant hero, full-bleed image + tonal overlay, palette-matched
cinematic grade. "SaaS/dashboard/fintech/infra" -> Mid hero, solid + inline asset, trust
framing, clarity up. "agency/studio/portfolio" -> Giant OR Mini (decisive), bold
background variety. "e-commerce/shop" -> Mid hero, product-led full-bleed, CTAs
unmistakable. Never force backgrounds/gradients where the brief asks restraint; never
strip atmosphere where the brief asks for it.

## 2. The combinatorial variation engine (pick, then commit)

Internally choose one option from each category and execute it cleanly; do not mash
everything together.

Theme paradigm (1): Pristine Light Mode | Deep Dark Mode | Bold Studio Solid (oxblood,
royal blue, forest, vermilion, emerald) | Quiet Premium Neutral (bone, sand, taupe,
stone, smoke).

Background character (1): subtle technical grid/dotted field | pure solid + soft
ambient gradient depth | full-bleed cinematic imagery with contrast control | quiet
textured paper/material surface.

Typography character (1): Satoshi-like clean grotesk | Neue-Montreal-like refined
grotesk | Cabinet/Clash-like expressive display | Monument-like compressed statement |
elegant editorial serif + sans pairing | Swiss rational sans with strong hierarchy.

Hero architecture (1): Cinematic Centered Minimalist | Asymmetric Split | Floating
Polaroid Scatter | Inline Typography Behemoth | Editorial Offset | Massive Image-First
with restrained text.

Section system (1 dominant): strict modular bento | alternating editorial blocks |
poster-like stacked storytelling | gallery-led visual cadence | Swiss grid discipline |
asymmetric premium marketing flow.

Signature component set (pick exactly 4 unique): Diagonal Staggered Square Masonry |
3D Cascading Card Deck | Hover-Accordion Slice Layout | Pristine Gapless Bento Grid |
Infinite Brand Marquee Strip | Turning Polaroid Arc | Vertical Rhythm Lines | Off-Grid
Editorial Layout | Product UI Panel Stack | Split Testimonial Quote Wall | Oversized
Metrics Strip | Layered Image Crop Frames.

Motion-implied language (pick exactly 2, conveyed through static composition):
scrubbing text reveal | pinned narrative | staggered float-up | parallax image drift |
smooth accordion expansion | cinematic fade-through.

Composition anchor (per section; at least 3 different anchors must appear across the
site; vary the hero off the AI default): centered statement | top-left lead +
bottom-right support | bottom-left text over image | bottom-right CTA cluster |
left-third caption + right two-thirds visual (use sparingly, never twice in a row) |
right-third caption + left two-thirds visual | centered-low (text in lower 40% over
image) | off-grid editorial offset | stacked center (ultra minimalist) | image-as-canvas
with text in a clean safe area.

Background mode (per section; vary across the page; backgrounds are a primary tool,
not a risk): solid surface + inline asset | subtle texture/paper/grid | full-bleed image
+ tonal overlay (text stays readable) | editorial side-image (50/50, 60/40, 40/60,
invertible) | image-as-entire-visual + overlaid text | flat color block + small detail
crop | cinematic tonal gradient (palette-matched, low chroma) | atmospheric graded photo
(single-tone) | duotone treated image | soft radial vignette + product crop | micro-noise
gradient over solid | color-blocked diptych.

CTA variation (fit each section; vary at least once across the site; primary action
always unmistakable): classic primary pill | outline/ghost | underlined inline link with
arrow | banner-style full-width | oversized headline + tiny CTA hint | CTA as caption
under a strong visual.

Hero scale (per page; pick one, match brand mood): Giant Statement | Mid Editorial |
Mini Minimalist (tiny logo + short statement + thin CTA, lots of negative space - Mini
means confident restraint, not weakness).

Narrative / concept spine (pick 1 and thread it through visuals + short copy):
artifact/collectible | journey/pilgrimage | tool/precision instrument | living
system/garden | stage/spotlight | archive/dossier.

Second-read moment (pick exactly 1, place once across the page, legible not gimmicky):
asymmetric bleed that respects hierarchy | one oversized numeral/punctuation serving
structure | a single unexpected material switch | a narrow vertical side-rail editorial
note | a macro crop carrying brand color.

## 3. Hero minimalism

Hero = a strong opening scene. Short, powerful headline (usually 5-10 words, never a
paragraph). Generous negative space, strong scale contrast. Do not overcrowd the first
viewport with pills, fake stats, badges, tiny logos. Before drafting a hero, ask: "am I
defaulting to text-left / image-right out of habit?" - if so, pick a different anchor
unless the brand truly requires the classic. Avoid gradient text and 6-line headings.

## 4. Anti-AI-slop catalogue (ban unless explicitly requested)

Layout: endless centered sections; identical repeated card rows; cloned
left-text/right-image; lifeless symmetry; fake complexity without hierarchy; empty
decorative space.
Visual: purple/blue (or pink/orange) AI gradients; glow halos; floating spheres/blobs;
unjustified stacked glassmorphism; random futuristic detail; over-rendered noise.
Typography: giant heading + weak tiny subcopy; too many font moods; awkward line breaks;
lazy all-caps; gradient headline as a "premium" shortcut.
Content: empty copy vibes (Unleash, Elevate, Revolutionize, Next-gen, Seamless, Powerful
solution, Transformative platform); fake brand wordmarks (Acme, Nexus, Flowbit,
Quantumly, NovaCore). Use short, believable copy.
Density: over-packed sections; card overload; tiny gaps between major sections;
wall-of-content.
Carousel/KPI: infinite mosquito-logo "trusted by" strips; three identical stat columns
and fake chart dashboards unless KPIs were requested.

## 5. Color & material

One controlled palette across the whole site: 1 primary (anchor) + 1 secondary +
1 accent (sparingly, for CTA/highlight) + a neutral scale (background, surface, text,
hairline). Section mood shifts REUSE that palette - no per-section theme swap. Full-bleed
images tonally match the palette and use overlays so text stays readable; the brand accent
stays constant. Gradients are allowed and encouraged when professional: low-chroma
palette-matched tonal grades, single-hue atmospheric grades behind hero photography, soft
vignettes, noise-textured depth, editorial color washes. Banned: rainbow/mesh blobs,
purple-to-blue and pink-to-orange defaults, purposeless neon/glow, gradient text. Add
materiality (paper, glass, brushed metal, matte, editorial photo grade) only where it
keeps structure readable.

## 6. Default section packs

4-pack: Hero; Features; Social proof/testimonial; CTA.
8-pack: Hero; Trust bar; Features; Product showcase; Benefits/use cases; Testimonials;
Pricing; CTA.
12-pack: Hero; Trust bar; Feature grid; Product preview; Problem/solution; Benefits;
Workflow; Metrics/proof/integration; Testimonials; Pricing; FAQ; CTA + footer.

Vary section ambition deliberately across the page: some large/art-directed, some
mini/minimalist, some medium editorial - a paced scrollscape, not uniform slabs. Keep
spacing between sections even and controlled even as section heights vary.

## 7. Multi-image continuity (because every section is its own image)

Across all per-section frames enforce ONE brand world: same palette + accent logic, same
type family + scale logic, same CTA family (style varies, identity does not), same border-
radius language, same image treatment (grade, framing, material), same tonal voice in any
short copy. Variation is allowed only in: composition anchor, background mode, section
size/density, and which second-read moment appears. Anything that breaks brand recall is
over-variation. This is what the wrapper's LOCKED STYLE SPEC enforces mechanically -
thread the same spec through every section call.

**Variety caps (mechanical).** Reject the set if the same composition anchor repeats >2
sections in a row, the same background mode repeats >3 sections in a row, or every section
is inline-asset (no full-bleed background ever appears) on a non-minimalist brief. A
non-minimalist multi-section site needs at least one full-bleed / duotone / atmospheric
background and at least one mini-minimalist section. For minimalist / swiss / typography-only
briefs this cap is suspended - restraint is the design.

## 8. Clarity check (run before declaring done)

1 hierarchy obvious? 2 hero clean? 3 visually distinctive? 4 free of AI tells? 5 premium
not template? 6 codeable from the image? 7 do the frames clearly belong together? 8 imagery
used strongly with variation? 9 does the page breathe? 10 even spacing between sections?
11 creativity intentional (concept spine visible, not cluttered)? 12 smaller sections still
have enough surrounding space? 13 exactly one disciplined second-read moment? 14 composition
varied across sections (anchors + background modes mixed)? 15 hero scale chosen and executed
cleanly? 16 clear conversion path (hook -> proof -> action) even in artistic sites? 17 palette
consistent across all images? 18 each image horizontal and one-section-only? 19 total images =
number of sections (never fewer)? 20 hero NOT defaulting to left-text/right-image out of habit?

If any fail, refine before output. If the count is wrong, regenerate the missing sections.

## 9. Response behaviour (the per-job loop)

1 infer site type + primary conversion goal. 2 infer section count (defaults in section 0).
3 announce the count out loud. 4 lock the hero scale + the combinatorial combination + ONE
palette/type/CTA/treatment/radius spec. 5 for each section pick a composition anchor +
background mode + CTA variation, varying across sections. 6 render one horizontal image per
section via the wrapper, labelled "Section X of N: <name>", threading the SAME style spec.
7 keep spacing generous and even. 8 run the clarity check. 9 do not stop early, summarise
instead of rendering, or return only one image. Do not ask unnecessary follow-ups when a
strong interpretation is possible.
