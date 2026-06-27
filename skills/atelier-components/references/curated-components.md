# Curated components — buy the hard parts

Don't hand-roll drawers, toasts, command palettes, or charts. These win on interaction feel + built-in
accessibility. All pair with shadcn/Tailwind.

## Vaul — drawer / bottom sheet
Best-in-class mobile sheet physics: drag-to-dismiss, velocity, snap points, background scaling, rubber-
banding. shadcn's `drawer` wraps it.
```bash
npx shadcn@latest add drawer
```
```tsx
import { Drawer, DrawerContent, DrawerTrigger } from "@/components/ui/drawer";
<Drawer>
  <DrawerTrigger asChild><Button>Open</Button></DrawerTrigger>
  <DrawerContent><div className="p-6">…</div></DrawerContent>
</Drawer>
```
Use for mobile menus, filters, detail sheets. On desktop, prefer Dialog.

## Sonner — toast
Opinionated, beautiful defaults; imperative `toast()` from anywhere (no provider plumbing); promise/
loading states; swipe-to-dismiss; stacking.
```bash
npx shadcn@latest add sonner
```
```tsx
// app root: <Toaster richColors closeButton />
import { toast } from "sonner";
toast.success("Saved");
toast.promise(save(), { loading: "Saving…", success: "Saved", error: "Couldn’t save" });
```
Keep toasts for transient confirmations; errors that need action belong inline (see atelier-motion states).

## cmdk — command palette (⌘K)
Correct fuzzy filtering, roving focus, keyboard nav, a11y handled. The standard command menu.
```bash
npx shadcn@latest add command
```
```tsx
import { CommandDialog, CommandInput, CommandList, CommandItem, CommandGroup } from "@/components/ui/command";
// bind ⌘K / Ctrl+K to toggle `open`
<CommandDialog open={open} onOpenChange={setOpen}>
  <CommandInput placeholder="Type a command…" />
  <CommandList>
    <CommandGroup heading="Navigation">
      <CommandItem onSelect={() => go("/dashboard")}>Dashboard</CommandItem>
    </CommandGroup>
  </CommandList>
</CommandDialog>
```
A command palette is a premium signal in any app — add one early.

## Tremor — dashboards / charts
35+ accessible analytics components (KPI cards, charts, tables) + ~300 blocks on React + Tailwind + Radix.
The fastest path to a clean data dashboard. **Acquired by Vercel — now fully free/MIT** (the former paid
Blocks are open too).
```bash
npm i @tremor/react
```
```tsx
import { Card, AreaChart, Metric, Text } from "@tremor/react";
<Card><Text>Revenue</Text><Metric>$48,210</Metric>
  <AreaChart data={data} index="date" categories={["revenue"]} className="h-40 mt-4" /></Card>
```
Theme it via your CSS vars so it matches the system.

## Newer shadcn composition primitives (Field · Empty · Item)
shadcn shipped (late-2025) three **optional** composition primitives — `npx shadcn@latest add field empty
item`. Reach for them when you'd otherwise hand-roll these patterns; they're additive, **not a new
framework**, and don't replace the rhf+zod `<Form>` default (`blocks-app.md`):
- **`Field` / `FieldGroup` / `FieldLabel` / `FieldDescription` / `FieldError` / `FieldSeparator`** — a
  current form-composition idiom that composes *under* react-hook-form (alongside the rhf+zod `<Form>`
  pattern in `blocks-app.md`) or stands alone: label-above, `orientation: vertical|horizontal|responsive`,
  and a `FieldError` that de-dupes and renders an array of messages with `role="alert"`. Maps onto
  atelier-copy's "label above / error = what + why + how" and atelier-harden's validation states.
- **`Empty` / `EmptyHeader` / `EmptyMedia` / `EmptyTitle` / `EmptyDescription` / `EmptyContent`** — a
  structural empty-state primitive; the markup target for `atelier-harden`'s error/empty states and the
  empty-state block in `blocks-app.md`.
- **`Item` / `ItemMedia` / `ItemContent` / `ItemTitle` / `ItemDescription` / `ItemActions`** (CVA
  `default|outline|muted` × `default|sm`) — one taxonomy for settings rows, list rows, and notification
  rows you'd otherwise hand-roll.

## Before reaching for a lib: native primitives (zero-JS, now Baseline-ish)
Some "hard parts" no longer need a dependency — lean on the platform first:
- **Popover API + Invoker Commands** — native top-layer overlays/menus/tooltips with light-dismiss, focus,
  Esc handled. `<button popovertarget="m">` + `<div id="m" popover>`; drive `<dialog>`/popovers declaratively
  with `command`/`commandfor` (`show-modal`, `close`, `toggle-popover`). Pair with CSS **anchor positioning**
  for a fully-CSS menu (Invokers Baseline ~Dec 2025–Jan 2026).
- **`field-sizing: content`** — auto-growing `<textarea>`/content-width inputs with no JS resize hack
  (Tailwind `field-sizing-content`; on the cusp of Baseline — keep a fallback for pre-152 Firefox).
- **`<details name>`** (exclusive accordion) and native **`<dialog>` + `closedby="any"`** (light-dismiss modal).

## When to use a batteries-included framework instead of shadcn
Choose these for **enterprise / internal / data-heavy** apps, fast teams, or no dedicated designer — you
trade customization for breadth:
- **Mantine v9** — DX champion, 120+ components + 70+ hooks, modern look (needs React 19.2+). Best
  SaaS-dashboard default.
- **MUI v9 (+ MUI X v9)** — largest, Material; MUI X DataGrid (now with an AI assistant)/Date pickers/Charts
  (Pro/Premium paid, application-licensed). Enterprise.
- **Ant Design v6** — richest free data components (Table/Form/Tree/Transfer); v6 defaults to CSS-variable
  theming. Admin/back-office/B2B.
- **Ark UI / Park UI** — cross-framework (React/Vue/Solid/Svelte) headless / styled. (**Chakra UI v3** is
  rebuilt on Ark.)
Default for premium marketing + bespoke product UI remains **shadcn** (you own + theme the code).

**Need a complex widget shadcn doesn't ship?** Before hand-rolling, reach for **Kibo UI**
(`haydenbleasel/kibo`, MIT) — an own-the-code shadcn *registry of higher-order components* for the gaps the
primitives leave: **Gantt, Kanban, code block, color picker, dropzone, AI-chat input, rich editor**. Uses
shadcn CSS vars (themes + dark mode just work), installs via the shadcn CLI (namespaced) or its own; has an
MCP server.
**No React?** Get the shadcn look without a framework: **Basecoat UI** (Tailwind + tiny vanilla JS, semantic
`btn`/`card` classes, shadcn-CSS-var compatible) or **Franken UI** (HTML-first UIkit + web components,
Tailwind v4) — for Rails/Laravel/Django/Astro/plain HTML.

## Accessibility note
These primitives are accessible out of the box, but *your* usage still matters: give icon-only triggers
accessible names, keep focus management on open/close, don't suppress focus rings. Verify with
`atelier-perf-a11y`.
