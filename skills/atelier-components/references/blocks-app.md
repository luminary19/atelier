# Block library — app / dashboard sections

Premium app UI blocks (React + Tailwind v4 + shadcn), token-driven, accessible. Data-dense screens earn
"premium" through **clarity, hierarchy, and consistency**, not decoration. Equal-size cards are fine here
(it's data, not marketing). Adapt to the Direction Doc; verify with `atelier-perf-a11y`.

## Contents
App shell (sidebar + topbar) · KPI / stat cards · Section header · Data table · Settings form (+ rhf/zod
validation) · Tabs / segmented / pagination · Command-palette wiring · Empty / loading states

---

## App shell (grid-template-areas)
```tsx
<div className="grid min-h-svh grid-cols-[var(--sb,16rem)_1fr] grid-rows-[auto_1fr]
                [grid-template-areas:'sidebar_topbar''sidebar_main'] max-md:grid-cols-1
                max-md:[grid-template-areas:'topbar''main']">
  <aside className="[grid-area:sidebar] border-r border-border bg-card p-4 max-md:hidden">
    <a className="font-display tracking-tight">Northwind</a>
    <nav className="mt-6 space-y-1 text-sm">
      {nav.map((i) => (
        <a key={i.href} href={i.href}
           className={cn("flex items-center gap-3 rounded-md px-3 py-2 text-muted-foreground hover:bg-accent hover:text-foreground",
             i.active && "bg-accent text-foreground")}>
          <i.icon className="size-4" />{i.label}
        </a>
      ))}
    </nav>
  </aside>
  <header className="[grid-area:topbar] flex h-14 items-center justify-between border-b border-border px-6">
    <button className="text-sm text-muted-foreground" onClick={openCmdk}>Search… <kbd className="ml-2 rounded border border-border px-1.5 text-xs">⌘K</kbd></button>
    <div className="flex items-center gap-3">{/* theme toggle, avatar */}</div>
  </header>
  <main className="[grid-area:main] overflow-y-auto p-6">{children}</main>
</div>
```
Mobile: hide the sidebar, move nav into a Vaul drawer triggered from the topbar.

> **Heavier sidebar?** For a collapsible, cookie-persisted, ⌘B-toggle sidebar with icon/offcanvas/inset
> modes, install shadcn's `sidebar` block (`sidebar-07` = the canonical app-sidebar + nav-user +
> team-switcher) and theme it on your tokens — it's the composition base to **de-template**, not the final
> look (`npx shadcn@latest add sidebar-07`).

## KPI / stat cards
```tsx
<div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
  {stats.map((s) => (
    <div key={s.label} className="rounded-xl border border-border bg-card p-5">
      <p className="text-sm text-muted-foreground">{s.label}</p>
      <p className="mt-2 font-display text-3xl tracking-tight tabular-nums">{s.value}</p>
      <p className={cn("mt-1 text-xs tabular-nums", s.delta >= 0 ? "text-emerald-600" : "text-destructive")}>
        {s.delta >= 0 ? "↑" : "↓"} {Math.abs(s.delta)}% vs last week
      </p>
    </div>
  ))}
</div>
```
`tabular-nums` everywhere numbers update (no width jitter). Pair charts with Tremor. For a card that scales
to *its own* width (not the viewport), wrap it in `@container/card` and bump the value with
`@[250px]/card:text-3xl` (container queries → `atelier-layout`).

## Section header (page title + actions)
```tsx
<div className="mb-6 flex flex-wrap items-end justify-between gap-4">
  <div><h1 className="font-display text-2xl tracking-tight">Deployments</h1>
    <p className="text-sm text-muted-foreground">Across all environments.</p></div>
  <div className="flex gap-2"><Button variant="outline">Filter</Button><Button>New</Button></div>
</div>
```

## Data table (shadcn/TanStack)
Use shadcn `table` + TanStack Table for sorting/filtering/pagination. Premium details: sticky header,
`tabular-nums` on numeric columns, row hover, right-aligned numbers, zebra via `even:bg-muted/40`,
keyboard-focusable rows, and a real **empty state** (below) instead of a blank table.
```tsx
<div className="overflow-hidden rounded-xl border border-border">
  <table className="w-full text-sm">
    <thead className="sticky top-0 bg-card text-left text-muted-foreground">
      <tr>{cols.map(c => <th key={c} className="px-4 py-3 font-medium">{c}</th>)}</tr>
    </thead>
    <tbody className="divide-y divide-border">
      {rows.map(r => (
        <tr key={r.id} tabIndex={0} className="hover:bg-accent/50 focus-visible:bg-accent/50 outline-none">
          <td className="px-4 py-3">{r.name}</td>
          <td className="px-4 py-3 text-right tabular-nums">{r.count}</td>
        </tr>
      ))}
    </tbody>
  </table>
</div>
```
> **Heavier table?** For drag-reorder rows (dnd-kit), a row-detail `Drawer`, faceted filters, and
> `toast.promise` saves, shadcn's `dashboard-01` data-table is the canonical TanStack-Table-v8 wiring to
> adapt (`npx shadcn@latest add dashboard-01`) — strip it to what the screen needs.

