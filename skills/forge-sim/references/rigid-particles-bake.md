# forge-sim — Rigid Body & Particle Systems Reference

## Contents
- §1. Rigid body world setup
- §2. Active / passive body configuration + shape table
- §3. Stacking / stability settings
- §4. Bake to point cache (headless)
- §5. Manual keyframe bake (true headless — no VIEW_3D needed)
- §6. Particle emitter setup
- §7. Hair particle system
- §8. Force fields
- §9. Bake particle cache (Blender 4.x)
- §10. Particle instance modifier
- §11. Convert particles to real mesh (pre-export)
- §12. Programmatic QA checks
- §13. Gotcha → fix table

---

## §1. Rigid Body World Setup

```python
import bpy

scene = bpy.context.scene

if scene.rigidbody_world is None:
    bpy.ops.rigidbody.world_add()

rbw = scene.rigidbody_world
rbw.enabled = True

# CRITICAL: sync point cache to scene range BEFORE baking.
# Default cache.frame_end == 250 — simulation freezes there even if scene.frame_end is longer.
rbw.substeps_per_frame           = 20   # default 10; use 20–60 for stacking
rbw.solver_iterations            = 40   # default 10; use 40–60 for stable stacks
rbw.time_scale                   = 1.0  # 0.5 = slow motion
rbw.use_split_impulse            = False  # True causes jitter on stacks

rbw.point_cache.frame_start = scene.frame_start   # ALWAYS set explicitly
rbw.point_cache.frame_end   = scene.frame_end     # ALWAYS set explicitly
```

---

## §2. Active / Passive Body Configuration

```python
def make_rigid_body(
    obj,
    rb_type='ACTIVE',         # 'ACTIVE'=simulated; 'PASSIVE'=static collider
    shape='CONVEX_HULL',      # see shape table
    mass=1.0,
    friction=0.5,
    restitution=0.0,          # bounce [0, 1]
    linear_damping=0.04,
    angular_damping=0.1,
    collision_margin=0.04,    # 0 for tiny objects < 20 cm
    use_margin=False,
):
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    if obj.rigid_body is None:
        bpy.ops.rigidbody.object_add(type=rb_type)
    rb = obj.rigid_body
    rb.type             = rb_type
    rb.collision_shape  = shape
    rb.mass             = mass
    rb.friction         = friction
    rb.restitution      = restitution
    rb.linear_damping   = linear_damping
    rb.angular_damping  = angular_damping
    rb.use_margin       = use_margin
    rb.collision_margin = collision_margin
    rb.use_deactivation            = True
    rb.use_start_deactivated       = False  # True = spawn asleep (useful for piles)
    rb.deactivate_linear_velocity  = 0.4
    rb.deactivate_angular_velocity = 0.5
    return rb
```

**Collision shape selection:**

| Shape | Best for | Speed | Concave? | Margin |
|-------|----------|-------|----------|--------|
| `BOX` | Cubes, planes | Fastest | No | Embedded |
| `SPHERE` | Spheres | Fastest | No | Embedded |
| `CAPSULE` | Z-aligned cylinders | Fast | No | Embedded |
| `CONVEX_HULL` | Most organic shapes | Good | No | Embedded |
| `MESH` | Complex concave (static) | Slow, unstable | Yes | NOT embedded |
| `COMPOUND` | Concave, via children | Medium | Yes | Per-child |

**Rules:**
- Never use `MESH` shape for ACTIVE rigid bodies — objects pass through each other.
- Max safe mass ratio: 100:1. Mass ratios > 1000:1 cause Bullet instability/explosion.
- Always apply object scale before simulation: unapplied scale gives wrong inertia tensors.

---

## §3. Stacking / Stability Settings

For stable stacks: `substeps_per_frame=30`, `solver_iterations=60`, `use_split_impulse=False`. Apply scale on all rigid body objects before sim (`bpy.ops.object.transform_apply(scale=True)` — unapplied scale causes wrong inertia tensors). Min object size ≥ 20 cm (Bullet unstable below 5 cm without `collision_margin=0`).

---

## §4. Bake to Point Cache (Headless)

