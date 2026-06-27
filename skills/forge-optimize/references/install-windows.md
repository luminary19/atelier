# forge-optimize — Windows Install & Gotchas Reference

# contents
- §1. gltf-transform install (Node.js, Sharp)
- §2. KTX-Software install (toktx / ktx CLI)
- §3. gltfpack native binary install
- §4. Windows-specific gotchas & fixes

---

## §1. gltf-transform install

**Requires Node.js LTS 18, 20, or 22.** Verify with `node --version`.

```powershell
# Install globally
npm install --global @gltf-transform/cli

# Verify
gltf-transform --version   # expect 4.4.0+

# If Sharp (image dep) fails with native binding error:
npm config set sharp_binary_host "https://npmmirror.com/mirrors/sharp"
npm config set sharp_libvips_binary_host "https://npmmirror.com/mirrors/sharp-libvips"
npm install --global @gltf-transform/cli

# Force platform-specific Sharp reinstall:
npm install --os=win32 --cpu=x64 sharp
npm install --global @gltf-transform/cli

# Verify Sharp loads (if this throws, texture compression will silently fail)
node -e "require('sharp'); console.log('Sharp OK')"
```

---

## §2. KTX-Software install (required for uastc / etc1s commands)

```powershell
# Download installer:
# https://github.com/KhronosGroup/KTX-Software/releases
# File: KTX-Software-<version>-Windows-x64.exe
# Installs to: C:\Program Files\KTX-Software\bin\toktx.exe (and ktx.exe)

# Verify install
toktx --version   # expect 4.3.x
where.exe toktx   # should show full path

# If toktx is not on PATH (Windows installer PATH truncation bug):
# The NullSoft installer uses setx which silently truncates PATH at 1024 chars.
# Check current PATH length:
($env:PATH).Length

# Add manually if installer failed:
$ktxBin = "C:\Program Files\KTX-Software\bin"
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
[Environment]::SetEnvironmentVariable("PATH", "$currentPath;$ktxBin", "User")
# Then restart PowerShell.
```

---

## §3. gltfpack native binary install

**Native binary required for texture compression (`-tc`, `-tw` flags).** The npm version is
a WASM wrapper without texture encoder binaries — those flags are silently ignored.

```powershell
# Download Windows binary:
# https://github.com/zeux/meshoptimizer/releases
# File: gltfpack-windows.zip (meshoptimizer v1.1+)

[System.Net.ServicePointManager]::SecurityProtocol = 'Tls12'
Invoke-WebRequest `
  -Uri "https://github.com/zeux/meshoptimizer/releases/download/v1.1/gltfpack-windows.zip" `
  -OutFile "$env:TEMP\gltfpack.zip"
Expand-Archive "$env:TEMP\gltfpack.zip" -DestinationPath "C:\tools\gltfpack"

# Add to PATH:
$env:PATH += ";C:\tools\gltfpack"
# Permanent (user-level):
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
[Environment]::SetEnvironmentVariable("PATH", "$currentPath;C:\tools\gltfpack", "User")

# Verify
gltfpack.exe --version   # or gltfpack -h
```

---

## §4. Windows-specific gotchas & fixes

### Gotcha 1: Sharp fails to load (ERR_DLOPEN_FAILED)

**Symptom:** `gltf-transform optimize ...` throws `Could not load the "sharp" module using
the win32-x64 runtime`.
**Cause:** Sharp prebuilt binary for wrong Node.js version, or version mismatch after Node
upgrade.
**Fix:**
```powershell
npm install --os=win32 --cpu=x64 sharp
npm install -g @gltf-transform/cli --force
# Verify:
node -e "require('sharp')"
```

### Gotcha 2: toktx not on PATH (KTX installer truncation)

**Symptom:** `gltf-transform uastc` or `etc1s` fails with `Error: toktx not found`.
**Cause:** Windows NullSoft/setx truncates PATH at 1024 chars (user) or 2048 chars (system).
**Detect:** `where toktx` returns nothing.
**Fix:**
```powershell
$ktxBin = "C:\Program Files\KTX-Software\bin"
$currentPath = [Environment]::GetEnvironmentVariable("PATH", "User")
[Environment]::SetEnvironmentVariable("PATH", "$currentPath;$ktxBin", "User")
```
Restart PowerShell after updating environment variables.

### Gotcha 3: gltfpack npm cannot compress textures

**Symptom:** `-tc` flag silently ignored or errors when installed via npm.
**Cause:** npm package is a JS/WASM wrapper that lacks the native BasisU encoder.
**Fix:** Use the native binary from GitHub Releases (see §3 above).

