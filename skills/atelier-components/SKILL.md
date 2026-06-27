---
name: atelier-components
version: 1.0.0
description: >
  Atelier suite — turn the design system into real, accessible, production code. Scaffold a premium
  React/Next + Tailwind v4 + shadcn/ui project, wire the atelier-foundations tokens into shadcn's theme
  variables, install the best-in-class single-purpose components (Vaul drawer, Sonner toast, cmdk command
  palette, Tremor dashboards), set up Storybook, and assemble pages from a copy-paste premium
  section-block library (hero variants, bento, feature rows, pricing, nav, footer, dashboard shell, data
  tables, forms, empty states). Use whenever building/scaffolding a frontend project, implementing
  components or page sections, setting up shadcn/Tailwind, adding a drawer/toast/command-palette/charts,
  or assembling marketing or app UI. Default stack: React/Next + Tailwind v4 + shadcn — with a no-framework path (Basecoat / Franken UI) for vanilla HTML / Rails / Laravel / Django / Astro. Part of the
  Atelier suite.
triggers:
  - build the components
  - scaffold the project
  - set up shadcn
  - set up tailwind
  - component library
  - command palette
  - toast
  - drawer
  - dashboard
  - landing page sections
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
---

# Atelier — Component System & Build

Where the design system becomes shipping code. The goal: a coherent, accessible, premium component layer
that **inherits the tokens automatically** (so the whole app looks designed, not assembled) and a library
of section blocks that aren't the generic shadcn-default look.

> **Project memory:** if **`ATELIER.md`** exists, read it first and honor its register, policies, and
> tokens (set up via **`/atelier init`** — the **`atelier`** router).
>
> **Inputs:** tokens from `atelier-foundations` (Tailwind `@theme` + shadcn mapping); the Direction Doc's
> archetype/aesthetic; the nav model + flows + screen-states from `atelier-ux`; type from
> `atelier-typography`; layout from `atelier-layout`; motion from `atelier-motion`; charts from
> `atelier-dataviz`; UX writing (labels, errors, empty-state copy) from **`atelier-copy`**. **Harden for
> production with `atelier-harden`, then always run `atelier-perf-a11y` before shipping.** Default stack:
> **React/Next + Tailwind v4 + shadcn/ui.** Deep reference: `references/fundamentals-deepdive.md` (§9).
>
> **Data — `atelier-data`:** current do/don't tables for the stack — `scripts/search.py "<topic>" --stack nextjs|react|shadcn|vue` and `--domain react` (RSC / Next 15 perf). An implementation cross-check, not a substitute for the section blocks + token wiring here.

---

## The flow

1. **Scaffold** (Next/Vite + Tailwind v4 + shadcn) → 2. **Wire tokens → shadcn** → 3. **Install curated
components** for the hard parts → 4. **Assemble pages from the block library** → 5. **Real assets
(images, icons, copy)** → 6. **Storybook** (if a real component library) → 7. **Perf/a11y gate**.

## 1. Scaffold

Set up the house stack. Full commands + `components.json` + `cn()`/`cva` in **`references/setup.md`**.
Short version: Next.js (or Vite) + Tailwind v4 (`@import "tailwindcss"`, CSS-first, no config file) +
`npx shadcn@latest init`. Choose the primitive layer: **Base UI** (actively developed, MUI team, v1) or
**Radix** (mature, broadest component set) — `init` supports both. shadcn copies component *source* into
your repo (you own it), uses `lucide` icons, `class-variance-authority` for variants, `cn()` =
`twMerge(clsx(...))`.

**Or start from AI design→code** (this stack is what they emit): **v0** (image/Figma → shadcn+Tailwind,
production-grade), **Magic Patterns** (prompt or pasted screenshot → React/Tailwind, matches an *imported*
design system via Figma MCP/Storybook), **Lovable** / **Bolt.new** for full-stack/code-level. Always send
the output through §5 assets + `atelier-perf-a11y` (de-template first).

