# Composition models & Gestalt

## Composition models (escape the centered stack)
- **Rule of thirds** — place focal elements on the power points (intersections of a 3×3 grid), not dead
  center. Good general balance for heroes and focal subjects.
- **Golden ratio (≈1.618)** — proportion sections/columns/type by 1.618 for organic harmony (e.g.
  content:sidebar ≈ 1.618:1). Combines well with thirds.
- **F-pattern** — how people scan *text-dense* pages (two horizontal sweeps near top, then down the
  left). Articles, search results, docs, feeds → key info top + left; front-load headings/links.
- **Z-pattern** — how people scan *sparse, visual* pages (TL → TR → diagonal → BR). Landing/hero with
  little text → logo TL, nav/CTA TR, hero center, primary CTA BR.
- **Asymmetry / broken grid** — offset, overlap, uneven columns, edge-bleed for energy and an editorial
  feel. **Balance it by visual weight:** a large element answered by whitespace or a cluster of small
  ones — never random. This is what separates "art-directed" from "broken."
- Heuristic: reading-dense → F; scanning-light → Z; want energy/premium-editorial → controlled asymmetry.

## Visual hierarchy — direct the eye
Five levers, combined: **size** (bigger = more important), **weight** (bold pulls focus), **color**
(saturated/accent advances; muted recedes — the single accent = the primary CTA), **position** (top/left
and optical center seen first), **contrast** (difference in any property is what the eye detects;
whitespace/isolation is contrast too). Aim for a clear 1→2→3 reading order and **one dominant focal
point per view**. De-emphasize secondary text with a lighter token — don't just enlarge the primary.

## Gestalt principles → concrete UI
The mind perceives the whole before the parts. Apply:
- **Proximity** — close things read as a group. Form label beside its input; cluster card meta; make
  inter-section spacing larger than intra-section. The cheapest grouping tool — beats boxes/borders.
- **Similarity** — like-looking = same function. All primary buttons one style; all links one style;
  one icon set. Inconsistent styling implies different behavior (confusing).
- **Common region** — a shared boundary/background groups items even when far apart (cards, fieldsets,
  colored section bands, table row striping). Stronger grouping than proximity alone — but don't
  box-everything (whitespace grouping is lighter and reads more premium).
- **Continuity** — the eye follows smooth lines. Aligned form fields and grid lines guide the scan; a
  flowing path can lead to the CTA; a partially-visible card edge implies "more, scroll."
- **Closure** — the mind completes shapes (logos with gaps, loading skeletons, peeking carousel item).
- **Figure / ground** — foreground vs background. Modal + dimmed scrim; elevation/shadow for dropdowns;
  hero text over imagery needs an overlay/scrim to stay legible as "figure."
- **Focal point** — the highest-contrast element wins attention first → make that the one accent CTA.

## Putting it together (a section)
1. Decide the scan model (F or Z) from content density. 2. Establish one focal point via hierarchy
levers. 3. Group with proximity/common-region so structure is obvious pre-reading. 4. Break symmetry
intentionally, balanced by weight. 5. Let whitespace do the separating before you reach for borders.
