# FDM part fit & verification — concrete pitfalls

Validated on a real enclosure iteration (`enclosure/gen_v2.py`).
Trois échecs réels documentés avec leur correctif.

## 1. Bevel modifier → bbox gonflé (~0.5 mm) → la porte ne rentre pas

Symptôme : pièce emboîtée (porte clipsée) aux cotes exactes qui ne rentre pas
dans son ouverture ; le bbox mesuré du STL est plus grand que les dimensions
passées au générateur.

Cause : `rounded_box` (box + modifier BEVEL `miter_outer='MITER_ARC'`) gonfle
l'enveloppe de ~0.45-0.8 mm selon les axes. La porte déborde de son ouverture.

Correctif — coins arrondis SANS bevel, bbox exact :

```python
def rounded_plate(name, x0, x1, y0, y1, z0, z1, r):
    """Plaque à coins arrondis : box + 4 cylindres tangents aux bords.
    Le bbox reste EXACTEMENT x0..x1 × y0..y1 (pas de gonflement bevel)."""
    ob = box(name, x0, x1, y0, y1, z0, z1)
    for sx in (-1, 1):
        for sy in (-1, 1):
            cx = (x0 if sx < 0 else x1) - sx * r
            cy = (y0 if sy < 0 else y1) - sy * r
            boolean(ob, cyl(f"{name}_corner_{sx}_{sy}", r, cx, cy, z0, z1, seg=24), 'UNION')
    return ob
```

Règle : toute pièce emboîtée (porte, couvercle, insert) = coins ronds par
cylindres, jamais par bevel. Le bevel reste OK pour les pièces non contraintes.

## 2. Booléens coplanaires → le 2e DIFFERENCE disparaît

Symptôme : fraisage étagé (Ø6.5×1 mm côté extérieur + passage Ø3.5 contigus)
— le passage n'apparaît pas dans le STL, alors que l'anneau intérieur est
visible au niveau de la face partagée (z=-1).

Cause : deux cylindres DIFFERENCE qui partagent une face coplanaire exacte →
le solver EXACT de Blender évapore le second (géométrie dégénérée).

Correctif : chevaucher les deux cylindres de 0.1 mm :
`passage z = -1.0..0` → `-0.9..0` quand le fraisage est `-2.0..-1.0`.

Vérification : coupe par intersection de plan (voir §4) — rayon attendu 3.25
dans le fraisage, 1.75 dans le passage.

## 3. Ouverture dans le fond → colonnes flottantes

Symptôme : le corps a 3 composantes connexes — les colonnes de vis arrière
(+ leurs pastilles d'ancrage) flottent dans le vide de l'ouverture.

Cause : une pastille cylindre Ø6 ajoutée par UNION dans le vide de l'ouverture
ne touche RIEN du corps (à 4 mm des murs) → pièce flottante.

Correctif : ancrer par PONT rectangulaire jusqu'à une zone pleine
(la bande de fond arrière) :
```python
# pastille = box(x 24..29.5, y 37..43.5, z 0..1.5) touchant la bande y≥43.5
```
Et la pièce emboîtée (porte) reçoit des ENCOCHES dans sa jupe aux positions
des ponts (sinon elle ne monte pas à fond). Les ponts ne doivent pas dépasser
le diamètre du fraisage de la pièce emboîtée (avalés par le fraisage Ø6.5).

## 4. Mesure d'un STL SANS trimesh — méthodes fiables

### bbox + comptage des composantes (pièces flottantes)

```python
def components(tris, tol=0.02):
    # union-find sur les triangles partageant une arête (sommets arrondis à tol)
    # → liste des tailles de composantes ; attendu [N] (1 seule pièce)
```

### Rayons de trous par INTERSECTION DE PLAN (pas par sondage de sommets)

PIÈGE : les parois d'un cylindre n'ont de sommets qu'aux DEUX extrémités (les
quads ne sont pas subdivisés) — sonder les sommets à z intermédiaire ne
trouve RIEN. Toujours couper par plan :

```python
def rings_at(tris, z):
    pts = []
    for t in tris:
        seg = []
        for a, b in ((t[0],t[1]),(t[1],t[2]),(t[2],t[0])):
            if (a[2]-z)*(b[2]-z) <= 0 and abs(a[2]-b[2]) > 1e-9:
                tt = (z-a[2])/(b[2]-a[2])
                seg.append((a[0]+(b[0]-a[0])*tt, a[1]+(b[1]-a[1])*tt))
        if len(seg) == 2: pts.append(seg[0]); pts.append(seg[1])
    return pts
# puis mesurer les distances au centre attendu (±26.75, ±42.5) → rayon
```

