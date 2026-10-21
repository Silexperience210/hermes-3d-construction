---
name: 3d-construction
description: "Build printable 3D parts: CAD, DfAM, slice, print, render."
version: 1.1.0
author: Silexperience210, Hermes Agent
license: MIT
platforms: [linux]
metadata:
  hermes:
    tags: [3d, cad, blender, fdm, dfam, slicing, trimesh, bambu]
---

# 3D construction — the whole chain, with the tools we actually use

Generate a part, prove it is printable, slice it headless, send it to the printer, render it for
the person who asked, and hand over the files in a folder they can open. Every rule below comes
from a real job that failed once; the *why* is kept because the number is what makes it stick.

**Start with [`examples/quickstart.md`](examples/quickstart.md)** — one small part, from nothing to
a slicing job, with the real output of every command. It is the fastest way to know your install
works before trusting the rest.

Detailed field notes live in `references/` — written during the jobs, so they carry the measured
numbers, the symptom and the fix.

## When to use

- "make me a case / a bracket / a gear / an adapter" — anything that ends up printed
- a parametric generator has to change (edit the generator, never the STL)
- a downloaded or AI-generated mesh (GLB / Draco / OBJ) must become printable
- a part must be validated, sliced, sent to a Bambu Lab printer
- a 3D preview, an exploded view or a cinematic is part of the deliverable
- Don't use for: web-only 3D scenes (Three.js and friends are out of scope here), or firmware-side
  mesh rendering on an MCU — that budget is pixels and flash, not millimetres.

## What it does NOT do

- **No support generation.** We measure overhangs and choose an orientation; the slicer's own
  supports are used as-is, and their volume is reported as a cost signal, not optimised.
- **No resin/SLS process tuning.** The process-limits table tells you whether a part *fits* a
  process; it does not ship profiles for it.
- **No CAM, no laser, no CNC.** Printing only.
- **No multi-material or colour assignment**, and no print-farm queueing beyond one job at a time.
- **No cloud.** The printer path is LAN or SD card; nothing is uploaded to a vendor account.

## Prerequisites

```bash
blender --version                 # 5.x expected; the STL API changed (see references/blender-stl-export.md)
python3 -m venv .venv             # the measuring stack, outside Blender
.venv/bin/pip install trimesh manifold3d shapely mapbox-earcut numpy networkx rtree scipy
```

That list is **complete and verified on a fresh venv** — every name is there for a reason, and
leaving one out does not crash: `dfam_tool.py` degrades into an embedded `"error"` field in its
JSON. In order: `networkx` (or `scipy`) for `connected_components`, `rtree` for `mesh.ray`,
`scipy` for the wall-thickness sampling. **Check for `"error"` in the output before trusting a
measurement.**

Optional, only if the job needs them: `cadquery` (read vendor STEP files), `paho-mqtt` (printer),
OSMesa libraries for the slicer CLI without a display, `ffmpeg` (encode render frames).

**Tested with** Blender 5.0.1 · trimesh 5.0 · manifold3d · Bambu Studio 02.07.01.62 · Python 3.11–3.14.
Those numbers age: if a command misbehaves, check the version before doubting the rule.

**Linux only, and here is the honest split**: stages 1–6 and 9–10 (CAD, measurement, renders,
delivery) are plain Python/Blender and work anywhere; stages 7–8 (slicing, sending to the printer)
are written for Linux — Bambu Studio AppImage, OSMesa libraries fetched with `apt-get download`.
On macOS or Windows, adapt those two stages; do not assume the commands transfer.

## The chain

