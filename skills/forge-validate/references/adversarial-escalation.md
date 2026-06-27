# Forge Validate — Adversarial Escalation Protocol
# Contents
- §1. When to escalate
- §2. Reviewer dimensions
- §3. Delegation prompt template
- §4. Output contract
- §5. Synthesis and gate decision

---

## §1. When to Escalate

Escalate to adversarial sub-reviewers when the asset is:
- A **hero asset** (primary deliverable for the project)
- A **print deliverable** (geometry error = failed print = wasted material)
- A **web-delivery GLB** (public-facing; perf + spec compliance matter)
- Flagged with any **WARN** (not just BLOCK) in tiers 0–2

Skip escalation for: draft iterations, internal prototypes, background props.

Escalation requires the Task tool. **Run = call the Task tool, not narrate.**

> **Cross-suite analogue (web):** this Tier-3 fan-out is the 3D-asset counterpart of
> **`atelier-review`**. Forge-validate mirrors the Atelier `atelier-perf-a11y → atelier-review`
> ladder: Tiers 0–2 (the deterministic self-checklist) are the `atelier-perf-a11y` analogue,
> and this adversarial tier is the `atelier-review` analogue. It is an analogy for orientation,
> not a handoff — do NOT `Skill(atelier-review)` on a 3D asset.

---

## §2. Reviewer Dimensions

Spawn these reviewers in PARALLEL (independent analysis, no cross-contamination):

| Reviewer | Responsibility | Key checks |
|----------|---------------|------------|
| **topology** | Manifold integrity, normals, poles, winding | validate.py JSON (is_watertight/broken_faces, raw) **+ topology_audit.py JSON** (non_manifold_edges/flipped_faces/poles) |
| **material** | PBR spec compliance, color space, channel packing | glTF-Validator warnings; sRGB vs linear; ORM packing; emissiveFactor |
| **printability** | Wall thickness, overhang, drain holes, volume | Only for print-target assets; FORGE.md process=fdm|sla|sls|dmls |
| **render-fidelity** | Visual defects in contact sheet | Reads the PNG; flags black patches, UV stretch, scale errors |

Each reviewer is a simple subagent (no specialized agent needed — use `code-explorer` or
a generic task agent). Provide each with the validate.py JSON output and the
contact-sheet PNG path.

---

## §3. Delegation Prompt Template

Use this template for each reviewer task. Substitute `[DIMENSION]` and the specific
checklist.

```
You are an adversarial [DIMENSION] reviewer for a Forge 3D asset.
Your job is to find every problem — be thorough and skeptical.

ASSET CONTEXT:
- File: <path>
- FORGE.md target: <engine, coordinate system, scale, budget>

EVIDENCE:
- validate.py JSON: <paste JSON here>
- Contact sheet PNG path: <path> (call Read on it)

YOUR TASK:
1. Read the contact sheet PNG.
2. Review the validate.py JSON for [DIMENSION]-specific failures.
3. List every finding with severity: BLOCK / WARN / NOTE.
4. For each BLOCK finding, propose the exact fix command or code.
5. Output ONLY the JSON contract below — no prose outside the JSON.

OUTPUT CONTRACT (strict):
{
  "dimension": "[DIMENSION]",
  "findings": [
    {
      "severity": "BLOCK|WARN|NOTE",
      "issue": "short description",
      "evidence": "specific JSON field or visual observation",
      "fix": "exact command or code snippet"
    }
  ],
  "overall": "PASS|WARN|BLOCK",
  "rationale": "one sentence"
}
```

---

## §4. Dimension-Specific Checklists (append to each reviewer prompt)

