# Shaders — GLSL recipes + TSL/WebGPU

## Mental model
Two GPU stages per draw:
- **Vertex shader** — runs per vertex; outputs clip-space position (`gl_Position = projectionMatrix *
  modelViewMatrix * vec4(position,1.)`); can displace geometry; passes data via `varying`/`out`.
- **Fragment shader** — runs per pixel; outputs color — `gl_FragColor` in GLSL ES 1.00 (Three's
  `ShaderMaterial` default), or a `out vec4` you declare in GLSL ES 3.00. 99% of effects live here.

Data flow: **attributes** (per-vertex: position, normal, uv) → vertex; **uniforms** (constant per draw:
time, resolution, textures) → both; **varyings** (interpolated vertex→fragment: uv, world pos).

Update animated uniforms each frame: `material.uniforms.uTime.value = clock.getElapsedTime()` (or in R3F
`useFrame`).

## Canonical fragment effects (copy-paste, tune)
These are **fragment-shader snippets** — they assume the varyings/uniforms below are declared and fed by a
companion vertex shader. Minimal scaffold (GLSL ES 1.00 — the default `ShaderMaterial`; Three injects the matrices/`uv`/`normal`):
```glsl
/* VERTEX */
varying vec2 vUv; varying vec3 vNormal, vView;
void main(){
  vUv = uv;
  vNormal = normalize(normalMatrix * normal);
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  vView = -mv.xyz;                                  // view-space eye vector (for fresnel)
  gl_Position = projectionMatrix * mv;
}
/* FRAGMENT — declare what each effect uses: */
varying vec2 vUv; varying vec3 vNormal, vView;
uniform float uTime, uAmp, uPower; uniform vec3 uColorA, uColorB, uColorC; uniform sampler2D uMap;
// `luminance` in effect 5 is a value YOU compute, e.g. dot(col, vec3(0.299, 0.587, 0.114)).
```
```glsl
// --- 1. Gradient (interpolate over uv) ---
vec3 grad = mix(uColorA, uColorB, vUv.y);

// --- 2. Value/Perlin-ish noise + fBm (organic clouds/flow/marble) ---
float hash(vec2 p){ return fract(sin(dot(p, vec2(127.1,311.7)))*43758.5453); }
float noise(vec2 p){ vec2 i=floor(p),f=fract(p); f=f*f*(3.-2.*f);
  return mix(mix(hash(i),hash(i+vec2(1,0)),f.x), mix(hash(i+vec2(0,1)),hash(i+vec2(1,1)),f.x), f.y); }
float fbm(vec2 p){ float v=0.,a=.5; for(int i=0;i<5;i++){ v+=a*noise(p); p*=2.; a*=.5; } return v; }

// --- 3. UV distortion (liquid/heat/hover-warp): offset before sampling a texture ---
vec2 uv = vUv + uAmp * vec2(fbm(vUv*3. + uTime*0.1), fbm(vUv*3. - uTime*0.1));
vec4 tex = texture2D(uMap, uv);

// --- 4. Fresnel rim (edge glow / hologram / glass edge) ---
float fres = pow(1.0 - max(dot(normalize(vView), normalize(vNormal)), 0.0), uPower);

// --- 5. Ordered (Bayer 4x4) dithering — retro 1-bit / banding-free shading ---
// GLSL ES 3.00 ONLY (WebGL2): the int[](…) array-constructor initializer + reliable dynamic indexing don't
// exist in a default (ES 1.00) ShaderMaterial. Needs glslVersion: THREE.GLSL3 — see the version note below.
float bayer(vec2 p){ int x=int(mod(p.x,4.)),y=int(mod(p.y,4.));
  int m[16]=int[](0,8,2,10,12,4,14,6,3,11,1,9,15,7,13,5);
  return float(m[y*4+x])/16.; }
float d = step(bayer(gl_FragCoord.xy), luminance);

// --- 6. Mesh-gradient blob (animated aurora field via fbm) ---
float n = fbm(vUv*2.0 + uTime*0.05);
vec3 col = mix(uColorA, uColorB, smoothstep(0.3,0.7,n));
col = mix(col, uColorC, smoothstep(0.5,0.9,fbm(vUv*3.0 - uTime*0.03)));
```
> **GLSL ES 1.00 vs 3.00 — read before using effect 5.** The scaffold + effects 1–6 are GLSL ES **1.00**
> (the default `ShaderMaterial`: `varying`, `texture2D`, write `gl_FragColor`). Effect 5 needs **ES 3.00**:
> `new THREE.ShaderMaterial({ glslVersion: THREE.GLSL3, … })`, which flips the *whole* shader —
> `varying`→`in`/`out`, `texture2D`→`texture()`, and `gl_FragColor`→a `out vec4 fragColor;` **you declare**
> (Three still injects `position`/`uv`/`normal` + matrices). It's not a drop-in into the ES 1.00 scaffold —
> convert the entire material when you enable it. (`RawShaderMaterial` needs the `#version 300 es` line +
> all declarations yourself.)

For **SDF metaballs**, sum signed-distance fields and blend with `smin` (smooth-min); for grain, add a
hash-noise term at low amplitude.

## Attaching shaders in Three
- **`ShaderMaterial`** — supply `vertexShader`, `fragmentShader`, `uniforms`; Three injects matrices/built-
  ins. `RawShaderMaterial` injects nothing.
- **`onBeforeCompile(shader)`** — patch a built-in PBR material's generated GLSL (string-replace `#include`
  chunks + add uniforms) so you keep lighting/shadows AND add a custom tweak. Powerful but brittle (depends
  on Three's internal chunk names).
- **Drei `shaderMaterial()`** — ergonomic factory for R3F (see `r3f-drei.md`).

## TSL (Three Shading Language) — the modern path
Write shaders as JS node graphs; TSL compiles to **GLSL (WebGL2) AND WGSL (WebGPU)** automatically, does
dead-code elimination, and unlocks GPU **compute**. The only write-once-for-both-backends path. Import
from `three/tsl`; assign to `material.colorNode`/`positionNode` on a `*NodeMaterial`.
```js
import * as THREE from "three/webgpu";
import { color, uv, mix, sin, time, positionLocal } from "three/tsl";

const renderer = new THREE.WebGPURenderer({ antialias: true });
await renderer.init();                       // REQUIRED before first render; falls back to WebGL2
const m = new THREE.MeshStandardNodeMaterial();
m.colorNode    = mix(color(0x5b8cff), color(0xff5bd0), uv().y);
m.positionNode = positionLocal.add(sin(time.add(positionLocal.y)).mul(0.1)); // vertex displacement
```
**Default new flagship 3D to TSL + `WebGPURenderer`** — the forward path (write-once for both backends).
`await renderer.init()` is required and **falls back to WebGL2 automatically**. WebGPU is widely supported
in 2026 but still maturing (not yet 100% feature-parity with `WebGLRenderer`, which remains the most
mature/compatible baseline) — so always keep, and verify on, the WebGL2 fallback. For uniforms:
`const t = uniform(0); m.colorNode = ...t...; // t.value = ...`.

## Performance
Fragment shaders are fill-rate bound (overdraw, transmission, big blurs kill mobile). Keep `numOctaves`
low (≤3–4 in fbm), clamp resolution/DPR, avoid full-screen heavy passes on phones, and prefer a static
poster on low-end. (See `integration-fallbacks.md` + `atelier-perf-a11y`.)