| # | Stage | Tool | Detail |
|---|---|---|---|
| 1 | Decide, then delegate | a coding agent + a written brief | this file, *Delegation* |
| 2 | Parametric CAD | Blender `bpy` (headless) | `templates/enclosure.py`, `templates/cabochon.py`, `references/parametric-enclosure.md` |
| 2b | CAD without Blender | `trimesh` + `manifold3d` + `shapely` | `examples/hole_plate.py`, `references/parametric-gears.md` |
| 3 | Tolerances, fits, booleans | constants + probes | `references/cad-advanced.md`, `references/blender-boolean-stability.md`, `references/enclosure-fit-pitfalls.md` |
| 4 | Is it printable? | `scripts/verify_stl.py`, `scripts/dfam_tool.py` | `references/dfam-process-limits.md` |
| 5 | Structural check | hand maths on the real section | `references/structural-sizing-fdm.md` |
| 6 | Renders for the human | Blender headless (EEVEE / Cycles GPU) | `templates/render_mechanical_preview.py`, `references/blender-rendering-cinematics.md` |
| 7 | Slice | Bambu Studio CLI (or its GUI) | `references/bambu-studio-cli.md`, `references/bambu-lab-printing.md` |
| 8 | Send to the printer | FTPS 990 + MQTT 8883 | `references/bambu-lan-mqtt-ftp.md` |
| 9 | Hand over | a folder + a README of its own | *Delivery* below |
| 10 | Foreign/AI mesh rescue | `trimesh`, `bmesh.bisect_plane` | `references/mesh-glb-to-printable.md`, `references/mesh-drill-then-slice.md` |

## Delegation: you measure and verify, you do not hand-edit geometry

For any change to an enclosure or an interlocking part, write a brief (target architecture, real
caliper measurements, mandatory checks) and hand it to a coding agent. You analyse, specify,
measure and **verify the artefacts yourself** — connected components, exact bbox, plane-section
fit, watertightness, renders. Only edit the generator by hand when no agent is available, keeping
a backup per experiment.

- End the brief on a **green verifier**: "loop your verify script until ZERO anomalies, THEN write
  the report". A turn budget always runs out mid-verification otherwise.
- Ask for the deliverables the reviewer needs (preview render, fit table, measured bbox per part)
  *inside* the brief — they are the first thing dropped.
- A dead run usually wrote nothing: check file mtimes before rewriting the brief.
- Before redesigning, ask what the user **already printed**: work on parts that are not on the
  plate yet.

## Rules that cost the most when ignored

- **Touch the generator, never the STL.** Regenerating rewrites committed STLs at the last float32
  bit: `git status` right after, and `git checkout -- <file>.stl` if the geometry did not change.
- **The slicer is the arbiter of printability, not `trimesh.is_watertight`.** A hollow shell with
  design openings is not watertight and prints fine. Count boundary edges (`counts==1`) for real
  holes; hundreds of non-manifold edges *plus* dozens of parts is a resolution regression.
- **Coplanar booleans leave zero-thickness membranes.** Every drilling tool must overshoot the exit
  face by 1–2 mm, and components whose bbox has a dimension < 0.05 mm must be purged by *edge*
  connectivity.
- **Holes print smaller**: add +0.2…0.4 mm on holes ≤ 10 mm; hole = shaft + clearance. House
  constants (0.4 mm nozzle, PLA/PETG): press 0.05, snap 0.20, sliding 0.15, clearance 0.30,
  M3 through-hole Ø3.5.
- **Bevel inflates the bounding box** (~0.5–0.8 mm). For interlocking parts use a rounded box whose
  bbox is exact, and bevel **before** booleans or the mesh explodes (5 588 → 47 788 faces).
- **Probe at feature centres, never on a nominal boundary**, and probe both symmetric instances
  (left *and* right tube, all 4 pilots). A point on an edge reports a false "absent".
- **A fit measured against the generator itself is blind**: measure the two meshes. Thread
  clearance read 0.117 mm where 0.30 was announced because the check compared a tool with its own
  grown copy.
- **Never size a cavity on the bare catalogue body** of a bought module: moulding tabs and the wire
  bundle are invisible on the drawing. Import real CAD, require *component ∩ shells = 0 mm³* with
  ~1 mm per face, and keep the screws reachable.
- **Torsion on an FDM part shears along the layers**: admissible stress is inter-layer adhesion
  (50–60 % of Z tension), and stiffness lives in the *perimeter* — a closed Ø32×2.5 shell gave
  ×8 in bending and ×42 in torsion against a solid 12×8 bar.
- **`/tmp` is RAM on Linux.** Put working copies and large intermediates in a real directory,
  not in the tmpfs — it has taken the machine down before.

## Renders are part of the deliverable

`blender --background --python render.py`. The traps that cost hours: the GPU device list is empty
on a cold start (Cycles silently falls back to CPU ~10× slower — `prefs.refresh_devices()` then
print the chosen device); a `read_factory_settings(use_empty=True)` scene has no world or lights
(renders come out black, and Workbench ignores lights entirely); frame an ortho camera by
projecting the part onto the *camera's* axes, not the world's; check the actual per-frame cadence
after 20–30 frames before announcing an ETA; and never pipe a long render into `tail` — the exit
code becomes `tail`'s and a Blender traceback disappears.

