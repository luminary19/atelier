# forge-light — Light Linking (Cycles 4.0+)
# Per-object light inclusion/exclusion and shadow blocking via bpy

## Contents
- §1. Light linking: receiver collection
- §2. Shadow linking: blocker collection
- §3. When to use light linking
- §4. Gotchas

---

## §1. Light linking: receiver collection

Use when a rim light should only illuminate the product and not the background
or cyclorama. Requires Cycles 4.0+ and `use_light_tree = True`.

```python
import bpy


def link_light_to_receivers(
    emitter_obj: bpy.types.Object,
    receiver_objects: list,
    mode: str = 'INCLUDE',   # 'INCLUDE' = only these; 'EXCLUDE' = all except these
) -> None:
    """
    Configure Cycles light linking so emitter_obj only affects receiver_objects.

    INCLUDE: emitter illuminates ONLY the listed objects.
    EXCLUDE: emitter illuminates EVERYTHING EXCEPT listed objects.

    Gotcha: the bpy.ops operator polls for an active object.
    Always set bpy.context.view_layer.objects.active = emitter_obj before calling.

    Example:
        center, radius = get_bounding_sphere()
        lights = build_three_point_rig(center, radius)
        product = bpy.data.objects['Widget']
        background = bpy.data.objects['Forge_Cyclorama']

        # Rim ONLY touches the product edge, not the cyclorama
        link_light_to_receivers(lights['rim'], [product], mode='INCLUDE')
    """
    # Operator context requirement
    bpy.context.view_layer.objects.active = emitter_obj

    if emitter_obj.light_linking.receiver_collection is None:
        bpy.ops.object.light_linking_receiver_collection_new()

    col = emitter_obj.light_linking.receiver_collection

    for obj in receiver_objects:
        if obj.name not in col.objects:
            col.objects.link(obj)

    # Ensure light_tree is on — required for performance
    bpy.data.scenes[0].cycles.use_light_tree = True
```

---

## §2. Shadow linking: blocker collection

Use when background geometry should not cast distracting shadows on the product.

```python
def link_shadow_blocking(
    emitter_obj: bpy.types.Object,
    blocker_objects: list,
) -> None:
    """
    Shadow linking: only listed objects block (cast shadows from) this emitter.

    Use to prevent cyclorama or environment geometry from casting
    distracting shadows on the product.

    Example:
        link_shadow_blocking(lights['key'], [product_obj])
        # Now only the product casts a shadow from the key light.
        # The cyclorama plane and other scene objects are ignored for shadows.
    """
    bpy.context.view_layer.objects.active = emitter_obj

    if emitter_obj.light_linking.blocker_collection is None:
        bpy.ops.object.light_linking_blocker_collection_new()

    col = emitter_obj.light_linking.blocker_collection
    for obj in blocker_objects:
        if obj.name not in col.objects:
            col.objects.link(obj)
```

---

## §3. When to use light linking

| Scenario | Use |
|---|---|
| Rim light on product only, not on background | `link_light_to_receivers(rim, [product], 'INCLUDE')` |
| Background fill that skips the product | `link_light_to_receivers(fill, [product], 'EXCLUDE')` |
| Key shadow only from product (not cyclorama) | `link_shadow_blocking(key, [product])` |
| Multiple products lit independently | Separate light sets with INCLUDE per object |

Light linking is only meaningful when you have a visible background or multiple
objects in the scene. For a single product on a transparent background (shadow
catcher), light linking is rarely needed.

---

## §4. Gotchas

**G — Poll error: `bpy.ops.object.light_linking_receiver_collection_new poll failed`**

Cause: operator polls for `bpy.context.active_object` to be the emitter.
Fix: always set active object first:
```python
bpy.context.view_layer.objects.active = emitter_obj
bpy.ops.object.light_linking_receiver_collection_new()
```

**G — Slow convergence with light linking enabled**

Cause: `use_light_tree = False`; Cycles falls back to rejection sampling.
Fix:
```python
bpy.data.scenes[0].cycles.use_light_tree = True
```
This is the default in Blender 4.x but can be disabled in old `.blend` files.

**G — Light linking silently ignored in EEVEE**

Cause: Light linking is a Cycles-only feature. EEVEE ignores receiver/blocker collections.
Detection: Check `scene.render.engine == 'CYCLES'` before setting up linking.
Fix: Switch to Cycles or accept that linking will have no effect in EEVEE.
