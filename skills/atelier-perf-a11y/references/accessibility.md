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
GSAP builds: **`gsap.matchMedia()`** with a `"(prefers-reduced-motion: reduce)"` condition registers the
reduced variant and **auto-reverts when the user toggles the OS setting** — the idiom for GSAP/ScrollTrigger
work (full recipe in `atelier-scroll/references/lenis-scrolltrigger.md`).

**Reduce, don't blanket-disable:** keep meaning-bearing motion as opacity fades / shortened durations;
remove large movement (parallax, big slides/zoom, scroll-jack, marquees, springy overshoot). Provide
non-motion signifiers so no info is lost. (WCAG 2.3.3.)

## The other OS preference features (honor user intent = a premium signal)
All widely supported; ignoring them is itself a tell.
- **`prefers-reduced-transparency`** — drop `backdrop-filter`/translucency for solid fills. The correct
  fix for glassmorphism a11y.
- **`prefers-contrast: more`** — thicken borders, deepen text, remove low-contrast greys.
- **`forced-colors: active`** (Windows High Contrast Mode, ~93% reach) — don't fight the user's palette:
  use `system-color` keywords, keep `outline` on focus, mark meaningful images so they aren't dropped,
  verify icon-only buttons survive.
- **`prefers-color-scheme`** for dark mode.

## Semantic HTML & ARIA
- **First rule of ARIA: don't use ARIA if native HTML gives the semantics + behavior.** `<button>`,
  `<a href>`, `<nav>`, `<input>`, `<dialog>`, `<details name>` (Baseline Sep 2025 — exclusive accordion,
  zero JS) come with focus + keyboard + roles free; a `<div role="button">` makes you reimplement all of
  it (and usually get it wrong).
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
  close. Prefer native `<dialog>` + `showModal()` (trapping + Esc + inert background + top layer free);
  add **`closedby="any"`** for light-dismiss (Chrome/Edge/Firefox now, Safari catching up — keep a JS
  backdrop-click fallback). No-JS overlays/menus/popovers: **Popover API + Invoker Commands**
  (`command`/`commandfor`) get top-layer + focus + Esc for free.
- **Hand-rolled focus trap + restore** (custom drawer / cmdk / menu — when native `<dialog>` won't do):
```js
const focusableSel = 'a[href],button:not([disabled]),input,select,textarea,[tabindex]:not([tabindex="-1"])';
const prevFocus = document.activeElement;                 // remember the trigger
overlay.querySelector(focusableSel)?.focus();             // move focus in
document.querySelector("#app")?.setAttribute("inert", ""); // background non-interactive (focus + pointer)
function onKey(e){
  if (e.key === "Escape") return close();
  if (e.key !== "Tab") return;
  const f = [...overlay.querySelectorAll(focusableSel)].filter(el => el.offsetParent);
  const first = f[0], last = f.at(-1);
  if (e.shiftKey && document.activeElement === first) { e.preventDefault(); last.focus(); }
  else if (!e.shiftKey && document.activeElement === last) { e.preventDefault(); first.focus(); }
}
function close(){ document.querySelector("#app")?.removeAttribute("inert");
  overlay.removeEventListener("keydown", onKey); prevFocus?.focus(); }   // RESTORE focus to trigger
overlay.addEventListener("keydown", onKey);
```
  (Vaul / cmdk / Radix dialogs do all of this for you — hand-roll only when you must. → `atelier-components`.)
- **Skip link** as the first focusable element → `#main`.
- **Focus Not Obscured (2.4.11):** sticky headers must not cover the focused element — use `scroll-margin`/
  `scroll-padding`.

## WCAG 2.2 new criteria (the load-bearing ones)
- **Target Size ≥ 24×24 CSS px** (2.5.8) — or 24px spacing. Exceptions: inline links in text, equivalent
  larger target, UA-default styling.
- **Dragging Movements** (2.5.7) — any drag has a single-pointer (tap/click) alternative.
- **Accessible Authentication** (3.3.8) — no cognitive-function test; allow paste + password managers.
- **Focus Appearance** (2.4.13, AAA) — informs how thick/contrasty the focus ring should be.

## Reflow, zoom & text spacing (1.4.10 / 1.4.4 / 1.4.12)
- **Reflow (1.4.10):** content reflows to a **320 CSS px** width (≈400% zoom on a 1280px screen) with **no
  two-dimensional scrolling** — no horizontal scrollbar, nothing clipped. Build fluid/responsive, prefer
  logical units, avoid fixed widths > 320px; data tables and code blocks are the usual offenders (let them
  scroll *within their own region* only).
- **Resize Text (1.4.4):** text scales to **200%** without loss — keep `rem`/`em` sizing (the fluid-type
  `rem`-intercept rule) and never `px`-locked containers that clip enlarged text.
- **Text Spacing (1.4.12):** the layout must survive a user override of `line-height: 1.5`,
  `letter-spacing: .12em`, `word-spacing: .16em`, paragraph-spacing `2em` with no clipping/overlap. Don't put
  fixed heights on text containers; let them grow.

## RTL & internationalization
- Drive direction from `<html dir="rtl">` and use **logical properties** (`margin-inline`, `padding-block`,
  `inset-inline`, `text-align: start`) so the whole UI mirrors with no per-direction CSS — never physical
  `left`/`right`. Mirror direction-implying icons (arrows, chevrons, progress); don't mirror logos/media.
- Test one screen in `dir="rtl"` and at +35% string length (translations expand). (Type-side script
  fallbacks + expansion live in `atelier-typography`.)

## Color & contrast
Text ≥ **4.5:1** (large ≥ 3:1); UI components/icons/focus ≥ **3:1** (1.4.11). **Never rely on color
alone** (1.4.1) — pair with text/icon/pattern (errors, required fields, chart series, in-text links).
Dynamic/data-driven backgrounds: `color: contrast-color(var(--accent))` auto-picks readable black/white
(Baseline Apr 2026 — Chrome 147 / FF 146 / Safari 26); `@supports` a static fallback first for older engines.

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
