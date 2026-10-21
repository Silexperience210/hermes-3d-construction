# Blender STL Export — Version Differences

## Parameter mapping

Blender 5.0+ changed several `bpy.ops.wm.stl_export` parameter names:

| Pre-5.0 name | Blender 5.0+ name |
|---|---|
| `ascii` | `ascii_format` |
| `use_mesh_modifiers` | `apply_modifiers` |

Other parameters (`filepath`, `export_selected_objects`, `global_scale`, `use_scene_unit`, `forward_axis`, `up_axis`) are unchanged.

## How to discover current parameter names

```python
import bpy
[p.identifier for p in bpy.ops.wm.stl_export.get_rna_type().properties if not p.is_hidden]
# → ['filepath', 'ascii_format', 'use_batch', 'export_selected_objects',
#     'global_scale', 'use_scene_unit', 'forward_axis', 'up_axis', 'apply_modifiers']
```

## Correct Blender 5.0 STL export call

```python
bpy.ops.wm.stl_export(
    filepath=output_path,
    export_selected_objects=True,
    ascii_format=False,
    apply_modifiers=True
)
```

## BlenderMCP addon note

If `BlenderMCP` is installed (check at Blender startup), it will print:
```
BlenderMCP: cannot start server in background mode (blender -b)
```
This is normal for headless mode. To use MCP, run Blender with a virtual display:
```bash
xvfb-run -a blender
```
