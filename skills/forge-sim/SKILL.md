---
name: forge-sim
version: 1.0.0
description: >
  Forge suite — simulation bake and export skill. Bakes cloth, rigid bodies, soft bodies,
  particle systems, hair/fur (GN Curves), and Mantaflow fluid/smoke/fire headlessly in
  Blender, then exports to Alembic (.abc) or OpenVDB (.vdb) mesh-cache for downstream
  rendering and handoff. Use whenever simulating cloth on a character or fabric, running
  rigid body destruction or stacking, emitting particles or object-scatter, grooming hair
  or fur with Geometry Nodes, baking smoke/fire volumes, or exporting any physics cache.
  Trigger phrases: "bake cloth", "cloth simulation", "rigid body", "particle system",
  "bake particles", "hair simulation", "fur grooming", "smoke sim", "fire simulation",
  "fluid simulation", "bake physics", "Alembic cache", "mesh cache", "point cache",
  "VDB export", "sim bake", "dynamics". All bakes run Blender headless; the result
  is verified by rendering a QA PNG and reading it. HEADLESS-ONLY: driven from code,
  output verified by reading a PNG. Part of the Forge suite.
triggers:
  - bake cloth
  - cloth simulation
  - rigid body sim
  - particle system
  - bake particles
  - hair simulation
  - fur groom
  - smoke simulation
  - fire simulation
  - fluid bake
  - VDB export
  - Alembic cache
  - mesh sequence cache
  - point cache bake
  - dynamics bake
allowed-tools:
  - Read
  - Write
  - Edit
  - Bash
  - PowerShell
  - Skill
---

# Forge — Simulation

> **Project memory:** if **`FORGE.md`** exists at the project root, read it first — it carries the
> frame range, output paths, coordinate system, and prior bake state for this project. Read
> **`ATELIER.md`** too if present (for aesthetic cues that affect simulation look: e.g. slow-motion
> physics, exaggerated cloth flutter for an award-grade direction).

---

> **Forge suite — simulation sits in the rigtech pipeline, between rigging/animation and render/export:**
>
> **forge** (router) → **forge-brief** (FORGE.md) → **forge-standards** (units/axes) →
> **forge-model** (mesh) → **forge-rig** (armature/skin) → **forge-animate** (keyframes) →
> **`forge-sim`** (YOU — cloth/RB/particles/hair/fluid bake) → **forge-export** (format matrix) →
> **forge-optimize** (Draco/Meshopt/KTX2) → **forge-validate** (gate) → **atelier-webgl** (web handoff)
>
> - **forge-rig** — armatures and skinning that cloth wraps over
> - **forge-animate** — keyframe/F-curve animation; baked RB keyframes land here
> - **forge-topology** — mesh resolution prep before cloth (edge length target 1–2 cm)
> - **forge-material** — Principled Hair BSDF, Principled Volume for smoke/fire
> - **forge-render** — headless Cycles render after bake; QA PNG loop
> - **forge-export** — format matrix; FBX/glTF/USD handoff; particle→mesh conversion
> - **forge-optimize** — Draco/Meshopt/KTX2 compression for web-bound baked meshes
> - **forge-validate** — mandatory gate after export; runs manifold + render QA
>
> Cross-suite: web-bound sims go **forge-export** → **forge-optimize** → **`Skill(atelier-webgl)`**;
> the web-runtime perf/a11y gate is **atelier-perf-a11y**. Atelier-side motion budget: **atelier-motion**.

**Run = call the Skill tool with the exact skill name (e.g. `Skill("forge-export")`). Saying "next, run forge-render" in prose runs nothing.**

---

## Decide first: which sim type, which bake strategy?

Before writing any script, pick the simulation type and confirm Blender is available:

```
1. Identify the type: cloth | rigid body | particles | hair/GN curves | fluid/smoke
2. Verify Blender (same preflight the other rigtech/lookdev skills use):
   python "$CLAUDE_CONFIG_DIR/skills/forge-render/scripts/preflight.py" --tools blender,python --json
   If `all_found` is false (or `blender` is in `missing`), stop and instruct installation;
   `blender_path` gives the resolved blender.exe for the bake invocation below.
3. Confirm .blend file is SAVED to disk (point cache requires a saved anchor)
4. Check cache type for fluid: must be ALL or MODULAR — never REPLAY for headless bakes
5. Confirm FORGE.md frame range and output paths
```

Each sim type has its own bake operator and gotchas. Deep references below — read only what you need.

---

## The flow

1. **Read project state** — read `FORGE.md`; if absent, ask for frame range, output dir, and target engine.

2. **Preflight gate** — verify `blender` is on PATH. If missing, stop and report.

3. **Identify sim type** — cloth / rigid body / particles / hair-fur / fluid-smoke. Multiple types in one scene: bake all via `ptcache.bake_all(bake=True)` first, then per-type operators if needed (Mantaflow needs `fluid.bake_all` separately — it is NOT covered by ptcache).

