# Quickstart — one part, from nothing to a slicing job

This is the whole chain on a piece small enough to check by hand: a 60 × 40 × 6 mm plate with a
Ø12 bore, a boss and four M3 pilots. Every command below was run to produce the outputs shown, so
if yours differ, something in your install does.

## 1. The measuring stack

```bash
python3 -m venv .venv
.venv/bin/pip install trimesh manifold3d shapely mapbox-earcut numpy
```

`manifold3d` is the CSG engine — without it `mesh.difference()` raises *Not all meshes are
volumes!*. `shapely` + `mapbox-earcut` are only needed from the gear/extrusion path onwards.

## 2. Generate the part

```bash
.venv/bin/python examples/hole_plate.py --out plate.stl
```

```
plate.stl: 860 triangles, volume 14.04 cm3, bbox [60.00, 40.00, 9.90]
```

Two rules are already in that script and they are the ones people get wrong: the bore is cut with
a tool **two millimetres longer than the part** (a cap flush with the face leaves a zero-thickness
membrane), and the boss is unioned with a **0.1 mm overlap** (coplanar unions are boolean-unstable).

## 3. Prove the topology

```bash
.venv/bin/python scripts/verify_stl.py plate.stl
```

```
=== plate.stl
  triangles: 860
  bbox: x -30.0..30.0 | y -20.0..20.0 | z -3.0..6.9
  composantes: 1 (OK, 1 pièce)
    860 tris, centre (0.0, 0.3, 1.1)
  bords libres: 0 (watertight OK) | non-manifold: 128
  ex. d'anneau à z=0.5: 696 pts d'intersection
```

Read it as: **1 component** (nothing floats), **0 boundary edges** (no hole), and 128 non-manifold
edges which are *cosmetic here* — the float32 STL write splits shared vertices. The rule of thumb
is the slicer's verdict, not this counter: 2–37 such edges with a single body are harmless;
hundreds of them *plus* dozens of parts mean a fragmented mesh (a resolution regression).

## 4. Measure printability

```bash
.venv/bin/python scripts/dfam_tool.py measure plate.stl --angle-limit 45
```

```
bbox [60.0, 40.0, 9.9] | volume 14044.2 | watertight True | corps 1
murs: min 2.985 p05 2.985 median 6.0
surplomb<45: 0.0 %
units_suspect: False
```

Judge walls on the **5th percentile**, not `min_mm` (a single sliver triangle can report 0.01 mm),
and check `units_suspect: false` before trusting any area — a mesh exported in metres measures
nothing.

## 5. Pick the orientation

```bash
.venv/bin/python scripts/dfam_tool.py orientations plate.stl --angle-limit 45
```

```
meilleure: current_plus_z | support 0.0 mm2 | hauteur 9.9 mm
```

The best orientation maximises plate contact and minimises support. Remember to subtract the
contact faces before calling something an overhang: a part sitting flat always "overhangs" on its
own footprint.

## 6. Slice

With Bambu Studio (headless; see `references/bambu-studio-cli.md` for the OSMesa setup, because the
binary segfaults without it):

```bash
LD_LIBRARY_PATH=./osmesa-local/usr/lib/x86_64-linux-gnu \
  ./squashfs-root/AppRun --slice 0 --export-3mf plate.gcode.3mf plate.stl
```

Two things bite here: the CLI **ignores `--load-filaments`** and slices with the profile stored in
your Bambu Studio config, and a large **hollow** shell over ~195 mm is rejected headless (`Nothing
to be sliced`) even though the GUI accepts it. When either happens, slice in the GUI — do not start
splitting the part to please the tool.

## 7. Hand it over

Copy the STL plus the 3MF into the project's delivery folder, with a `README.md` inside that lists
what to print first, what still waits for a measurement, and the exact command to regenerate.
Announce the path, the SHA256 and the revision you built from:

```
5abb44450ccfec8d488a97aa7abf67b1cebcbc1391ca4989a6440978b3c76acf  plate.stl
```

## Where to go next

| You now need | Open |
|---|---|
| a real case around hardware | `templates/enclosure.py`, `references/parametric-enclosure.md` |
| fits, screws, inserts, bores | `references/cad-advanced.md`, `references/enclosure-fit-pitfalls.md` |
| a printed gear | `references/parametric-gears.md` |
| an image or an animation for the user | `templates/render_mechanical_preview.py`, `references/blender-rendering-cinematics.md` |
| a downloaded or AI-generated mesh | `references/mesh-glb-to-printable.md`, `references/mesh-drill-then-slice.md` |
| to send the job to the printer | `references/bambu-lab-printing.md`, `references/bambu-lan-mqtt-ftp.md` |