```python
import bpy

def bake_rigidbody_ptcache():
    """ptcache.bake_all needs NO context override — correct headless method."""
    bpy.ops.ptcache.free_bake_all()
    bpy.ops.ptcache.bake_all(bake=True)
    bpy.ops.wm.save_mainfile()
    print("is_baked:", bpy.context.scene.rigidbody_world.point_cache.is_baked)

bake_rigidbody_ptcache()
```

PowerShell invocation:
```powershell
$blender = "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
& $blender -b "C:/Forge/scene.blend" --python "C:/Forge/bake_rb.py" -- --forge
```

---

## §5. Manual Keyframe Bake (True Headless — No VIEW_3D)

`bpy.ops.rigidbody.bake_to_keyframes` requires a VIEW_3D context area; in `--background` mode there is no screen. Use this manual approach instead.

```python
import bpy

def manual_bake_rb_to_keyframes(frame_start=1, frame_end=250, step=1):
    """
    Prerequisite: ptcache must be baked first (bpy.ops.ptcache.bake_all).
    Works in --background mode — no VIEW_3D area needed.
    """
    scene    = bpy.context.scene
    depsgraph = bpy.context.evaluated_depsgraph_get()

    rb_objects = [obj for obj in scene.objects
                  if obj.rigid_body and obj.rigid_body.type == 'ACTIVE']

    for frame in range(frame_start, frame_end + 1, step):
        scene.frame_set(frame)
        depsgraph.update()
        for obj in rb_objects:
            obj_eval           = obj.evaluated_get(depsgraph)
            obj.location       = obj_eval.location
            obj.rotation_euler = obj_eval.rotation_euler
            obj.scale          = obj_eval.scale
            obj.keyframe_insert(data_path="location",       frame=frame)
            obj.keyframe_insert(data_path="rotation_euler", frame=frame)

    # Remove rigid body so it doesn't conflict with keyframes
    for obj in rb_objects:
        obj.select_set(True)
        bpy.context.view_layer.objects.active = obj
        bpy.ops.rigidbody.object_remove()

    bpy.ops.wm.save_mainfile()
    print(f"Baked {len(rb_objects)} objects, frames {frame_start}–{frame_end}")
```

---

## §6. Particle Emitter Setup

```python
def create_particle_emitter(
    emitter_obj,
    count=1000,
    lifetime=100.0,
    frame_start=1.0,
    frame_end=50.0,
    emit_from='FACE',          # 'VERT' | 'FACE' | 'VOLUME'
    physics_type='NEWTON',     # 'NEWTON' | 'BOIDS' | 'FLUID' | 'KEYED' | 'NO'
    render_type='OBJECT',      # 'NONE' | 'HALO' | 'LINE' | 'PATH' | 'OBJECT' | 'COLLECTION'
    instance_obj=None,
    instance_collection=None,
    use_collision=False,
    collision_collection=None,
):
    bpy.context.view_layer.objects.active = emitter_obj
    mod  = emitter_obj.modifiers.new("ParticleSystem", 'PARTICLE_SYSTEM')
    ps   = mod.particle_system
    pset = ps.settings

    pset.type        = 'EMITTER'
    pset.count       = count
    pset.lifetime    = lifetime
    pset.frame_start = frame_start
    pset.frame_end   = frame_end
    pset.emit_from            = emit_from
    pset.use_emit_random      = True
    pset.use_even_distribution = True  # weight by face area

    pset.physics_type   = physics_type
    pset.normal_factor  = 1.0
    pset.factor_random  = 0.0
    pset.mass           = 1.0
    pset.drag_factor    = 0.0
    pset.integrator     = 'MIDPOINT'  # MIDPOINT=best balance; RK4=most stable (4x slower)
    pset.subframes      = 0

    pset.render_type = render_type
    if render_type == 'OBJECT' and instance_obj:
        pset.instance_object             = instance_obj
        pset.use_rotation_instance       = True
        pset.use_scale_instance          = True
        emitter_obj.show_instancer_for_render   = False
        emitter_obj.show_instancer_for_viewport = False
    elif render_type == 'COLLECTION' and instance_collection:
        pset.instance_collection         = instance_collection
        pset.use_collection_pick_random  = True

    if use_collision and collision_collection:
        pset.collision_collection = collision_collection
        pset.use_die_on_collision  = False

    return ps, pset
```

