# Parametric Involute Gears → STL

Use for spur gears, turntables, or any 3D-printable part with involute teeth.

## Involute math (the easy-to-get-wrong part)

For teeth `Z`, module `m`, pressure angle `α = 20°`:
- pitch radius `r = m·Z/2`, tip `ra = r+m`, root `rf = r−1.25·m`, base `rb = r·cos α`
- `inv(x) = tan(x) − x`; `inv_a = inv(α)`; `half = π/(2·Z)` (half-thickness at the pitch circle)
- Flank angle RELATIVE to tooth centre (tooth NARROWS toward tip):
  - `th_right = half + inv_a − inv(αk)`   (right flank)
  - `th_left  = −half − inv_a + inv(αk)`  (left flank, mirror)
- `αk` from `α_min = arccos(rb / max(rb,rf))` up to `α_max = arccos(rb/ra)`; radius `rk = rb / cos(αk)`

**Sign bug that wastes ~30 min:** `th_right = half − inv_a + inv(αk)` (wrong) makes the tooth WIDEN toward the tip → adjacent teeth overlap → non-manifold mesh. The correct sign makes the tooth narrower at the tip than at the pitch.

## Winding order (counter-clockwise, increasing angle)

Per tooth, in order:
1. left flank: root → tip
2. tip arc: left flank → right flank
3. right flank: tip → root
4. root fillet: end of RIGHT flank of tooth i → start of LEFT flank of tooth i+1

Do NOT connect left flank(tooth i) → right flank(tooth i+1): that skips over the whole next tooth and self-intersects.

## Undercut → use trimesh, don't hand-roll triangulation

- Undercut (`rb > rf`) happens for `Z < ~41`. A hand-rolled root fillet that dips `rb→rf` produces degenerate/non-manifold triangles for small `Z` (e.g. 14 teeth).
- **Robust pipeline** (shapely triangulates the polygon-with-hole, trimesh extrudes):

```python
from shapely.geometry import Polygon
import trimesh
poly = Polygon(outer_contour.tolist(), holes=[hole_circle.tolist()])
mesh = trimesh.creation.extrude_polygon(poly, height)
mesh.apply_translation([0, 0, z_bottom])
combined = trimesh.util.concatenate([mesh_a, mesh_b])  # parts that touch at a plane
```

- trimesh needs a triangulation engine: `pip install mapbox-earcut` (MIT). Missing → `ValueError: No available triangulation engine!`
- Validate manifold-ness: `mesh.is_watertight` (True = closed/oriented). A hand-rolled edge-count check (each edge seen exactly twice) works too.

## Environment gotchas (this machine)

- `uv venv` has NO `pip` → `uv pip install --python <venv>/bin/python <pkg>`.
- trimesh offscreen render needs `pyglet<2` AND system GLU (headless box has no GLU → render fails). Make a 2D preview instead (SVG or Pillow PNG of the tooth profile).
- Run with `<venv>/bin/python`, not system python3 (no libs there).

## Turntable reference (OpenScan-style scanner)

- Crown 100 teeth m=1.5 (pitch 150mm, tip 153mm) + pinion 14 teeth (pitch 21mm) → centre distance `(150+21)/2 = 85.5 mm`, reduction `100/14 ≈ 7.14:1`.
- Module 1.5 prints fine on a 0.4 mm nozzle (tooth ≈ 2.4 mm wide at pitch).
- Bearing 608 (Ø22 OD, Ø8 ID) as central pivot; NEMA17 shaft Ø5 mm for the pinion.
