# Boolean (EXACT) stability for parametric CAD shells

Hard-won rules for building multi-part shells (2 halves + bearings) with bpy
boolean modifiers. A single unstable op silently corrupts the WHOLE chain —
ops after it compound the damage.

## Symptom signatures of a silently-failed boolean

- Final body bbox collapses to a small fragment / few faces (e.g. a 104×40×195
  body degrades to a 1-quad sliver) while intermediate debug shows it was whole.
- A DIFFERENCE cutter reappears as a floating residue component in the export
  (same volume as the cutter cylinder) = its modifier never applied.
- The FAST solver RAISES an exception on geometry where EXACT silently corrupts
  — FAST is not the fallback; fix the geometry instead.

## Root causes and the rules that avoid them

- **Never end a bore flush with a face.** A cylinder whose end is coplanar with a
  cut/joint plane or a cavity face fails or corrupts. End it 0.2 mm PAST a face
  (through-hole) or keep it clearly blind with ≥ 0.5 mm of material ahead.
- **Never let two union volumes touch by a coplanar face** — union requires frank
  interpenetration (≥ 1.4-1.5 mm into the wall). An anchor that stops 0.3 mm
  short of a cavity face leaves a paper-thin sliver; EXACT resolves it by
  destroying the mesh on the next large operation.
- **No slivers < ~0.5 mm between concentric/parallel surfaces.** E.g. a bearing
  tube Ø28.5 whose bottom (z 22.25) grazes a cavity floor (z 22.4): shrink the
  tube or raise the axis so clearance ≥ 0.85 mm.
- **A boolean SECTION carries sub-micron debris, and stacking sections with a 1 µm
  overlap multiplies it.** Clipper sections contain segments shorter than a micron
  and zero-area "needles" (an out-and-back). Extruded as-is and then written to a
  binary STL (float32, positions only), those coincident points weld at the slicer
  into non-manifold edges: one solid part is then seen as hundreds of fragments.
  Remedies, cheapest first: remove from every section the vertices closer than 1 µm
  to the previous one, along with the needles; replace an overlapped layer stack with
  **stepped prisms** (one step per layer, no coincident flanks); where a profile
  self-overlaps, set the fill rule to `Positive` instead of `NonZero` so flipped
  pieces no longer hang off the rest by a single point (a "collar" attached only
  by a zero-thickness edge is a real design defect, not an artefact). **Bisect by
  revision**: re-mesh at two revisions bracketing the change — a clean earlier
  state plus the faulty one dates the regression and decides geometry vs writer.
  After the fix the VOLUME must be unchanged (a 10⁻⁷ relative delta is float noise,
  not a new part) and untouched sibling parts must still measure clean.
- **Large bores through thin shell walls are catastrophes.** An Ø24.5 bearing
  bore through a 2.4 mm curved wall killed the whole body. Fix: bore the thick
  boss/tube material ONLY (start the bore after the wall), and give the thin
  wall its own small through-hole (Ø boss + 1) for the shaft.
- **When post-split booleans keep failing in one region, drill the holes in the
  WHOLE body BEFORE splitting it into halves.** Each half then inherits a clean
  half-hole. Post-split bores on that geometry failed whether they crossed the
  joint plane by 0.02 mm or started blind at +0.02 mm.
- **Debug by bbox + face-count prints after every phase** (envelope, cavity,
  unions, subtractions) and bisect by disabling whole groups — the phase where
  the bbox collapses names the culprit. Keep a backup copy of the script before
  each experiment.

## Splitting a solid shell into two halves

- **Do NOT split hollow shells with `bmesh.ops.bisect_plane`** — it does not
  close ring cuts (shell + inner cavity = annulus topology): the export shows
  hundreds of free edges, all exactly ON the cut plane. Bisect only closes
  solid (non-cavity) volumes.
- Boolean cut-box DIFFERENCE on a sanitized body closes the faces correctly and
  is the reliable split. Empirically: `clear_inner=True` removes the half-space
  OPPOSITE `plane_no`, `clear_outer=True` removes the half-space OF `plane_no`
  (verify on a unit cube first — the intuitive mapping is inverted).
- After a split, bores whose opening lands exactly on the new joint face are the
  failure mode above — drill them pre-split.
- `dissolve_degenerate` / `delete_loose` do NOT remove duplicate faces left by
  EXACT along a cut plane (edges shared by >2 faces persist). But **do not wave
  micro non-manifold edges away as "slicer-tolerant"**: judge them at the
  SLICER, never by counting. A handful (2–37 edges, one body) is benign — the
  slicer repairs it silently — whereas hundreds of edges WITH dozens of bodies
  means the piece prints as fragments (one arm seen as 212 pieces). Measure with
  the extracted BambuStudio CLI (`HOME=/tmp/slice-home …/squashfs-root/AppRun
  --info piece.stl`, calibrated on a reference cube: `manifold = yes`,
  `number_of_parts = 1`) before deciding, and fix the CAUSE upstream rather than
  shaving the mesh. And check whether the defect predates your change at all: a
  shared part may have carried it through several revisions.

## Print-orientation × relief features

Engrave (recess) face details — logo, glyph — so the face prints FLAT on the
plate: raised relief on the bed-facing side leaves unsupported first layers.
A raised-relief design forces the part face-up with supports; an engraved one
prints cleanly face-down, and the recess reads as relief once printed.

## Verification

numpy STL parse: triangle count at offset 80 (`<I`), triangles at `84 + i*50`;
union-find over rounded shared vertices → components; edge-use count → free
edges (0 = watertight) and >2-face edges; signed volume positive. See
`scripts/verify_stl.py`.
