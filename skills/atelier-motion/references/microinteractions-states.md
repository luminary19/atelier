# Micro-interactions & the missing states

Perceived quality lives in the small feedback moments and the non-happy states. Build these deliberately.

## Micro-interaction anatomy (Dan Saffer)
Trigger (explicit tap / implicit system event) → Rules (what can happen) → Feedback (visual/audio/haptic,
≤100ms) → Loops & Modes. Every interactive element needs a clear **signifier** and immediate **feedback**.

### Button / toggle / like (Motion)
```tsx
<motion.button whileTap={{ scale: 0.96 }} transition={{ type:"spring", stiffness:500, damping:30 }}>
  <motion.span animate={{ scale: liked ? [1, 1.3, 1] : 1 }} transition={{ duration: 0.3 }}>♥</motion.span>
</motion.button>
```
### Copy-confirm / input focus
Swap label to "Copied ✓" for ~1.5s; animate focus ring in 120ms (`:focus-visible`, see atelier-perf-a11y).

## Skeleton / shimmer
Mirror the final layout; improves *perceived* speed vs a spinner (shows structure/context). Static under
reduced motion.
```css
.skeleton { background: var(--surface); border-radius: var(--radius-md); position: relative; overflow: hidden; }
@media (prefers-reduced-motion: no-preference) {
  .skeleton::after {
    content:""; position:absolute; inset:0;
    background: linear-gradient(90deg, transparent, oklch(1 0 0 / .06), transparent);
    transform: translateX(-100%); animation: shimmer 1.4s infinite;
  }
}
@keyframes shimmer { to { transform: translateX(100%); } }
```
React: `react-loading-skeleton` + Suspense for data-driven layouts.

## Optimistic UI (React 19 `useOptimistic`)
Update the UI as if the mutation succeeded; reconcile or roll back on the server response. Only for
likely-success, cheap-to-reverse actions (likes, toggles, list adds) — never irreversible/financial.
```tsx
const [optimistic, addOptimistic] = useOptimistic(items, (state, next) => [...state, next]);
async function add(formData) {
  addOptimistic({ id: "temp", text: formData.get("text"), pending: true });
  await save(formData); // on throw, React reverts the optimistic state automatically
}
```
Always surface errors gracefully and preserve user input on failure.

## Animated numbers (counters / prices / stats)
`NumberFlow` (`@number-flow/react`; `number-flow` for Vue/Svelte/vanilla) — dependency-free, accessible
rolling-digit transitions, `Intl.NumberFormat`-aware (currency/locale), respects reduced motion by default
(`respectMotionPreference`, `useCanAnimate()`). The correct default over a hand-rolled odometer (usually
janky *and* inaccessible). On Motion, `Motion+ AnimateNumber` is the equivalent (`trend` prop for spin direction).

## CSS-native entry/exit & height:auto (no JS)
- **Entry + exit:** `@starting-style` (the "from" on first render) + `transition-behavior: allow-discrete`
  lets `display`/`overlay` animate, so popovers/dialogs/toasts fade in *and* out with zero JS — often
  replacing `<AnimatePresence>`. Baseline; degrades to instant show/hide. Use Motion's `AnimatePresence`
  only when you need spring exits, layout, or interruption.
- **Accordions/disclosures:** animate to `height:auto` with `interpolate-size: allow-keywords` (set on
  `:root`) then transition `height` 0→auto — no JS measuring. Chromium-only; degrades to an instant snap.

## Layout / shared-element via GSAP Flip (explicit-control escalation)
When you need FLIP between two *arbitrary* layout states and Motion's `layout`/`layoutId` (the React
default) or Auto-Animate (zero-config) don't fit — vanilla/GSAP contexts, or precise control of the delta:
```js
import { Flip } from "gsap/Flip";            // free; gsap.registerPlugin(Flip)
const state = Flip.getState(".item");        // 1. capture current positions/sizes
container.classList.toggle("expanded");      // 2. mutate the DOM (reorder, add/remove, swap classes)
Flip.from(state, { duration: 0.5, ease: "power2.inOut", absolute: true, nested: true }); // 3. animate the delta
```
Flip animates `transform` (+ clip) only, so it stays compositor-safe; gate it behind reduced motion like
any movement. Keep it a **secondary** tool — Motion `layout`/`layoutId` stays the default for React UI.
(Every GSAP plugin — Flip, SplitText, MorphSVG, DrawSVG, ScrollSmoother — is free now: install from the
public `gsap` package, never an auth-token `.npmrc`.)

## Empty / loading / error states (the trinity)
- **Empty** — an onboarding moment, not a void: explain the value + a clear primary CTA + maybe a sample.
- **Loading** — prefer skeleton/optimistic over spinner; respond to input within 100ms; show progress for
  waits > ~1s.
- **Error** — human language, the cause + a recovery action, **preserve the user's input**, never
  dead-end. Pair with a non-color signifier (icon/text) for accessibility; announce via `aria-live`.

## Haptics
`navigator.vibrate([10])` for confirmations — but **Android Chrome/Edge/Samsung only (~77%); NOT iOS
Safari (never implemented), NOT Firefox (removed 129+).** Feature-detect, treat as pure enhancement,
requires a user gesture. Short, meaningful patterns (select/success/error); never spam; never haptic-only
— always pair with visual feedback. Respect OS settings.

## Reduced motion across all of the above
Skeleton → static (no shimmer). Like/celebration → instant state change (no bounce). Toasts/reveals →
fade only. Keep meaning; remove movement. Branch with `useReducedMotion()` or the CSS media query.
