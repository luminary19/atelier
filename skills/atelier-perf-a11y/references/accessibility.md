# Accessibility — WCAG 2.2 AA

Target **WCAG 2.2 AA**. (WCAG 3.0 is years off; **APCA** is better for dark-mode contrast but not yet a
conformance standard — design with it, certify with 2.x.)

## prefers-reduced-motion (the headline for animated builds)
Critical for vestibular disorders (motion → nausea/dizziness), migraine, attention sensitivity. Default-
safe pattern = opt INTO motion:
```css
.card { /* static by default */ }
@media (prefers-reduced-motion: no-preference) {
  .card { transition: transform .3s var(--ease-out); }
}
/* OR, if you animate by default, override: */
@media (prefers-reduced-motion: reduce) {
  *, *::before, *::after {
    animation-duration: .01ms !important; animation-iteration-count: 1 !important;
    transition-duration: .01ms !important; scroll-behavior: auto !important;
  }
}
```
JS / Motion / GSAP / canvas:
```js
const mq = matchMedia("(prefers-reduced-motion: reduce)");
function apply() { if (mq.matches) {/* skip parallax, instant transitions, no Lenis */} else {/* full */} }
apply(); mq.addEventListener("change", apply);
```
**Reduce, don't blanket-disable:** keep meaning-bearing motion as opacity fades / shortened durations;
remove large movement (parallax, big slides/zoom, scroll-jack, marquees, springy overshoot). Provide
non-motion signifiers so no info is lost. (WCAG 2.3.3.)

## Semantic HTML & ARIA
- **First rule of ARIA: don't use ARIA if native HTML gives the semantics + behavior.** `<button>`,
  `<a href>`, `<nav>`, `<input>`, `<dialog>` come with focus + keyboard + roles free; a `<div role="button">`
  makes you reimplement all of it (and usually get it wrong).
- **Landmarks:** `<header> <nav> <main>` (one) `<aside> <footer>`; let SR users jump between regions.
- **Headings:** logical, non-skipping (`h1→h2→h3`), one `h1`; structure not size (style with CSS).
- **Accessible names:** every interactive element needs one (visible label / `aria-label` / `aria-labelledby`
  / `alt`). Icon-only buttons MUST have one. Don't let `aria-label` contradict visible text.

## Focus & keyboard
- **Never `outline: none` without a replacement** (fails 2.4.7).
```css
:focus-visible { outline: 3px solid var(--ring); outline-offset: 2px; }
:focus:not(:focus-visible) { outline: none; }
```
- Everything operable by pointer must be operable by keyboard; visible focus follows a logical order;
  avoid positive `tabindex`.
- **Modals:** move focus in, **trap** Tab/Shift+Tab, close on `Esc`, **restore focus to the trigger** on
  close. Prefer native `<dialog>` + `showModal()` (trapping + Esc + inert background + top layer free).
- **Skip link** as the first focusable element → `#main`.
- **Focus Not Obscured (2.4.11):** sticky headers must not cover the focused element — use `scroll-margin`/
  `scroll-padding`.

## WCAG 2.2 new criteria (the load-bearing ones)
- **Target Size ≥ 24×24 CSS px** (2.5.8) — or 24px spacing. Exceptions: inline links in text, equivalent
  larger target, UA-default styling.
- **Dragging Movements** (2.5.7) — any drag has a single-pointer (tap/click) alternative.
- **Accessible Authentication** (3.3.8) — no cognitive-function test; allow paste + password managers.
- **Focus Appearance** (2.4.13, AAA) — informs how thick/contrasty the focus ring should be.

## Color & contrast
Text ≥ **4.5:1** (large ≥ 3:1); UI components/icons/focus ≥ **3:1** (1.4.11). **Never rely on color
alone** (1.4.1) — pair with text/icon/pattern (errors, required fields, chart series, in-text links).

## Screen readers & dynamic content
- Browser builds an **accessibility tree** (role + name + state) from the DOM. Bad semantics → unusable tree.
- `alt`: describe purpose for informative images; **`alt=""`** (present, empty) for decorative; long
  description nearby for complex charts.
- **`aria-live`:** `polite` (status/results/toasts), `assertive` (urgent errors). Region must exist before
  it updates, or use native `role="status"`/`role="alert"`.
- **`<canvas>`/WebGL are invisible to AT** — provide a DOM/table/text equivalent or focusable labeled
  controls. Never put essential info only in canvas. (See `atelier-webgl`.)

## Motion-specific a11y
- **Pause/Stop/Hide (2.2.2):** any auto motion/blink/scroll > 5s alongside other content needs a
  pause/stop/hide control (carousels, animated backgrounds, autoplay, marquees, looping heroes).
- **No flashing > 3×/sec** (2.3.1/2.3.2) — seizure risk. Hard ceiling; never strobe.
- **Parallax / scroll-jacking** are top vestibular triggers — gate behind `no-preference`, keep magnitudes
  small, never hijack scroll position, keep keyboard scroll working.
