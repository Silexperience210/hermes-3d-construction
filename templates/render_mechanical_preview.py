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
# Blender's render.filepath is resolved against ITS OWN working directory, which is not
# guaranteed to be yours: a relative "./preview.png" fails with
#   RuntimeError: Render error (No such file or directory) cannot save: 'preview.png'
# Resolve both paths up front, and create the output directory.
STL_DIR = os.path.abspath(argv[0] if len(argv) > 0 else "./stl")
OUT = os.path.abspath(argv[1] if len(argv) > 1 else "./preview.png")
RES_X = int(argv[2]) if len(argv) > 2 else 1280
RES_Y = int(argv[3]) if len(argv) > 3 else 720
SAMPLES = int(argv[4]) if len(argv) > 4 else 32

if not os.path.isdir(STL_DIR):
    raise SystemExit(f"STL directory not found: {STL_DIR}")
os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)

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
if not stls:
    # fail loudly: an empty scene renders a clean black image and looks like a success
    raise SystemExit(f"no .stl file in {STL_DIR}")
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

# Bounding box of everything actually imported — the camera must fit THIS, not a guess.
# (A hard-coded camera position framed the part off the right and bottom edges: the
# picture looked like a render failure while the geometry was fine.)
# `matrix_world` is STALE until the depsgraph runs: without this update the bboxes are
# still the pre-layout ones, the camera aims at the origin, and the render comes out
# empty — the failure looks exactly like a lighting problem.
bpy.context.view_layer.update()
from mathutils import Vector

bbox_pts = []
for obj in objects:
    bbox_pts += [obj.matrix_world @ Vector(corner) for corner in obj.bound_box]
if bbox_pts:
    bb_min = Vector((min(p.x for p in bbox_pts), min(p.y for p in bbox_pts), min(p.z for p in bbox_pts)))
    bb_max = Vector((max(p.x for p in bbox_pts), max(p.y for p in bbox_pts), max(p.z for p in bbox_pts)))
else:
    bb_min, bb_max = Vector((-50, -50, -50)), Vector((50, 50, 50))
center = (bb_min + bb_max) / 2.0
radius = max((bb_max - bb_min).length / 2.0, 1.0)

# Ground plane, just under the lowest point
bpy.ops.mesh.primitive_plane_add(size=radius * 6, location=(center.x, center.y, bb_min.z - 0.5))
ground = bpy.context.active_object
ground_mat = make_material("ground", (0.08, 0.08, 0.1))
ground.data.materials.append(ground_mat)

# Camera: place it on a fixed direction, at the distance that fits the bbox, and AIM it
# at the bbox centre (rotation computed, never eyeballed).
bpy.ops.object.camera_add()
cam = bpy.context.active_object
bpy.context.scene.camera = cam
cam.data.lens = 50
cam.data.sensor_width = 36
fov = 2.0 * math.atan(cam.data.sensor_width / (2.0 * cam.data.lens))
direction = Vector((1.0, -1.3, 0.85)).normalized()
cam.location = center + direction * (radius / math.sin(fov / 2.0) * 1.35)
cam.rotation_euler = (center - cam.location).to_track_quat("-Z", "Y").to_euler()

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

# Self-check: project the corners into the camera's own space and print the range.
# 0..1 means "inside the frame"; anything outside is a cropped render. The camera matrix
# is stale until the depsgraph runs, so update BEFORE measuring (skipping this made a
# perfectly framed image read as "-41..42" and sent us chasing a lighting bug).
bpy.context.view_layer.update()
from bpy_extras.object_utils import world_to_camera_view

scene_now = bpy.context.scene
ndc = [world_to_camera_view(scene_now, cam, obj.matrix_world @ Vector(c))
       for obj in objects for c in obj.bound_box]
if ndc:
    print(f"framing: x {min(p.x for p in ndc):.2f}..{max(p.x for p in ndc):.2f} | "
          f"y {min(p.y for p in ndc):.2f}..{max(p.y for p in ndc):.2f}  (0..1 = in frame)")
