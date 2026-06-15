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

## Empty / loading / error states (the trinity)
- **Empty** — an onboarding moment, not a void: explain the value + a clear primary CTA + maybe a sample.
- **Loading** — prefer skeleton/optimistic over spinner; respond to input within 100ms; show progress for
  waits > ~1s.
- **Error** — human language, the cause + a recovery action, **preserve the user's input**, never
  dead-end. Pair with a non-color signifier (icon/text) for accessibility; announce via `aria-live`.

## Haptics
`navigator.vibrate([10])` for confirmations on Android/mobile (iOS Safari support is limited — feature-
detect, treat as enhancement). Short, meaningful patterns (select/success/error); never spam; never
haptic-only — always pair with visual feedback. Respect OS settings.

## Reduced motion across all of the above
Skeleton → static (no shimmer). Like/celebration → instant state change (no bounce). Toasts/reveals →
fade only. Keep meaning; remove movement. Branch with `useReducedMotion()` or the CSS media query.
