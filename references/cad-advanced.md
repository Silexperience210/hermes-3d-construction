# Advanced CAD — joints, inserts, screws

Companion to SKILL.md for 3D-printed mechanical assembly.

## Snap-fit joints

The simplest clip: a flexible tab that locks into a
window. Key parameters for PLA:

- **Tab thickness**: 1.0–1.5 mm (flexible but not brittle)
- **Flex length**: ≥ 10 mm (longer = less stress)
- **Draft**: 1–2° on the engagement face for a smooth snap
- **Side clearance**: 0.2 mm on each side of the window

```python
# Simple clip tab (to be inserted into an enclosure)
import bpy

TAB_WIDTH   = 8.0    # tab width
TAB_DEPTH   = 12.0   # flex length
TAB_THICK   = 1.5    # thickness
TAB_HOOK    = 1.2    # hook height

# Tab body
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
tab = bpy.context.active_object
tab.scale = (TAB_WIDTH / 2, TAB_DEPTH / 2, TAB_THICK / 2)
bpy.ops.object.transform_apply(scale=True)

# Hook: a small cube at the end, offset upward
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, TAB_DEPTH/2 - 1, TAB_HOOK/2))
hook = bpy.context.active_object
hook.scale = (TAB_WIDTH / 2, 1.0, TAB_HOOK / 2)
bpy.ops.object.transform_apply(scale=True)
```

## Heat-set threaded inserts

For repeated screws, never screw directly into the plastic:
insert a metal thread hot. The receiving hole:

| Insert | Hole Ø | Depth |
|---|---|---|
| M2 | 3.2 mm | 4 mm |
| M2.5 | 3.7 mm | 4 mm |
| M3 | 4.2 mm | 5 mm |
| M4 | 5.2 mm | 6 mm |

The hole must be slightly smaller than the insert (0.2 mm interference),
with an entry chamfer to guide the insert when hot.

## Through vs tapped screw holes

- **Through (screw + nut)**: Ø = screw + 0.5 mm (M3 → Ø 3.5)
- **Self-tapping (screw directly into the plastic)**: Ø = screw × 0.8 (M3 → Ø 2.4
  pilot hole, screw once, do not disassemble often)

## Thread tolerance

If you print a thread (rare, fragile in FDM): add 0.2 mm to the pitch
and use a `SLIDING_FIT` of 0.2 mm. Otherwise, prefer inserts or a
captive nut.

## Captive nut

For a recessed M3 nut: hexagonal cavity of 5.6 mm (across flats) + 0.3 mm
of clearance, depth = nut thickness + 0.5 mm, with a side
opening to slide the nut into place.