**Sane particle defaults:**

| Setting | Cap / Sane value | Rationale |
|---------|------------------|-----------|
| `count` | ≤ 100k for interactive; ≤ 500k for bake | Beyond 500k: RAM and bake time explode |
| `integrator` | `MIDPOINT` | Best balance; RK4 most accurate, 4× slower |
| `subframes` | 2–5 | Needed when particles move > 1 object-diameter/frame |
| `lifetime` | > frame range | Keep all particles alive through the full render window |
| `use_even_distribution` | True | Prevents face-size-dependent clustering |

---

## §7. Hair Particle System

Legacy particle HAIR setup. For modern GN Curves hair with Principled Hair BSDF, see `references/hair-fluid-bake.md §1–§3`. Legacy particle hair is primarily used for Alembic curve export (`export_hair=True`).

```python
def create_hair_system(obj, count=500, hair_length=0.3, step_count=6,
                        use_dynamics=False):
    """use_dynamics=True enables cloth physics on hair."""
    mod = obj.modifiers.new("Hair", 'PARTICLE_SYSTEM')
    ps = mod.particle_system; pset = ps.settings
    pset.type='HAIR'; pset.count=count; pset.hair_length=hair_length
    pset.hair_step=step_count; pset.render_type='PATH'; pset.render_step=3
    pset.child_type='INTERPOLATED'; pset.rendered_child_count=50
    if use_dynamics: ps.use_hair_dynamics = True
    return ps, pset
```

---

## §8. Force Fields

Types: `'FORCE' 'WIND' 'VORTEX' 'TURBULENCE' 'DRAG' 'HARMONIC' 'BOID' 'TEXTURE' 'GUIDE'`

```python
def add_force_field(location=(0,0,0), field_type='WIND', strength=10.0,
                    noise=0.0, seed=1) -> tuple:
    bpy.ops.object.empty_add(location=location)
    fs = bpy.context.active_object.field
    fs.type = field_type; fs.strength = strength
    if field_type == 'TURBULENCE': fs.noise=noise; fs.seed=seed; fs.size=1.0
    if field_type == 'WIND': fs.wind_factor = 0.0
    return bpy.context.active_object, fs
# Effector weights: ps.settings.effector_weights.gravity = 0.5
# RB world:  scene.rigidbody_world.effector_weights.wind = 0.0
```

---

## §9. Bake Particle Cache (Blender 4.x)

```python
# Method A: bake_all (bakes ALL physics including cloth; simplest headless)
def bake_particles_all():
    bpy.ops.ptcache.bake_all(bake=True)
    bpy.ops.wm.save_mainfile()

# Method B: single particle system (Blender 4.x temp_override)
def bake_single_particle_system(obj, modifier_name):
    mod = obj.modifiers[modifier_name]
    pc  = mod.particle_system.point_cache
    with bpy.context.temp_override(scene=bpy.context.scene,
                                    active_object=obj,
                                    point_cache=pc):
        bpy.ops.ptcache.free_bake()      # free_bake takes NO args (it is a free op)
        bpy.ops.ptcache.bake(bake=True)
    bpy.ops.wm.save_mainfile()

# Verification:
def verify_particle_bake(obj, modifier_name) -> bool:
    pc = obj.modifiers[modifier_name].particle_system.point_cache
    print(f"is_baked: {pc.is_baked}, range: {pc.frame_start}-{pc.frame_end}")
    return pc.is_baked
```

**Determinism (seeds):**
```python
ps.seed = 42          # particle system (not settings)
ff.seed = 7           # force field FieldSettings
import mathutils
mathutils.noise.seed_set(12345)
```

---

## §10. Particle Instance Modifier

```python
def instance_mesh_on_particles(mesh_obj, emitter_obj, ps_index=1,
                                use_normal=True, use_size=True) -> bpy.types.Modifier:
    """
    Mesh_obj appears at every particle of emitter_obj's particle system.
    Bake must be complete before this renders correctly (except HAIR/KEYED types).
    """
    bpy.context.view_layer.objects.active = mesh_obj
    mod = mesh_obj.modifiers.new("ParticleInstance", 'PARTICLE_INSTANCE')
    mod.object                = emitter_obj
    mod.particle_system_index = ps_index
    mod.use_normal            = use_normal
    mod.use_size              = use_size
    mod.use_path              = False
    mod.space                 = 'WORLD'
    mod.show_alive            = True
    mod.show_dead             = False
    mod.show_unborn           = False
    return mod
```

