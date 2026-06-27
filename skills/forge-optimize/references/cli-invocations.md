# forge-optimize — CLI Invocations Reference

# contents
- §1. Install & preflight
- §2. Full pipeline (step-by-step, order is load-bearing)
- §3. LOD simplification chain
- §4. gltfpack (native binary)
- §5. Texture compression detail (toktx / ktx CLI)
- §6. Validation commands

---

## §1. Install & preflight

```powershell
# Install gltf-transform (Node LTS 18/20/22 required)
npm install --global @gltf-transform/cli
gltf-transform --version   # expect 4.4.0+

# Install gltf-validator (optional standalone)
npm install --global gltf-validator

# Verify gltf-transform can find toktx (required for uastc/etc1s commands)
where.exe toktx             # expect C:\Program Files\KTX-Software\bin\toktx.exe

# Verify node
node --version              # expect 18+
```

---

## §2. Full pipeline (step-by-step)

**Order is load-bearing.** Violating it silently degrades quality or produces corrupt output.

```
1. prune + dedup     (remove waste — always first)
2. weld              (topology cleanup — REQUIRED before simplify)
3. simplify          (optional LOD reduction)
4. join / instance   (draw-call reduction — for static scenes only)
5. resize            (texture resize — before codec)
6. geometry codec    (draco OR meshopt — mutually exclusive)
7. texture codec     (uastc → etc1s, or webp — always last)
8. validate
```

### One-shot (80% of cases)

```powershell
# One-shot: prune + dedup + weld + meshopt + webp textures
gltf-transform optimize input.glb output.glb `
  --compress meshopt `
  --texture-compress webp

# One-shot with Draco (static mesh, max size reduction)
gltf-transform optimize input.glb output.glb `
  --compress draco `
  --texture-compress webp `
  --texture-resize 1024

# One-shot with KTX2 (requires toktx on PATH)
gltf-transform optimize input.glb output.glb `
  --compress meshopt `
  --texture-compress ktx2
```

### Fine-grained pipeline (full control)

```powershell
# Step 1: Remove orphaned nodes, materials, textures, accessors
gltf-transform prune input.glb step1.glb

# Step 2: Deduplicate identical accessors + textures (content-hash)
gltf-transform dedup step1.glb step2.glb

# Step 3: Merge near-coincident vertices (MANDATORY before simplify)
gltf-transform weld step2.glb step3.glb --tolerance 0.0001

# Step 4a: Simplify (optional — 0.75 = keep 75% of vertices)
gltf-transform simplify step3.glb step4.glb --ratio 0.75 --error 0.001

# Step 4b: Join static meshes (draw-call reduction)
# WARNING: destroys individual mesh identity — do NOT use on animated or interactive parts
gltf-transform join step3.glb step4b.glb

# Step 4c: GPU instancing (for scenes with repeated identical meshes, min 5 instances)
gltf-transform instance step4b.glb step4c.glb

# Step 5: Resize oversized textures (power-of-two recommended for WebGL1)
gltf-transform resize step4.glb step5.glb --width 2048 --height 2048

# Step 6a: Geometry compression — Meshopt (animated + static; faster decode)
gltf-transform meshopt step5.glb step6.glb --level medium
# level: 'low' | 'medium' (QUANTIZE) | 'high' (FILTER — needs gzip/brotli at CDN)

# Step 6b: Geometry compression — Draco (static only; higher compression, slower decode)
# gltf-transform draco step5.glb step6.glb --method edgebreaker --quantize-position 14
# DO NOT use Draco on animated/rigged/morph-target meshes

# Step 7a: Texture compression — UASTC for data textures (normal, ORM, clearcoat)
# Requires toktx on PATH
gltf-transform uastc step6.glb step7a.glb `
  --slots "{normalTexture,occlusionTexture,metallicRoughnessTexture}" `
  --level 4 --rdo --rdo-lambda 4 --zstd 18

# Step 7b: ETC1S for color textures (base color, emissive — smaller file)
gltf-transform etc1s step7a.glb output.glb --quality 192

