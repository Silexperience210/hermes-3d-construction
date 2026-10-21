# CAD avancé — joints, inserts, vis

Complément au SKILL.md pour l'assemblage mécanique imprimé en 3D.

## Joints d'encliquetage (snap-fit)

Le clip le plus simple : une languette flexible qui se verrouille dans une
fenêtre. Paramètres clés pour du PLA :

- **Épaisseur de la languette** : 1.0–1.5 mm (flexible mais pas cassante)
- **Longueur de flexion** : ≥ 10 mm (plus long = moins de contrainte)
- **Dépouille** : 1–2° sur la face d'engagement pour un encliquetage souple
- **Jeu latéral** : 0.2 mm de chaque côté de la fenêtre

```python
# Languette de clip simple (à insérer dans un boîtier)
import bpy

TAB_WIDTH   = 8.0    # largeur de la languette
TAB_DEPTH   = 12.0   # longueur de flexion
TAB_THICK   = 1.5    # épaisseur
TAB_HOOK    = 1.2    # hauteur du crochet

# Corps de la languette
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, 0, 0))
tab = bpy.context.active_object
tab.scale = (TAB_WIDTH / 2, TAB_DEPTH / 2, TAB_THICK / 2)
bpy.ops.object.transform_apply(scale=True)

# Crochet : un petit cube en bout, décalé vers le haut
bpy.ops.mesh.primitive_cube_add(size=1, location=(0, TAB_DEPTH/2 - 1, TAB_HOOK/2))
hook = bpy.context.active_object
hook.scale = (TAB_WIDTH / 2, 1.0, TAB_HOOK / 2)
bpy.ops.object.transform_apply(scale=True)
```

## Inserts filetés thermiques (heat-set inserts)

Pour des vis répétées, ne jamais visser directement dans le plastique :
insérer un filetage métallique à chaud. Le trou d'accueil :

| Insert | Ø trou | Profondeur |
|---|---|---|
| M2 | 3.2 mm | 4 mm |
| M2.5 | 3.7 mm | 4 mm |
| M3 | 4.2 mm | 5 mm |
| M4 | 5.2 mm | 6 mm |

Le trou doit être légèrement plus petit que l'insert (interférence 0.2 mm),
avec un chanfrein d'entrée pour guider l'insert à chaud.

## Trous de vis traversants vs taraudés

- **Traversant (vis + écrou)** : Ø = vis + 0.5 mm (M3 → Ø 3.5)
- **Auto-taraudé (vis directe dans le plastique)** : Ø = vis × 0.8 (M3 → Ø 2.4
  trou pilote, visse une fois, ne pas démonter souvent)

## Tolérance des filetages

Si tu imprimes un filetage (rare, fragile en FDM) : majorer le pas de 0.2 mm
et utiliser un `SLIDING_FIT` de 0.2 mm. Sinon, préférer les inserts ou un
écrou prisonnier.

## Écrou prisonnier (captive nut)

Pour un écrou M3 encastré : cavité hexagonale de 5.6 mm (sur-plat) + 0.3 mm
de jeu, profondeur = épaisseur de l'écrou + 0.5 mm, avec une ouverture
latérale pour glisser l'écrou en place.
