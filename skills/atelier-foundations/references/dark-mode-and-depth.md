# Dark mode & depth

## Dark mode as a semantic remap
Don't build a second palette — remap the semantic tokens. This is why the three-tier architecture
matters. Two ways to author the remap: a `[data-theme="dark"]` (or `.dark`) block as below, or inline
per-token with **`light-dark(<light>, <dark>)`** (Baseline; set `color-scheme: light dark` on `:root`)
so each token follows the theme toggle with no media query. Either way the dark rules below hold.

```css
[data-theme="dark"] {
  --bg:            oklch(0.180 0.006 255);  /* charcoal, NOT #000 */
  --surface:       oklch(0.215 0.007 255);  /* elevation by lightness... */
  --surface-hover: oklch(0.250 0.008 255);  /* ...each level steps lighter */
  --border:        oklch(1 0 0 / 0.09);     /* translucent white hairlines */
  --border-strong: oklch(1 0 0 / 0.14);
  --ring:          oklch(0.70 0.14 255);
  --primary:       oklch(0.68 0.17 255);    /* desaturated ~10–15% vs light */
  --primary-hover: oklch(0.74 0.16 255);
  --text:          oklch(0.92 0.004 255);   /* off-white, ~L .92 not pure white */
  --text-muted:    oklch(0.70 0.010 255);
}
```

### The dark-mode rules
- **Base is charcoal/ink, never `#000`.** Pure black causes text halation (the text vibrates) and
  leaves no headroom to show elevation. Aim `L ≈ 0.16–0.22`.
- **Elevation by lightness, not shadow.** On dark surfaces shadows are nearly invisible — raised
  surfaces get *lighter* (stepped L, or stacked `rgba(255,255,255,.03→.06→.09)` overlays that
  auto-compound when nested).
- **Desaturate accents ~10–15%.** Full-saturation brand colors buzz/neon on dark. Drop chroma, nudge L up.
- **Text:** off-white (~`L 0.92`), muted ~`L 0.70`. Keep ≥4.5:1; verify with **APCA** (it's far more
  accurate than WCAG 2 ratios on dark — WCAG 2 wrongly passes muddy near-black pairs).
- **Borders:** translucent white hairlines read cleaner than solid grays.

## Beyond dark mode — multi-theme from one token layer
Dark mode is just the first *remap*. The same tier-2 semantic layer gives you any number of themes — the
rule never changes: **components read semantics; a theme is a block that re-points them.**
- **Multiple brands / sub-brands:** one `[data-brand="x"]` block per brand re-pointing `--primary` /
  `--ring` / neutrals (and maybe `--radius`). Components don't change.
- **High-contrast theme (first-class, not an afterthought):** a `[data-theme="hc"]` (or `@media
  (prefers-contrast: more)`) variant that thickens borders, drops low-contrast greys, and pushes text to
  ramp step 12. Honor `forced-colors: active` (Windows HCM) *separately* — there you cede color to the OS
  (`system-color` keywords), not restyle. (Both gated by `atelier-perf-a11y`.)
- **User-customizable accent:** expose ONE hue knob, derive the rest. Take `--brand-h` from the user, build
  `--primary: oklch(0.60 0.16 var(--brand-h))`, and let `oklch(from …)` / `color-mix()` generate every
  state — one slider re-themes the whole app with guaranteed-even ramps. Pair with
  `contrast-color(var(--primary))` for readable button text on any chosen hue.

Author with `light-dark()` for the light/dark axis and data-attributes for the brand/contrast axes; the two
compose. One source of truth per token — never fork a component per theme.

## Translucent elevation overlay (compounds when nested)
```css
[data-theme="dark"] .elevated { background: oklch(1 0 0 / 0.04); }   /* card */
[data-theme="dark"] .elevated .elevated { background: oklch(1 0 0 / 0.04); } /* nested → reads lighter */
```

## Depth in light mode — layered soft shadows
Use two-part shadows (ambient + direct) at low opacity, tied to an elevation scale, so cards feel lifted
without looking heavy. (Tokens in `tokens-and-output.md`.) Light direction stays consistent (top-down).

## Grain — the highest-ROI "expensive" tactic
A fine SVG `feTurbulence` overlay kills gradient banding and adds analog depth. Self-generating (no
asset), tiles seamlessly, scalable. Keep it a whisper.

```css
.grain::after {
  content: ""; position: fixed; inset: 0; pointer-events: none; z-index: 50;
  opacity: 0.05; mix-blend-mode: overlay;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg'%3E%3Cfilter id='n'%3E%3CfeTurbulence type='fractalNoise' baseFrequency='0.8' numOctaves='3' stitchTiles='stitch'/%3E%3C/filter%3E%3Crect width='100%25' height='100%25' filter='url(%23n)'/%3E%3C/svg%3E");
}
```
- `type=fractalNoise` = soft grain (use this); `turbulence` = liquid ripples.
- `baseFrequency` 0.6–0.9 = fine grain (higher = finer). `numOctaves` 1–3.
- **Opacity 0.03–0.08**, `mix-blend-mode: overlay` (or `soft-light`). Stronger than that = dirty screen.
- The famous combo: a smooth gradient + this overlay = "grainy gradient," no banding. Animate the
  filter seed/position for a film-grain shimmer (respect `prefers-reduced-motion`).

## Grainy gradient (banding-free hero backdrop)
```css
.hero {
  background:
    radial-gradient(at 20% 30%, oklch(0.55 0.18 255 / .6) 0, transparent 50%),
    radial-gradient(at 80% 20%, oklch(0.50 0.16 280 / .5) 0, transparent 50%),
    var(--bg);
  position: relative; isolation: isolate;
}
/* + the .grain overlay above, or a blurred wrapper for full aurora softness */
```
Interpolate multi-stop gradients in OKLCH for clean midpoints: `linear-gradient(in oklch, A, B)`
(`in oklch longer hue` for rainbow sweeps).

- **Animate gradients with `@property`, not JS.** Plain `--vars` parse as strings and can't
  interpolate; register a type to animate them: `@property --angle { syntax:"<angle>"; inherits:false;
  initial-value:0deg }` then `@keyframes { to { --angle:360deg } }` animates a `conic-gradient(from
  var(--angle) …)`; `syntax:"<color>"` animates gradient color-stops. Compositor-friendly animated
  gradient heroes/loaders with zero JS (respect `prefers-reduced-motion`). Baseline since Jul 2024 —
  and it's *why* Tailwind v4 requires `@property` + OKLCH-capable browsers.
