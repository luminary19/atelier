# forge-sim — Cloth Simulation Reference

## Contents
- §1. Cloth modifier setup (bpy)
- §2. Fabric presets table
- §3. Pinning vertex groups
- §4. Collision object setup
- §5. Wind / force field
- §6. Pressure (inflatables)
- §7. Point cache configuration
- §8. Bake patterns (three strategies)
- §9. Alembic export + MeshSequenceCache (pointer → export-cache.md)
- §10. Apply as shape key (single-frame)
- §11. Programmatic verification
- §12. Explosion detection
- §13. Gotcha → fix table

---

## §1. Cloth Modifier Setup

```python
# bake_cloth.py — run as:
# blender -b scene.blend -t 0 --python bake_cloth.py -- --forge
import bpy

def setup_cloth(obj_name: str, preset: str = "cotton") -> None:
    """
    Add and configure Cloth modifier on obj_name.
    preset: 'cotton' | 'silk' | 'denim' | 'leather' | 'rubber'
    Call this BEFORE custom overrides — presets overwrite fields.
    """
    obj = bpy.data.objects[obj_name]
    if "Cloth" not in obj.modifiers:
        obj.modifiers.new(name="Cloth", type="CLOTH")

    cloth = obj.modifiers["Cloth"]
    s = cloth.settings           # ClothSettings
    c = cloth.collision_settings # ClothCollisionSettings

    s.mass              = 0.3    # kg/vertex; cotton ~0.3, silk ~0.15, denim ~0.8
    s.air_damping       = 1.0
    s.bending_model     = 'ANGULAR'   # ANGULAR=accurate (default); LINEAR=legacy only

    s.tension_stiffness    = 15.0
    s.compression_stiffness = 15.0
    s.shear_stiffness      = 5.0
    s.bending_stiffness    = 0.5   # higher = larger, stiffer folds

    s.tension_damping    = 5.0
    s.compression_damping = 5.0
    s.shear_damping      = 5.0
    s.bending_damping    = 0.5

    # Quality — steps per frame: SINGLE most important performance lever
    s.quality = 10   # 5=draft; 10=production; 15-20=hero/slow cloth

    c.use_collision     = True
    c.collision_quality = 4      # iterations [1, 32767]; default 2
    c.distance_min      = 0.015  # repulsion threshold in metres
    c.friction          = 5.0
    c.damping           = 1.0
    c.impulse_clamp     = 30.0   # 0=disabled → "polygon explosions"; use 25–55

    c.use_self_collision   = True
    c.self_distance_min    = 0.015
    c.self_friction        = 5.0
    c.self_impulse_clamp   = 30.0
```

---

## §2. Fabric Presets Table

| Fabric | `tension` | `compression` | `bending` | `shear` | `mass` (kg/v) | Notes |
|--------|-----------|--------------|-----------|---------|---------------|-------|
| Cotton | 15 | 15 | 0.5 | 5 | 0.30 | Default cloth |
| Silk   | 5  | 5  | 0.05 | 2 | 0.15 | Very light drape |
| Denim  | 40 | 40 | 1.0 | 15 | 0.80 | Stiff, heavy folds |
| Leather | 80 | 80 | 2.0 | 25 | 1.00 | Board-like behaviour |
| Rubber | 15 | 15 | 0.5 | 5  | 0.40 | + `use_pressure=True` |

**Quality steps guideline:**

| Use case | `quality` | `collision_quality` | Sim time factor |
|----------|-----------|---------------------|-----------------|
| Draft    | 5  | 2 | 1× |
| Standard | 10 | 4 | ~3× |
| Hero / slow cloth | 15–20 | 6–8 | ~6–10× |
| Garment with self-collision | 12 | 6 | ~5× |

---

## §3. Pinning Vertex Groups

```python
def setup_pinning(obj_name: str, pin_group: str = "Pin",
                  pin_stiffness: float = 1.0) -> None:
    """
    Weight=1.0 → fully fixed. Weight=0.5 → partial pin (seams/waistbands).
    pin_stiffness: 1.0=rigid pin; 0.3–0.5=soft pin (allows drift under force).
    """
    obj   = bpy.data.objects[obj_name]
    cloth = obj.modifiers["Cloth"]
    s     = cloth.settings

    if pin_group not in obj.vertex_groups:
        raise ValueError(f"Vertex group '{pin_group}' not found on {obj_name}")

    s.vertex_group_mass = pin_group
    s.pin_stiffness     = pin_stiffness
    s.goal_default      = 0.0
    s.goal_min          = 0.0
    s.goal_max          = 1.0
    s.goal_spring       = 1.0
```

**Rules:**
- Always assign a pin group. Cloth with no pins freefalls.
- Use partial weights (0.3–0.7) at seams; full weight (1.0) at attachment points.

---

## §4. Collision Object Setup

