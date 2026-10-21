"""Boîtier paramétrique 3D-imprimable — template CAD complet.

Un boîtier rectangulaire avec :
  - fillets (bevel) sur les arêtes extérieures
  - couvercle amovible avec clearance fit
  - trous de vis M3 aux coins (traversants)
  - ajustement mesuré au caliper

Modifie les constantes en tête, puis :
    blender --background --python enclosure.py
"""

import bpy
import os

# ═══════════ PARAMÈTRES ═══════════
LENGTH          = 80.0    # mm (dimension X)
WIDTH           = 50.0    # mm (dimension Y)
HEIGHT          = 25.0    # mm (dimension Z)
WALL_THICKNESS  = 2.0
FILLET_RADIUS   = 2.0     # rayon des arêtes arrondies
LID_CLEARANCE   = 0.3     # jeu couvercle/boîtier (clearance fit)
SCREW_HOLE_DIA  = 3.5     # Ø trou de passage vis M3
SCREW_OFFSET    = 6.0     # distance du trou au coin

# ═══════════ SCÈNE ═══════════
bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)

# ═══════════ CORPS DU BOÎTIER ═══════════
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, HEIGHT / 2))
body = bpy.context.active_object
body.name = "EnclosureBody"
body.scale = (LENGTH / 2, WIDTH / 2, HEIGHT / 2)
bpy.ops.object.transform_apply(scale=True)

# Creuser l'intérieur (boolean difference)
inner_l = LENGTH - 2 * WALL_THICKNESS
inner_w = WIDTH - 2 * WALL_THICKNESS
inner_h = HEIGHT - WALL_THICKNESS  # fond conservé
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, HEIGHT / 2))
cavity = bpy.context.active_object
cavity.scale = (inner_l / 2, inner_w / 2, inner_h / 2)
bpy.ops.object.transform_apply(scale=True)

bpy.context.view_layer.objects.active = body
mod = body.modifiers.new(name="Hollow", type='BOOLEAN')
mod.operation = 'DIFFERENCE'
mod.object = cavity
bpy.ops.object.modifier_apply(modifier="Hollow")
bpy.ops.object.select_all(action='DESELECT')
cavity.select_set(True)
bpy.ops.object.delete(use_global=False)

# ═══════════ TROUS DE VIS M3 ═══════════
# Bossages cylindriques aux 4 coins pour les vis
for sx in (-1, 1):
    for sy in (-1, 1):
        bx = sx * (LENGTH / 2 - SCREW_OFFSET)
        by = sy * (WIDTH / 2 - SCREW_OFFSET)
        # Bossage (renfort)
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32, radius=SCREW_HOLE_DIA + WALL_THICKNESS,
            depth=HEIGHT, location=(bx, by, HEIGHT / 2),
        )
        boss = bpy.context.active_object
        bpy.context.view_layer.objects.active = body
        bm = body.modifiers.new(name=f"Boss{sx}{sy}", type='BOOLEAN')
        bm.operation = 'UNION'
        bm.object = boss
        bpy.ops.object.modifier_apply(modifier=f"Boss{sx}{sy}")
        bpy.ops.object.select_all(action='DESELECT')
        boss.select_set(True)
        bpy.ops.object.delete(use_global=False)

        # Trou traversant
        bpy.ops.mesh.primitive_cylinder_add(
            vertices=32, radius=SCREW_HOLE_DIA / 2,
            depth=HEIGHT + 2, location=(bx, by, HEIGHT / 2),
        )
        hole = bpy.context.active_object
        bpy.context.view_layer.objects.active = body
        hm = body.modifiers.new(name=f"Hole{sx}{sy}", type='BOOLEAN')
        hm.operation = 'DIFFERENCE'
        hm.object = hole
        bpy.ops.object.modifier_apply(modifier=f"Hole{sx}{sy}")
        bpy.ops.object.select_all(action='DESELECT')
        hole.select_set(True)
        bpy.ops.object.delete(use_global=False)

# ═══════════ FILLETS (bevel) ═══════════
bpy.context.view_layer.objects.active = body
bpy.ops.object.select_all(action='DESELECT')
body.select_set(True)
bevel = body.modifiers.new(name="Fillet", type='BEVEL')
bevel.width = FILLET_RADIUS
bevel.segments = 3
bevel.limit_method = 'ANGLE'
bevel.angle_limit = 1.0472
bpy.ops.object.modifier_apply(modifier="Fillet")

# ═══════════ COUVERCLE ═══════════
lid_h = WALL_THICKNESS
lid_l = LENGTH + LID_CLEARANCE
lid_w = WIDTH + LID_CLEARANCE
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, HEIGHT + lid_h / 2))
lid = bpy.context.active_object
lid.name = "EnclosureLid"
lid.scale = (lid_l / 2, lid_w / 2, lid_h / 2)
bpy.ops.object.transform_apply(scale=True)

# Lèvre d'emboîtement (s'ajuste dans l'ouverture du boîtier)
lip_h = 3.0
bpy.ops.mesh.primitive_cube_add(
    size=1, location=(0, 0, HEIGHT - lip_h / 2 + 0.1),
)
lip = bpy.context.active_object
lip.scale = (inner_l / 2 - 0.1, inner_w / 2 - 0.1, lip_h / 2)
bpy.ops.object.transform_apply(scale=True)
bpy.context.view_layer.objects.active = lid
lipmod = lid.modifiers.new(name="Lip", type='BOOLEAN')
lipmod.operation = 'UNION'
lipmod.object = lip
bpy.ops.object.modifier_apply(modifier="Lip")
bpy.ops.object.select_all(action='DESELECT')
lip.select_set(True)
bpy.ops.object.delete(use_global=False)

# Fillets du couvercle
bpy.context.view_layer.objects.active = lid
bpy.ops.object.select_all(action='DESELECT')
lid.select_set(True)
lbevel = lid.modifiers.new(name="LidFillet", type='BEVEL')
lbevel.width = FILLET_RADIUS
lbevel.segments = 3
lbevel.limit_method = 'ANGLE'
lbevel.angle_limit = 1.0472
bpy.ops.object.modifier_apply(modifier="LidFillet")

# ═══════════ EXPORT ═══════════
out_dir = os.path.dirname(os.path.abspath(__file__))

for obj, name in [(body, "enclosure_body"), (lid, "enclosure_lid")]:
    bpy.ops.object.select_all(action='DESELECT')
    obj.select_set(True)
    bpy.context.view_layer.objects.active = obj
    path = os.path.join(out_dir, f"{name}.stl")
    bpy.ops.wm.stl_export(
        filepath=path,
        export_selected_objects=True,
        ascii_format=False,
        apply_modifiers=True,
    )
    print(f"✅ {path} — {os.path.getsize(path)} bytes")