Verify a render you cannot see by sending it to a vision model with **closed** questions ("two eyes
visible? whole subject in frame?"). It catches cropped framing and black objects.

## Delivery

- Hand back the file **under the name it was exported with**, in the folder the user already uses
  for that project. Search for that folder before inventing one — a new folder means they have to
  move everything.
- Put a `README.md` **inside the delivery folder**: what to print first, what still waits for a
  measurement, the slicer settings, the exact command to regenerate. Name it `README.md` — a French
  `LISEZ-MOI.md` only belongs in a French project.
- Prove the copy (SHA256, path, hash) and name the revision of the repo it came from.
- When the user says "just store it", stop there: no slicing, no printing.

## Verification (before saying "it's ready")

```bash
.venv/bin/python scripts/verify_stl.py part.stl            # bbox, components, boundary edges, z-rings
.venv/bin/python scripts/dfam_tool.py measure part.stl --angle-limit 45
.venv/bin/python scripts/dfam_tool.py orientations part.stl --angle-limit 45
.venv/bin/python scripts/audit_print_batch.py part.stl --material petg
```

Green means: 1 component (or the designed count), boundary loops only where the design opens,
walls at or above the process limit at the 5th percentile (`min_mm` alone is a parasite sample),
`units_suspect: false`, and the slicer reporting `manifold = yes` — that last verdict comes from
the slicer's own `--info`, not from `trimesh`, which is stricter than every slicer in existence
(the command is in `references/bambu-studio-cli.md`).

## References — which note to open, and when

| Note | Open it when |
|---|---|
| `bambu-lab-printing.md` | you take a part all the way to a Bambu Lab printer over the LAN |
| `bambu-lan-mqtt-ftp.md` | the upload or the start command fails: FTPS 990, MQTT 8883, `project_file` |
| `bambu-studio-cli.md` | you slice without a GUI (OSMesa libs, `--info`, `--slice`), or the CLI refuses a part |
| `blender-boolean-stability.md` | a boolean corrupts a shell, a bore, or a split body |
| `blender-rendering-cinematics.md` | you owe the user an exploded view, a hero image or an animation |
| `blender-stl-export.md` | `bpy.ops.wm.stl_export` throws on a parameter name (Blender 5 renamed them) |
| `cad-advanced.md` | fillets, chamfers, inserts, screw bosses, and how to measure a real fit |
| `dfam-integration.md` | you want the generator itself to run the DfAM check after every export |
| `dfam-process-limits.md` | you compare a measurement against per-process limits (FDM, SLS, SLA, MJF, metal) |
| `enclosure-fit-pitfalls.md` | two printed parts must fit, and they do not |
| `enclosure-generator-workflow.md` | you change a parametric enclosure generator (order of operations, QA loop) |
| `mesh-drill-then-slice.md` | a foreign mesh must receive holes and be cut into printable pieces |
| `mesh-functional-verification.md` | a regenerated part must be proven to still *work*, not just to be clean |
| `mesh-glb-to-printable.md` | a downloaded or AI-generated mesh (GLB, Draco, OBJ) must become printable |
| `module-spec-from-vendor-cad.md` | you need the real dimensions of a bought module instead of asking for a caliper |
| `parametric-enclosure.md` | you build a case around real hardware from scratch |
| `parametric-gears.md` | involute teeth, turntables, anything with a correct gear profile |
| `structural-sizing-fdm.md` | the part carries a load: torque, torsion, orientation, safety margin |
| `threejs-stl-viewer.md` | you want a browser preview of an STL (upload page, no install) |

## File map

- `examples/hole_plate.py` — one small part, no Blender (proves the measuring stack)
- `examples/quickstart.md` — the chain end to end, with the real output of every command
- `scripts/verify_stl.py` — topology + bbox + section rings
- `scripts/dfam_tool.py` — walls, overhangs, supports, orientations (adapted from `text-to-cad`, MIT)
- `scripts/audit_print_batch.py` — audit a part set: masses, orientations, real overhang
- `templates/enclosure.py` — parametric case around real hardware (cavities, clearances, constants first)
- `templates/cabochon.py` — parametric curved part
- `templates/render_mechanical_preview.py` — headless preview render
