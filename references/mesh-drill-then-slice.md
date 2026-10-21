---
name: mesh-print-prep
description: Use when preparing a 3D mesh for print (drilling, slicing).
---

# Mesh Print Prep — préparer un mesh 3D (souvent généré par IA) pour l'impression

Pipeline validé sur la a 1 m statue (WebAR GLB → 3 morceaux imprimables
avec chevilles, 24 cm). Les modèles générés par IA (Tripo — préfixe
`tripo_node_`, Meshy…) sont des meshes « artistiques » pour WebAR, PAS des
modèles CAO : multi-coquilles, coquilles ouvertes, 100-400 corps éclatés.
Le slicer refuse ou produit du vide.

## Ordre des opérations (validé)

1. **Convertir GLB → OBJ via Blender** si le GLB est compressé
   `KHR_draco_mesh_compression` : trimesh lit alors des vertices à ZÉRO
   (bbox 0,0,0). `bpy.ops.import_scene.gltf` décode Draco nativement, puis
   `wm.obj_export` avec `transform_apply` (sinon transform non appliquée).
2. **Réparer/scaler** : `m.apply_scale(1000.0)` si l'export Blender est en
   MÈTRES (bbox 0,077 au lieu de 77 mm) → sinon volume nul au DfAM.
3. **Percer AVANT de découper** : les trous traversants (Ø6) percés sur le
   mesh complet se retrouvent alignés dans les 2 morceaux adjacents après
   découpe. NE PAS percer après remesh (le remesh détruit les trous).
4. **Découper en morceaux** avec `bmesh.ops.bisect_plane` (voir ci-dessous).
5. **Chevilles d'alignement** : Ø5,8 pour trous Ø6 (jeu 0,2 mm), hauteur
   20 mm (chevauche 10 mm par morceau). Imprimées séparément.

## ⚠️ Le boolean échoue sur ces meshes — utilise manifold3d

- **Blender boolean** : échoue silencieusement (trous partiels, 1/4 percés)
  ou **détruit le mesh** (export « 0 verts », fichiers STL corrompus 84 o).
- **trimesh engine défaut** (Blender backend) : `ValueError: Not all meshes
  are volumes!` — même sur un mesh `is_watertight=True` (coquilles multiples).
- **SOLUTION** : `pip install manifold3d` puis
  `mesh.difference(cyl, engine='manifold')` — le solver Google répare les
  coquilles au passage et perce proprement (testé : 4/4 trous, watertight).

## Découpe bisect (fiable, contrairement aux boolean)

```python
def bisect_at(bm, z, keep_above):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=0.02,
                           plane_co=(0, 0, z), plane_no=(0, 0, 1),
                           clear_inner=keep_above, clear_outer=not keep_above)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
# garder la tranche [z0, z1] : bisect_at(z0, True) puis bisect_at(z1, False)
# puis bmesh.ops.holes_fill sur les bords aux cotes z0/z1 (referme les plans)
```

## Vérifier les trous percés (la section shapely est trompeuse)

Compter les faces de paroi : normale horizontale (`|nz| < 0.3`) ET centroïde
à ~3 mm des positions attendues (x=±18, y=0), seuil > 20 faces = trou présent.
`m.section().to_planar()` sous-compte (1 trou au lieu de 2, 0 au lieu de 4).

## Pièges

- Le fichier envoyé par l'utilisateur peut porter un nom différent de ce qui
  est annoncé (90 Mo « eef8f…obj » = en réalité `Fred_statue.obj`) — toujours
  lister le dossier réel (`ls -b` pour les caractères spéciaux) avant d'agir.
- Le chemin a path containing an accented character (`~/Státue/`) fait échouer trimesh (`ValueError:
  string is not a file`) — copier vers un chemin ASCII pour l'analyse.
- OBJ Blender 5.0 avec vertex colors (lignes `v x y z r g b`) : trimesh charge
  avec `process=False`, ou passer par Blender.
- Corps microscopiques (1-2 faces) = débris à ignorer/supprimer ; le corps
  principal est souvent le seul avec volume non nul.
- Un mesh « 409 corps » n'est pas forcément perdu : le remesh voxel Blender
  (3 mm, `use_remove_disconnected=True`) ferme une coquille monobloc — utile
  pour imprimer d'un bloc, mais percer APRÈS le remesh.

## Outils

- dedicated venv: `python3 -m venv .venv` then `pip install trimesh manifold3d shapely mapbox-earcut`
- Blender headless : `blender --background --factory-startup --python script.py`
- Validation finale : skill `dfam-check` (murs, surplombs, watertight).

## Références

- ``mesh-glb-to-printable.md` : the full repair pipeline (scripts).
