---
name: enclosure-stl-cad
description: Use when modifying parametric Blender STL enclosures.
---

# Enclosure STL CAD — générateurs paramétriques Blender

Conçoit/modifie des boîtiers imprimés 3D générés par des scripts Blender Python paramétriques
(ex. `enclosure/gen_v2.py` — terminal plat v2 ; `gen.py` = legacy wedge).

## Workflow
1. **Toucher le GÉNÉRATEUR, jamais le STL brut** : les `.stl` sont des sorties. Modifier les constantes/geometry dans le script, puis :
   `blender --background --python gen_v2.py` (régénère body/top_plate/battery_door)
   `blender --background --python gen_v2.py -- --preview` (rend preview.png/front/iso/bottom — ajoute la vue top si absente)
2. **QA obligatoire** : `blender --background --python check_watertight.py` (les check-scripts utilisent `bpy` → tourner DANS Blender, pas python système), + `check_components.py` / `check_bridge_fit.py` / `check_door_components.py` (trimesh via le .venv du dossier).
3. **Validation visuelle utilisateur AVANT commit** : previews (iso/top/bottom) envoyées, l'utilisateur tranche. Zéro commit/push avant.

## Leçon bevel (critique — « beaucoup de problèmes de maillage »)
- **Bevel APRÈS les booléens = explosion** : 5 588 → 47 788 faces + 1 447 triangles dupliqués + normales inversées (volume négatif).
- **Bevel AVANT les booléens** (sur la coque simple — les découpes internes ne touchent pas le pourtour) → ~9-10k faces.
- **Nettoyage final obligatoire** (les booléens sur la coque bevelée laissent doublons/dégénérés) : `cleanup_mesh(ob)` — 2 passes `bmesh.ops.remove_doubles` (dist 0.001) + `dissolve_degenerate` + suppression des faces dupliquées avec clé par **POSITIONS** arrondies (les booléens créent des coïncidences à index différents) + `recalc_face_normals` (fixe le volume négatif). Appliquer aussi à la porte et la plaque.

## QA mesh — interpréter les checks
- **Blender = l'autorité** : `WATERTIGHT body=True door=True` + `non-manifold edges=0` = OK.
- **trimesh `is_watertight: False` = NORMAL** pour un boîtier : les « arêtes de bord » sont les OUVERTURES du design (cavité du haut, porte batterie, trou USB, poches) — pas des défauts.
- **Volume négatif** (trimesh) = normales inversées → `recalc_face_normals` dans le cleanup.
- Les ~90 doublons restants (intersections booléennes) : 0,3 %, les slicers les gèrent.

## Component-first : MESURER le vrai PCB avant de percer
- L'orientation du connecteur USB-C varie : **côté**, **arrière**, ou **vertical au MILIEU de la carte** (câble par le dessous — trou dans la FACE INFÉRIEURE, pas une encoche de bord !). L'utilisateur a corrigé 3× une mauvaise supposition — **demander/checker la doc** (projet de référence même carte, STL du boîtier fabricant : `/tmp/blockclock-gh/ref/case_orig/files/Case_JC3248W535C.stl`, mesurer la découpe via trimesh) avant d'implémenter.
- Les composants sur les modules (RC522/PN522) : l'épaisseur réelle = PCB + chip + pins (~4 mm, pas 3) — les rails de retenue doivent dégager l'encombrement réel.
- Rayon des coins de l'écran (ex. r5 sur JC3248W535C) → la fenêtre verre doit matcher.

## Délégation géométrie à Kimi K3 — piège et micro-étapes
Kimi K3 **analyse indéfiniment sans écrire** sur les géométries complexes (5 runs de pur raisonnement sur l'enclosure, zéro modif). Remèdes :
1. Micro-étapes : **1 seule action par run** (ex. « change la constante H 22→29, sauve, régénère, vérifie »), timeout court 300 s — ça, il le fait.
2. Spec ultra-précise : coordonnées/valeurs exactes (les constantes + les lignes), jamais « transforme la poche en glissière ».
3. Si ça bloque encore : **implémenter soi-même** (le générateur est lisible) — plus rapide que de relancer en boucle.

## Pièges
- `check_watertight.py` importe `bpy` → `blender --background --python check_watertight.py`, pas python.
- Les STL binaires : lire les dimensions via `struct` (header 80 o + uint32 n + 50 o/triangle) ou trimesh (venv du dossier).
- Blender 5 : `export_mesh.stl` déprécié → `wm.stl_export` (le script gère les deux).
