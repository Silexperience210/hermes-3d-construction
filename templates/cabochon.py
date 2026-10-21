#!/usr/bin/env python3
"""
Cabochon / tube cap — parametric STL generator for Blender headless.
Usage: blender --background --python cabochon.py

Modify the PARAMETERS section below for your tube dimensions.
All values in mm.
"""

import bpy
import os
import sys

# ═══════════════════════════════════════════════════
# PARAMETERS — measure your tube and edit these
# ═══════════════════════════════════════════════════

OUTER_DIAMETER  = 30.0   # tube outer diameter
INNER_DIAMETER  = 26.0   # tube inner diameter
INSERT_HEIGHT   = 8.0    # how deep the insert goes into the tube
LIP_HEIGHT      = 2.0    # collar height (visible above tube rim)
LIP_OVERHANG    = 2.0    # how far the collar extends past the outer wall
TOLERANCE       = 0.2    # clearance fit (0.2 = snug, 0.4 = loose)
WALL_THICKNESS  = 2.0    # wall thickness when hollow
SOLID           = False  # True = solid plug, False = hollow shell

OUTPUT_FILE     = "cabochon.stl"

# ═══════════════════════════════════════════════════
# GEOMETRY — do not edit below unless you know bpy
# ═══════════════════════════════════════════════════

outer_r = OUTER_DIAMETER / 2.0
inner_r = INNER_DIAMETER / 2.0
insert_r = inner_r - TOLERANCE
lip_r = outer_r + LIP_OVERHANG
# Write where you RUN it, not next to this file (see enclosure.py for the reasoning).
_argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
out_dir = os.path.abspath(_argv[0]) if _argv else os.getcwd()
os.makedirs(out_dir, exist_ok=True)
output_path = os.path.join(out_dir, OUTPUT_FILE)

# Clean scene
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ── Insert (cylinder into tube) ──
bpy.ops.mesh.primitive_cylinder_add(
    vertices=64, radius=insert_r, depth=INSERT_HEIGHT,
    location=(0, 0, INSERT_HEIGHT / 2.0)
)
insert = bpy.context.active_object
insert.name = "Insert"

# ── Collar (lip above tube rim) ──
bpy.ops.mesh.primitive_cylinder_add(
    vertices=64, radius=lip_r, depth=LIP_HEIGHT,
    location=(0, 0, INSERT_HEIGHT + LIP_HEIGHT / 2.0)
)
lip = bpy.context.active_object
lip.name = "Collar"

# ── Join parts ──
bpy.ops.object.select_all(action='SELECT')
bpy.context.view_layer.objects.active = insert
bpy.ops.object.join()
cabochon = bpy.context.active_object
cabochon.name = "Cabochon"

# ── Hollow if requested ──
if not SOLID:
    cavity_r = insert_r - WALL_THICKNESS
    if cavity_r > 1.0:
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=64, radius=cavity_r,
            depth=INSERT_HEIGHT + LIP_HEIGHT + 0.1,
            location=(0, 0, (INSERT_HEIGHT + LIP_HEIGHT) / 2.0)
        )
        cavity = bpy.context.active_object
        cavity.name = "Cavity"

        mod = cabochon.modifiers.new(name="Hollow", type='BOOLEAN')
        mod.operation = 'DIFFERENCE'
        mod.object = cavity
        bpy.context.view_layer.objects.active = cabochon
        bpy.ops.object.modifier_apply(modifier="Hollow")

        bpy.ops.object.select_all(action='DESELECT')
        cavity.select_set(True)
        bpy.ops.object.delete(use_global=False)

# ── Apply transforms ──
bpy.context.view_layer.objects.active = cabochon
bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

# ── Export STL ──
bpy.ops.object.select_all(action='DESELECT')
cabochon.select_set(True)
bpy.ops.wm.stl_export(
    filepath=output_path,
    export_selected_objects=True,
    ascii_format=False,
    apply_modifiers=True
)

print(f"✅ {output_path}")
print(f"   Insert: Ø{insert_r*2:.1f} x H{INSERT_HEIGHT}mm | Collar: Ø{lip_r*2:.1f} x H{LIP_HEIGHT}mm")
print(f"   Mode: {'SOLID' if SOLID else f'HOLLOW ({WALL_THICKNESS}mm wall)'}")
