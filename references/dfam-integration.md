# Intégration DfAM dans les générateurs d'enclosure (août 2026)

## Pattern validé (gen_v2.py and gen_v3.py of a parametric enclosure generator)

Après chaque export STL, le générateur appelle `dfam_check(path)` qui lance le
venv dédié en subprocess et parse le JSON. Règles d'or :

1. **Non-bloquant** : le check DfAM ne fait JAMAIS échouer la génération.
   `try/except` + message « DfAM: ... — ignoré ». Un souci de murs/surplombs
   s'imprime comme avertissement, la pièce reste générée pour inspection visuelle.
2. **JSON factuel** : l'outil (`dfam_tool.py measure`) rend des mesures brutes —
   le verdict (pass/fail) appartient au workflow, pas à l'outil.

```python
def dfam_check(path):
    try:
        py = os.path.expanduser("python3")
        tool = os.path.expanduser(
            "scripts/dfam_tool.py")
        if not (os.path.exists(py) and os.path.exists(tool)):
            print("    DfAM: outil indisponible — ignoré")
            return
        import json
        raw = subprocess.run([py, tool, "measure", path, "--angle-limit", "45"],
                             capture_output=True, text=True, timeout=120)
        if raw.returncode != 0:
            print(f"    DfAM: échec ({raw.stderr.strip()[-120:]}) — ignoré")
            return
        d = json.loads(raw.stdout)
        mesh = d.get("mesh", {})
        walls = d.get("wall_thickness", {})
        over = d.get("overhangs", {})
        wt = mesh.get("watertight")
        wt_txt = "OK" if wt else "non fermé (normal pour pièce assemblée)"
        print(f"    DfAM  watertight {wt_txt} | {mesh.get('triangle_count', '?')} tris | "
              f"{mesh.get('body_count', '?')} corps")
        if walls:
            print(f"    DfAM  murs: min {walls.get('min_mm')} mm | p05 {walls.get('p05_mm')} mm | "
                  f"médiane {walls.get('median_mm')} mm (FDM ≥1,2)")
        if over:
            pct = over.get("down_facing_area_below_limit_pct")
            print(f"    DfAM  surplombs <45°: {over.get('down_facing_area_below_limit_mm2')} mm² "
                  f"({pct}%)")
    except Exception as exc:
        print(f"    DfAM: erreur ({exc}) — ignoré")
```

## Interprétation des sorties (pièges vus en réel)

- **`watertight: true` + `body_count > 1` = NORMAL** pour une construction par
  booléens : les bossages PCB, colonnes de vis et nervures unionés au shell
  principal forment des coquilles fermées séparées. Exemple réel : boîtier v3
  PUPITRE → `watertight OK | 5 corps`, murs p05 1,5 mm ✅. Ne pas alarmer.
- **`watertight: false` = normal pour pièce assemblée** (coquille ouverte par
  design, couvercle séparé). Blender `check_watertight.py` est l'autorité
  topologique (0 arête non-manifold) ; trimesh est plus strict.
- **`min_mm` des murs = échantillon parasite possible** (0,011 mm vu) →
  regarder `p05_mm` et la médiane. `p05_mm` sous la limite = vraie violation.
- **`units_suspect: true`** → source en mètres/pouces, toutes les mesures de
  surplomb sont nulles. Vérifier les unités avant comparaison.

## Cas réels documentés

| Pièce | p05 murs | Verdict |
|---|---|---|
| body v2 (boîtier plat) | 3,18 mm | ✅ largement au-dessus 1,2 |
| battery_door v2 (jupe 1,0) | 1,0 mm | ❌ → épaissir à 1,5 → ✅ |
| top_plate v2 | 1,89 mm | ✅ watertight, 1 corps |
| v3 body (PUPITRE) | 1,5 mm | ✅ watertight OK, 5 corps |
| v3 bezel | 1,95 mm | ✅ (surplombs 32,7 % = bossages, à noter) |
| v3 tray | 1,6 mm | ✅ 0 % surplombs |

## Wrapper autonome

`~/.local/bin/dfam-check.sh <fichier.stl> [--angle-limit 45] [--orientations]`
— mesure n'importe quel STL sans toucher au générateur.
