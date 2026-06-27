# React Three Fiber + Drei

R3F (v9, React 19) is a React reconciler that renders to a Three.js scene graph. JSX maps to Three
classes (lowercased): `<mesh>` = `new THREE.Mesh()`, `<boxGeometry args={[1,1,1]}>` passes constructor
args. Props set properties; `attach` wires a child onto a parent property (geometry/material auto-attach).

## Minimal scene
```tsx
import { Canvas, useFrame } from "@react-three/fiber";
import { useRef } from "react";

function Box() {
  const ref = useRef<THREE.Mesh>(null!);
  useFrame((_, dt) => { ref.current.rotation.y += dt * 0.5; }); // mutate refs; NEVER setState per frame
  return (
    <mesh ref={ref}>
      <boxGeometry args={[1, 1, 1]} />
      <meshStandardMaterial color="orange" />
    </mesh>
  );
}

export default function Scene() {
  return (
    <Canvas camera={{ position: [0, 0, 5], fov: 45 }} dpr={[1, 2]} frameloop="demand">
      <ambientLight intensity={0.4} />
      <directionalLight position={[3, 3, 3]} />
      <Box />
    </Canvas>
  );
}
```
- `useFrame((state, delta) => ...)` is the render loop — mutate refs directly; calling `setState` here
  re-renders the React tree every frame (jank).
- `useThree()` → `gl` (renderer), `scene`, `camera`, `size`, `viewport`.
- `dpr={[1, 2]}` clamps device pixel ratio (mobile fill-rate). `frameloop="demand"` + `invalidate()` for
  static scenes (saves battery).
- R3F disposes objects on unmount automatically (unlike raw Three).

### WebGPU canvas (default for new flagship work)
R3F v9's `gl` prop accepts an **async factory** returning a `WebGPURenderer` (which needs `await init()`).
Import Three from `three/webgpu`, `extend(THREE)` to register Node materials as JSX, then drive them with
TSL. The renderer falls back to WebGL2 automatically; WebGPU is still maturing (not full feature-parity),
so keep the plain `<Canvas>` (WebGLRenderer) as the baseline/fallback and verify on it.
```tsx
import * as THREE from "three/webgpu";
import { Canvas, extend } from "@react-three/fiber";
extend(THREE as any);                                    // Node materials usable as JSX
<Canvas
  dpr={[1, 2]}
  gl={async (props) => {                                 // async → WebGPU (auto WebGL2 fallback)
    const renderer = new THREE.WebGPURenderer(props as any);
    await renderer.init();
    return renderer;
  }}>
  <mesh><boxGeometry /><meshBasicNodeMaterial /></mesh>
</Canvas>
```

Feature-detect before committing UI to WebGPU: `const hasWebGPU = !!navigator.gpu` — and note even when the
API exists, `await navigator.gpu.requestAdapter()` can return `null` on a blocklisted GPU. The async `gl`
factory's auto-fallback covers *unsupported* engines at **init**; a *runtime* device-loss still needs the
poster swap (`renderer.getDevice?.().lost` → fallback — see `integration-fallbacks.md`).

