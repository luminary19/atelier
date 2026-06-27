# forge-optimize — Budgets, Runtime Loader Wiring & Handoff Reference

# contents
- §1. Web budget tiers
- §2. Compression selection decision matrix
- §3. THREE.LOD wiring (Three.js / R3F)
- §4. Poster generation (static fallback)
- §5. Three.js / R3F loader wiring (DRACOLoader / KTX2Loader / MeshoptDecoder)
- §6. Handoff contract to atelier-webgl
- §7. Runtime measurement & draw-call debugging

---

## §1. Web budget tiers

Source: Khronos 3D Commerce v1.0 + 2025 practitioner consensus.

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

**Draw calls dominate over triangle count.** A 500k-triangle scene with 20 draw calls runs
faster than a 100k-triangle scene with 200 draw calls on mobile. Fix draw calls first via
`gltf-transform instance` / `join` (static parts only) or `gltfjsx --instanceall`.

**File size rule of thumb:** aim for ≤ 3 MB for any single interactive GLB (hero product).
Typical pipeline reduction:
```
Raw FBX:           100%  (e.g., 11 MB Mixamo character)
→ GLB export:       75%  (8.2 MB)
→ optimize (prune/dedup/weld):  26%  (2.1 MB)
→ + draco:           9%  (720 KB)
→ + uastc:           5%  (420 KB)
```

### Texture VRAM formula

```
vram_bytes = width × height × 4 × 1.333  // ×4 RGBA, ×1.333 mip chain
// 4096×4096 → 89 MB uncompressed; KTX2 ETC1S ≈ 11 MB, UASTC ≈ 22 MB
```

WebP saves bandwidth but NOT GPU memory — a 200 KB WebP becomes 16 MB on GPU at 2048×2048.
Use KTX2 when GPU memory is the constraint (WebXR, mobile, many textures).

### Texture sizing rule

```
rendered_pixels = canvas_width × object_screen_fraction
appropriate_res = next_power_of_2(rendered_pixels × 2)   // ×2 for Retina
// texture never renders > 256 px → max 512×512 in file
```

---

## §2. Compression selection decision matrix

### Geometry

| Factor | Choose Draco | Choose Meshopt |
|--------|-------------|----------------|
| Static mesh, max size reduction | Yes (50–80%) | No (30–60%) |
| Animated / morph targets | **No — Draco cannot** | **Yes** |
| Scene with 50+ meshes | No (decode cost × N) | Yes |
| 1–3 hero models | Yes | Either |
| Mesh poly count > 1M | Yes | Either |
| CDN with gzip/Brotli | Either | Yes (Meshopt+gzip ≈ Draco size) |
| Load-time priority | No (5–10× slower decode) | Yes (~20% faster than raw) |

**Concrete benchmark data (PlayCanvas):**
- Draco: 655 ms decode / 3.1 MB (large bed mesh) vs uncompressed 24 MB
- Meshopt: 105 ms decode / same mesh

### Textures

| Slot | Codec | Rationale |
|------|-------|-----------|
| baseColorTexture | ETC1S | Color correlation; smaller file |
| emissiveTexture (flat) | ETC1S | Same |
| emissiveTexture (detailed) | UASTC | High contrast color detail |
| normalTexture | **UASTC** | Channel independence; ETC1S = serious artifacts |
| occlusionTexture | **UASTC** | Precision critical |
| metallicRoughnessTexture | **UASTC** | Packed R+G channels, unrelated signals |
| Quick / 1–3 textures | WebP | No toktx dep; browser-compressed only |
| GPU VRAM critical | KTX2 (UASTC+ETC1S) | 4–8× VRAM reduction vs PNG |

---

## §3. THREE.LOD wiring (Three.js / R3F)

After generating LOD GLBs (see `references/cli-invocations.md §3`):

```typescript
// three-lod.ts — load pre-generated LOD GLBs into THREE.LOD
import * as THREE from 'three';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

async function buildLOD(loader: GLTFLoader, baseName: string) {
  const lod = new THREE.LOD();

  const [l0, l1, l2] = await Promise.all([
    loader.loadAsync(`/forge/${baseName}-lod0-opt.glb`),
    loader.loadAsync(`/forge/${baseName}-lod1-opt.glb`),
    loader.loadAsync(`/forge/${baseName}-lod2-opt.glb`),
  ]);

  // addLevel(object, distance) — shown when camera is CLOSER than distance
  lod.addLevel(l0.scene, 0);    // full detail: 0–10 m
  lod.addLevel(l1.scene, 10);   // 50% detail: 10–50 m
  lod.addLevel(l2.scene, 50);   // 25% detail: 50 m+

  scene.add(lod);
  // lod.autoUpdate = true (default) — updates in render loop automatically
  return lod;
}
```

