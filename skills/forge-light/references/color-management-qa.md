# forge-light — Color Management QA & Three.js Web Matching
# Programmatic pixel checks + Three.js AgX parity

## Contents
- §1. Three.js web matching (match Blender 4.x AgX renders)
- §2. Programmatic QA checks (Python, system Python + Pillow)
- §3. Three.js-specific gotchas

---

## §1. Three.js web matching

Match Blender 4.x AgX renders in a Three.js / R3F scene:

```javascript
import * as THREE from 'three';

const renderer = new THREE.WebGLRenderer({ antialias: true });

// ColorManagement.enabled = true since r152 — DO NOT disable
THREE.ColorManagement.enabled = true;

// outputColorSpace = SRGBColorSpace matches Blender's "sRGB" display device
renderer.outputColorSpace = THREE.SRGBColorSpace;

// AgXToneMapping matches Blender 4.x default (shipped r160; gamut fix in r161)
renderer.toneMapping         = THREE.AgXToneMapping;
renderer.toneMappingExposure = 1.0;  // matches Blender exposure=0.0 stops

// Other tone mapping options:
//   THREE.ACESFilmicToneMapping  → matches Blender 3.x Filmic (approximate)
//   THREE.NeutralToneMapping     → Khronos PBR Neutral (r158+)
//   THREE.NoToneMapping          → matches Blender "Standard" (no tone mapping)

// Color textures (albedo, emissive) → tag sRGB
const albedo = new THREE.TextureLoader().load('albedo.png');
albedo.colorSpace = THREE.SRGBColorSpace;

// Non-color textures (normal, roughness, metallic, AO) → NoColorSpace (default)
const normalMap = new THREE.TextureLoader().load('normal.png');
normalMap.colorSpace = THREE.NoColorSpace;

// HDR / EXR environment map → linear
import { EXRLoader } from 'three/addons/loaders/EXRLoader.js';
new EXRLoader().load('env.exr', (tex) => {
    tex.colorSpace = THREE.LinearSRGBColorSpace;
    tex.mapping    = THREE.EquirectangularReflectionMapping;
    scene.environment = tex;
});

// EffectComposer: OutputPass MUST be the last pass
// Without it, renderer.outputColorSpace and toneMapping are bypassed
import { EffectComposer } from 'three/addons/postprocessing/EffectComposer.js';
import { RenderPass }     from 'three/addons/postprocessing/RenderPass.js';
import { OutputPass }     from 'three/addons/postprocessing/OutputPass.js';

const composer = new EffectComposer(renderer);
composer.addPass(new RenderPass(scene, camera));
// ... other passes ...
composer.addPass(new OutputPass());  // ALWAYS last; handles tone map + color space
```

---

## §2. Programmatic QA checks

