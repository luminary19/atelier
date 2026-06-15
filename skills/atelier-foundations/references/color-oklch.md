# Color in OKLCH

Build the whole color system in OKLCH. It's perceptually uniform (equal `L` = equal perceived
lightness across hues), hue-stable when you change L/C, and P3-capable. HSL is not — its ramps are
uneven and dark themes go muddy.

## Syntax & ranges
`oklch(L C H / a)` — **L** lightness `0–1` (perceived), **C** chroma `0 → ~0.37` (0 = gray; practical
max varies by hue/gamut), **H** hue `0–360°`, **a** alpha.

Hue anchors: red ≈25, orange ≈60, yellow ≈100, green ≈145, teal ≈180, blue ≈250, indigo ≈265,
purple ≈300, magenta ≈330.

## Build a brand ramp (50–950)
Fix `H`. Sweep `L` evenly across 11 steps. **Curve `C`** — low at the light end, peak in the mid
(steps 500–600), taper at the dark end (chroma can't survive near black/white). Example for a blue
brand (`H≈255`); tune `C` to taste and gamut:

```css
:root {
  --blue-50:  oklch(0.971 0.013 255);
  --blue-100: oklch(0.946 0.030 255);
  --blue-200: oklch(0.902 0.060 255);
  --blue-300: oklch(0.842 0.100 255);
  --blue-400: oklch(0.762 0.150 255);
  --blue-500: oklch(0.682 0.190 255);  /* mid: highest chroma */
  --blue-600: oklch(0.600 0.205 255);
  --blue-700: oklch(0.512 0.190 255);
  --blue-800: oklch(0.430 0.155 255);
  --blue-900: oklch(0.360 0.115 255);
  --blue-950: oklch(0.250 0.075 255);
}
```

## Neutrals (tinted, not pure gray)
Give grays a *tiny* chroma at the brand hue (`C ≈ 0.01–0.02`). Pure-gray reads clinical; a whisper of
tint reads designed.

```css
:root {
  --neutral-50:  oklch(0.985 0.003 255);
  --neutral-100: oklch(0.967 0.004 255);
  --neutral-200: oklch(0.922 0.006 255);
  --neutral-300: oklch(0.870 0.008 255);
  --neutral-400: oklch(0.708 0.010 255);
  --neutral-500: oklch(0.556 0.012 255);
  --neutral-600: oklch(0.439 0.012 255);
  --neutral-700: oklch(0.371 0.011 255);
  --neutral-800: oklch(0.269 0.009 255);
  --neutral-900: oklch(0.205 0.007 255);
  --neutral-950: oklch(0.145 0.006 255);
}
```

## Map ramps → semantic tokens (Radix 12-step roles)
Don't let components touch primitives. Map ramp steps to roles. The Radix 12-step model is the proven
role system:

| Step | Role | Light-mode source |
|---|---|---|
| 1 | App background | neutral-50 / white |
| 2 | Subtle background | neutral-100 |
| 3 | UI element bg (normal) | neutral-100/200 |
| 4 | UI element bg (hover) | neutral-200 |
| 5 | UI element bg (active/selected) | neutral-200/300 |
| 6 | Subtle border (cards, separators) | neutral-200/300 |
| 7 | UI border + focus ring | neutral-300 |
| 8 | Strong border / hover border | neutral-400 |
| 9 | **Solid (CTA, brand fill — the purest chroma)** | brand-500/600 |
| 10 | Solid hover | brand-600/700 |
| 11 | Low-contrast text | neutral-600 |
| 12 | High-contrast text | neutral-900/950 |

```css
:root {
  --bg:            var(--neutral-50);
  --surface:       var(--neutral-100);
  --surface-hover: var(--neutral-200);
  --border:        var(--neutral-200);
  --border-strong: var(--neutral-300);
  --ring:          var(--blue-500);
  --primary:       var(--blue-600);
  --primary-hover: var(--blue-700);
  --text:          var(--neutral-900);
  --text-muted:    var(--neutral-600);
  --danger:        oklch(0.58 0.21 25);
  --success:       oklch(0.62 0.17 150);
  --warning:       oklch(0.75 0.16 75);
}
```

## Relative color for states (keep hue/chroma locked)
```css
.btn:hover  { background: oklch(from var(--primary) calc(l - 0.06) c h); }
.btn:active { background: oklch(from var(--primary) calc(l - 0.12) c h); }
.tint       { background: oklch(from var(--primary) 0.96 0.03 h); } /* faint brand wash */
```

## P3 wide-gamut boost (optional)
```css
@media (color-gamut: p3) {
  :root { --primary: oklch(0.60 0.26 255); } /* push chroma beyond sRGB */
}
```

## Generating ramps without hand-tuning
If you'd rather not hand-place values: use **uicolors.app** (hex → 50–950), **Radix custom palette**,
or **Leonardo** (leonardocolor.io — generate by *target contrast ratio*, best for guaranteed-contrast
systems). Then convert/output in OKLCH. Always re-verify the contrast of `--primary` solid, `--text`,
and `--text-muted` against their backgrounds (WCAG 2.2 AA: 4.5:1 text, 3:1 UI; tune dark mode with APCA).

## Scheme shortcuts
- Monochromatic + 1 accent (safest premium). Analogous (±30°, calm). Complementary (180°, energetic).
  Triadic (120°, vibrant — let one lead). Split-complementary (safe contrast).
- **60-30-10:** 60% dominant/neutral, 30% secondary surfaces, 10% accent (CTAs). Keeps a clear focal point.
