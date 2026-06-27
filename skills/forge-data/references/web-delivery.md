# forge-data — Web Delivery Reference

gltf-transform / gltfpack / toktx pipelines, KTX2 selection rules, web budget tiers, and Core
Web Vitals alignment for 3D assets. Decision authority: **forge-optimize**.

## Contents
- §1. Budget tiers (Khronos 3D Commerce + practitioner consensus)
- §2. Compression selection rules
- §3. Tool installation (Windows)
- §4. KTX2 encoding recipes
- §5. Three.js loader wiring
- §6. CWV alignment
- §7. Optimization size reduction targets

---

## §1. Budget tiers

| Scenario | Max GLB size | Max triangles | Max draw calls/frame | Max texture res |
|----------|-------------|---------------|---------------------|-----------------|
| Desktop hero (viewport-filling) | 3 MB | 250,000 | < 100 | 2048×2048 |
| Mobile AR / mobile hero | 3 MB | 150,000 | < 20 (strict) | 2048×2048 |
| Single-item 3D catalogue (mobile) | 3 MB | 50,000 | < 20 | 1024×1024 |
| Decorative / background prop | 500 KB | 5,000 | < 5 | 512×512 |
| Banner ad | 500 KB | 30,000 | < 5 | 512×512 |
| Web planning tool (per item) | 1 MB | 40,000 | < 5 | 1024×1024 |
| Scene total (desktop, 60 FPS) | — | 500,000 | < 100 | — |
| Scene total (mobile, 60 FPS) | — | 150,000–200,000 | < 50 | — |

**Key insight:** Draw calls dominate over triangle count on mobile. 500 K tris / 20 draw calls
runs faster than 100 K tris / 200 draw calls. Fix draw calls (via join/instance) first.

---

## §2. Compression selection rules

**Geometry:**
| Situation | Codec | Notes |
|-----------|-------|-------|
| Static mesh | Draco (`edgebreaker`) | 70–90% geometry size reduction |
| Animated mesh / morph targets | Meshopt | Draco CANNOT compress animations or morph targets |
| Downstream tools without Draco/Meshopt | Quantization only | `gltf-transform quantize` |
| CDN with gzip/Brotli | Meshopt + gzip | ≈ Draco in transfer size; faster decode on CPU |

**Textures:**
| Texture type | Encoding | Notes |
|-------------|---------|-------|
| Color / albedo / emissive | ETC1S | Smaller file; adequate for flat color areas |
| Normal maps, ORM (packed data) | UASTC | Preserves per-channel precision ETC1S destroys |
| Quick / simple scenes (1–3 textures) | WebP | Avoids toktx dependency; no GPU memory savings |
| GPU-memory-critical (WebXR, mobile VR) | KTX2 always | 4–8× VRAM reduction vs PNG/JPEG |
| ETC1S artifacts visible on color texture | UASTC or WebP | Switch that specific texture only |

**Draco quantization bits:**
- Default 14-bit can cause visible seams on large-scale / photogrammetry models.
- Use `--quantize-position 20` for photogrammetry or highly detailed models.

---

## §3. Tool installation (Windows)

```powershell
# gltf-transform (Node LTS required: 18/20/22)
npm install --global @gltf-transform/cli
gltf-transform --version    # expect 4.4.0+

# gltfpack native binary (RECOMMENDED over npm for -tc texture flag)
# Download gltfpack-windows.zip from:
# https://github.com/zeux/meshoptimizer/releases/tag/v0.21
# Extract gltfpack.exe to C:\tools\ and add to PATH

# toktx (for gltf-transform etc1s / uastc commands)
# Download Windows installer from:
# https://github.com/KhronosGroup/KTX-Software/releases
# Add C:\Program Files\KTX-Software\bin to PATH:
[Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Program Files\KTX-Software\bin", "User")
toktx --version     # expect 4.3.x

# Verify all tools
gltf-transform --version
gltfpack -h
toktx --version
where.exe gltf-transform
where.exe gltfpack
where.exe toktx
```

**Sharp install fail (gltf-transform image dep):**
```powershell
npm config set sharp_binary_host "https://npmmirror.com/mirrors/sharp"
npm config set sharp_libvips_binary_host "https://npmmirror.com/mirrors/sharp-libvips"
npm install --global @gltf-transform/cli
```

---

## §4. KTX2 encoding recipes