# Step 8: Validate
gltf-transform validate output.glb
if ($LASTEXITCODE -ne 0) { throw "GLB validation failed" }
```

### Codec-only invocations (common quick paths)

```powershell
# Meshopt only (no texture change)
gltf-transform meshopt input.glb output-meshopt.glb --level medium

# Draco only (no texture change)
gltf-transform draco input.glb output-draco.glb --method edgebreaker

# WebP textures only (no geometry compression)
gltf-transform optimize input.glb output-webp.glb --texture-compress webp

# Quantize only (no codec — for targets without Draco/Meshopt support)
gltf-transform quantize input.glb output-quantized.glb
```

### Draco quantization bits (safe defaults)

```
POSITION:  14 bits  (16 = lossless; 12 = seam risk on large meshes; 20 for photogrammetry)
NORMAL:    10 bits
TEXCOORD:  12 bits  (10 = UV seam risk on fine details)
COLOR:      8 bits
GENERIC:   12 bits
```

```powershell
# Override quantization (photogrammetry — use higher precision)
gltf-transform draco input.glb output.glb `
  --method edgebreaker `
  --quantize-position 20 `
  --quantize-normal 10 `
  --quantize-texcoord 12
```

---

## §3. LOD simplification chain

**Cascade strategy:** simplify from the previous LOD, not from source each time. Smoother
visual transitions; better attribute preservation. Error accumulates — regenerate from LOD0
if LOD4 drift is visible.

```powershell
# Build: hero-lod0.glb, hero-lod1.glb, hero-lod2.glb from a single source
# Weld once on source, then cascade simplify

gltf-transform weld hero.glb hero-welded.glb --tolerance 0.0001

# LOD0 = welded source (copy)
Copy-Item hero-welded.glb hero-lod0.glb

# LOD1 = 50% of LOD0
gltf-transform simplify hero-lod0.glb hero-lod1.glb --ratio 0.5 --error 0.001

# LOD2 = 50% of LOD1 (= 25% of original)
gltf-transform simplify hero-lod1.glb hero-lod2.glb --ratio 0.5 --error 0.001