```python
def make_collision_object(obj_name: str) -> None:
    """
    Enable Collision modifier on obj_name so cloth bounces off it.
    The COLLIDER gets this modifier — NOT a cloth modifier.
    """
    obj = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj
    if "Collision" not in obj.modifiers:
        obj.modifiers.new(name="Collision", type="COLLISION")
    col = obj.collision
    col.use              = True
    col.thickness_outer  = 0.025
    col.thickness_inner  = 0.2
    col.cloth_friction   = 5.0
    col.damping_factor   = 0.1
```

---

## §5. Wind / Force Field

Wind blows along the Empty's LOCAL -Z axis; rotate the Empty to aim it. For the full force-field API see `references/rigid-particles-bake.md §8`.

```python
import math, bpy

def add_wind_field(location=(0,0,0), rotation_euler=(0,math.pi/2,0),
                   strength=8.0, noise=0.5) -> bpy.types.Object:
    """rotation_euler=(0, pi/2, 0) points wind along world +X."""
    bpy.ops.object.effector_add(type='WIND', location=location,
                                 rotation=rotation_euler)
    f = bpy.context.active_object.field
    f.strength = strength; f.noise = noise; f.seed = 1; f.flow = 0.0
    return bpy.context.active_object

# Effector weights on cloth modifier:
# s = bpy.data.objects["Cloth"].modifiers["Cloth"].settings
# s.effector_weights.wind = 1.0; s.effector_weights.gravity = 1.0
```

---

## §6. Pressure (Inflatables)

```python
def enable_pressure(obj_name: str,
                    uniform_pressure: float = 1.0,
                    pressure_scale: float = 1000.0,
                    target_volume: float = 0.0) -> None:
    """Mesh MUST be a CLOSED manifold — holes cause pressure leakage."""
    s = bpy.data.objects[obj_name].modifiers["Cloth"].settings
    s.use_pressure           = True
    s.uniform_pressure_force = uniform_pressure   # [-10000, 10000] kPa
    s.pressure_scale         = pressure_scale
    s.target_volume          = target_volume       # 0 = auto from mesh
    s.fluid_density          = 0.0                # 0=gas; >0=liquid weight
```

---

## §7. Point Cache Configuration

```python
def configure_cache(obj_name: str,
                    cache_dir: str,        # absolute Windows path, no spaces
                    start_frame: int = 1,
                    end_frame: int   = 120,
                    frame_step: int  = 1,
                    cache_name: str  = "ClothCache") -> None:
    """
    MUST call bpy.ops.wm.save_mainfile() first — cache writes beside .blend.
    frame_step > 1 reduces size but disables exact interpolation.
    Avoid spaces in cache_dir path (Blender path handling on Windows).
    """
    cloth = bpy.data.objects[obj_name].modifiers["Cloth"]
    pc    = cloth.point_cache
    pc.frame_start    = start_frame
    pc.frame_end      = end_frame
    pc.frame_step     = frame_step
    pc.name           = cache_name    # prevents filename collisions
    pc.use_disk_cache = True
    pc.filepath       = cache_dir.replace("\\", "/")
```

---

## §8. Bake Patterns

### Pattern A — bake_all (simplest; works reliably headless)

```python
# bake_all_cloth.py
import bpy, os

CACHE_DIR = r"C:\Projects\cloth_cache"

os.makedirs(CACHE_DIR, exist_ok=True)
bpy.ops.wm.save_mainfile()           # anchor the .blend before baking
bpy.ops.ptcache.bake_all(bake=True)  # no context override needed
bpy.ops.wm.save_mainfile()
print("Baked.")
```

### Pattern B — per-modifier bake (Blender 4.0+ temp_override required)

```python
import bpy

def bake_cloth_per_object(scene_name: str = "Scene") -> None:
    scene = bpy.data.scenes[scene_name]
    for obj in scene.objects:
        for mod in obj.modifiers:
            if mod.type != 'CLOTH':
                continue
            print(f"Baking: {obj.name}")
            with bpy.context.temp_override(scene=scene,
                                           active_object=obj,
                                           point_cache=mod.point_cache):
                bpy.ops.ptcache.free_bake()
            with bpy.context.temp_override(scene=scene,
                                           active_object=obj,
                                           point_cache=mod.point_cache):
                bpy.ops.ptcache.bake(bake=True)
    bpy.ops.wm.save_mainfile()
```

### Pattern C — frame-stepping via depsgraph (post-bake extraction)

Read evaluated (post-modifier) vertex positions per frame. Bake must be complete first.

```python
import bpy, bmesh, json

def extract_cloth_positions(obj_name, start, end, out_path):
    scene = bpy.context.scene; obj = bpy.data.objects[obj_name]; result = {}
    for frame in range(start, end + 1):
        scene.frame_set(frame)
        dg = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(dg)   # post-modifier; do NOT mutate
        bm = bmesh.new(); bm.from_object(obj_eval, dg); bm.verts.ensure_lookup_table()
        result[frame] = [[v.co.x, v.co.y, v.co.z] for v in bm.verts]; bm.free()
    with open(out_path, "w") as f: json.dump(result, f)
    print(f"Exported {end - start + 1} frames to {out_path}")
```

