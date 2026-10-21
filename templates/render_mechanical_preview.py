#!/usr/bin/env python3
"""
Blender headless — simple product preview for mechanical parts.
Usage: blender --background --factory-startup --python render_mechanical_preview.py -- <stl_dir> <out_png>
Renders all STL files in <stl_dir> in an exploded layout on a ground plane.
"""
import bpy
import sys
import os
import math

argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
STL_DIR = argv[0] if len(argv) > 0 else "./stl"
OUT = argv[1] if len(argv) > 1 else "./preview.png"
RES_X = int(argv[2]) if len(argv) > 2 else 1280
RES_Y = int(argv[3]) if len(argv) > 3 else 720
SAMPLES = int(argv[4]) if len(argv) > 4 else 32

# Cleanup
for obj in list(bpy.data.objects):
    bpy.data.objects.remove(obj, do_unlink=True)

# Materials palette
PALETTE = [
    (0.2, 0.7, 0.9),   # cyan
    (0.9, 0.3, 0.6),   # magenta
    (1.0, 0.8, 0.2),   # yellow
    (0.4, 0.9, 0.4),   # green
    (0.8, 0.5, 0.9),   # purple
]

def make_material(name, color):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (*color, 1.0)
    bsdf.inputs["Roughness"].default_value = 0.4
    return mat

# Import STLs
stls = sorted([f for f in os.listdir(STL_DIR) if f.lower().endswith(".stl")])
objects = []
for i, name in enumerate(stls):
    path = os.path.join(STL_DIR, name)
    bpy.ops.wm.stl_import(filepath=path, global_scale=1.0)
    obj = bpy.context.selected_objects[0]
    obj.name = name.replace(".stl", "")
    bpy.context.view_layer.objects.active = obj
    bpy.ops.object.origin_set(type="GEOMETRY_ORIGIN", center="BOUNDS")
    mat = make_material(f"mat_{obj.name}", PALETTE[i % len(PALETTE)])
    obj.data.materials.append(mat)
    objects.append(obj)

# Layout: place objects in a circle/spaced row to avoid overlap
n = len(objects)
spacing = 120.0
for i, obj in enumerate(objects):
    angle = 2 * math.pi * i / max(n, 1)
    obj.location = (spacing * math.cos(angle), spacing * math.sin(angle), 0.0)

# Ground plane
if n > 0:
    size = spacing * 2.5
    bpy.ops.mesh.primitive_plane_add(size=size, location=(0, 0, -40))
    ground = bpy.context.active_object
    ground_mat = make_material("ground", (0.08, 0.08, 0.1))
    ground.data.materials.append(ground_mat)

# Camera: frame all objects
bpy.ops.object.camera_add(location=(200, -250, 180), rotation=(math.radians(60), 0, math.radians(40)))
cam = bpy.context.active_object
bpy.context.scene.camera = cam
cam.data.lens = 45

# Lights
bpy.ops.object.light_add(type="SUN", location=(100, -100, 150), rotation=(0.8, 0, 0.5))
key = bpy.context.active_object
key.data.energy = 4.0

bpy.ops.object.light_add(type="AREA", location=(-120, -50, 100), rotation=(1.0, 0, -0.8))
fill = bpy.context.active_object
fill.data.energy = 150
fill.data.size = 80

bpy.ops.object.light_add(type="AREA", location=(0, 120, 80), rotation=(math.radians(80), 0, math.pi))
rim = bpy.context.active_object
rim.data.energy = 100
rim.data.size = 60

# Render settings
scene = bpy.context.scene
scene.render.engine = "CYCLES"
scene.cycles.device = "CPU"
scene.cycles.samples = SAMPLES
scene.render.resolution_x = RES_X
scene.render.resolution_y = RES_Y
scene.render.filepath = OUT
scene.render.image_settings.file_format = "PNG"
scene.view_settings.view_transform = "Khronos PBR Neutral"

bpy.ops.render.render(write_still=True)
print("Saved preview to", OUT)
