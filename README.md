# 3d-construction — a Hermes Agent skill

A drop-in skill for **building real, printable 3D parts**: parametric CAD in Blender, printability
measured instead of eyeballed, headless slicing, LAN send to a Bambu Lab printer, renders that
prove the result, and files handed over in a folder a human can actually open.

This is not a tutorial. It is the discipline we apply after each failure: every rule in
`SKILL.md` names the number or the symptom that produced it (a 0.117 mm thread clearance
announced as 0.30, a 5 588 → 47 788 face explosion after a bevel in the wrong order, a 212-part
mesh that was a resolution regression, not a broken model).

## Install

Hermes Agent loads any folder containing a `SKILL.md` from its skills directory:

```bash
git clone https://github.com/Silexperience210/hermes-3d-construction.git \
  ~/.hermes/skills/3d-construction
```

Then ask for a part; the skill triggers on CAD, printability, slicing and printer jobs.

## What is inside

| Path | What it gives you |
|---|---|
| `SKILL.md` | the whole chain, the rules, the verification gate |
| `references/` | the field notes: tolerances, booleans, bores, threads, DfAM limits, headless renders, Bambu CLI + MQTT/FTPS, mesh rescue, structural sizing, delivery |
| `scripts/verify_stl.py` | bounding box, connected components, boundary / non-manifold edges, section rings |
| `scripts/dfam_tool.py` | wall thickness, overhangs, support volume, print orientations |
| `scripts/audit_print_batch.py` | audit a whole part set: masses, orientations, real overhang above the plate |
| `templates/enclosure.py` | parametric case around real hardware — constants first, boolean cavities, fits |
| `templates/cabochon.py` | parametric curved part |
| `templates/render_mechanical_preview.py` | headless preview render |

## Toolchain

Blender 5 (`bpy`, headless) · trimesh + manifold3d + shapely + mapbox-earcut · numpy ·
Bambu Studio CLI (headless slicing) · paho-mqtt + curl/FTPS (printer) · ffmpeg (render frames) ·
whatever vision model you have, to check a render you cannot see.

No dependency is vendored: the repo ships our scripts and notes, not third-party code.

## The five rules that matter most

1. **Touch the generator, never the STL** — and check `git status` right after regenerating.
2. **The slicer arbitrates printability, not `trimesh.is_watertight`.**
3. **Coplanar booleans leave zero-thickness membranes** — overshoot every cutting tool by 1–2 mm.
4. **Probe at feature centres, on both symmetric instances**, never on a nominal boundary.
5. **A render you cannot see gets checked by a vision model with closed questions.**

## Notes are partly in French

The `references/` files were written during real jobs and are in French. `SKILL.md` and this
README are the English entry point; translations are welcome.

## Licence

MIT — see [LICENSE](LICENSE). Third-party material and its terms: [THIRD-PARTY.md](THIRD-PARTY.md).

---

## En français

Skill Hermes pour **construire des pièces 3D réellement imprimables** : CAO paramétrique sous
Blender, impressionnabilité **mesurée** et non jugée à l'œil, découpe sans interface graphique,
envoi réseau vers une Bambu Lab, rendus qui prouvent le résultat, et livraison dans un dossier
utilisable.

`SKILL.md` décrit la chaîne complète et les règles ; `references/` contient les notes de terrain
(jeux et tolérances, booléens, alésages, filetages, limites DfAM par procédé, rendus headless,
CLI Bambu + MQTT/FTPS, sauvetage de maillages GLB/Draco, dimensionnement structurel, livraison).

Installation : cloner dans `~/.hermes/skills/3d-construction`. Licence MIT.