## 2. Wire tokens → shadcn (the step that makes it look designed)

Point shadcn's semantic CSS variables at the `atelier-foundations` OKLCH tokens (the mapping block lives
in foundations' `tokens-and-output.md`). This is what stops the project looking like every other
shadcn site — the components inherit *your* color/radius/spacing instead of the defaults. Confirm
`--background/--foreground/--primary/--card/--muted/--border/--ring` + `--radius` and the `.dark` block.

## 3. Install curated, best-in-class components

Don't hand-roll the hard interactive components — these win on feel + accessibility. Details + install +
usage in **`references/curated-components.md`**:
- **Vaul** — drawer / bottom sheet (mobile gesture physics). **Sonner** — toast (imperative `toast()`).
  **cmdk** — ⌘K command palette. **Tremor** — dashboard charts/KPIs. (shadcn wraps the first three.)
- **When to choose a batteries-included framework instead** (MUI/Ant/Mantine for enterprise/data-heavy)
  is covered there too.

## 4. Assemble pages from the block library

This suite ships a **premium section-block library** so pages don't default to the generic look. Blocks
are React + Tailwind v4 + shadcn, token-driven, responsive, accessible, with motion hooks for
`atelier-motion`. Adapt them to the Direction Doc — don't paste verbatim.
- **Marketing blocks** (`references/blocks-marketing.md`): hero variants (asymmetric, giant-type, split),
  bento feature grid, alternating feature rows, logo strip, pricing, testimonial, sticky/mobile nav,
  footer, CTA band.
- **App blocks** (`references/blocks-app.md`): dashboard shell (sidebar/topbar), KPI/stat cards, data
  table, settings form + **validated forms (react-hook-form + zod)**, tabs/segmented/pagination,
  command-palette integration, empty/loading states. (Charts/dashboards → **`atelier-dataviz`**.)

Compose with `atelier-layout` (grid/whitespace), `atelier-typography` (the type), `atelier-motion`
(reveals/feedback). Every block carries the perf/a11y baseline; verify with `atelier-perf-a11y`.

> **Optional — ship the block library as an installable registry.** The shadcn CLI installs from *any*
> registry, so Atelier's blocks/themes can be packaged for `npx shadcn add @atelier/<item>` (one command,
> auto-pulled deps) — see **`references/registry.md`**. This is a reuse convenience on the shadcn/app path;
> it does **not** replace the bespoke editorial `globals.css` default, and you still de-template to the
> Direction Doc.

## 5. Real assets — images & copy (stack-agnostic; do this, don't skip it)

A polished component layer with placeholder content still ships as slop. Real assets are part of the
build, not an afterthought. (This applies to *any* stack — vanilla, React, anything.)

> **Icon system, the responsive image component (`next/image` / `<picture>`), CSS image treatment
> (duotone/scrim/grain), and the favicon/OG pipeline** are in **`references/icons-and-imagery.md`**; the
> *art-direction* for them (icon/illustration language, imagery mood + treatment) is set in `atelier-direction`.