Vérifier aussi la COUVERTURE ANGULAIRE (12 secteurs de 30°) pour distinguer un
cercle complet d'un trou coupé par le bord de la pièce (demi-lune).

### Étanchéité

bmesh (Blender headless) : `[e for e in bm.edges if not e.is_manifold]` +
`[e for e in bm.edges if e.is_boundary]` → attendu : peu de non-manifold
(artefacts booléens), 0 bord libre. (trimesh 5.0 n'a plus `edges_boundary`.)

## 5. Rendu Blender — ne jamais rendre noir

- `read_factory_settings(use_empty=True)` = scène SANS lumière → noir.
  Ajouter : world (Background 0.6,0.63,0.7 / 1.4), SUN (energy 4), AREA.
- `film_transparent = True` → les pixels de fond sont alpha 0 : un check de
  luminance lit « noir ». Désactiver pour les previews.
- Caméra : `type='ORTHO'`, `ortho_scale ≈ 0.135` pour un objet 100 mm, cadrée
  sur la pièce. Vues : iso, ¾ dessous (pour voir une porte), dessus (fraiseur).
- Contrôle automatique : luminance moyenne du PNG (stdlib zlib, filtre IDAT)
  > 15/255 sinon suspect.

## 6. Monobloc INA SSEMBLABLE → dessus amovible (plaque écran)

Symptôme (découvert après 3 itérations « OK » du générateur) : la coque
fermée (poche écran fraisée dans le dessus + fond + parois) ne peut RECEVOIR
aucun module. Le verre 63×95 passe dans la poche 63,5×95,5, mais le panneau
LCD derrière (~53×78) est PLUS GRAND que la fenêtre active (49×73,5) → bloqué
par le fond de poche ; l'ouverture porte (62×44) est trop petite pour la carte
(59×91) ; aucun accès arrière. Le STL était parfait (étanche, 1 composante)
et totalement inutilisable.

Règle : vérifier le CHEMIN D'INSERTION du plus grand sous-ensemble AVANT de
générer. Un monobloc n'est assemblable que si la carte+module passe par une
ouverture (dessus, dessous ou arrière).

Correctif — dessus amovible (type téléphone), validated on a real part :
- Le corps s'arrête sous le dessus (`Z1_BODY = Z1 - TOP_PLATE_T`), la cavité
  est OUVERTE en haut ; le rebord supérieur du corps doit rester PLAT (ne pas
  utiliser `rounded_box`/bevel sur ce rebord : le bevel le ronge et la plaque
  n'a plus d'appui — coins ronds par cylindres, §1).
- Plaque écran (`TOP_PLATE_T ≈ 2.4 mm`) avec poche verre **TRAVERSANTE**
  (63,5×95,5) : AUCUN fond sous le verre, sinon il colle au panneau qui pend
  sous la plaque (0,8 mm de fond = collision). La fenêtre active devient
  inutile (le verre est transparent).
- 4 bossages taraudés sous la plaque (vis M2.5 par le dessous : fond →
  colonne Ø6 → trou carte → pré-trou Ø2,2 du bossage). Ils sont SOUS le trou
  verre (la plaque y est absente) → les relier à l'anneau par des AILES
  (fins parallélépipèdes ~2×5×6 mm, sous le verre donc invisibles, au-dessus
  de la carte) pénétrant 1 mm dans l'anneau.
- Piège UNION coplanaire (même famille que §2) : un bossage dont le sommet
  est coplanaire avec le dessous de la plaque reste une composante séparée →
  chevaucher verticalement de 0,5 mm dans la plaque.
- Bonus printabilité : le corps s'imprime fond-à-plat SANS pont long (toit
  ouvert) et la plaque à plat. Un monobloc ferait brider le dessus (cadre de
  poche écran) sur 60-95 mm de cavité — quasi impossible en PETG sans
  supports (cf. §6 de l'audit Kimi).

Séquence d'assemblage : module (verre+panneau+carte) posé dans le corps (la
carte tombe sur les colonnes) → plaque posée (le verre entre dans la poche)
→ 4 vis par le dessous pincant tout l'empilement.
