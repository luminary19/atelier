# Internationalization & RTL

Even an English-only product benefits from these — they're really "don't hardcode the layout to one
exact string." Doing them up front is far cheaper than retrofitting.

## Text expansion budget

- **Plan for +30-40% length.** German, Finnish, Russian, and French run long; UI labels can nearly double.
- **Never size a control to the English label.** Let buttons/menus/labels grow; don't fix a width that
  only fits "Save". Don't truncate critical actions — truncation is for *content*, not *commands*.
- Test with a pseudo-locale (e.g. accented + padded strings) or a real long-language sample.

## Layout that mirrors: logical properties

Drive direction from `<html dir="rtl">` and use **logical properties** so the whole layout flips for free:

| Physical (avoid in flow layout) | Logical (use) |
|---|---|
| `margin-left` / `margin-right` | `margin-inline-start` / `-end` |
| `padding-top` / `padding-bottom` | `padding-block-start` / `-end` |
| `left` / `right` | `inset-inline-start` / `-end` |
| `text-align: left` | `text-align: start` |
| `border-left` | `border-inline-start` |

- Flexbox/grid already follow the inline axis — just avoid hardcoded physical offsets.
- **Mirror directional icons** (arrows, chevrons, back) for RTL; do **not** mirror logos, media controls,
  or numerals.
- Keep `min-inline-size: 0` on flex/grid children (truncation still needs it in RTL).

## Formatting: always `Intl`, never string math

```js
new Intl.NumberFormat(locale).format(1234567)                          // 1,234,567 / 1.234.567 …
new Intl.NumberFormat(locale, { style: "currency", currency }).format(x)
new Intl.NumberFormat(locale, { notation: "compact" }).format(1200000) // 1.2M / 1,2 Mio. …
new Intl.DateTimeFormat(locale, { dateStyle: "medium" }).format(date)
new Intl.RelativeTimeFormat(locale).format(-3, "day")                  // "3 days ago" localized
new Intl.PluralRules(locale).select(n)                                 // "one" | "few" | "many" | "other"
```

- **Never concatenate translated fragments** (`"You have " + n + " items"`). Languages reorder and have
  more than two plural forms. Use a full templated string per plural category with interpolation
  (ICU MessageFormat / your i18n lib's plural support).
- Numbers, dates, currencies, and lists (`Intl.ListFormat`) are all locale-shaped — never hand-format.

## Fonts & glyphs

- Declare **script-aware fallbacks** so CJK/Arabic/Cyrillic don't tofu: a stack that includes a font with
  the needed coverage (e.g. Noto Sans family) after the Latin display face.
- Watch line-height: tall scripts (Thai, Devanagari) need more leading than Latin; don't clip with a tight
  fixed height.
- Self-host or preload the Latin subset, but ensure non-Latin content has a real fallback (`atelier-typography`
  owns loading strategy; this is about *coverage*).

## Checklist

- [ ] No control sized to its English label; +30-40% expansion survives.
- [ ] Logical properties throughout; `dir="rtl"` flips the layout cleanly; directional icons mirror.
- [ ] All numbers/dates/currency/lists via `Intl`; no concatenated translated strings; real plural rules.
- [ ] Script-aware font fallbacks declared; non-Latin sample renders without tofu or clipping.
