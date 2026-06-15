# Block library — marketing sections

Premium, token-driven React + Tailwind v4 + shadcn blocks. **Adapt to the Direction Doc — never paste
verbatim** (that's how you get the generic look). All use semantic tokens (`bg-background`, `text-fore
ground`, `text-muted-foreground`, `bg-primary`, `border-border`), the spacing/radius scale, and leave
motion to `atelier-motion`. Classes assume the foundations tokens are wired.

## Contents
Sticky nav · Asymmetric hero · Giant-type hero · Split hero · Logo strip · Bento features · Feature row ·
Pricing · Testimonial · CTA band · Footer

---

## Sticky nav (with mobile drawer)
```tsx
<header className="sticky top-0 z-40 border-b border-border/60 bg-background/80 backdrop-blur-md">
  <nav className="mx-auto flex h-16 max-w-7xl items-center justify-between px-6">
    <a href="/" className="font-display text-lg tracking-tight">Northwind</a>
    <ul className="hidden gap-8 text-sm text-muted-foreground md:flex">
      <li><a className="transition-colors hover:text-foreground" href="#">Product</a></li>
      <li><a className="transition-colors hover:text-foreground" href="#">Pricing</a></li>
      <li><a className="transition-colors hover:text-foreground" href="#">Docs</a></li>
    </ul>
    <div className="flex items-center gap-3">
      <Button variant="ghost" className="hidden md:inline-flex">Sign in</Button>
      <Button>Get started</Button>
    </div>
  </nav>
</header>
```
Mobile: replace the `md:flex` list with a Vaul `Drawer` trigger. Keep the nav ≤64px and let content scroll under the blur.

## Asymmetric hero (giant headline left, visual right — the premium default)
```tsx
<section className="mx-auto grid max-w-7xl items-center gap-12 px-6 py-[clamp(4rem,10vw,9rem)] lg:grid-cols-[1.1fr_0.9fr]">
  <div className="max-w-xl">
    <p className="mb-4 text-sm uppercase tracking-[0.08em] text-muted-foreground">Infrastructure</p>
    <h1 className="font-display text-[clamp(2.75rem,6vw,5rem)] font-semibold leading-[0.98] tracking-[-0.02em]">
      Infrastructure you can <span className="text-primary">see</span>.
    </h1>
    <p className="mt-6 max-w-md text-lg leading-relaxed text-muted-foreground">
      One control plane for everything you ship. Observe, deploy, and roll back in one place.
    </p>
    <div className="mt-8 flex flex-wrap gap-3">
      <Button size="lg">Start free</Button>
      <Button size="lg" variant="outline">Book a demo</Button>
    </div>
  </div>
  <div className="relative aspect-square rounded-2xl border border-border bg-card">
    {/* product visual / atelier-webgl graph / screenshot — lazy-load if heavy */}
  </div>
</section>
```
Not centered, not three equal cards. The headline does the work; one accent word; generous whitespace.

## Giant-type hero (editorial / portfolio / agency)
```tsx
<section className="mx-auto max-w-[90rem] px-6 py-[clamp(5rem,12vw,12rem)]">
  <h1 className="font-display text-[clamp(3rem,13vw,12rem)] font-semibold leading-[0.9] tracking-[-0.03em]">
    We build<br/>the <span className="italic">unreasonable</span>.
  </h1>
  <div className="mt-10 flex max-w-2xl flex-col gap-6 sm:flex-row sm:items-end sm:justify-between">
    <p className="text-lg text-muted-foreground">An independent studio for brands that refuse the template.</p>
    <Button variant="outline" size="lg">See the work</Button>
  </div>
</section>
```
Pair with a kinetic line-reveal (atelier-typography) as the one signature moment.

## Split hero (consumer / product)
Two equal columns: copy + CTA on one side, full-bleed image/video on the other (`lg:grid-cols-2`, image
`object-cover h-full`, reserve with `aspect-[4/5]`). Good when the visual *is* the pitch.

## Logo strip (social proof)
```tsx
<section className="border-y border-border/60 py-10">
  <p className="mb-6 text-center text-xs uppercase tracking-[0.1em] text-muted-foreground">Trusted by teams at</p>
  <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-center gap-x-12 gap-y-6 px-6 opacity-70 grayscale">
    {logos.map((L) => <img key={L.alt} src={L.src} alt={L.alt} className="h-6 w-auto" />)}
  </div>
</section>
```
For a marquee version, see `atelier-scroll`.

## Bento features (one hero cell — never a uniform grid)
```tsx
<section className="mx-auto max-w-7xl px-6 py-[clamp(4rem,8vw,8rem)]">
  <div className="grid auto-rows-[minmax(0,1fr)] grid-cols-1 gap-3 md:grid-cols-4">
    <article className="md:col-span-2 md:row-span-2 flex flex-col rounded-2xl border border-border bg-card p-8">
      <h3 className="font-display text-2xl tracking-tight">Real-time topology</h3>
      <p className="mt-2 text-muted-foreground">See every service and its dependencies update live.</p>
      <div className="mt-auto pt-8">{/* big visual */}</div>
    </article>
    <article className="md:col-span-2 rounded-2xl border border-border bg-card p-8">…wide…</article>
    <article className="rounded-2xl border border-border bg-card p-8">…small…</article>
    <article className="rounded-2xl border border-border bg-card p-8">…small…</article>
  </div>
</section>
```
Rules (atelier-layout): one hero cell, purposeful size variation, consistent radius+gap, no empty cells,
one idea per cell. Collapse to 2-col then 1-col.

## Feature row (alternating, editorial)
```tsx
<section className="mx-auto grid max-w-6xl items-center gap-12 px-6 py-24 lg:grid-cols-2">
  <div className="lg:order-2"> {/* swap order per row for rhythm */}
    <h2 className="font-display text-[clamp(1.75rem,3vw,2.75rem)] leading-tight tracking-tight">Ship with confidence</h2>
    <p className="mt-4 text-lg text-muted-foreground">Preview every change before it’s live.</p>
    <ul className="mt-6 space-y-3 text-muted-foreground">{/* checked list */}</ul>
  </div>
  <div className="aspect-video rounded-xl border border-border bg-card lg:order-1" />
</section>
```

## Pricing (3 tiers, one highlighted)
```tsx
<section className="mx-auto max-w-6xl px-6 py-24">
  <div className="grid gap-6 md:grid-cols-3">
    {tiers.map((t) => (
      <div key={t.name} className={cn("flex flex-col rounded-2xl border bg-card p-8",
        t.featured ? "border-primary ring-1 ring-primary" : "border-border")}>
        <h3 className="font-medium">{t.name}</h3>
        <p className="mt-4 font-display text-4xl tracking-tight tabular-nums">{t.price}<span className="text-base text-muted-foreground">/mo</span></p>
        <ul className="mt-6 flex-1 space-y-3 text-sm text-muted-foreground">{t.features.map(f => <li key={f}>✓ {f}</li>)}</ul>
        <Button className="mt-8" variant={t.featured ? "default" : "outline"}>{t.cta}</Button>
      </div>
    ))}
  </div>
</section>
```
Note `tabular-nums` on prices (atelier-typography). Highlight one tier with the accent, not color-on-everything.

## Testimonial (single, large — premium > a wall of cards)
```tsx
<section className="mx-auto max-w-3xl px-6 py-24 text-center">
  <blockquote className="font-display text-[clamp(1.5rem,3.5vw,2.5rem)] leading-snug tracking-tight">
    “It replaced four tools and a weekly meeting.”
  </blockquote>
  <figcaption className="mt-6 text-sm text-muted-foreground">Dana Lin — VP Eng, Acme</figcaption>
</section>
```

## CTA band
```tsx
<section className="mx-auto my-24 max-w-7xl px-6">
  <div className="relative overflow-hidden rounded-3xl border border-border bg-card px-8 py-16 text-center">
    {/* optional grainy-gradient backdrop from atelier-foundations */}
    <h2 className="font-display text-[clamp(2rem,5vw,3.5rem)] leading-tight tracking-tight">Start shipping today.</h2>
    <div className="mt-8 flex justify-center gap-3"><Button size="lg">Get started</Button>
      <Button size="lg" variant="outline">Talk to sales</Button></div>
  </div>
</section>
```

## Footer
```tsx
<footer className="border-t border-border/60">
  <div className="mx-auto grid max-w-7xl gap-10 px-6 py-16 md:grid-cols-[2fr_1fr_1fr_1fr]">
    <div><a className="font-display text-lg tracking-tight">Northwind</a>
      <p className="mt-3 max-w-xs text-sm text-muted-foreground">Infrastructure you can see.</p></div>
    {cols.map((c) => (
      <nav key={c.title}><h4 className="text-sm font-medium">{c.title}</h4>
        <ul className="mt-4 space-y-2 text-sm text-muted-foreground">{c.links.map(l => <li key={l}><a className="hover:text-foreground" href="#">{l}</a></li>)}</ul></nav>
    ))}
  </div>
  <div className="border-t border-border/60 py-6 text-center text-xs text-muted-foreground">© 2026 Northwind</div>
</footer>
```
