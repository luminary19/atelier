# glTF KHR Material Extensions — forge-material reference

# Contents
- §1. Extension overview and Three.js support matrix
- §2. KHR_materials_emissive_strength (HDR bloom)
- §3. KHR_materials_ior (dielectric IOR)
- §4. KHR_materials_specular (per-material F0 override)
- §5. KHR_materials_clearcoat (protective lacquer layer)
- §6. KHR_materials_transmission (thin-walled glass)
- §7. KHR_materials_volume (thick glass, amber, liquids)
- §8. KHR_materials_sheen (cloth, velvet)
- §9. KHR_materials_iridescence (soap bubble, oil slick)
- §10. KHR_materials_anisotropy (brushed metal, hair, satin)
- §11. extensionsUsed vs extensionsRequired policy

---

## §1. Extension Overview — Three.js r168+ Support Matrix

All extensions below are supported by Three.js r168+ via `GLTFLoader`.

| Extension                           | Status    | Three.js Class                   | Blender Export |
|-------------------------------------|-----------|----------------------------------|----------------|
| KHR_materials_emissive_strength     | Ratified  | emissiveIntensity                | Emission Strength > 1 |
| KHR_materials_ior                   | Ratified  | MeshPhysicalMaterial.ior         | IOR socket (with transmission) |
| KHR_materials_specular              | Ratified  | specularIntensity, specularColor | Specular IOR Level + Tint |
| KHR_materials_clearcoat             | Ratified  | clearcoat, clearcoatRoughness    | Coat Weight + Coat Roughness |
| KHR_materials_transmission          | Ratified  | transmission                     | Transmission Weight >= 0 |
| KHR_materials_volume                | Ratified  | thickness, attenuationColor      | Manual; requires closed mesh |
| KHR_materials_sheen                 | Ratified  | sheen, sheenColor, sheenRoughness| Sheen Weight + Tint |
| KHR_materials_iridescence           | Ratified  | iridescence, iridescenceIOR      | Not auto-exported; set manually |
| KHR_materials_anisotropy            | Ratified  | anisotropy, anisotropyRotation   | Blender 4.2+ |
| KHR_materials_unlit                 | Ratified  | (shadeless)                      | Emission-based only |

---

## §2. KHR_materials_emissive_strength (HDR Bloom)

Unlocks emissive values above 1.0. Without this extension, `emissiveFactor` is silently clamped
to [0,1] by older viewers.

```json
{
  "emissiveFactor": [1.0, 1.0, 1.0],
  "emissiveTexture": { "index": 0 },
  "extensions": {
    "KHR_materials_emissive_strength": {
      "emissiveStrength": 5.0
    }
  }
}
```

**BRDF:** `emission = emissiveFactor.rgb × sRGB_to_Linear(emissiveTexture.rgb) × emissiveStrength`

**Best practice (BP-5):** Set `emissiveFactor` to `[1,1,1]` (white) and control color via
`emissiveTexture`. Set `emissiveStrength` to the desired nit-equivalent multiplier.
Do NOT multiply large values into `emissiveFactor` — older viewers without this extension
clamp to 1.0.

**Blender export:** Principled BSDF `Emission Strength > 1.0` triggers this extension automatically.
Set `Emission Color` as the color (sRGB texture), `Emission Strength` as the multiplier.

**Three.js:** `MeshStandardMaterial.emissiveIntensity` (auto-mapped by GLTFLoader)

---

## §3. KHR_materials_ior (Dielectric IOR)

Sets the Index of Refraction for the dielectric BRDF. Default without this extension is 1.5.

```json
{
  "extensions": {
    "KHR_materials_ior": { "ior": 1.33 }
  }
}
```

**BRDF impact:** Changes `dielectric_f0 = ((ior - 1)/(ior + 1))^2`
- IOR 1.5 → F0 = 4% (standard plastic/glass, glTF default)
- IOR 1.33 → F0 = 2% (water)
- IOR 2.42 → F0 = 17% (diamond)

**IOR = 0 special case:** backward-compatibility mode for spec-gloss conversion (legacy; avoid).

**Three.js:** `MeshPhysicalMaterial.ior` (range 1.0–2.333; values above 2.333 are clamped)

**Blender export:** `Principled BSDF.IOR` is exported when Transmission Weight > 0 or when
Specular IOR Level is connected. Without these, IOR may not be included in export.

---

## §4. KHR_materials_specular (Per-Material F0 Override)

Adds per-material specular intensity and F0 color override for dielectrics.

```json
{
  "extensions": {
    "KHR_materials_specular": {
      "specularFactor": 1.0,
      "specularTexture": { "index": 5 },
      "specularColorFactor": [1.0, 1.0, 1.0],
      "specularColorTexture": { "index": 6 }
    }
  }
}
```