---

## §9. Alembic Export and MeshSequenceCache Re-import

Full operator signatures in `references/export-cache.md §1` (Alembic) and `§2` (MeshSequenceCache).

Critical flags for cloth:
```python
bpy.ops.wm.alembic_export(
    filepath=out_path.replace("\\", "/"), start=start, end=end,
    uvs=True, normals=True, as_background_job=False,  # as_background_job=True hangs headless
    evaluation_mode='RENDER', xsamples=1,
)
# Re-import: add MESH_SEQUENCE_CACHE modifier; set mod.cache_file, mod.object_path
# object_path = '/cloth/clothShape' — discover by importing the .abc first
```

---

## §10. Apply as Shape Key (Single-Frame Still)

```python
def bake_cloth_to_shape_key(obj_name: str, frame: int) -> None:
    """Frozen cloth pose — useful for stills or as sculpt base."""
    scene = bpy.context.scene
    obj   = bpy.data.objects[obj_name]
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    scene.frame_set(frame)
    bpy.ops.object.modifier_apply_as_shapekey(keep_modifier=False,
                                               modifier="Cloth")
    sk = obj.data.shape_keys.key_blocks[-1]
    sk.value = 1.0
    sk.name  = f"cloth_f{frame}"
```

---

## §11. Programmatic Bake Verification

```python
import glob, os

def verify_cloth_bake(obj_name: str, expected_frames: int) -> bool:
    cloth = bpy.data.objects[obj_name].modifiers["Cloth"]
    pc    = cloth.point_cache
    ok    = True
    if not pc.is_baked:
        print(f"FAIL: {obj_name} not baked"); ok = False
    if pc.is_frame_skip:
        print(f"WARN: {obj_name} has skipped frames")
    if pc.is_outdated:
        print(f"WARN: {obj_name} cache is outdated")

    cache_dir   = bpy.path.abspath(pc.filepath)
    bphys_files = glob.glob(os.path.join(cache_dir, "**", "*.bphys"), recursive=True)
    if len(bphys_files) < expected_frames:
        print(f"FAIL: expected {expected_frames} .bphys, found {len(bphys_files)}"); ok = False
    else:
        print(f"OK: {len(bphys_files)} cache files")
    return ok
```

---

## §12. Explosion Detection

```python
def check_cloth_stability(obj_name: str, frame_range: range,
                           max_extent: float = 100.0) -> list:
    """Returns frames where cloth has exploded (vertex dist > max_extent)."""
    scene    = bpy.context.scene
    obj      = bpy.data.objects[obj_name]
    bad      = []
    for frame in frame_range:
        scene.frame_set(frame)
        dg       = bpy.context.evaluated_depsgraph_get()
        obj_eval = obj.evaluated_get(dg)
        max_v    = max((v.co.length for v in obj_eval.data.vertices), default=0)
        if max_v > max_extent:
            bad.append(frame)
            print(f"Frame {frame}: EXPLOSION — max dist {max_v:.1f}")
    return bad
```

---

## §13. Gotcha → Fix Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| `RuntimeError: Operator bpy.ops.ptcache.bake.poll() failed` | Dict-override removed in Blender 4.0 | Use `bpy.context.temp_override(scene=…, active_object=…, point_cache=…)` |
| "Not exact since frame 0" / first frame is reset pose | Frame 0 treated as reset by legacy physics | Set `pc.frame_start = 1`; never bake from frame 0 |
| No `.bphys` files written | `.blend` not saved before bake; `//` has no anchor | `bpy.ops.wm.save_mainfile()` **before** bake; use absolute path in `pc.filepath` |
| `alembic_export` returns immediately, no file | `as_background_job=True` | Always `as_background_job=False` in headless |
| Vertices fly to infinity | Penetration at frame start; stiffness too high for mesh density | `impulse_clamp=30.0`; raise `quality` to 12–15; increase `distance_min=0.025` |
| Two bakes produce different results | Multi-thread floating-point non-determinism | `blender -t 1` for single-threaded deterministic bake (3–5× slower) |
| Cloth looks wrong at render vs. viewport | Subdivision Surface modifier above Cloth in stack | Cloth must be BELOW Subdivision (or disable subdiv during sim) |
| Cache written to user temp / path not found | Path with spaces; Blender Windows path handling | Use paths without spaces; or create a junction: `New-Item -ItemType Junction -Path C:\cc -Target "C:\My Cache"` |
| Depsgraph returns old geometry after script changes | Stale depsgraph | `bpy.context.view_layer.update()` before `evaluated_depsgraph_get()` |
| EEVEE headless render = black frame | EEVEE needs OpenGL context; Windows headless has none | `scene.render.engine = 'CYCLES'` — EEVEE headless only works on Linux (EGL) |

**Modifier order check:**
```python
for i, mod in enumerate(bpy.data.objects["Cloth"].modifiers):
    print(i, mod.name, mod.type)
# Cloth must come AFTER Subdivision if subdiv feeds cloth resolution
```
