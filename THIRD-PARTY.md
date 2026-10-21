# Third-party material and terms

This repository ships **our own** scripts, templates and field notes. Nothing is vendored, and no
third-party source code is redistributed. What follows is what it builds on and what it talks to.

## Adapted code (redistributed here, with attribution)

| File | Origin | Licence | What we changed |
|---|---|---|---|
| `scripts/dfam_tool.py` | [`earthtojake/text-to-cad`](https://github.com/earthtojake/text-to-cad) — DfAM measurement tool | MIT | kept the measurement core, adapted to our workflow (fact-only JSON output, our process-limit table, our CLI defaults) |

The MIT text of that project applies to `scripts/dfam_tool.py`; the rest of this repository is
under the MIT licence in [LICENSE](LICENSE).

## Tools used, not distributed

| Tool | Role here | Licence |
|---|---|---|
| **Blender** | parametric CAD (`bpy`), headless renders | GPL-2.0-or-later |
| **trimesh**, **manifold3d**, **shapely**, **mapbox-earcut**, **numpy** | CSG, repair, measurement | MIT / Apache-2.0 / BSD / ISC / BSD |
| **Bambu Studio** | headless slicing (CLI) and printer communication | AGPL-3.0 |
| **paho-mqtt**, **curl** | printer MQTT / FTPS transport | EPL-2.0 / curl licence |
| **ffmpeg** | encoding rendered frames | LGPL/GPL, depending on the build |
| **cadquery** (optional) | reading vendor STEP files | Apache-2.0 |

We install and invoke these; we do not ship them. If you redistribute a slicer profile, a printer
firmware or a vendor CAD file, check its own terms first — a vendor enclosure drawing is usually
not yours to publish.

## References and standards

`references/dfam-process-limits.md` cites process limits (wall thickness, minimum feature, overhang)
for FDM, SLS, SLA/DLP, metal PBF and MJF. The values are used as engineering constants with their
source named (ISO/ASTM 52910, 52911-1 families); no standard text is reproduced here. Buy the
standard if you need the normative wording.