**needle-tools/gltf-progressive (alternative):** embeds LOD metadata in a single GLB.
Lazily fetches lower-LOD geometry based on screen-space density.
```powershell
npm install @needle-tools/gltf-progressive
```
Assets must be pre-processed with the needle-tools exporter or Needle Cloud.

---

## §4. Poster generation (static fallback)

The poster MUST exist before the Canvas mounts. It is the fallback for:
- `prefers-reduced-motion` users
- No-WebGL devices
- Low-end devices (budget decision in `atelier-webgl`)
- Initial paint before 3D loads

### Option A: frame3d (easiest)

```powershell
npm install --global frame3d

# Set Chrome path (Windows):
$env:PUPPETEER_EXECUTABLE_PATH = "C:\Program Files\Google\Chrome\Application\chrome.exe"

# Generate PNG poster
frame3d model=.\public\forge\hero-hero.glb `
  out=.\public\forge\hero-hero-poster.png `
  width=1200 height=800

# Convert to WebP
npx sharp-cli `
  --input .\public\forge\hero-hero-poster.png `
  --output .\public\forge\hero-hero-poster.webp `
  --webp
```

### Option B: screenshot-glb (Shopify)

```powershell
npm install --global screenshot-glb

screenshot-glb `
  -i .\public\forge\hero-hero.glb `
  -o .\public\forge\hero-hero-poster.png `
  -w 1200 -h 800 `
  -m "environment-image=neutral&exposure=1.0"
```

### Option C: Blender headless render (best quality)

For Forge pipeline, the poster can be the same render used for QA in `forge-render`.
The Cycles render (turntable frame 0) produces the poster PNG. Convert to WebP:
```powershell
npx sharp-cli `
  --input .\public\forge\hero-hero-poster.png `
  --output .\public\forge\hero-hero-poster.webp `
  --webp
```

**Poster size QA:**
```powershell
$poster = Get-Item ".\public\forge\hero-hero-poster.webp"
if ($poster.Length -lt 10KB) {
  Write-Error "Poster suspiciously small ($($poster.Length) B). Check generation."
  exit 1
}
Write-Host "Poster OK: $([math]::Round($poster.Length/1KB)) KB"
```

---

## §5. Three.js / R3F loader wiring

Copy decoder files once per web project:
```powershell
Copy-Item -Path ".\node_modules\three\examples\jsm\libs\draco" `
  -Destination ".\public\draco" -Recurse -Force
Copy-Item -Path ".\node_modules\three\examples\jsm\libs\basis" `
  -Destination ".\public\basis" -Recurse -Force
```

### Vanilla Three.js

```typescript
// src/lib/loaders.ts — call once AFTER renderer is created
import { GLTFLoader }     from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader }    from "three/addons/loaders/DRACOLoader.js";
import { KTX2Loader }     from "three/addons/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
import * as THREE from "three";

export function createGLTFLoader(renderer: THREE.WebGLRenderer): GLTFLoader {
  const draco = new DRACOLoader()
    .setDecoderPath("/draco/")   // trailing slash required; self-hosted (NOT gstatic.com)
    .preload();                   // background-preload WASM decoder

  // Order is load-bearing: setTranscoderPath BEFORE detectSupport
  const ktx2 = new KTX2Loader()
    .setTranscoderPath("/basis/")
    .detectSupport(renderer);    // MUST have live renderer — queries GL context for format caps

  return new GLTFLoader()
    .setDRACOLoader(draco)
    .setKTX2Loader(ktx2)
    .setMeshoptDecoder(MeshoptDecoder);
}
```

**Critical ordering trap:** `KTX2Loader.detectSupport(renderer)` must be called AFTER
`new THREE.WebGLRenderer(...)`. Calling it before the renderer exists = silent fallback to
uncompressed (textures render correctly but VRAM savings disappear).

### R3F (React Three Fiber)