- `specularFactor` [0–1]: scales specular reflection strength (stored in texture A channel)
- `specularColorFactor` [RGB linear]: overrides the F0 color (stored in texture RGB, sRGB)
- **Incompatible with:** `KHR_materials_pbrSpecularGlossiness`, `KHR_materials_unlit`

**Three.js:** `MeshPhysicalMaterial.specularIntensity` + `specularColor`

---

## §5. KHR_materials_clearcoat (Protective Lacquer Layer)

Thin protective lacquer layer on top of the base material (car paint, lacquered wood, nail polish).

```json
{
  "extensions": {
    "KHR_materials_clearcoat": {
      "clearcoatFactor": 0.8,
      "clearcoatTexture": { "index": 7 },
      "clearcoatRoughnessFactor": 0.05,
      "clearcoatRoughnessTexture": { "index": 8 },
      "clearcoatNormalTexture": { "index": 9, "scale": 1.0 }
    }
  }
}
```

- `clearcoatFactor` [0–1]: intensity (texture stored in R channel)
- `clearcoatRoughnessFactor` [0–1]: roughness (texture stored in G channel)
- `clearcoatNormalTexture`: allows independent normal for the coat layer (e.g., orange-peel texture)
- **BRDF:** Uses fixed IOR = 1.5 for coat (NOT affected by `KHR_materials_ior`)
- Layer order: coat is on TOP of sheen + emission + base

**Blender Principled BSDF:** `Coat Weight`, `Coat Roughness`, `Coat Normal`

**Three.js car paint example:**
```javascript
const mat = new THREE.MeshPhysicalMaterial({
    clearcoat: 1.0,
    clearcoatRoughness: 0.05,
    metalness: 0.9,
    roughness: 0.4,
    clearcoatNormalScale: new THREE.Vector2(2.0, -2.0),  // Y negated for handedness
});
```

---

## §6. KHR_materials_transmission (Thin-Walled Glass)

Percentage of light transmitted through the surface. Models thin walls — no net refraction
displacement. For thick glass with actual refraction, add `KHR_materials_volume`.

```json
{
  "extensions": {
    "KHR_materials_transmission": {
      "transmissionFactor": 1.0,
      "transmissionTexture": { "index": 10 }
    }
  }
}
```

- `transmissionFactor` [0–1]: fraction of light passing through (texture in R channel)
- Roughness blurs transmitted light; IOR (from KHR_materials_ior) modulates blurring
- Does NOT produce refraction displacement alone — add KHR_materials_volume for that
- **alphaMode must be OPAQUE** (not BLEND) when transmission is active

**Three.js:** `MeshPhysicalMaterial.transmission` (requires `side: THREE.FrontSide`)

**Three.js transmission requirement:** Requires a scene environment or background to refract
against — transmission material appears black without it:
```javascript
scene.environment = new THREE.RGBELoader().load('envmap.hdr');
scene.background = scene.environment;
```

---

## §7. KHR_materials_volume (Thick Glass, Amber, Liquids)

Turns the surface into a true volume boundary. Requires `KHR_materials_transmission`.
**Mesh must be closed (manifold).**

```json
{
  "extensions": {
    "KHR_materials_volume": {
      "thicknessFactor": 1.0,
      "thicknessTexture": { "index": 11 },
      "attenuationDistance": 0.006,
      "attenuationColor": [0.2, 0.8, 0.4]
    }
  }
}
```

- `thicknessFactor` >= 0: 0 = thin-walled (default); any non-zero = thick volumetric mode.
  Value is in mesh coordinate space — must match actual geometry scale.
- `thicknessTexture`: G channel only (R and B unused). Bake from rays cast inward along -normal.
- `attenuationDistance` > 0: average free path in world space — smaller = denser/darker.
- `attenuationColor`: color of white light after traveling one `attenuationDistance`.
  Beer's law: `T(x) = attenuationColor^(x / attenuationDistance)`
- `doubleSided` has NO effect on volume boundaries — mesh must be closed instead.
- IOR from `KHR_materials_ior` governs refraction angle (default 1.5).

**Three.js:** `MeshPhysicalMaterial.thickness`, `.attenuationColor`, `.attenuationDistance`

**Mesh validation before export:**
```python
# In Blender, select mesh and check for non-manifold edges
import bpy, bmesh

def is_manifold(obj_name: str) -> bool:
    obj = bpy.data.objects.get(obj_name)
    if not obj or obj.type != 'MESH':
        return False
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    non_manifold = [e for e in bm.edges if not e.is_manifold]
    bm.free()
    if non_manifold:
        print(f"  Non-manifold edges: {len(non_manifold)}")
    return len(non_manifold) == 0
```

---

## §8. KHR_materials_sheen (Cloth, Velvet, Microfiber)

Retroreflective micro-fiber layer for fabric materials.

```json
{
  "extensions": {
    "KHR_materials_sheen": {
      "sheenColorFactor": [0.6, 0.4, 0.2],
      "sheenColorTexture": { "index": 12 },
      "sheenRoughnessFactor": 0.5,
      "sheenRoughnessTexture": { "index": 13 }
    }
  }
}
```