# LOD3 = 40% of LOD2 (= ~10% of original) — use --error 0.005 for more aggressive
gltf-transform simplify hero-lod2.glb hero-lod3.glb --ratio 0.4 --error 0.005
```

Then compress each LOD independently (same codec, same texture settings):
```powershell
foreach ($lod in @("lod0","lod1","lod2","lod3")) {
  gltf-transform optimize "hero-$lod.glb" "hero-$lod-opt.glb" `
    --compress meshopt --texture-compress webp
}
```

Three.js `THREE.LOD` wiring → see **`references/budgets-and-runtime.md §3`**.

---

## §4. gltfpack (native binary)

**Use when:** no Node.js available, batch processing thousands of files, animation-heavy scenes.
Requires the native binary (npm version CANNOT compress textures).

```powershell
# Download binary: https://github.com/zeux/meshoptimizer/releases
# Extract gltfpack.exe to C:\tools\gltfpack\ and add to PATH

# Basic Meshopt compression
gltfpack.exe -i scene.glb -o scene-opt.glb -cc

# Meshopt + KTX2 textures (native binary only — npm cannot do this)
gltfpack.exe -i scene.glb -o scene-tc.glb -cc -tc

# Meshopt + 50% simplification
gltfpack.exe -i scene.glb -o scene-s.glb -cc -si 0.5

# Meshopt + simplification + KTX2 + GPU instancing
gltfpack.exe -i scene.glb -o scene-full.glb -cc -si 0.5 -mi -tc

# Aggressive simplification (ignores seam topology) — LOD3+ only
gltfpack.exe -i scene.glb -o scene-lod3.glb -cc -si 0.1 -sa

# Keep named nodes/materials for runtime manipulation
gltfpack.exe -i scene.glb -o scene-k.glb -kn -km

# Verbose — shows triangle/vertex counts (useful for LOD QA)
gltfpack.exe -i scene.glb -o scene-opt.glb -cc -v

# Disable quantization (larger file, no dequantization nodes added to scene)
gltfpack.exe -i scene.glb -o scene-noq.glb -noq -cc
```

**Windows path spaces:** always quote paths — `gltfpack.exe -i "C:\My Models\scene.glb" -o "C:\out\opt.glb"`.

---

## §5. Texture compression detail (toktx / ktx CLI)

For use outside gltf-transform, or when maximum control over per-texture encoding is needed.

### ETC1S (color textures: baseColor, emissive flat areas)

```powershell
# toktx ETC1S — good quality
toktx --t2 --encode etc1s --clevel 4 --qlevel 192 --genmipmap `
  out_basecolor.ktx2 in_basecolor.png

# toktx ETC1S — maximum quality
toktx --t2 --encode etc1s --clevel 5 --qlevel 255 --genmipmap `
  out_basecolor_hq.ktx2 in_basecolor.png

# ktx CLI (KTX-Software v4+ unified tool)
ktx create --encode etc1s --format VK_FORMAT_R8G8B8A8_SRGB `
  in_basecolor.png out_basecolor.ktx2
```

### UASTC (data textures: normal maps, ORM, clearcoat — preserves per-channel precision)

```powershell
# toktx UASTC — normal map (tight RDO range for quality)
toktx --t2 --encode uastc `
  --uastc_quality 4 `
  --uastc_rdo_l 0.5 `
  --uastc_rdo_d 65536 `
  --zcmp 22 `
  --genmipmap `
  out_normal.ktx2 in_normal.png

# toktx UASTC — ORM map (Occlusion/Roughness/Metalness)
toktx --t2 --encode uastc `
  --uastc_quality 3 `
  --uastc_rdo_l 1.0 `
  --zcmp 18 `
  --genmipmap `
  out_orm.ktx2 in_orm.png

# ktx CLI UASTC with Zstandard supercompression (MANDATORY — without zcmp/zstd UASTC
# is larger than JPEG with no VRAM benefit)
ktx create --encode uastc --uastc-quality 3 --zstd 18 `
  --format VK_FORMAT_R8G8B8A8_SRGB in_normal.png out_normal.ktx2
```

### Texture slot strategy (critical rule)

| Texture slot | Codec | Why |
|---|---|---|
| baseColorTexture | ETC1S | Luma-chroma correlation is fine; smaller file |
| emissiveTexture (flat) | ETC1S | Same |
| emissiveTexture (detailed) | UASTC | High contrast color detail needs quality |
| normalTexture | UASTC | Channel independence; ETC1S causes serious banding |
| occlusionTexture | UASTC | Precision critical; packed channel |
| metallicRoughnessTexture | UASTC | R+G are unrelated packed signals |

**UASTC without Zstandard supercompression** (`--zcmp 18` / `--zstd 18`) produces files
1–2× LARGER than JPEG. Always apply it. Without it, the VRAM benefit does not materialize
in file size.

---

## §6. Validation commands

```powershell
# Khronos spec validation (built into gltf-transform)
gltf-transform validate output.glb

# Inspect: triangle count, draw calls, texture sizes, extension list
gltf-transform inspect output.glb

# Check for dual-codec bug (should see only one extension)
gltf-transform inspect output.glb | Select-String "meshopt\|draco"
# If both appear: pipeline error — the file has both codecs (corrupt)

# Standalone gltf-validator (more detailed error messages)
gltf_validator.exe output.glb --validate-resources -o -r

# File size gate (fail if > 3 MB)
$size = (Get-Item output.glb).Length
if ($size -gt 3MB) {
  Write-Error "GLB exceeds 3 MB budget: $([math]::Round($size/1MB, 2)) MB"
}

# Sanity: confirm meshopt OR draco present, not both, not neither
gltf-transform inspect output.glb | Select-String "EXT_meshopt\|KHR_draco"
```
