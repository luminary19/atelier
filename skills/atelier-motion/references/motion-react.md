# Motion (motion/react) recipes

Package: `motion` (the renamed Framer Motion). Import from `motion/react`. Hybrid engine — runs on
WAAPI (hardware-accelerated, off main thread) where it can, JS engine for springs/layout. Shrink the
bundle with `LazyMotion` + `domAnimation`.

## Basics — animate, gestures
```tsx
import { motion } from "motion/react";

<motion.button
  initial={{ opacity: 0, y: 8 }}
  animate={{ opacity: 1, y: 0 }}
  transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
  whileHover={{ scale: 1.03 }}
  whileTap={{ scale: 0.97 }}
>Save</motion.button>
```

## Variants + stagger (lists, menus)
```tsx
const list = { hidden: {}, show: { transition: { staggerChildren: 0.05, delayChildren: 0.1 } } };
const item = { hidden: { opacity: 0, y: 12 }, show: { opacity: 1, y: 0 } };

<motion.ul variants={list} initial="hidden" animate="show">
  {items.map((t) => <motion.li key={t} variants={item}>{t}</motion.li>)}
</motion.ul>
```

## Exit animations — AnimatePresence
Exit animations are impossible without this (React unmounts immediately otherwise).
```tsx
import { AnimatePresence, motion } from "motion/react";

<AnimatePresence mode="wait">
  {open && (
    <motion.div key="panel"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -20 }}
      transition={{ type: "spring", stiffness: 300, damping: 30 }} />
  )}
</AnimatePresence>
```
`mode`: `wait` (out then in), `popLayout` (removed items pop from layout flow), `sync`.

## Layout & shared-element ("magic move")
```tsx
<motion.div layout transition={{ type: "spring", stiffness: 350, damping: 35 }} />
{/* same layoutId across two components → morph between them */}
{active && <motion.div layoutId="highlight" className="indicator" />}
```
`<Reorder.Group>` / `<Reorder.Item>` for drag-to-reorder lists. Scope layout animations to small trees
(expensive on large ones).

## Scroll-linked (light) — useScroll/useTransform
For simple scroll-tied values. Heavy scroll choreography (pin/scrub/horizontal) → use `atelier-scroll`.
```tsx
import { useScroll, useTransform, motion } from "motion/react";
const { scrollYProgress } = useScroll();
const opacity = useTransform(scrollYProgress, [0, 0.2], [0, 1]);
<motion.div style={{ opacity }} />
```

## Reduced motion (mandatory)
```tsx
import { useReducedMotion } from "motion/react";
function Card() {
  const reduce = useReducedMotion();
  return <motion.div
    initial={reduce ? false : { opacity: 0, y: 16 }}
    whileInView={{ opacity: 1, y: 0 }}
    viewport={{ once: true, margin: "0px 0px -10% 0px" }}
    transition={{ duration: reduce ? 0 : 0.4, ease: [0.16,1,0.3,1] }} />;
}
```
Or wrap globally with `<MotionConfig reducedMotion="user">` so Motion auto-respects the OS setting.

## Bundle discipline
```tsx
import { LazyMotion, domAnimation, m } from "motion/react";
<LazyMotion features={domAnimation}>
  <m.div animate={{ opacity: 1 }} />   {/* use `m`, not `motion`, inside LazyMotion */}
</LazyMotion>
```
Use `motion/mini`'s `animate` (~2.3KB) for one-off vanilla WAAPI tweens. Keep everything to
`transform`/`opacity`; springs/layout run on the JS engine (still smooth, just not WAAPI).