```tsx
// In your R3F model component:
import { useThree } from "@react-three/fiber";
import { useGLTF }  from "@react-three/drei";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";

function HeroModel() {
  const { gl } = useThree();

  const { nodes, materials } = useGLTF(
    "/forge/hero-hero.glb",
    true,   // useDraco = true → uses CDN decoder by default; pass "/draco/" for self-hosted
    true,   // useMeshOpt
    (loader) =>
      loader.setKTX2Loader(
        new KTX2Loader().setTranscoderPath("/basis/").detectSupport(gl)
      )
  );

  return (
    <group dispose={null}>
      <mesh geometry={nodes.Body.geometry} material={materials.PBR} castShadow />
    </group>
  );
}

// Preload at module level (before Canvas mounts):
useGLTF.preload("/forge/hero-hero.glb");
```

### Color space / tone mapping (match Blender 4.x AgX)

```typescript
// Set on the renderer after creation
THREE.ColorManagement.enabled = true;        // always; auto-converts hex/CSS to linear
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.AgXToneMapping; // matches Blender 4.x default
renderer.toneMappingExposure = 1.0;
```

---

## §6. Handoff contract to atelier-webgl

`atelier-webgl` expects this file layout (write to `FORGE.md §Output paths` after completing):

```
public/
  forge/
    <slug>-hero.glb          ← optimized GLB (Draco/Meshopt + KTX2/WebP)
    <slug>-hero-poster.webp  ← static fallback (1200×800 min, matches hero viewport)
    <slug>-hero-poster.png   ← source PNG
  draco/                     ← DRACOLoader decoder files
  basis/                     ← KTX2Loader transcoder files
```

**Codec contract** (document in FORGE.md, pass to atelier-webgl):
- Which geometry codec: `draco` | `meshopt` | `none`
- Which texture codec: `ktx2` | `webp` | `none`
- Decoder paths: `/draco/` and/or `/basis/`
- Color space: `AgXToneMapping` (Blender 4.x) or `ACESFilmicToneMapping` (pre-4.x)

After confirming these files exist and sizes are within budget, invoke:
```
Skill("atelier-webgl")
```
Pass the GLB path, poster path, decoder paths, and codec contract. **Run = call the Skill
tool. Writing "hand to atelier-webgl" in prose runs nothing.**

---

## §7. Runtime measurement & draw-call debugging

```typescript
// Add to render loop in dev builds
function renderLoop() {
  requestAnimationFrame(renderLoop);
  renderer.render(scene, camera);

  // Read AFTER render() — values are for the just-completed frame
  const r = renderer.info.render;
  const m = renderer.info.memory;

  if (r.drawCalls > 100) console.warn(`Draw calls over budget: ${r.drawCalls}`);
  if (r.triangles > 500_000) console.warn(`Triangles over budget: ${r.triangles}`);
  if (m.textures > 20) console.warn(`Texture count: ${m.textures}`);
}

// In R3F (dev mode):
function MemoryMonitor() {
  useFrame(({ gl }) => {
    if (process.env.NODE_ENV !== "development") return;
    const r = gl.info.render;
    const m = gl.info.memory;
    // Sample once per second at 60 fps:
    if (r.frame % 60 === 0) {
      console.debug(`DC:${r.drawCalls} Tris:${r.triangles} Tex:${m.textures} Geo:${m.geometries}`);
    }
  });
  return null;
}
// <MemoryMonitor /> inside Canvas during dev only.
```

**Online spot-check tools:**
- `gltf.report` — drag-and-drop; Script tab runs gltf-transform API; shows tri/draw count, VRAM estimate
- `spatialpack.dev` — CLI: `spatialpack analyze model.glb`; returns predicted frame time, ΔE94 perceptual diff
- Khronos glTF Validator — https://github.khronos.org/glTF-Validator/
- Khronos glTF-Compressor — side-by-side compression comparison in browser

### Core Web Vitals alignment for 3D

| CWV | Target | 3D mitigation |
|-----|--------|---------------|
| LCP | < 2.5s | Defer 3D bundle past initial paint; LCP = DOM text/image not canvas |
| INP | < 200ms | Avoid main-thread Draco decode blocking; use Web Worker / OffscreenCanvas |
| CLS | < 0.1 | Reserve canvas with `aspect-ratio` CSS; never inject after paint |
| TBT | < 200ms | Code-split Three.js; lazy-load GLB after `load` event |