4. **Write the bake script** — use the patterns from `references/` for the chosen type. Save to `.forge-build/scripts/<slug>_bake.py`. Configuration at the top of the script as named constants, not inline magic numbers.

5. **Save the .blend first** — before any bake: `bpy.ops.wm.save_mainfile()`. Disk cache writes to `blendcache_<filename>/` beside the .blend; an unsaved file has no anchor path.

6. **Run the bake** — PowerShell, absolute paths, forward slashes in Blender filepath args:
   ```powershell
   $blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
   & $blender -b "C:/Projects/scene.blend" -t 0 --python "C:/Projects/bake.py" -- --forge
   ```
   The `--` separator before custom args is mandatory. `-t 0` uses all CPU cores (fast, but
   **non-deterministic** — switch to `-t 1` for byte-reproducible / idempotent rebuilds; see Operating principles).

7. **Verify the cache** — run the type-specific programmatic check (see `references/<type>-bake.md`). For cloth: `pc.is_baked`. For rigid body: `rbw.point_cache.is_baked`. For fluid: `ds.has_cache_baked_data` + VDB file count.

8. **QA render** — render a mid-sim frame headlessly (Cycles, 32–64 samples). Read the PNG with the Read tool and inspect visually. If the render is blank, static, or exploded — diagnose via the gotcha tables in `references/`.

9. **Export cache** — Alembic for cloth/rigid body/hair; OpenVDB folder for smoke/fire. See `references/export-cache.md` for operator flags. Always `as_background_job=False`.

10. **Hand off** (Run = call the Skill tool, not prose):
    - **Game engine** (Unreal/Unity/Godot): `Skill("forge-export")`.
    - **Web / Three.js / R3F**: `Skill("forge-export")` → `Skill("forge-optimize")` → `Skill("atelier-webgl")` — the export→compress→web chain; the baked cache ships as a Meshopt-compressed GLB, never stopping at forge-export.
    - **Full-quality final render** over the baked cache: `Skill("forge-render")`.
    - Always gate the result with `Skill("forge-validate")`.

---

## Sim-type quick reference

| Type | Bake operator | Cache format | Export |
|------|--------------|-------------|--------|
| **Cloth** | `ptcache.bake_all` or `ptcache.bake` + `temp_override` | `.bphys` | Alembic (`.abc`) |
| **Rigid body** | `ptcache.bake_all` | `.bphys` | Keyframes (headless manual) or Alembic |
| **Particles** | `ptcache.bake_all` or per-system `temp_override` | `.bphys` | Instances→real objects → FBX/glTF |
| **Hair (GN Curves)** | No bake needed (static); use cloth dynamics if physics needed | — | Alembic (particle hair) or GroomExporter (UE5) |
| **Fluid/smoke/fire** | `fluid.bake_all` + `temp_override` | OpenVDB `.vdb` | Copy `cache/data/` folder |

**Critical split:** `ptcache.bake_all` does NOT bake Mantaflow fluid. Fluid needs `fluid.bake_all`.

---

## Deep references (read on demand)

- **`references/cloth-bake.md`** — cloth modifier setup, pinning, presets (cotton/silk/denim/rubber), impulse clamping, Alembic export, explosion detection, gotcha table
- **`references/rigid-particles-bake.md`** — rigid body world config, active/passive bodies, manual keyframe bake (headless-safe), particle emitter setup, force fields, particles-to-real-mesh for export, gotcha table
- **`references/hair-fluid-bake.md`** — GN Curves creation, Principled Hair BSDF, Mantaflow ALL/MODULAR bake, VDB export structure, REPLAY gotcha, Windows path pitfalls, decision matrix
- **`references/export-cache.md`** — Alembic export operator flags, MeshSequenceCache re-import, VDB import, UE5 Groom scale (100×), game-engine conversion notes

---

## Operating principles

- **Bake before render, always.** In headless mode Blender cannot evaluate physics on-the-fly. A render of an unbaked sim returns the reset pose. Check `is_baked` or `has_cache_baked_data` before launching forge-render.
- **Save the .blend before baking.** Point cache and VDB files anchor to the .blend path. An unsaved file silently loses all cache data on exit.
- **Use `ptcache.bake_all` for cloth/RB/particles; use `fluid.bake_all` for Mantaflow.** These are separate operators; one does not call the other.
- **Always set `as_background_job=False`** in any export operator (Alembic, USD, FBX). The background-job thread exits before Blender's main loop can collect it — the file will not be written.
- **Forward slashes in all Blender file paths.** Use `pathlib.Path(p).as_posix()` or raw forward-slash strings. Backslashes can be silently misinterpreted in Blender's internal path handling on Windows.
- **Determinism: sims are FP-order-sensitive.** `-t 0` (all cores) is fast but NOT reproducible — two bakes give different results. Use `-t 1` (single-thread) whenever a bake must be byte-reproducible: CI, regression, or an idempotent rebuild. Always set an explicit force-field `seed` (e.g. `seed=1`) so wind/turbulence is repeatable, and seed the particle system (`ps.seed`) as well. See the `references/*.md` gotcha tables ("two bakes produce different results → -t 1").
