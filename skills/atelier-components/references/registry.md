# Shipping an Atelier registry (optional — installable blocks & themes)

The shadcn CLI resolves **any** registry, not just shadcn's own (the suite already *consumes* namespaced
registries + public GitHub repos — see `setup.md`). So Atelier's **section-block library** and **token
themes** can be packaged as an installable registry that `npx shadcn add @atelier/<item>` pulls in — turning
the copy-paste blocks in `blocks-marketing.md` / `blocks-app.md` into a one-command install that *also*
auto-pulls each block's shadcn dependencies. This is a distribution convenience, not a new default.

> **When to use this — and when NOT.** Use it on the **shadcn/app path**: you're repeatedly standing up
> shadcn-based app UIs and want Atelier's blocks/themes as a private, versioned library. It does **not**
> replace the **bespoke token-driven `globals.css` editorial path** that is the director's default for
> premium marketing/portfolio sites — those sections are hand-authored to their comps, never installed.
> A registry is plumbing for reuse, not the way you make a site look bespoke.

## The registry format (what an item is)
A registry is a `registry.json` manifest listing typed **items**; `npx shadcn build` compiles it into
self-contained per-item JSON the CLI installs. Item types:
`registry:block | ui | component | hook | lib | page | file | theme | style | font | base | item`.
```json
{
  "name": "hero-split",
  "type": "registry:block",
  "title": "Split hero",
  "description": "Asymmetric split hero on Atelier tokens.",
  "dependencies": ["lucide-react"],               // npm deps
  "registryDependencies": ["button", "badge"],    // shadcn items (bare name), @atelier/… , or a URL
  "files": [
    { "path": "blocks/hero-split/page.tsx", "type": "registry:page", "target": "app/page.tsx" },
    { "path": "blocks/hero-split/hero.tsx", "type": "registry:component" }
  ],
  "cssVars": { "theme": {}, "light": {}, "dark": {} },   // optional token overrides
  "categories": ["marketing", "hero"]
}
```
Rules: `files[].target` is required for `registry:file`/`registry:page` and accepts `@components/ @ui/ @lib/
@hooks/` aliases; `registryDependencies` reference shadcn primitives by **bare name**, other Atelier items
by **`@atelier/…`**, or any item by **URL** — the CLI resolves the whole dependency graph transitively, so
an installed block brings its primitives with it.

## Build → host → consume
1. **Author** items under e.g. `atelier-registry/` with a root `registry.json` (`{name, homepage, items[]}`,
   or `{ "include": [ … ] }` to chunk a large registry).
2. **Build:** `npx shadcn build -o ./public/r` emits one JSON per item (validate against the schema at
   `apps/v4/public/schema/registry-item.json` upstream).
3. **Host** `public/r/` on any static host (GitHub Pages / CDN / Vercel) at a stable URL.
4. **Consume:** one line in the target project's `components.json`, then install:
   ```json
   { "registries": { "@atelier": "https://<host>/r/{name}.json" } }
   ```
   ```bash
   npx shadcn add @atelier/hero-split @atelier/pricing-tiers   # auto-pulls their shadcn deps
   ```
   The `atelier-build-engineer` can call `shadcn add` instead of hand-pasting. Gated/private items: the
   builder expands `${ENV_VAR}` inside registry `headers` (e.g. `"Authorization": "Bearer ${ATELIER_TOKEN}"`),
   so token-gating works — you own the token lifecycle.

## Themes as installable token sets
A `registry:theme` (or `registry:style` with `extends:"none"`) carries `cssVars{theme,light,dark}` + `css{}`
— a complete Atelier "world" (one of the `atelier-direction` aesthetics) installable via
`shadcn add @atelier/aesthetic-<name>`, which overwrites the CSS vars in lockstep. This is the
registry-output mode referenced from `atelier-foundations/references/tokens-and-output.md` (Output D).

## Caveats
- **Tailwind/React path only** — the no-framework path (Basecoat / Franken UI) can't consume `registry:style`
  cssVars; keep registry distribution for the shadcn path.
- **Maintenance** — needs a static host + a `shadcn build` CI step + a stable URL. Shipping multiple styles
  means a per-style output tree (or keep it single-style and omit the `{name}`-only URL's `{style}` placeholder).
- **Don't re-vendor shadcn primitives** — reference them by bare name; ship only *your* blocks/themes.
- Format is **MIT** (shadcn) — clean to author your own registry against it.
