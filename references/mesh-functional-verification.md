# Functional verification of a regenerated mesh (probes, not eyeballing)

Topology checks (`verify_stl.py`) prove a mesh is CLEAN; they do not prove it still WORKS. After any
regeneration that changed a boolean tree, prove each functional feature with ray probes before
showing the part or slicing it.

## Probe rules

- **Derive every coordinate from the generator's constants** (mirror maps, axle height, pitch). A
  probe typed from memory lands in the wrong feature and reports a phantom defect.
- Cast rays from OUTSIDE the part and read the **material intervals** (enter/exit pairs). Reference
  signatures, from the feature's own tool geometry:
  - blind pilot hole Ød × L: `[joint_face, hole_start, hole_end, outer_face]` → 4 crossings
  - through opening (window, sensor eye): **0** crossings
  - tube wall probed OFF the bore axis: ≥ 2 crossings
  - bore axis itself: 0 crossings (it is a void) — never probe there
- **Do not probe on a bore axis or on a symmetry plane**: the axis is void (looks like missing
  material) and seams on a symmetry plane return a false "empty".
- **A hole in a closed solid does NOT create free edges** — a through-hole's wall is part of the
  shell. So `free_edges == 0` does NOT mean "no openings", and `is_watertight` does NOT mean "no
  cavity". Use rays for openness; use edge counters only for topology damage.
- **A concave part is topologically closed**: the rim band at the cut plane joins the outer surface
  to the inner cavity surface. To decide open-vs-capped, probe the cavity: 2 crossings = external
  wall only (open), 3+ = a skin/cap at the joint.
- **An internal blind void is a legitimate SEPARATE closed component** (self-tapping pilot, trapped
  bubble). Do not purge it as a floating part. Purge rule: only components whose bbox has a
  dimension < 0.05 mm, connected by EDGES (a component joined only by a vertex is not solid).
- **Non-manifold counts on a raw STL are inflated by unwelded vertices** — `merge_vertices()` first,
  then count; never "repair" healthy geometry because of a raw count.

## A/B against a reference mesh

Sample N points on the new mesh and measure them against the reference:

```python
from trimesh.proximity import ProximityQuery
pts, _ = new.sample(20000, return_index=True)
d = ProximityQuery(ref).signed_distance(pts)
```

median ≈ 0.000 and p99 < 1.2 mm ⇒ same shape. Cluster the outliers > 0.5 mm and NAME each cluster:
intended change (new void, removed skin, purged sheet) vs regression. The SIGN says which way:
positive = the new mesh has extra material there, negative = missing material.

## Deliverable checklist (one line per part)

bbox exact · volume/mass · component count + what each component IS · free edges = 0 · non-manifold
= 0 after `merge_vertices()` · watertight · one ray signature per functional feature (bores, pilots,
through-openings, fits). Print a scripted pass/fail total (e.g. `25/25`) — a number a future session
can re-run beats prose. Ship the probe script inside the project (`chassis/review/`) so the check is
repeatable, and make it path-relative (no `/tmp`, no absolute home paths).