## Drei — the helpers you'll actually use
```tsx
import { OrbitControls, Environment, useGLTF, Html, Text, Instances, Instance,
         MeshTransmissionMaterial, PerformanceMonitor, AdaptiveDpr, Float } from "@react-three/drei";
```
- **`<Environment preset="city" />`** — HDRI image-based lighting + reflections. The easiest way to make
  PBR/glass/metal look right. (Compress HDRIs; they're large.)
- **`useGLTF("/model.glb")`** (+ `useGLTF.preload`) — load models; **DRACO + Meshopt are on by default**
  (the signature is `useGLTF(path, useDraco = true, useMeshOpt = true)`), with the DRACO decoder fetched
  from a Google CDN. For offline/self-hosted, pass a local decoder path: `useGLTF(url, "/draco/")` (or
  `useGLTF.setDecoderPath`). Wrap the scene in `<Suspense fallback={...}>`.
- **`<Html>`** — project real DOM into 3D space (`transform`, `occlude`). Costly with many instances.
- **`<Text>`** — sharp SDF text (troika) at any scale; preload fonts to avoid pop-in.
- **`<Instances>`/`<Instance>`** — ergonomic InstancedMesh; one draw call for many repeats (big perf win).
- **`<MeshTransmissionMaterial>`** — the go-to glass/refraction material (needs an Environment). Expensive
  — gate `samples`/`resolution`, drop on mobile.
- **`<PerformanceMonitor>` / `<AdaptiveDpr>`** — auto-scale quality to measured FPS.
- **`<Float>`, `<Stage>`, `<Center>`, `<ContactShadows>`** — staging niceties.

## R3F add-ons & ecosystem
- **Physics → `@react-three/rapier`** (Rapier, Rust→WASM) — the current standard: fast, **deterministic**,
  v2 supports R3F v9 / React 19. (Older `@react-three/cannon` is effectively superseded.)
- **Post-processing → `@react-three/postprocessing`** — wires the `postprocessing` composer (bloom, DoF,
  SSAO, vignette) into R3F declaratively. Cheaper/cleaner than rolling EffectComposer by hand.
- **In-canvas UI → `@react-three/uikit`** (`@pmndrs/uikit`, v1) — real flexbox UI (buttons/text/inputs,
  scroll, theming) rendered **inside** WebGL via Yoga; instanced + fast. Use for HUDs and **spatial/VR**
  menus that must live in the GL layer — vs `<Html>`, which is a DOM overlay (not GL-native or VR-capable).
- **Gaussian Splatting (3DGS)** — photoreal radiance-field scenes in-browser. **Spark** (`@sparkjsdev/spark`,
  Three.js) fuses splats *and* mesh, 98%+ WebGL2, reads `.PLY/.SPZ/.SPLAT/.SOG`; Three.js and Babylon 9 also
  load splats natively. Files are heavy (tens of MB) → lazy-load, LOD, and ship a poster fallback.

## Custom shader material in R3F (Drei factory)
```tsx
import { shaderMaterial } from "@react-three/drei";
import { extend, useFrame } from "@react-three/fiber";

const WaveMaterial = shaderMaterial(
  { uTime: 0, uColor: new THREE.Color("#5b8cff") },
  /* vertex */   `varying vec2 vUv; void main(){ vUv=uv; gl_Position=projectionMatrix*modelViewMatrix*vec4(position,1.); }`,
  /* fragment */ `uniform float uTime; uniform vec3 uColor; varying vec2 vUv;
                  void main(){ float w=0.5+0.5*sin(vUv.x*10.+uTime); gl_FragColor=vec4(uColor*w,1.); }`
);
extend({ WaveMaterial });
function Plane(){ const m=useRef<any>(null!); useFrame((_,dt)=>{ m.current.uTime+=dt; });
  return <mesh><planeGeometry args={[4,4,64,64]} /><waveMaterial ref={m} /></mesh>; }
```
(See `shaders-glsl-tsl.md` for the shader effects themselves.)

## Compressed assets — loader wiring (KTX2 / DRACO / Meshopt)
Compression only kicks in if the loader is configured. In **R3F**, `useGLTF` wires DRACO + Meshopt for you
(local decoder: `useGLTF(url, "/draco/")`); for **KTX2/Basis** textures inside a glTF, extend the loader:
```ts
import { useGLTF } from "@react-three/drei";
import { KTX2Loader } from "three/addons/loaders/KTX2Loader.js";
// 4th arg extends the GLTFLoader; gl from useThree()
useGLTF(url, true, true, (loader) =>
  loader.setKTX2Loader(new KTX2Loader().setTranscoderPath("/basis/").detectSupport(gl)));
```
**Vanilla Three** — wire all three onto the GLTFLoader once and reuse:
```ts
import { GLTFLoader }   from "three/addons/loaders/GLTFLoader.js";
import { DRACOLoader }  from "three/addons/loaders/DRACOLoader.js";
import { KTX2Loader }   from "three/addons/loaders/KTX2Loader.js";
import { MeshoptDecoder } from "three/addons/libs/meshopt_decoder.module.js";
const draco = new DRACOLoader().setDecoderPath("/draco/");
const ktx2  = new KTX2Loader().setTranscoderPath("/basis/").detectSupport(renderer);
const loader = new GLTFLoader().setDRACOLoader(draco).setKTX2Loader(ktx2).setMeshoptDecoder(MeshoptDecoder);
```
Self-host the decoder/transcoder files (copy from `three/examples/jsm/libs/{draco,basis}/`). KTX2 GPU-
compressed textures stay compressed in VRAM (~4–8× smaller than decoded PNG/JPG) and transcode to the GPU's
native format — the single biggest texture-memory win on mobile.

## Performance rules (same as raw Three)
- **Draw calls dominate** → keep them **< 100** (>500 degrades even strong GPUs); watch
  `renderer.info.render.calls`. Collapse via instancing / `BatchedMesh` (different geos, one material) / merge
  geometry / reuse materials. Watch `renderer.info.memory` for leaks (GPU resources never GC).
- **Dispose** geometries/textures/render-targets on teardown (R3F handles unmount; manual for dynamic).
- Clamp DPR ≤ 2; compress assets (DRACO/Meshopt geometry, KTX2/Basis textures).
- Lazy-load the Canvas (dynamic import); pause with `frameloop="demand"` or IntersectionObserver when
  offscreen. (Full perf/a11y in `integration-fallbacks.md` + `atelier-perf-a11y`.)

## Vanilla Three / OGL
Non-React or tiny shader-only widgets → vanilla Three.js or **OGL** (minimal WebGL2, ~tens of KB, you
write the GLSL). Same scene/camera/renderer mental model; you manage the loop + dispose yourself.