- `sheenColorFactor` [RGB linear]: default `[0,0,0]` (sheen disabled when black)
- `sheenColorTexture`: sRGB; final color = factor × texture.RGB
- `sheenRoughnessFactor` [0–1]: texture stored in the **ALPHA** channel (not RGB)
- Layer order: sheen is below clearcoat
- Uses albedo-scaling to prevent energy gain:
  `sheen_material = sheenColor × sheen_brdf + base_material × sheen_albedo_scaling`

**Three.js:** `MeshPhysicalMaterial.sheen`, `.sheenColor`, `.sheenRoughness`

**Blender:** `Sheen Weight`, `Sheen Roughness`, `Sheen Tint` sockets on Principled BSDF (4.x+)

---

## §9. KHR_materials_iridescence (Soap Bubble, Oil Slick, Beetle Wing)

Thin-film interference producing view-angle-dependent color shifts.

```json
{
  "extensions": {
    "KHR_materials_iridescence": {
      "iridescenceFactor": 1.0,
      "iridescenceTexture": { "index": 14 },
      "iridescenceIor": 1.3,
      "iridescenceThicknessMinimum": 100.0,
      "iridescenceThicknessMaximum": 400.0,
      "iridescenceThicknessTexture": { "index": 15 }
    }
  }
}
```

- `iridescenceFactor` [0–1]: intensity (× R channel of iridescenceTexture)
- `iridescenceIor`: IOR of the thin-film layer (not the base). Default 1.3
- `iridescenceThicknessMinimum/Maximum` [nm]: film thickness range.
  `iridescenceThicknessTexture` G channel interpolates between min (0.0) and max (1.0)
- Effect: view-angle-dependent color shift across the Fresnel term

**Three.js:** `MeshPhysicalMaterial.iridescence`, `.iridescenceIOR`,
`.iridescenceThicknessRange`, `.iridescenceMap`

**Blender export:** Not automatically exported from standard Principled BSDF sockets.
Set JSON values manually via a post-export pygltflib script, or use a custom Blender add-on.

---

## §10. KHR_materials_anisotropy (Brushed Metal, Hair, Satin)

Elongated specular lobe aligned along a tangent direction.

```json
{
  "extensions": {
    "KHR_materials_anisotropy": {
      "anisotropyStrength": 0.8,
      "anisotropyRotation": 0.0,
      "anisotropyTexture": { "index": 16 }
    }
  }
}
```

- `anisotropyStrength` [0–1]: overall stretch amount (× blue channel of texture)
- `anisotropyRotation` [radians]: CCW rotation from tangent direction
- `anisotropyTexture` channel layout:
  - R: X direction component, remapped [0,1] → [-1,1]
  - G: Y direction component, remapped [0,1] → [-1,1]
  - B: strength [0,1] — NOT remapped; NOT a direction component

**CRITICAL:** Mesh MUST have `NORMAL` + `TANGENT` vertex attributes, OR a `normalTexture` must
be set (which triggers MikkTSpace tangent computation). Without tangent space, anisotropy
silently produces wrong results.

**Normalization rule:** Normalize ONLY the RG channels as a 2D vector:
`length_rg = sqrt(r² + g²); r_norm = r / length_rg; g_norm = g / length_rg`
Do NOT include B in this normalization (B is strength, not direction).

**Blender export:** Principled BSDF `Anisotropic` + `Anisotropic Rotation` → `KHR_materials_anisotropy` (Blender 4.2+).
Export with `export_normals=True` and ensure a UV map exists (tangents are derived from UVs).

**Verify with gltf-validator after export** — it will flag missing TANGENT attributes.

**Three.js:** `MeshPhysicalMaterial.anisotropy`, `.anisotropyRotation`, `.anisotropyMap`

---

## §11. extensionsUsed vs extensionsRequired Policy

**`extensionsUsed`:** List ALL extensions present in the file. Viewers that don't support a
listed extension can still display the file (with graceful degradation — e.g., fallback to
opaque for transmission, no sheen effect, etc.).

**`extensionsRequired`:** Add ONLY when the asset is unusable without the extension.
- Glass sphere with transmission: if a viewer without transmission support renders it as a
  solid white sphere, that is acceptable degradation — keep in `Used` only.
- A material that is ONLY meant to be transparent (e.g., a window pane) with no opaque fallback:
  move transmission to `Required`.
- Most KHR material extensions should stay in `Used` only. Overusing `Required` breaks
  compatibility with older viewers and engines unnecessarily.

```json
{
  "extensionsUsed": [
    "KHR_materials_transmission",
    "KHR_materials_volume",
    "KHR_materials_ior",
    "KHR_materials_emissive_strength"
  ],
  "extensionsRequired": []
}
```

Blender's glTF exporter auto-populates `extensionsUsed` based on detected material features.
Use `gltf-transform inspect` to verify what was included.
