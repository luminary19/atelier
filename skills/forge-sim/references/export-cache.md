# forge-sim — Cache Export Reference

## Contents
- §1. Alembic export operator (cloth / rigid body / hair)
- §2. MeshSequenceCache re-import
- §3. USD export alternative
- §4. VDB copy and import (smoke/fire)
- §5. Particle → real mesh for FBX/glTF export
- §6. Export target quick-reference table
- §7. Post-bake output directory layout
- §8. QA render-check (PNG read-back)

---

## §1. Alembic Export Operator

```python
import bpy

def export_alembic(
    out_path: str,
    start: int = 1,
    end: int   = 120,
    selected_only: bool = False,
    xsamples: int = 1,    # geometry sub-samples/frame (>1 = motion-blur data)
    gsamples: int = 1,    # transform sub-samples/frame
    export_hair: bool = False,       # particle hair → animated curves
    export_particles: bool = False,  # particle positions
    global_scale: float = 1.0,       # 100.0 for UE5 (metres → cm)
    apply_subdiv: bool = False,
) -> None:
    """
    as_background_job MUST be False for headless/scripted export.
    evaluation_mode='RENDER' respects render visibility and subsurf levels.
    out_path: absolute Windows path; use forward slashes or raw string.
    """
    bpy.ops.wm.alembic_export(
        filepath               = out_path.replace("\\", "/"),
        start                  = start,
        end                    = end,
        xsamples               = xsamples,
        gsamples               = gsamples,
        selected               = selected_only,
        uvs                    = True,
        normals                = True,
        vcolors                = False,
        face_sets              = False,
        apply_subdiv           = apply_subdiv,
        use_instancing         = True,
        global_scale           = global_scale,
        triangulate            = False,
        export_hair            = export_hair,
        export_particles       = export_particles,
        as_background_job      = False,     # CRITICAL: True hangs headless
        evaluation_mode        = 'RENDER',
        init_scene_frame_range = True,
    )
    print(f"Alembic exported: {out_path}")
```

**When to set `export_hair=True`:** only for **particle hair** systems (`ps.settings.type == 'HAIR'`).
GN Curves (Geometry Nodes hair) need the GroomExporter add-on for UE5, or `curves_as_mesh=True` for card meshes.

**`xsamples` for motion blur:** set to 2–4 to embed per-frame geometry sub-sample data; downstream DCC
reads this as motion-blur vectors. Doubles/quadruples export time and file size.

---

## §2. MeshSequenceCache Re-import

```python
def attach_alembic_cache(obj_name: str, abc_path: str,
                          object_path: str = "/cloth") -> bpy.types.Modifier:
    """
    Attaches a MeshSequenceCache modifier to an existing object.
    object_path: internal Alembic hierarchy path, e.g. '/Cloth/ClothShape'
    Discover the path by importing the .abc with:
      bpy.ops.wm.alembic_import(filepath=abc_path, as_background_job=False)
    then read the hierarchy from the imported objects.
    """
    bpy.ops.cachefile.open(filepath=abc_path.replace("\\", "/"))
    cache_key = bpy.path.basename(abc_path).replace(".abc", "")
    cache_file = bpy.data.cache_files.get(cache_key)
    if cache_file is None:
        raise RuntimeError(f"CacheFile not found after open: {abc_path}")

    obj = bpy.data.objects[obj_name]
    mod = obj.modifiers.new(name="MeshSequenceCache", type="MESH_SEQUENCE_CACHE")
    mod.cache_file               = cache_file
    mod.object_path              = object_path
    mod.read_data                = {'VERT', 'POLY', 'UV'}
    mod.use_vertex_interpolation = True    # sub-frame position interpolation
    return mod
```

---

## §3. USD Export (Alternative to Alembic)

```python
def export_usd(out_path: str, start: int = 1, end: int = 120,
                export_animation: bool = True,
                export_hair: bool = False) -> None:
    """
    Blender 4.x bpy.ops.wm.usd_export — alternative to Alembic.
    Produces USDC (binary) or USDA (ASCII, .usd extension).
    Use for USD-native pipelines (USD-based game engines, OpenUSD preview).
    """
    bpy.ops.wm.usd_export(
        filepath              = out_path.replace("\\", "/"),
        selected_objects_only = False,
        export_animation      = export_animation,
        export_hair           = export_hair,
        export_uvmaps         = True,
        export_normals        = True,
        export_materials      = True,
        export_textures       = True,
        overwrite_textures    = False,
        start_frame           = start,
        end_frame             = end,
        default_prim_path     = "/root",
        root_prim_path        = "/root",   # concrete prim, not the pseudo-root "/"; matches blender-export.md §4
    )
    print(f"USD exported: {out_path}")
```

---

## §4. VDB Cache Copy and Import

Mantaflow writes VDB files to a directory structure — copy that directory to distribute:

```powershell
# PowerShell: copy VDB cache to delivery folder
$srcDir  = "C:\Forge\scenes\blendcache_smoke\data"
$destDir = "C:\Forge\delivery\smoke_vdb"
New-Item -ItemType Directory -Force -Path $destDir | Out-Null
Copy-Item -Path "$srcDir\*.vdb" -Destination $destDir
Write-Host "Copied $($(Get-ChildItem $destDir -Filter *.vdb).Count) VDB files"
```