### Gotcha 4: Draco breaks animations / morph targets

**Symptom:** Animated GLB loses animation or plays in T-pose after Draco compression.
**Cause:** `KHR_draco_mesh_compression` only covers static vertex buffers. Animation accessors
and morph target data are NOT compressed by Draco.
**Fix:** Use Meshopt for animated/rigged/morph-target meshes. If a scene has both static and
animated parts, apply Meshopt for animations and optionally Draco for non-animated sub-meshes
(advanced: filter by mesh type before encoding).

### Gotcha 5: Draco and Meshopt are mutually exclusive per file

**Symptom:** Running both codecs on one file produces a corrupt or bloated GLB.
**Detect:** `gltf-transform inspect output.glb | Select-String "meshopt\|draco"` — if
BOTH appear, the pipeline is broken.
**Fix:** Choose one. Never chain draco then meshopt (or vice versa) on the same document.

### Gotcha 6: ETC1S artifacts on normal maps / packed textures

**Symptom:** Normal map shows visible banding; metallicRoughness shows block artifacts.
**Cause:** ETC1S prioritizes luma and averages chroma, destroying the independent per-channel
data in packed textures (ORM = R:occlusion, G:roughness, B:metallic — unrelated signals).
**Fix:** Always use UASTC for `normalTexture`, `occlusionTexture`, `metallicRoughnessTexture`.
Use `--slots` in CLI to target specific texture types.
**Detect:** Compare in Babylon.js sandbox or Three.js editor at 100% zoom with flat gray mat.

### Gotcha 7: UASTC without Zstandard supercompression bloats file

**Symptom:** KTX2-compressed GLB is larger than the WebP version.
**Cause:** UASTC is high-quality and low-compression by itself; without `--zcmp`/`--zstd`
the file is 1–2× larger than JPEG with no VRAM benefit.
**Fix:** Always add `--zstd 18` (gltf-transform) or `--zcmp 18` (toktx).

### Gotcha 8: `weld` must precede `simplify`

**Symptom:** `simplify` runs but provides no reduction, or mesh has holes/artifacts.
**Cause:** Non-welded meshes have redundant vertices at shared edges. The simplifier cannot
collapse edges correctly without merged topology.
**Fix:** Always run `weld` before `simplify` in the pipeline. The `optimize` one-shot command
does this internally; the standalone `simplify` command does NOT auto-weld.

### Gotcha 9: KTX2 textures need power-of-two for WebGL1

**Symptom:** Textures black in older WebGL1 contexts (some older iOS, legacy browsers).
**Cause:** WebGL1 requires NPOT textures to be non-mipmapped + clamp-to-edge; block-compressed
textures must be exact multiples of block size.
**Fix:** Resize to power-of-two BEFORE KTX encoding:
```powershell
gltf-transform resize input.glb resized.glb --width 1024 --height 1024
# then: gltf-transform uastc resized.glb output.glb ...
```

### Gotcha 10: `optimize` command uses different `--simplify` defaults

**Symptom:** `gltf-transform optimize --simplify 0.5` behaves differently than standalone
`simplify --ratio 0.5 --error 0.001`.
**Cause:** The `optimize` command's `--simplify` flag uses internal defaults that differ from
the standalone `simplify` command (`ratio: 0.0` = 0% by default in optimize).
**Fix:** For precise simplification, run `simplify` as a standalone step before `optimize`,
or use the Node.js JS API for full control over every parameter.

### Gotcha 11: Windows path separators in gltf-transform / gltfjsx

**Symptom:** `gltf-transform optimize .\raw\model.glb` fails on some Node versions.
**Fix:** Use forward slashes in gltf-transform CLI arguments on Windows:
```powershell
gltf-transform optimize "./raw/model.glb" "./out/model-opt.glb"
# Or use Join-Path and convert separators:
$input  = (Join-Path $PWD "raw\model.glb") -replace '\\', '/'
$output = (Join-Path $PWD "out\model-opt.glb") -replace '\\', '/'
gltf-transform optimize $input $output --compress meshopt
```

### Gotcha 12: Sharp mirror config is session-only

**Symptom:** After setting sharp mirror via `npm config set`, next session forgets it.
**Cause:** `npm config set` writes to the npm user config (`~/.npmrc`); in some environments
this is not persisted.
**Fix:** Write to the project `.npmrc` or use `npm config edit` to open the file directly
and add the mirror settings permanently.
