# Rendus 3D headless : vue éclatée, image « hero », cinématique

Recette validée sur un châssis imprimé multi-pièces (coques + roues + carte + servos)
reconstruit depuis ses STL réels et les cotes du projet.

## 1. Reconstruire l'ensemble, ne pas le dessiner

Importer les **pièces réelles** (`bpy.ops.wm.stl_import`) et n'ajouter en volume simple que
les composants absents des STL (servos, cartes, capteurs, batterie), avec leurs **cotes
constructeur** — jamais des proportions devinées :

- servo 9 g : corps 22,8 × 12,2 × 22,5 ; bride à 15,9 de la semelle, épaisseur 2,5, entraxe
  de pattes 32,2 ; axe Ø4,8 sur bossage Ø11,8 hauteur 1,5 ; avant-trous Ø1,7.
- carte T-Display-S3 Touch : 62 × 26 × 1,2 ; entraxe des trous M2 = 20,01.
- HC-SR04 : PCB 45 × 20 × 1,6 ; transducteurs Ø16, entraxe 26.

Placer chaque sous-ensemble par sa **liaison mécanique** (l'axe du servo est sur l'axe de
la roue ; le moyeu de la roue fait la longueur annoncée ; le composant repose sur sa face
d'appui), puis vérifier le rendu par vision (§5) : c'est le seul juge de « ça a l'air
assemblé correctement ».

## 2. Vue éclatée lisible

- Un décalage **par pièce** le long de sa **direction de montage réelle** (coques ±Y, roues
  ±X vers l'extérieur, carte/dalles vers l'avant, servos latéralement), pas une explosion
  radiale uniforme : le lecteur doit comprendre dans quel ordre on emboîte.
- Étiquettes : objets TEXTE créés **après** la caméra et orientés dessus
  (`(cam.location - pos).to_track_quat("Z", "Y").to_euler()`), taille ≥ 9 mm dans un cadre
  de 600 mm. Des étiquettes couchées dans le plan du sol sont illisibles.
- Deux rendus complémentaires : **iso éclaté** (comprendre l'ordre) et **interne** (coque
  avant masquée, pièces à leur place — c'est la vue qui sert au montage).
- Rendu « plan technique » : Workbench (fond clair, `show_object_outline`, `show_cavity`,
  caméra ORTHO) ou Cycles + `view_settings.view_transform = "Standard"`.

## 3. Image « hero » métal

- Matériaux Principled : `metallic = 1`, `roughness` 0,22-0,35, plus clair pour la coque,
  très sombre pour les roues ; bande de roulement en « caoutchouc » (`metallic` 0,15,
  `roughness` 0,65).
- **Écran émissif** : base presque noire + `Emission Color` orange à `Emission Strength`
  10-15 pour les yeux ; sans émission l'écran reste un rectangle noir et le rendu paraît
  « éteint ».
- **Environnement** : le métal se lit dans ce qu'il REFLÈTE → fond noir uni = métal mort.
  Un gris sombre (0,05) + 3-4 area lights (clé orange chaude, contre-jour froid, rasante
  chaude, dessus froid) donnent le rendu métal orange & noir.
- **`view_transform = "Standard"`** : AgX écrase les saturations — un orange vif ressort
  brun/cuivré. Ne pas chercher à compenser par la couleur de base.
- Penser à l'échelle : une area light de 240 mm sur un objet de 200 mm avec 10⁶ W éclaire
  correctement ; les énergies d'un studio de taille humaine donnent du noir.

## 4. Cinématique (orbite → éclaté → remontage → en marche)

Chronologie qui fonctionne (30 fps, ~26 s) :

| Phase | Images | Contenu |
|---|---|---|
| Orbite | 0-240 | tour lent autour de l'objet assemblé |
| Éclatement | 240-420 | pièces vers leur direction de montage, caméra qui recule |
| Remontage | 420-570 | retour à la position assemblée |
| En marche | 570-780 | l'objet *fonctionne* : pièces mobiles animées, clignements |

- **Orbite** = empty parent + caméra enfant, rotation de l'empty ; distance/hauteur en
  keyframes sur la position LOCALE de la caméra (§ piège des repères dans SKILL.md).
- **Éclatement** = stocker la position assemblée et la position décalée, keyframer les deux
  aux bornes de phases (assemblé → éclaté → assemblé) : la valeur intermédiaire est
  interpolée, aucune courbe à écrire à la main.
- **« En marche »** : animer ce qui prouve que l'objet vit — rotation des roues (keyframes
  sur `rotation_euler`), **tangage du corps autour de l'axe réel** (parenté des pièces du
  corps à un empty placé sur l'axe des roues, on ne fait tourner QUE cet empty), balayage
  du capteur de tête, clignement des yeux (mise à l'échelle verticale des amandes).
- Laisser l'interpolation par défaut (Bézier) : `action.fcurves` n'existe plus en Blender 5.

## 5. Contrôle qualité sans pouvoir regarder

Envoyer l'image (réduite à ~1600 px, JPEG q≈88, jamais le PNG 3-4 Mo) à un modèle
multimodal avec des questions fermées : « teinte dominante / aspect métal ? », « deux yeux
lumineux visibles ? », « sujet entier et centré ? », « défaut visible ? ». Les réponses
attrapent ce qu'aucune vérification numérique ne voit : cadrage coupé, écran éteint,
étiquettes illisibles, pièce dupliquée. Itérer jusqu'à « aucun défaut » avant de livrer.
Cette boucle coûte quelques minutes et évite de présenter un rendu raté.

## 6. Performance et encodage

- Ordre de grandeur pour arbitrer : `secondes/image ≈ k × (Mpx) × (échantillons)`. Mesurer
  sur 20-30 images plutôt que d'extrapoler une première image.
- Réduire d'abord les échantillons (32 + débruitage suffit largement pour une animation),
  ensuite la résolution : une vidéo 1280×720 livrée vaut mieux qu'un 1080p annoncé et jamais
  rendu. Garder l'image fixe en haute définition, c'est elle qu'on imprime/regarde.
- `scene.render.use_persistent_data = True` réutilise la scène entre les images.
- Encodage sans ffmpeg système (ffmpeg Playwright, VP8/WebM) :
  `ffmpeg -y -framerate 30 -i frames/f_%04d.png -c:v libvpx -b:v 8M -crf 10 -deadline good -cpu-used 3 -pix_fmt yuv420p sortie.webm`

## 7. Mesurer une ouverture dans une pièce imprimée

- **Comparaison de versions** : bbox / volume / nombre de sommets / nombre de faces (trimesh).
  Un volume qui baisse exactement de la matière retirée par un élargissement d'ouverture
  (`Δsurface × épaisseur de paroi`) **prouve** que seule cette ouverture a changé — c'est la
  vérification à présenter à l'utilisateur (une empreinte md5 ne prouve rien, Blender
  réordonne les sommets).
- **Sonder une ouverture au rayon est peu fiable sur une coque ouverte au plan de joint** :
  le rayon traverse l'ouverture puis ressort par le joint sans rien toucher, et le test
  « pas de matière » confond ouverture et vide extérieur (silhouette d'un glyphe, bord de
  pièce). Préférer le **script de vérification du projet** (qui mesure les cotes nominales)
  ou la lecture des paramètres du générateur, et n'utiliser le sondage que pour un oui/non
  (« cette ouverture débouche-t-elle ? »).