Import VDB sequence back in Blender:
```python
def import_vdb_sequence(cache_dir: str, sequence_name: str = "SmokeVDB") -> bpy.types.Object:
    """
    Creates a Volume object that reads the VDB sequence.
    cache_dir: path to the 'data/' folder containing numbered .vdb files.
    """
    import pathlib, os
    vdb_files = sorted(pathlib.Path(cache_dir).glob("*.vdb"))
    if not vdb_files:
        raise RuntimeError(f"No VDB files found in {cache_dir}")

    # Import the first file; Blender will detect sequence
    first = str(vdb_files[0]).replace("\\", "/")
    bpy.ops.object.volume_import(filepath=first,
                                  files=[{"name": f.name} for f in vdb_files])
    vol_obj = bpy.context.active_object
    vol_obj.name = sequence_name
    # Enable sequence playback
    vol = vol_obj.data
    vol.is_sequence = True
    vol.frame_duration = len(vdb_files)
    vol.frame_start    = 1
    vol.frame_offset   = 0
    return vol_obj
```

**Attribute names when using VDB in Principled Volume shader:**
- Data VDB (`/data/`): `density`, `temperature`, `color`, `velocity`
- Noise VDB (`/noise/`): `density_noise`, `temperature_noise`

Use the correct names in the Principled Volume node's `Grid` socket; wrong names show empty volume.

---

## §5. Particle → Real Mesh for FBX/glTF Export

Particle instances are not mesh geometry — they must be converted before format export:

```python
def convert_particles_to_mesh_export(emitter_obj, frame: int,
                                      join_all: bool = False) -> list:
    """
    At frame, make all particle instances real independent objects.
    Optionally join them into one mesh (join_all=True reduces draw calls).
    Returns list of new objects.
    """
    scene = bpy.context.scene
    scene.frame_set(frame)

    bpy.ops.object.select_all(action='DESELECT')
    emitter_obj.select_set(True)
    bpy.context.view_layer.objects.active = emitter_obj
    bpy.ops.object.duplicates_make_real()

    new_objs = [o for o in bpy.context.selected_objects if o != emitter_obj]

    if join_all and new_objs:
        bpy.ops.object.join()
        joined = bpy.context.active_object
        joined.name = f"{emitter_obj.name}_instances"
        return [joined]

    return new_objs


def export_instances_as_glb(obj_list: list, out_path: str) -> None:
    """Export converted particle instances as glTF/GLB."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in obj_list:
        o.select_set(True)
    bpy.ops.export_scene.gltf(
        filepath      = out_path.replace("\\", "/"),
        use_selection = True,
        export_format = 'GLB',
    )
    print(f"GLB exported: {out_path}")
```

---

## §6. Export Target Quick-Reference

| Sim type | Primary export | Format | Key flags |
|----------|---------------|--------|-----------|
| Cloth | Alembic | `.abc` | `uvs=True, normals=True, as_background_job=False` |
| Rigid body (animated) | Alembic or keyframes | `.abc` / `.blend` | For FBX/glTF: bake to keyframes first |
| Particle instances | Make real → GLB/FBX | `.glb` / `.fbx` | `duplicates_make_real()` then export |
| GN hair (static groom) | Alembic (particle) or GroomExporter | `.abc` | `export_hair=True` (particle only); GroomExporter for GN Curves → UE5 |
| Smoke / fire | OpenVDB folder | `.vdb` | Copy `/data/` dir; attach as Volume object |
| USD pipeline | USD | `.usdc` | `bpy.ops.wm.usd_export(export_animation=True)` |

**Engine-specific scale corrections:**
- Unreal Engine 5: `global_scale=100.0` in Alembic/FBX export (Blender metres → UE centimetres)
- Unity: `global_scale=1.0`; Unity expects metres; apply transforms in Blender first
- Godot 4: `global_scale=1.0`; use `.glb` (best round-trip)

---

## §7. Post-Bake Output Directory Layout

```
.forge-build/
  out/
    sim_cloth_<slug>.abc       ← Alembic cloth export
    sim_rb_<slug>.abc          ← Alembic rigid body export
    sim_smoke_<slug>/          ← VDB sequence folder (copy of Mantaflow data/)
      data/
        <name>_0001.vdb
        <name>_0002.vdb
        ...
    sim_qa_<slug>_f060.png     ← QA render at mid-sim frame
  scripts/
    <slug>_bake.py             ← generated bake script (configuration at top)
```

These paths should be written to `FORGE.md` under `## Output paths` so forge-render and forge-export can locate them without re-scanning.

---

## §8. QA Render-Check (PNG Read-Back)

```python
import pathlib, bpy

def render_and_verify(output_path: str, frame: int = 1,
                       samples: int = 32,
                       min_nonblack: float = 0.01) -> bool:
    """
    Renders one Cycles frame headlessly and checks PNG is non-blank.
    min_nonblack: minimum fraction of pixels with any channel > 0.01
    The Forge verification model: agent reads the PNG via Read tool after this.
    """
    scene = bpy.context.scene
    scene.render.engine = 'CYCLES'
    scene.cycles.samples = samples
    scene.render.filepath = output_path.replace("\\", "/")
    scene.render.image_settings.file_format = 'PNG'
    scene.frame_set(frame)
    bpy.ops.render.render(write_still=True)

    p = pathlib.Path(output_path)
    if not p.exists():
        print("[RENDER QA FAIL] File not created"); return False
    if p.stat().st_size < 1024:
        print(f"[RENDER QA WARN] Suspiciously small file: {p.stat().st_size} bytes")

    img   = bpy.data.images.load(output_path)
    pxs   = list(img.pixels)     # RGBA flat array
    total = len(pxs) // 4
    nonblack = sum(1 for i in range(total)
                   if max(pxs[i*4], pxs[i*4+1], pxs[i*4+2]) > 0.01)
    frac  = nonblack / total
    bpy.data.images.remove(img)
    print(f"[RENDER QA] Non-black pixels: {frac:.2%} (threshold {min_nonblack:.2%})")
    return frac >= min_nonblack
```

After calling this, use **Read** on the PNG path to visually inspect the output. The Forge loop: render → verify size → Read PNG → critique → fix script if needed → re-render.