```powershell
# ETC1S (albedo / color textures) — small file, medium quality
toktx --t2 --encode etc1s --clevel 4 --qlevel 255 --genmipmap out_basecolor.ktx2 in_basecolor.png

# UASTC (normal maps, ORM) — high quality, larger file
toktx --t2 --encode uastc --uastc_quality 4 --uastc_rdo_l 0.5 --uastc_rdo_d 65536 --zcmp 22 --genmipmap out_normal.ktx2 in_normal.png

# UASTC for normal map (tighter RDO for sharper gradients)
toktx --t2 --encode uastc --uastc_quality 4 --uastc_rdo_l 0.25 --uastc_rdo_d 65536 --zcmp 22 --genmipmap out_normalmap.ktx2 in_normalmap.png
```

**Key toktx flags:**
- `--t2`: output KTX2 format (not legacy KTX)
- `--genmipmap`: generate full mip pyramid (REQUIRED; missing mips = GPU stall)
- `--zcmp 22`: Zstandard supercompression level 22 (max; slow but smallest)
- `--clevel 4`: ETC1S codec compression level (0–5; default 1)
- `--qlevel 255`: ETC1S quality (1–255; 255 = highest quality)
- `--uastc_quality 4`: UASTC encode quality (0–4; 4 = best/slowest)

**gltf-transform KTX2 via CLI (delegates to toktx):**
```powershell
gltf-transform uastc input.glb out.glb `
  --slots "{normalTexture,occlusionTexture,metallicRoughnessTexture}" `
  --level 4 --rdo --rdo-lambda 4 --zstd 18
gltf-transform etc1s out.glb output-final.glb --quality 255
```

---

## §5. Three.js loader wiring

```javascript
// loader-setup.mjs — configure ONCE, reuse everywhere
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';
import { DRACOLoader } from 'three/addons/loaders/DRACOLoader.js';
import { KTX2Loader } from 'three/addons/loaders/KTX2Loader.js';
import { MeshoptDecoder } from 'three/addons/libs/meshopt_decoder.module.js';

export function createGLTFLoader(renderer) {
  const dracoLoader = new DRACOLoader();
  dracoLoader.setDecoderPath('/static/draco/');  // trailing slash required
  dracoLoader.preload();                          // optional WASM preload

  // MUST be called AFTER new THREE.WebGLRenderer(...)
  const ktx2Loader = new KTX2Loader();
  ktx2Loader.setTranscoderPath('/static/basis/');
  ktx2Loader.detectSupport(renderer);            // reads GPU capabilities

  const loader = new GLTFLoader();
  loader.setDRACOLoader(dracoLoader);
  loader.setKTX2Loader(ktx2Loader);
  loader.setMeshoptDecoder(MeshoptDecoder);
  return loader;
}

// Copy decoder files:
// node_modules/three/examples/jsm/libs/draco/ → public/static/draco/
// node_modules/three/examples/jsm/libs/basis/ → public/static/basis/
```

**Handoff asset contract (forge-optimize → atelier-webgl):**
- GLB: DRACO + Meshopt; naming `public/forge/<slug>-hero.glb`
- Poster WebP: rendered first (build-the-fallback-first rule); naming `public/forge/<slug>-hero-poster.webp`
- Local Draco decoder path: `public/draco/`
- Formats: `KHR_draco_mesh_compression` or `EXT_meshopt_compression` in GLB extensions

---

## §6. CWV alignment

| CWV Metric | Target | 3D-specific mitigations |
|-----------|--------|------------------------|
| LCP | < 2.5s | Defer 3D bundle past initial paint; LCP = DOM text/image, not canvas |
| INP | < 200ms | Off-thread Draco decode via Web Worker / OffscreenCanvas |
| CLS | < 0.1 | Reserve canvas space with `aspect-ratio` CSS; don't inject canvas after paint |
| TBT | < 200ms | Code-split Three.js; lazy-load GLB after `load` event; async geometry build |

**Mobile-first rule:** For marketing / brand sites where 3D is decorative, serve a static WebP
screenshot on mobile breakpoints. 3D on mobile = product configurators and viewers, not brand
animations.

---

## §7. Optimization size reduction targets

Typical reduction chain for a Mixamo-style character (starting at 11 MB FBX):

```
Raw FBX:                  100%  (11 MB)
→ Blender GLB export:      75%  (8.2 MB)
→ gltf-transform prune/dedup/weld:  26%  (2.1 MB)
→ + draco:                  9%  (720 KB)
→ + uastc + etc1s:          5%  (420 KB)
```

90–95% total reduction is typical. The `3 MB single-asset` budget is achievable for almost any
hero prop with this pipeline.

**WebP vs KTX2 GPU memory comparison:**
- WebP 200 KB on disk → ~16 MB on GPU (decompressed to RGBA at 2048²)
- KTX2 ETC1S same texture → ~11 MB on GPU (stays compressed in GPU VRAM)
- WebP saves bandwidth only; KTX2 saves both bandwidth AND GPU memory.
