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
35+ accessible analytics components (KPI cards, charts, tables) on React + Tailwind + Radix. The fastest
path to a clean data dashboard.
```bash
npm i @tremor/react
```
```tsx
import { Card, AreaChart, Metric, Text } from "@tremor/react";
<Card><Text>Revenue</Text><Metric>$48,210</Metric>
  <AreaChart data={data} index="date" categories={["revenue"]} className="h-40 mt-4" /></Card>
```
Theme it via your CSS vars so it matches the system.

## When to use a batteries-included framework instead of shadcn
Choose these for **enterprise / internal / data-heavy** apps, fast teams, or no dedicated designer — you
trade customization for breadth:
- **Mantine** — DX champion, 120+ components + 100+ hooks, modern look. Best SaaS-dashboard default.
- **MUI (+ MUI X)** — largest, Material; MUI X DataGrid/Date pickers/Charts (some paid). Enterprise.
- **Ant Design** — richest free data components (Table/Form/Tree/Transfer). Admin/back-office/B2B.
- **Ark UI / Park UI** — cross-framework (React/Vue/Solid/Svelte) headless / styled.
Default for premium marketing + bespoke product UI remains **shadcn** (you own + theme the code).

## Accessibility note
These primitives are accessible out of the box, but *your* usage still matters: give icon-only triggers
accessible names, keep focus management on open/close, don't suppress focus rings. Verify with
`atelier-perf-a11y`.
