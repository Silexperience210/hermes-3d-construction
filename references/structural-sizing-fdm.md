# Dimensionner une pièce porteuse imprimée (couples, torsion, orientation)

When the user says « ça a l'air fragile », la réponse est un calcul, pas un avis. Ce
fichier donne l'ordre des opérations qui a tenu sur un bras de lampe articulée (deux servos
20 kg·cm, leviers ~110 mm) et les règles de dimensionnement qui en sont sorties.

## 1. Relever la section RÉELLE dans le générateur, pas sur l'écran

- `grep` les constantes du générateur (`T`, `BAR_W`, épaisseurs) : une « barre » de 12 × 8 mm
  n'est pas un tube, et c'est souvent la première fois qu'on regarde la section.
- Flexion : `W = b·h²/6` (mm³) → `M_adm = W × σ_adm`. Torsion d'un rectangle `a ≥ b` :
  `J = a·b³/3 × [1 − 0,63·(b/a) + 0,052·(b/a)⁵]` (≈ **1 200 mm⁴** pour 12 × 8, pas 2 050) et
  `W_t = b·h²/(3 + 1,8·h/b)`.
- **Ne jamais sortir un J « de tête »** : le vérifier par deux formules concordantes, puis faire
  recouper le calcul par un second agent. Un J surestimé de 70 % fait conclure à tort que la
  pièce est saine ; ici la valeur exacte était encore plus basse que celle de l'auditeur, donc la
  conclusion s'est renforcée au lieu de s'affaiblir.
- Comparer à l'**événement réel**, pas au nominal : couple servo × la marge lue dans le contrôle,
  **plus** un cas d'usage (une main qui s'appuie sur la tête : 20 N à 20 mm ≈ **40 kg·cm**).
- Un bras très surdimensionné en flexion peut être juste en torsion — c'est le cas normal d'une
  barre pleine, et c'est ce que l'œil perçoit comme « fragile ».

## 2. En torsion, le cisaillement court LE LONG des couches

- Sur une pièce FDM, τ s'applique aux **interfaces de couches** : la contrainte admissible est
  celle de l'adhésion inter-couches (~50-60 % de la traction Z), pas la résistance dans le plan
  (~45 MPa pour du PETG). Sur un barreau 12 × 8 : capacité ≈ **28 kg·cm** — sous le cas d'usage
  ci-dessus : la pièce se délaminera en torsion **avant** de casser en flexion.
- La raideur de torsion vit dans le **périmètre**, pas dans le remplissage. Le barreau plein est
  la pire forme, la coque **fermée** la meilleure : ordre de grandeur mesuré (Ø32 × 2,5 mm contre
  12 × 8, PETG) → **×8 en flexion, ×42 en torsion**, avec 29 % de la matière d'un Ø32 plein.
- Ajourer ne se justifie que par la charge : **cordons fermés** (anneaux pleins tous les 10-15 mm,
  denses près des articulations, ouverts seulement à mi-portée), aucun trou à moins de ~1,5× la
  hauteur locale du moment. Un ajouré décoratif coupe le périmètre en rubans non connectés et
  **détruit** la torsion — l'inverse de l'intention.

## 3. L'orientation d'impression fait partie du calcul

- Poser la pièce pour que les contraintes de flexion travaillent **dans le plan des couches**
  (axe long horizontal), jamais pour que les couches deviennent des sections. Imprimer debout une
  poutre sollicitée en flexion fait tirer directement sur l'adhésion.
- Fendre une coque porteuse au **plan neutre** (contrainte nulle) en deux demi-coques et les
  réunir par des **brides boulonnées** (M3 + inserts à chaud) tous les 20-30 mm : deux vis
  n'exploitent pas un gain de ×42. La colle est un complément, jamais la reprise d'effort.
- Parois travaillantes : ≥3 périmètres (~1,2 mm) ; ≥4 périmètres et 4-5 mm de matière autour de
  chaque insert ; ≥40 % de remplissage dans les bossages et anneaux de bord. Une paroi < 0,8 mm
  en torsion vibre et devient bruyante.
- Sans support : ponts ≤ 10 mm, fentes ≤ 8 mm, Ø ≤ 6 mm dans une paroi verticale ; un passage de
  câble = un rectangle arrondi 8 × 3 mm.
- Les carters d'articulation s'impriment dans leur **position d'usage**, pour que les vis de
  serrage pincent dans le plan des couches (c'est là que les molettes imprimées se fendent).

## 4. Ne pas transformer un composant acheté en organe de structure

- Le boîtier d'un servo n'est pas une zone de serrage : appui sur des patins, retenue par les
  oreilles de fixation, 0,2-0,3 mm de jeu.
- **Le PETG flue sous serrage permanent et près de 50 °C** : le serrage se relâche, le jeu
  apparaît. Préférer un blocage **géométrique** à un blocage par friction.
- Un volume **clos** autour d'un servo qui tient la charge en permanence chauffe : prévoir des
  ouvertures de ventilation discrètes (les trous hors zones chargées ventilent — l'ajouré gagne
  alors sur les deux tableaux), sinon prouver au banc que l'articulation tient seule une fois le
  servo relâché. Vérifier aussi le **jeu total** de la chaîne articulée : au-delà de ~0,5° il
détruit toute stratégie de reprise « sans saut » au réveil (démarrage sur la position persistée).

## 5. Un organe de sécurité se juge sur sa FONCTION, pas sur sa présence

- Mesurer la **garde réelle** : angle de butée − angle de contact, l'organe de sécurité **ôté**.
  Un pion dont la garde est plus fine que le dépassement de l'actionneur ne protège rien et
  consomme du jeu dans toutes les postures — c'est un alibi. Un pion PETG n'arrête pas un 20 kg·cm.
- Quand deux contraintes sont **arithmétiquement incompatibles** (tenir 0,4 mm de jeu *et*
  arrêter avant le contact, à 0,38 mm fermé par degré), ce n'est pas un seuil à ajuster : c'est
  la **géométrie** qui bouge, ou la fonction qu'on supprime. Calculer l'impossibilité AVANT de
  faire tourner un agent dessus — deux étapes entières ont été perdues à régler une butée
  impossible, et deux autres à découvrir la chaîne de contacts qu'un balayage trop grossier
  cachait (voir `coding-agent-delegation/references/verifier-le-travail-dun-delegue.md` §3).