Run with system Python (NOT Blender's internal Python) after rendering.
Requires: `pip install Pillow numpy`

```python
"""
qa_color_check.py — verify color management is applied correctly to a rendered PNG.
"""
import numpy as np
from PIL import Image


def load_png_float(path: str) -> np.ndarray:
    """Returns float32 HxWxC in [0,1] (sRGB display-referred)."""
    return np.array(Image.open(path).convert("RGBA"), dtype=np.float32) / 255.0


def check_middle_gray(png_path: str, expected_srgb: float = 0.50,
                      tolerance: float = 0.05) -> bool:
    """
    Verify 18% gray maps to the expected sRGB value after tone mapping.

    Reference values:
      AgX + exposure=0.0   → scene-linear 0.18 → sRGB ~0.50
      Standard (no TM)     → scene-linear 0.18 → sRGB ~0.46 (gamma 2.2)
      Filmic (deprecated)  → scene-linear 0.18 → sRGB ~0.46–0.48

    Use a known-18%-gray patch in the scene for calibration.
    """
    img = load_png_float(png_path)
    h, w = img.shape[:2]
    patch = img[h//4:3*h//4, w//4:3*w//4, :3]
    mean = float(np.mean(patch))
    ok = abs(mean - expected_srgb) < tolerance
    print(f"[qa] middle-gray: mean={mean:.4f}  expected={expected_srgb:.4f}  "
          f"tol={tolerance:.4f}  {'PASS' if ok else 'FAIL'}")
    return ok


def check_no_clipping(png_path: str, clip_threshold: float = 0.99) -> bool:
    """
    < 1% of pixels should be hard-clipped (AgX rolls highlights off to white gracefully).
    More than 1% clipped = overexposed or AgX not applied.
    """
    img = load_png_float(png_path)
    clipped = float(np.mean(img[:, :, :3] >= clip_threshold))
    ok = clipped < 0.01
    print(f"[qa] clipping: {clipped:.2%}  {'PASS' if ok else 'WARN: highlights clipping'}")
    return ok


def check_no_double_gamma(png_path: str) -> bool:
    """
    Double-gamma heuristic: if mean patch luminance > 0.65 sRGB, view transform was
    applied twice (render PNG re-imported as sRGB and rendered again).
    Expected for correctly tone-mapped AgX render: mid-gray ~0.40–0.55 sRGB.
    """
    img = load_png_float(png_path)
    h, w = img.shape[:2]
    mean = float(np.mean(img[h//4:3*h//4, w//4:3*w//4, :3]))
    suspect = mean > 0.65
    if suspect:
        print(f"[qa] WARN: mean={mean:.4f} — possible double-gamma")
    else:
        print(f"[qa] gamma check PASS: mean={mean:.4f}")
    return not suspect


def check_luminance_range(png_path: str,
                          min_mean: float = 0.15,
                          max_mean: float = 0.85,
                          min_bright: float = 0.02,
                          max_dark: float = 0.40,
                          transparent_bg: bool = True) -> dict:
    """
    Post-render luminance QA. Thresholds for product white-bg packshot:
      mean_luminance:        0.4–0.75
      bright_pixels (>0.8): > 5% (some specular highlight present)
      dark_pixels (<0.05):  < 30% (not shadow-dominated)
    """
    img = load_png_float(png_path)
    mask = (img[:, :, 3] > 0.05) if transparent_bg else np.ones(img.shape[:2], dtype=bool)
    lum  = 0.2126 * img[:, :, 0] + 0.7152 * img[:, :, 1] + 0.0722 * img[:, :, 2]
    lum_m = lum[mask]

    if lum_m.size == 0:
        raise AssertionError("No non-transparent pixels — scene may be empty.")

    mean_lum    = float(lum_m.mean())
    bright_frac = float((lum_m > 0.8).mean())
    dark_frac   = float((lum_m < 0.05).mean())

    errors = []
    if not (min_mean <= mean_lum <= max_mean):
        errors.append(f"mean_lum {mean_lum:.3f} outside [{min_mean}, {max_mean}]")
    if bright_frac < min_bright:
        errors.append(f"bright_fraction {bright_frac:.3f} < {min_bright} — no highlights?")
    if dark_frac > max_dark:
        errors.append(f"dark_fraction {dark_frac:.3f} > {max_dark} — too much shadow?")

    metrics = {"mean_luminance": mean_lum, "bright_frac": bright_frac, "dark_frac": dark_frac}
    if errors:
        print("[qa] FAIL: " + "; ".join(errors))
    else:
        print(f"[qa] PASS: {metrics}")
    return metrics
```

---

## §3. Three.js-specific gotchas

| # | Symptom | Fix |
|---|---|---|
| C-G7 | Tone mapping applied twice with EffectComposer | `OutputPass` last; after r155 renderer disables inline TM automatically |
| C-G8 | Three.js output too bright vs Blender render | Use `SRGBColorSpace`; `LinearSRGBColorSpace` bypasses sRGB OETF → browser double-decodes |
| C-G9 | AgX artifacts on saturated highlights | Upgrade to three.js r161+ (gamut mapping added in PR #27413) |

### Tone mapping correspondence table

| Blender view transform | Three.js constant | Notes |
|---|---|---|
| `AgX` (4.0+ default) | `THREE.AgXToneMapping` | Use r161+; gamut fix in r161 |
| `Filmic` (deprecated 4.x) | `THREE.ACESFilmicToneMapping` | Approximate match only |
| `Khronos PBR Neutral` (4.5+) | `THREE.NeutralToneMapping` | Exact match |
| `Standard` (no TM) | `THREE.NoToneMapping` | Exact: no tone mapping |
