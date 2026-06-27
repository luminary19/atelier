# forge-uv — Pre-flight Reference

# Contents
- §1. Scale check and apply
- §2. UV layer normalization
- §3. Modifier-stack gotchas
- §4. Mesh sanity checks
- §5. PowerShell pre-flight pattern

---

## §1. Scale check and apply

**This is the single most important pre-condition for UV work.**
Unapplied scale corrupts texel density calculations: an object scaled 2× reads as 4× higher TD
because surface area is computed in object-local space.

```python
import bpy

def check_scale(obj, tolerance=0.0001) -> bool:
    """Returns True if scale is (1,1,1) within tolerance."""
    return all(abs(s - 1.0) < tolerance for s in obj.scale)

def apply_scale(obj):
    """Apply scale to a single object. Object must be a MESH."""
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    obj.select_set(False)
    print(f"[INFO] {obj.name}: scale applied → {tuple(round(s,4) for s in obj.scale)}")

def apply_scale_all_meshes():
    """Apply scale to every MESH object in the scene. Run before any UV operation."""
    bpy.ops.object.select_all(action='DESELECT')
    for obj in bpy.data.objects:
        if obj.type == 'MESH':
            if not check_scale(obj):
                apply_scale(obj)
    print("[INFO] apply_scale_all_meshes: complete")

def preflight_scale(scene_objects=None) -> list:
    """
    Check all mesh objects for unapplied scale.
    Returns list of (name, scale) tuples for offenders.
    Does NOT modify anything — report only.
    """
    objs = scene_objects or [o for o in bpy.data.objects if o.type == 'MESH']
    offenders = []
    for obj in objs:
        if not check_scale(obj):
            offenders.append((obj.name, tuple(round(s, 4) for s in obj.scale)))
    if offenders:
        for name, sc in offenders:
            print(f"[ERROR] Scale not applied: {name} {sc}")
    else:
        print("[OK] All mesh objects have scale (1,1,1)")
    return offenders
```

---

## §2. UV layer normalization

When batch-processing multiple objects, UV layer names may differ across meshes
(`"UVMap"`, `"UV0"`, `"UVChannel_0"`, `"UVMap.001"`). UV operators always act on the **active**
UV layer. Ensure a consistent canonical name before running any batch operation.

```python
import bpy

def ensure_uv_layer(obj, name="UVMap") -> bool:
    """
    Create a UV layer named `name` if it doesn't exist, then make it active.
    Returns True if the layer already existed; False if it was created.
    """
    if name not in obj.data.uv_layers:
        obj.data.uv_layers.new(name=name)
        print(f"[INFO] {obj.name}: created UV layer '{name}'")
        existed = False
    else:
        existed = True
    obj.data.uv_layers.active = obj.data.uv_layers[name]
    return existed

def normalize_uv_layer_names(target_name="UVMap", lightmap_name="UVMap.001"):
    """
    Rename the first UV layer on every mesh to target_name,
    and the second UV layer (if present) to lightmap_name.
    Safe to call multiple times — skips already-correct names.
    """
    for obj in bpy.data.objects:
        if obj.type != 'MESH':
            continue
        uv_layers = obj.data.uv_layers
        if len(uv_layers) >= 1:
            if uv_layers[0].name != target_name:
                print(f"[INFO] {obj.name}: rename UV layer 0 '{uv_layers[0].name}' → '{target_name}'")
                uv_layers[0].name = target_name
        if len(uv_layers) >= 2:
            if uv_layers[1].name != lightmap_name:
                print(f"[INFO] {obj.name}: rename UV layer 1 '{uv_layers[1].name}' → '{lightmap_name}'")
                uv_layers[1].name = lightmap_name

def list_uv_layers(obj):
    """Print all UV layers on an object with their index and active status."""
    for i, layer in enumerate(obj.data.uv_layers):
        active = "(active)" if layer == obj.data.uv_layers.active else ""
        print(f"  UV{i}: '{layer.name}' {active}")
```

---

## §3. Modifier-stack gotchas

### Subdivision Surface — UVs match base cage, not subdivided mesh

UVs are authored on the base cage. When the mesh is exported, the export tool typically evaluates
the modifier stack. Textures applied in the 3D viewport look correct (the engine applies SubDiv at
render), but UV editing in the UV Editor always shows the base cage topology.

**Fix:** Use `use_subsurf_data=True` in `bpy.ops.uv.unwrap()` to generate subdivision-aware UVs.

```python
bpy.ops.uv.unwrap(method='ANGLE_BASED', use_subsurf_data=True, correct_aspect=True)
```

Or apply the Subdivision modifier before unwrapping:

```python
def apply_modifiers_for_export(obj):
    """Apply all modifiers (evaluated mesh) before UV export. Destructive — creates new mesh."""
    import bpy
    depsgraph = bpy.context.evaluated_depsgraph_get()
    obj_eval = obj.evaluated_get(depsgraph)
    mesh_from_eval = bpy.data.meshes.new_from_object(obj_eval)
    obj.data = mesh_from_eval
    obj.modifiers.clear()
    print(f"[INFO] {obj.name}: modifiers applied to mesh (destructive)")
```

### Mirror Modifier — UVs overlap by default

The Mirror modifier creates mirrored geometry that shares UV space (overlap). This is intentional
for diffuse textures (shared UV = same texture on both sides) but breaks baking.

**Fix for baking:** Apply the Mirror modifier first, then re-unwrap the full mesh with unique UVs.

```python
def apply_mirror_before_bake(obj):
    for mod in list(obj.modifiers):
        if mod.type == 'MIRROR':
            bpy.context.view_layer.objects.active = obj
            bpy.ops.object.modifier_apply(modifier=mod.name)
    print(f"[INFO] {obj.name}: Mirror modifier applied — re-unwrap recommended")
```

### Solidify / Bevel — modifier order matters for UV projection

Solidify adds inner faces that need UV coverage. Bevel multiplies edge loops. Both should be applied
or UV-unwrapped after being applied, never before.

**Detection pattern:**

```python
def check_modifier_stack(obj) -> list:
    """
    Return list of modifier names that could affect UV correctness.
    Caller decides whether to apply or warn.
    """
    problematic = ['SUBSURF', 'MIRROR', 'SOLIDIFY', 'BEVEL', 'MULTIRES']
    found = [m.name for m in obj.modifiers if m.type in problematic]
    if found:
        print(f"[WARN] {obj.name}: modifiers that may affect UV: {found}")
    return found
```

---

## §4. Mesh sanity checks

```python
import bpy
import bmesh

def check_mesh_sanity(obj) -> dict:
    """
    Basic mesh sanity check before UV work.
    Returns a dict of potential issues.
    """
    results = {
        'has_faces': False,
        'ngon_count': 0,
        'isolated_verts': 0,
        'non_manifold_edges': 0,
    }

    if obj.type != 'MESH' or not obj.data.polygons:
        print(f"[ERROR] {obj.name}: no faces found")
        return results

    results['has_faces'] = True
    bm = bmesh.new()
    bm.from_mesh(obj.data)
    bm.faces.ensure_lookup_table()
    bm.edges.ensure_lookup_table()
    bm.verts.ensure_lookup_table()

    results['ngon_count'] = sum(1 for f in bm.faces if len(f.verts) > 4)
    results['isolated_verts'] = sum(1 for v in bm.verts if not v.link_edges)
    results['non_manifold_edges'] = sum(1 for e in bm.edges if not e.is_manifold)

    bm.free()

    if results['ngon_count'] > 0:
        print(f"[WARN] {obj.name}: {results['ngon_count']} N-gons — "
              f"may cause poor unwrap; dissolve before UV")
    if results['non_manifold_edges'] > 0:
        print(f"[WARN] {obj.name}: {results['non_manifold_edges']} non-manifold edges — "
              f"run forge-topology cleanup first")
    if results['isolated_verts'] > 0:
        print(f"[WARN] {obj.name}: {results['isolated_verts']} isolated vertices — delete before UV")

    return results
```

---

## §5. PowerShell pre-flight pattern

Before any headless UV session, confirm Blender is available and the scene file is valid:

```powershell
# PowerShell — UV session pre-flight
$blender = "blender"   # Or full path: "C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
$scene   = "C:/assets/prop.blend"

# 1. Check Blender is available
$ver = & $blender --version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0 -or -not $ver) {
    Write-Error "Blender not found on PATH. Run: winget install BlenderFoundation.Blender"
    exit 1
}
Write-Host "Blender: $ver"

# 2. Check scene file exists
if (-not (Test-Path $scene)) {
    Write-Error "Scene file not found: $scene"
    exit 1
}

# 3. Confirm Python is available (for stdlib scripts)
$pyver = & python --version 2>&1 | Select-Object -First 1
if ($LASTEXITCODE -ne 0) {
    Write-Error "Python not found. Install from python.org"
    exit 1
}
Write-Host "Python: $pyver"

Write-Host "[OK] Pre-flight passed — ready to run UV scripts"
```

**Note:** Blender ships its own CPython (`blender --python`). The standalone `python` above is for
pre/post-processing scripts (TD reporting, file renaming, contact sheets) that run outside Blender.
Blender UV scripts always run via `blender --python script.py`.
