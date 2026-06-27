# Live verification playbook (the main thread, in a real browser)

Static review finds *candidate* problems; the running app is the source of truth. Do this yourself (not in
subagents — they'd fight over one browser + the server). Examples use the Playwright MCP, but any
browser-driver + DevTools works. **Confirm or refute every finding here, and catch what static missed.**

## 0. Serve it
ES modules / fetch need HTTP, not `file://`. For a vanilla build, serve with **no-cache** so edits show on
reload:
```python
# serve.py — python serve.py  → http://127.0.0.1:8124
import http.server, socketserver
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store"); super().end_headers()
socketserver.TCPServer.allow_reuse_address = True
socketserver.TCPServer(("127.0.0.1", 8124), H).serve_forever()
```
Browser **module cache** will otherwise serve stale JS after an edit — the no-cache server (or a fresh
port) is the reliable fix. For framework apps, use the dev server.

## 1. Load + settle + console
Navigate, then wait for the loader/fonts/lazy work to settle before reading anything:
```js
() => new Promise(res => setTimeout(() => res({
  ready: document.readyState,
  theme: document.documentElement.getAttribute('data-theme'),
  fonts: document.fonts ? document.fonts.status : 'n/a',
  loaderGone: !document.querySelector('#loader') || getComputedStyle(document.querySelector('#loader')).display === 'none',
}), 3500))
```
**Console errors AND warnings are findings.** A missing favicon, a deprecation warning, a 404 — log them.
Target: **0 errors, 0 warnings** for award-grade.

## 2. Contrast — trust pixels, not strings
`getComputedStyle().color` returns `oklch()`/`oklab()`; naive parsing gives garbage. Paint to a 1×1 canvas
and read sRGB, then compute the real WCAG ratio. **Switch theme and wait for the background transition to
settle** before measuring (a synchronous read mid-transition reports the old color):
```js
() => new Promise(resolve => {
  const c = document.createElement('canvas'); c.width = c.height = 1;
  const ctx = c.getContext('2d', { willReadFrequently: true });
  const rgb = s => { ctx.clearRect(0,0,1,1); ctx.fillStyle = '#000'; ctx.fillStyle = s; ctx.fillRect(0,0,1,1);
    const d = ctx.getImageData(0,0,1,1).data; return [d[0],d[1],d[2]]; };
  const L = ([r,g,b]) => { const f = [r,g,b].map(v => (v/=255) <= .03928 ? v/12.92 : ((v+.055)/1.055)**2.4);
    return .2126*f[0] + .7152*f[1] + .0722*f[2]; };
  const ratio = (a,b) => { const x=L(rgb(a)), y=L(rgb(b)), hi=Math.max(x,y), lo=Math.min(x,y);
    return +(((hi+.05)/(lo+.05)).toFixed(2)); };
  const col = sel => getComputedStyle(document.querySelector(sel)).color;
  const bg = () => getComputedStyle(document.body).backgroundColor;
  document.documentElement.setAttribute('data-theme','light');
  setTimeout(() => {                                   // let the bg transition finish
    const out = { /* e.g. */ accentText: ratio(col('.accent-text-el'), bg()), muted: ratio(col('.muted-el'), bg()) };
    document.documentElement.setAttribute('data-theme','dark');
    resolve(out);
  }, 700);
})
```
Pass: text ≥ 4.5:1, large/UI/icon/focus ≥ 3:1 — **in every theme**. Beware false positives: compare text
to the surface it actually sits on (an element's own transparent background reads as black → bogus ratio).

## 3. Horizontal-overflow truth
`getBoundingClientRect` ignores `overflow:hidden`/`clip`, so an element can look like it overflows while
being clipped. Confirm with the *real* scroll position, not just geometry:
```js
() => { const before = window.scrollX; window.scrollTo(900, window.scrollY);
  const moved = window.scrollX !== before; window.scrollTo(0, window.scrollY);
  return { docW: document.documentElement.scrollWidth, winW: innerWidth, horizontallyScrollable: moved }; }
```
`horizontallyScrollable: false` = no real overflow even if `docW > winW`.

## 4. Screenshot matrix (deterministic)
Capture **desktop (1440×900) and mobile (390×844)**, in **both themes**, across the key sections. For
smooth-scroll sites, programmatic `window.scrollTo` fights the scroll lib — expose the instance for QA
(`window.lenis = lenis`) and jump deterministically with `{ immediate: true }`. To screenshot lazy assets,
flip them eager first:
```js
() => { document.querySelectorAll('img[loading=lazy]').forEach(i => i.loading = 'eager');
  window.lenis && window.lenis.scrollTo('#work', { immediate: true }); }
```
To trigger all `once` scroll-reveals for a full-page capture, step-scroll to the bottom and back. Read each
screenshot and judge it against the Direction Doc.

## 5. Reduced motion
Emulate `prefers-reduced-motion: reduce` (DevTools Rendering panel, or the driver's `emulateMedia`) and
reload. Confirm: instant loader, no smooth-scroll inertia, reveals visible (no stuck-hidden), marquee
static, WebGL a single static frame, no infinite loops. If you can't emulate it in the harness, read the
JS reduced-motion branches AND the global `@media (prefers-reduced-motion: reduce)` CSS net by hand.
Also emulate `prefers-reduced-transparency: reduce` and `forced-colors: active` — confirm glass/backdrop
panels become solid, focus rings still show, and meaningful icons aren't dropped.

## 6. Keyboard + mobile specifics
- **Keyboard:** Tab through the whole page — reach and operate every control, focus always visible, no trap
  in loaders/pinned/horizontal sections; skip link works; tab a control behind the sticky header — it must
  scroll fully into view, not stay half-hidden (2.4.11).
- **Mobile layout:** check a fixed header isn't eating the viewport (measure its height as a % of `innerHeight`);
  horizontal sections collapse to vertical; tap targets ≥ ~44px. Note: headless desktop Chrome reports
  `pointer: fine` even at 390px, so hover-cursor/coarse-pointer behavior must be read from the media queries,
  not inferred from the screenshot.
- **Capability gating:** confirm WebGL goes live when on-screen and the static fallback shows only on real
  failure (not merely because the canvas is below the fold).

## 7. Loop
Re-run the relevant checks after each fix round. Done = console clean, contrast passes in both themes, no
real overflow, reduced-motion correct, keyboard clean, screenshots match the Direction Doc — only
acceptable lows remain.
