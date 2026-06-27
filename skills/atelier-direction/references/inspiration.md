# Inspiration: sources & how to mine a reference

Use galleries to *reverse-engineer decisions*, not to copy surfaces. When the user gives a reference,
mine it (below) before inventing anything.

## Where to look (and what each is for)
- **Awwwards** — SOTD/SOTM/SOTY; cutting-edge interaction/WebGL. Aspirational (award world), not
  production-realistic. Mine for motion, scroll choreography, signature moments.
- **Godly (godly.website)** — curated, *video* thumbnails (captures motion). Best for the motion layer.
- **Mobbin** — real app flows (onboarding, paywalls, settings, edge cases). The research tool for
  product/app/dashboard UX — use for *patterns*, not eye candy. **Ships a Mobbin MCP** (2026) that
  feeds real app screens straight to the agent — ask it instead of browsing.
- **Refero** — real product screenshots + flows; its **Refero MCP** adds a `DESIGN.md` layer (real
  product *styles*) so the agent can reason about visual direction *before* generating UI.
- **Land-book / SaaS Landing Page / Lapa Ninja** — landing & real-product layouts, hero
  patterns, pricing, conversion structure.
- **siteInspire (clean/editorial) / Minimal Gallery / Httpster / The FWA (experimental)** — curated
  showcases by temperament.
- **Typewolf** — typography in the wild; font pairings and "fonts in use." Use when picking type.
- **CodePen** — runnable technique demos (search "glassmorphism", "hover distortion", a shader name).
- **Cosmos / Savee / Are.na** — build a personal taste library over time.
- **Dribbble / Behance** — aspirational concepts; **caveat: much is non-functional design fiction.**

## Studios to study (and the technique each is known for)
- **Active Theory** — immersive WebGL/3D experiences and installations.
- **Resn** — playful, surreal, high-craft WebGL.
- **Locomotive** — polished scroll-driven sites (gave us Locomotive Scroll; Lenis is the successor).
- **Obys** — bold editorial typography + motion (Awwwards-decorated).
- **Cuberto** — fluid cursor/gooey interactions, slick micro-interactions.
- **Unseen Studio / Aristide Benoist** — refined motion + type; advanced WebGL/shaders.
- **OFF+BRAND** — Webflow shell + WebGL/Rive cinematic motion; the current Awwwards SOTY studio.
- **Codrops (tympanus)** — the tutorial engine of this whole scene; read recent posts to see what's hot.

## What's actually winning now (mid-2026)
**Awwwards Site of the Year 2025 = the official Lando Norris site by OFF+BRAND** (also SOTM/SOTD/FWA;
SOTD score 8.18). The representative award stack: **Webflow shell + WebGL/WebGPU 3D + Rive motion +
GSAP/scroll-driven cinematic transitions + Lenis smooth scroll**, on a tight 2-color system (lime
`#D2FF00` on `#111112`), 3D rotating helmets + millisecond-timed scroll choreography. **Treat SOTY as a
*tier*, not one canonical site — Awwwards crowns several annual winners.** Trend toward **faux-3D**
(image sequences / shader tricks) to dodge real-WebGL perf cost. On award sites, *motion is the product.*
On production sites, the winning formula is the opposite: bento grids, restraint, real content, speed,
accessibility, sub-400ms responsiveness.

## How to mine a reference (do this when given a URL/screenshot)
Look past the surface and extract the *decisions* you can carry over:
1. **Grid** — column count, gutters, where it breaks symmetry, the measure for body text.
2. **Type** — display vs body families, the scale ratio (how big is H1 vs body), tracking on display,
   line-height.
3. **Color** — how many colors actually carry the page; the one accent; light/dark logic; neutral tint.
4. **Space** — section padding rhythm; macro whitespace; density.
5. **Motion** — what moves, when (load/scroll/hover), how long, the easing feel; the one signature moment.
6. **Concept** — what idea is the design expressing? That's the part worth stealing.
Then translate those decisions into *your* tokens and Direction Doc — don't pixel-copy the skin.
(WebFetch the URL to inspect, or ask the user for a screenshot if it's JS-rendered/blocked.)