## Settings form (label + help + inline errors)
```tsx
<form className="max-w-xl space-y-6">
  <div className="space-y-2">
    <Label htmlFor="name">Workspace name</Label>
    <Input id="name" aria-describedby="name-help" defaultValue="Acme" />
    <p id="name-help" className="text-xs text-muted-foreground">Shown to your team.</p>
  </div>
  {/* on error: add aria-invalid + an inline <p role="alert"> with the cause; preserve input */}
  <div className="flex justify-end gap-2"><Button variant="ghost">Cancel</Button><Button>Save</Button></div>
</form>
```
Optimistic save + Sonner toast (atelier-motion). Every input needs a real `<Label htmlFor>`.

**With validation — react-hook-form + zod + shadcn `<Form>`** (the production default). `npx shadcn@latest
add form` scaffolds the rhf wrappers; one zod schema is the source of truth for shape *and* messages, and the
shadcn `<Form*>` parts wire `aria-invalid` / `aria-describedby` / error text automatically:
```tsx
"use client";
import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";
import { Form, FormField, FormItem, FormLabel, FormControl, FormMessage } from "@/components/ui/form";

const schema = z.object({
  name: z.string().min(1, "Workspace name is required"),
  seats: z.coerce.number().int().min(1, "At least one seat"),
});
type Values = z.infer<typeof schema>;

function SettingsForm() {
  const form = useForm<Values>({
    resolver: zodResolver(schema),
    defaultValues: { name: "Acme", seats: 3 },
    mode: "onTouched",            // validate on blur, then re-validate on change once touched
  });
  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="max-w-xl space-y-6" noValidate>
        <FormField control={form.control} name="name" render={({ field }) => (
          <FormItem>
            <FormLabel>Workspace name</FormLabel>
            <FormControl><Input {...field} /></FormControl>
            <FormMessage />        {/* renders the zod message + links it via aria-describedby */}
          </FormItem>
        )} />
        <Button type="submit" disabled={form.formState.isSubmitting}>Save</Button>
      </form>
    </Form>
  );
}
```
- **Timing:** `mode: "onTouched"` — validate on blur, then live-revalidate touched fields; don't error on the
  first keystroke. Keep errors inline (`FormMessage`); for long forms also summarize at top and focus the first error.
- **Never clear input on a failed submit.** `zodResolver` auto-detects zod v3/v4; use `z.coerce.number()` (or
  `valueAsNumber`) for numeric fields. Multi-step *flow* → `atelier-ux`; form *layout* → `atelier-layout`.

## Tabs, segmented control & pagination
- **Tabs** (shadcn `tabs`, Radix) — roving focus + arrow keys free; switch views *in place*. Short trigger
  labels; the active tab carries the one accent. Don't use tabs for sequential steps (that's a flow → `atelier-ux`).
- **Segmented control** = a styled single-select `ToggleGroup` (shadcn `toggle-group`, `type="single"`) for
  2–4 mutually-exclusive options (Day/Week/Month). One always selected; animate the active pill with a Motion
  `layoutId` (atelier-motion).
- **Pagination** (shadcn `pagination`) — semantic `<nav aria-label="Pagination">` with prev/next + page links;
  the current page gets `aria-current="page"`. Prefer it over infinite scroll for data users must return to or
  deep-link; reserve infinite scroll for feeds (and still give it a real loading state + a "Load more" fallback).

## Command-palette wiring
```tsx
useEffect(() => {
  const onKey = (e: KeyboardEvent) => {
    if ((e.metaKey || e.ctrlKey) && e.key === "k") { e.preventDefault(); setOpen(o => !o); }
  };
  document.addEventListener("keydown", onKey);
  return () => document.removeEventListener("keydown", onKey);
}, []);
// render <CommandDialog open={open} .../> from atelier-components/curated-components.md
```

## Empty / loading states (don't ship a blank screen)
```tsx
// Empty — onboarding moment
<div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-border py-16 text-center">
  <Icon className="size-8 text-muted-foreground" />
  <h3 className="mt-4 font-medium">No deployments yet</h3>
  <p className="mt-1 max-w-sm text-sm text-muted-foreground">Connect a repo to ship your first deployment.</p>
  <Button className="mt-6">Connect repository</Button>
</div>
// Loading — skeleton rows (shimmer from atelier-motion; static under reduced motion)
```
> **Primitives:** shadcn's `Empty` (`EmptyHeader`/`EmptyMedia`/`EmptyTitle`/…) is the structural target for
> this empty state, and `Field`/`FieldError` for the form above — see `curated-components.md`.
Always design empty + loading + error (atelier-motion's states reference). Run `atelier-perf-a11y`:
keyboard nav, focus order, labels, contrast, `aria-live` for async updates.
