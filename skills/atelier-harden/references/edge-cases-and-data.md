# Edge cases & real-data stress — the catalogue

Replace seed data with these and check every breakpoint. The goal: nothing the user can do, and nothing
the data can be, breaks layout, blanks the screen, or loses work.

## Collections (lists, grids, tables)

| Shape | What to build |
|---|---|
| **Zero** | A real empty state — onboarding moment + CTA, never a blank panel. (Copy: `atelier-copy`.) |
| **One** | Layout still reads intentional (a 1-item grid shouldn't look broken). |
| **A few (2-5)** | The common case; check alignment/rhythm. |
| **Many (100s-1000s)** | Pagination, infinite scroll, or **virtualization** (`@tanstack/react-virtual`). A 1,500-node DOM list tanks INP and scroll. |
| **Loading** | Skeleton at *final* dimensions (reserve space → no CLS). `atelier-motion` builds it. |
| **Partial / stale** | Some rows loaded, more pending; degraded permissions; offline cache. Show the seam honestly. |

## Strings

- **Long, unbroken:** a 60-char name, an email, a URL, an ID with no spaces. Needs `overflow-wrap: anywhere`
  or `hyphens: auto`, and `min-width: 0` on flex/grid children.
- **Missing / null / undefined:** render a sensible placeholder or omit the row — never `"undefined"`,
  `"null"`, or `"NaN"` on screen.
- **Emoji & combining marks:** don't byte-slice strings for truncation (breaks grapheme clusters).
- **User-generated content:** escape it (XSS); assume it contains `<`, `&`, quotes, newlines, RTL marks.
- **Whitespace-only / leading-trailing spaces:** trim before length checks and "empty" checks.

## Truncation recipes

```css
/* single line */
.truncate { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; min-inline-size: 0; }

/* multi-line clamp */
.clamp-2 { display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; }

/* the flex/grid fix that actually enables the above inside a row */
.row > * { min-inline-size: 0; }   /* default min-width:auto refuses to shrink → overflow */

/* long unbroken tokens */
.wrap-anywhere { overflow-wrap: anywhere; hyphens: auto; }
```

Always pair a clipped label with a `title` (or tooltip) so the full value is still reachable.

## Numbers & dates

- **Magnitude:** very large (`1,234,567` — needs grouping + maybe compact notation `1.2M`), zero, negative,
  fractional, currency with the right minor-unit precision.
- **Format with `Intl`, not string math:** `Intl.NumberFormat(locale, {notation:'compact'})`,
  `Intl.DateTimeFormat`, `Intl.RelativeTimeFormat`. (Locale wiring → `references/i18n-and-rtl.md`.)
- **Tabular figures** for any aligned column (`font-variant-numeric: tabular-nums`) — `atelier-typography`.
- **Dates:** far past / far future, missing timestamps, timezones, "just now" vs absolute, invalid dates.
- **No fake precision** — `92.4%`, `4.1×` invented for looks is a copy Tell (`atelier-copy`); use real or
  labelled-mock numbers.

## Media

- **Broken image:** real `onerror` fallback (placeholder block or initials), not a broken-image icon.
- **Slow image:** width/height or `aspect-ratio` reserved so it doesn't shove content on load (CLS).
- **Missing avatar:** initials-on-tinted-bg fallback.
- **Wrong aspect ratio:** `object-fit: cover` + a fixed box, so an off-ratio upload doesn't distort the grid.

## The pass

Walk each screen with worst-case data at **mobile, tablet, desktop**. If anything overflows, clips
critical content, blanks, or shows a raw `null`/`undefined`/broken-image — it's a finding. Fix the layout
or the state, not the data.
