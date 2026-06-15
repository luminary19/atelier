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

## Performance rules (same as raw Three)
- **Draw calls dominate** → instancing / `BatchedMesh` / merge geometry / reuse materials.
- **Dispose** geometries/textures/render-targets on teardown (R3F handles unmount; manual for dynamic).
- Clamp DPR ≤ 2; compress assets (DRACO/Meshopt geometry, KTX2/Basis textures).
- Lazy-load the Canvas (dynamic import); pause with `frameloop="demand"` or IntersectionObserver when
  offscreen. (Full perf/a11y in `integration-fallbacks.md` + `atelier-perf-a11y`.)

## Vanilla Three / OGL
Non-React or tiny shader-only widgets → vanilla Three.js or **OGL** (minimal WebGL2, ~tens of KB, you
write the GLSL). Same scene/camera/renderer mental model; you manage the loop + dispose yourself.