**Topology reviewer checklist:**
```
From the validate.py JSON (trimesh tier — these ARE emitted there):
- is_watertight: must be true for print/boolean targets (reported RAW, pre-repair)
- is_volume: must be true for print targets
- broken_faces: must be 0 for print/export targets
- degenerate_faces: reported raw count; must be 0

From the topology_audit.py JSON (bmesh tier — run this SEPARATELY; validate.py does NOT
emit these. Invocation:
  blender -b <file> --factory-startup --python-exit-code 1 -P topology_audit.py -- --input <file> --json
then read the `totals` block):
- non_manifold_edges: must be 0 for all targets
- flipped_faces: must be 0 for all targets
- high_valence_poles: must be 0 for subdiv/rig targets
- ngons / pct_quads: 0 ngons for subdiv; >=90% quads for deform meshes

In the contact sheet: look for black patches (matcap) and irregular wireframe density.
```

**Material reviewer checklist:**
```
Check these in the glTF-Validator JSON (numErrors, numWarnings, messages):
- Any IMAGE_COLORSPACE_MISMATCH → sRGB on ORM/normal textures → BLOCK
- Any IMAGE_NPOT_DIMENSIONS → resize to power-of-two → WARN
- Any INVALID_URI → backslash in texture path → BLOCK
- emissiveFactor > 1.0 without KHR_materials_emissive_strength → WARN
- metallicRoughnessTexture: B=metallic, G=roughness, R=unused (confirm channel packing)
- normalTexture: must be LINEAR, OpenGL convention (+Y=up green channel)
- alphaMode=BLEND on opaque surfaces → expensive; confirm intentional
```

**Printability reviewer checklist (print targets only):**
```
Run validate.py in printability mode first — these fields only exist when --print is passed:
  python validate.py --input <file.stl> --print --process fdm|sla|sls|dmls --units mm --json
Then check the print_* checks (each carries the named field):
- print_is_volume: must be PASS (is_volume True)
- print_volume_mm3 (volume_mm3): must be > 0
- print_wall_thickness (thin_sample_frac): must be < 0.05 — WARN/None if no ray engine
  (rtree/pyembree absent); flag that the wall check did not actually run
- print_overhang (overhang_face_count): 0 for FDM/SLA/DMLS (SLS uses 360deg = never flags)
- print_body_count (body_count): 1 preferred (multi-body raises WARN)
If process=sla: print_drain_holes is an explicit WARN reminder — confirm >= 2 drain holes
(diameter >= 3mm, one near the lowest Z); the script cannot detect drilled holes from mesh.
```

**Render-fidelity reviewer checklist:**
```
Call Read on the contact sheet PNG path. Inspect:
- Turntable: silhouette consistent all angles; no floating geometry
- Matcap: no black patches; no shading seams on smooth surfaces
- Wireframe: uniform edge density; no stray vertices/edges; no high-valence poles
- Normal RGB: smooth gradients; no abrupt color reversals
- UV checker: uniform square size; no elongation > 2:1; no mirrored faces
- 6-view: proportions match FORGE.md target dimensions
```

---

## §5. Synthesis and Gate Decision

After all reviewers return, synthesise:

```python
def synthesise_escalation(reviewer_outputs: list[dict]) -> dict:
    """
    Merge adversarial reviewer findings into a single gate decision.
    reviewer_outputs: list of output-contract dicts, one per dimension.
    """
    all_findings = []
    for r in reviewer_outputs:
        for f in r.get("findings", []):
            all_findings.append({**f, "dimension": r["dimension"]})

    blocks = [f for f in all_findings if f["severity"] == "BLOCK"]
    warns  = [f for f in all_findings if f["severity"] == "WARN"]

    if blocks:
        gate = "BLOCK"
    elif warns:
        gate = "WARN"
    else:
        gate = "PASS"

    return {
        "gate":     gate,
        "blocks":   blocks,
        "warnings": warns,
        "total_findings": len(all_findings),
        "dimensions_reviewed": [r["dimension"] for r in reviewer_outputs],
    }
```

**Final gate rule:**
- Any `BLOCK` finding from any reviewer → pipeline stops; fix required before export.
- Only `WARN` findings → document each in FORGE.md with acceptance rationale; then proceed.
- All `PASS` → gate clears; proceed to `Skill("forge-export")` or `Skill("forge-optimize")`.