---

## §11. Convert Particles to Real Mesh (Pre-Export)

Particle instances must be converted to real objects before FBX/glTF export. Full implementation in `references/export-cache.md §5` (`convert_particles_to_mesh_export` + `export_instances_as_glb`).

Quick form:
```python
# At desired frame, make instances real, then export
bpy.ops.object.select_all(action='DESELECT')
emitter_obj.select_set(True)
bpy.context.view_layer.objects.active = emitter_obj
bpy.ops.object.duplicates_make_real()
new_objs = [o for o in bpy.context.selected_objects if o != emitter_obj]
```

Alive particle positions via depsgraph (point-cloud export):
```python
bpy.context.scene.frame_set(frame)
dg = bpy.context.evaluated_depsgraph_get()
positions = [p.location.copy()
             for ps in emitter_obj.evaluated_get(dg).particle_systems
             for p in ps.particles if p.alive_state == 'ALIVE']
```

---

## §12. Programmatic QA Checks

Key assertions to run before headless render:
```python
rbw = bpy.context.scene.rigidbody_world
assert rbw is not None, "No RigidBodyWorld"
assert rbw.point_cache.is_baked, "Cache not baked — render will be static"
assert rbw.point_cache.frame_end >= bpy.context.scene.frame_end, \
    f"Cache ends at {rbw.point_cache.frame_end}, scene ends at {bpy.context.scene.frame_end}"
# Unapplied scale check:
for obj in bpy.context.scene.objects:
    if obj.rigid_body:
        s = obj.scale
        if max(abs(s.x-1),abs(s.y-1),abs(s.z-1)) > 0.001:
            print(f"WARN: {obj.name} unapplied scale {tuple(s)}")

# Particle count at a frame:
def count_alive(obj, frame):
    bpy.context.scene.frame_set(frame)
    dg = bpy.context.evaluated_depsgraph_get()
    for ps in obj.evaluated_get(dg).particle_systems:
        alive = sum(1 for p in ps.particles if p.alive_state == 'ALIVE')
        print(f"Frame {frame}: {alive}/{len(ps.particles)} alive in '{ps.name}'")
```

---

## §13. Gotcha → Fix Table

| Symptom | Cause | Fix |
|---------|-------|-----|
| Rigid bodies don't move in headless render | No ptcache bake before render | `bpy.ops.ptcache.bake_all(bake=True)` then `save_mainfile()` |
| Simulation stops at frame 250 | `rbw.point_cache.frame_end` defaults to 250 | Set `rbw.point_cache.frame_end = scene.frame_end` |
| `ValueError: 1-2 args execution context` | Dict-override API removed in Blender 4.0 | Use `bpy.context.temp_override(...)` context manager |
| `RuntimeError: bpy.ops.anim.keyframe_insert.poll() failed` | `bake_to_keyframes` needs VIEW_3D context | Use manual keyframe bake (§5) instead |
| Cache lost on re-open | `.blend` unsaved before bake | `bpy.ops.wm.save_mainfile()` before `bake_all()` |
| Particles invisible in render | `show_instancer_for_render=True` or no bake | Set False + ensure bake complete |
| Objects explode on frame 1 | Initial interpenetration at start | No overlap at frame 1; or `use_start_deactivated=True` |
| Mass behaves wrong | Unapplied object scale | `bpy.ops.object.transform_apply(scale=True)` |
| Cloth bake skipped by `ptcache.bake_all` | Cloth sometimes needs individual `ptcache.bake` | Per-modifier loop with `temp_override(point_cache=mod.point_cache)` |
| Windows path backslashes fail in `bpy.ops` | Blender expects forward slashes | Use `path.replace("\\", "/")` or `pathlib.Path(p).as_posix()` |
| Non-ASCII / space in cache path → cache not written | Blender file I/O limitation on Windows | ASCII-only paths; no spaces; use junctions if needed |