**Images — generate first, never fake.**
- **Image-gen first.** Make section-specific assets — hero, product/UI shots, textures, OG image — *on the
  Direction Doc's aesthetic* (art-direct every prompt: palette, mood, accent, lighting, composition,
  negative space). On this machine that's **`/codex-imagegen`** (local Codex CLI, ChatGPT login, no API
  key). For a **full premium page / hero comp** — a one-image-per-section design reference, not a lone asset — use **`/codex-imagegen-taste`** (it adds the anti-slop taste layer and drives this same helper under the hood); for **single one-off assets** (one texture, a logo, an OG card) call the bare helper directly:

  ```powershell
  $skills = if ($env:CLAUDE_CONFIG_DIR) { "$env:CLAUDE_CONFIG_DIR\skills" } else { "$env:USERPROFILE\.claude\skills" }
  & "$skills\codex-imagegen\scripts\codex-image.ps1" `
    -Prompt "<art-directed prompt on the Direction Doc aesthetic>" -OutDir ".\public\img" -Count 1 -Size 1536x1024
  ```
  Size ↔ aspect: **1536×1024** landscape (hero/feature), **1024×1536** portrait, **1024×1024** square; add
  **`-Transparent`** for logos / icons / cut-outs; **`-Edit in.png`** to refine an existing asset. Cost is
  ~30k tokens/image, so generate a deliberate handful (hero + a few section assets), never loop. **Then
  optimize (required, or you trade a design Tell for a perf regression):** downscale to display size,
  convert to **WebP/AVIF**, set `width`/`height` (CLS), `loading="lazy"` below the fold, real `alt`
  (`alt=""` if decorative). On a non-Windows box or without Codex, substitute any available image-gen
  (MCP/IDE) the same way.
- **Never div-based fake screenshots.** Hand-built `<div>` dashboards / task lists / terminals / "product
  previews" are a Tell (see `atelier-perf-a11y/references/anti-slop-preflight.md`). Use a generated image,
  a real screenshot, a real mini-component, or editorial imagery — or leave a labelled TODO slot and say so.
- **Real logos** for social proof — **Simple Icons** (`https://cdn.simpleicons.org/{slug}/{color}`) or a
  generated monogram for invented brands; logos only, no category labels; render in both themes.
- Decorative imagery gets `alt=""`; meaningful imagery gets real `alt`. A pure-text "hero" is a placeholder.

**Copy — author it, then audit it.** (UX writing is owned by **`atelier-copy`** — labels, errors,
empty-state and loading copy, confirmations; pull the patterns from there. The essentials inline:)
- Write real copy to the brand voice; one register per page.
- **Copy self-audit before ship:** re-read every visible string and cut/rewrite anything broken,
  ambiguous, or AI-cute (forced wordplay, mock-poetic micro-meta). No placeholder-as-label.
- **No fake-precise numbers** (`92%`, `13.4 lb`): real, explicitly-labelled mock, or cut.

## 6. Storybook (for real design systems)

If you're building a reusable component library (not a one-off page), set up **Storybook 9** — isolated
component dev + interaction tests (Vitest), a11y tests (axe across all stories), and visual regression.
Setup in `references/setup.md`. Skip it for small one-off sites.

## 7. Harden, then gate

**For anything production-bound, run `atelier-harden` first** — real/empty/huge data, text overflow,
i18n/RTL, per-status error states, double-submit/cleanup. A build that's only been seen with seed data on
the happy path isn't done. Then run **`atelier-perf-a11y`**: keyboard + screen-reader pass, visible focus, contrast, Core Web Vitals,
reduced motion — **and the anti-slop / "AI Tells" check** (div-faked assets, copy audit, eyebrow/CTA/
marquee Tells). shadcn/Radix/Base UI give you accessible primitives — but *your* composition (focus
order, labels, color, motion, real assets) still has to pass. For a substantial/award build, escalate to
**`atelier-review`** — the adversarial, multi-reviewer red-team of the finished build (no ultracode needed).

---

## Operating principles
- **Tokens first, then components.** A component layer that reads `atelier-foundations` semantics is what
  makes the whole app cohesive; hard-coded values are the #1 cause of "assembled, not designed."
- **You own the code (shadcn model).** Customize freely; re-pull for upstream fixes.
- **Buy the hard parts** (Vaul/Sonner/cmdk/Tremor) — they're better than hand-rolled and accessible.
- **Use the block library, then de-template it** to the Direction Doc — never ship the default shadcn look.
- **Real assets, not placeholders.** Generate images (image-gen-first) on the aesthetic; never div-fake
  screenshots; audit every visible string. Placeholder content is unfinished work, not a draft to ship.
- **Accessibility is composition, not just primitives.** Verify with the gate.
