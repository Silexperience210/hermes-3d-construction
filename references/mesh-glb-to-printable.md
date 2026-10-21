---
name: 3d-mesh-preparation
description: Use when preparing 3D meshes for printing (GLB, Draco).
---

# Préparation de maillages 3D pour impression

Prépare un modèle 3D quelconque (téléchargé, généré par IA, GLB WebAR, OBJ
Blender) jusqu'au STL prêt à slicer : décodage, unités, réparation de coquille,
découpe en pièces imprimables, chevilles d'assemblage.

Complémentaire : `dfam-check` VALIDE le résultat (murs/surplombs/watertight) ;
`bambu-lab-printing` slice et envoie. Ce skill transforme le mesh AVANT.

## Pipeline général

1. **Identifier le format et la source** (en-tête du fichier) :
   - `# Blender X.Y.Z OBJ File` → export Blender, échelle en **mètres** par défaut
   - `KHR_draco_mesh_compression` dans un GLB → vertices compressés, trimesh les lit à zéro
   - `o tripo_...` → mesh généré par IA (Tripo/IA) → multi-coquilles, NON watertight
2. **Décoder** : GLB Draco → **Blender** (`import_scene.gltf`) le décode nativement ;
   trimesh renvoie des vertices à zéro sans handler. Puis exporter OBJ/STL.
3. **Unités** : Blender exporte en mètres, les slicers lisent en mm. Si le bbox
   est ~0,1-1,0 (mètres) au lieu de 20-300 (mm) : **scale ×1000** avant tout calcul.
   Le signe : `volume ≈ 0` et `murs ≈ 0,001 mm` au DfAM.
4. **Analyser** (`trimesh`) : verts/faces, bbox, volume, `is_watertight`, `split()`
   → nb de corps. Un mesh IA = souvent 100-400 corps + fragments microscopiques.
5. **Réparer** si pas imprimable :
   - Blender **Remesh voxel** (taille ~3 mm pour un modèle de 24 cm) → coquille
     fermée, supprime les fragments ; `use_remove_disconnected=True`
   - **Decimate** ratio ~0,25 pour alléger (le slicer n'a pas besoin de 1M faces)
6. **Scaler** à la hauteur cible (ex. 240 mm = max plateau Bambu), centrer Z=0.
7. **Découper** en pièces si trop haut ou trop de supports (voir ci-dessous).
8. **Exporter STL** + **vérifier** chaque pièce : watertight, dims, volume, DfAM.

## Découpe en pièces — le piège n°1 : les booléens

**Les opérations booléennes (Blender ET trimesh) échouent sur les meshes
générés par IA multi-coquilles.** Symptômes : 1 trou percé sur 4, mesh détruit
(« 0 verts », STL de 84 octets), ou `ValueError: Not all meshes are volumes!`
(trimesh délègue à Blender et exige des volumes fermés).

**Ce qui MARCHE de façon fiable : la découpe par plans (bisect)**
```python
# Blender, bmesh : garder la tranche [z0, z1]
bmesh.ops.bisect_plane(bm, geom=..., plane_co=(0,0,z), plane_no=(0,0,1),
                       clear_inner=keep_above, clear_outer=not keep_above)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z-z0)<0.6 or ...])
```
→ chaque morceau est watertight et se slice proprement.

## Chevilles d'alignement (assemblage multi-pièces)

- Imprimer les chevilles **séparément** (Ø5,8 mm × 20 mm pour des trous Ø6)
- **Percer les trous AU FORET après impression** (Ø6, 2 trous par jointure,
  x = ±18 mm, traversant les 2 faces jointes) — le PLA se perce parfaitement
- C'est la méthode pro standard quand les booléens refusent le mesh ; ne pas
  bloquer sur des trous intégrés si le mesh résiste.
- Coller : époxy ou cyanoacrylate, cheville + morceaux, alignement garanti.

## Vérification finale

- `trimesh` : chaque pièce watertight, dims cohérentes avec la somme des morceaux
- Section pour compter les trous : `mesh.section(plane_origin, plane_normal)` →
  `to_planar()[0].polygons_full` (besoin de `shapely` dans le venv)
- `dfam-check` sur chaque pièce avant de slicer

## Références

- ``mesh-drill-then-slice.md` : full case — a 1 m statue (WebAR Draco GLB
  → 24 cm imprimable en 3 pièces), 4 tentatives booléennes échouées, solution bisect.
