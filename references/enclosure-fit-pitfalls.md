# FDM part fit & verification — concrete pitfalls

Validated on a real enclosure iteration (`enclosure/gen_v2.py`).
Three real failures documented along with their fix.

## 1. Bevel modifier → inflated bbox (~0.5 mm) → the door doesn't fit

Symptom: a mating part (clipped door) built to exact dimensions that does not go
into its opening; the measured bbox of the STL is larger than the dimensions
passed to the generator.

Cause: `rounded_box` (box + BEVEL modifier `miter_outer='MITER_ARC'`) inflates
the envelope by ~0.45-0.8 mm depending on the axis. The door overflows its opening.

Fix — rounded corners WITHOUT bevel, exact bbox:

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

Rule: every mating part (door, lid, insert) = round corners via cylinders, never
via bevel. Bevel stays OK for unconstrained parts.

## 2. Coplanar booleans → the 2nd DIFFERENCE vanishes

Symptom: stepped pocket (Ø6.5×1 mm on the outside + contiguous Ø3.5 through-passage)
— the passage does not appear in the STL, although the inner ring is visible at the
shared face (z=-1).

Cause: two DIFFERENCE cylinders sharing an exactly coplanar face → Blender's EXACT
solver evaporates the second one (degenerate geometry).

Fix: overlap the two cylinders by 0.1 mm:
`passage z = -1.0..0` → `-0.9..0` when the pocket is `-2.0..-1.0`.

Verification: plane-intersection cut (see §4) — expected radius 3.25 inside the
pocket, 1.75 inside the passage.

## 3. Opening in the bottom → floating posts

Symptom: the body has 3 connected components — the rear screw posts (+ their anchor
pads) float in the void of the opening.

Cause: a Ø6 cylinder pad added by UNION in the void of the opening touches NOTHING
of the body (4 mm away from the walls) → floating part.

Fix: anchor it with a rectangular BRIDGE reaching a solid area
(the rear bottom strip):
```python
# pastille = box(x 24..29.5, y 37..43.5, z 0..1.5) touchant la bande y≥43.5
```
And the mating part (door) gets NOTCHES in its skirt at the bridge positions
(otherwise it will not seat fully home). The bridges must not exceed the diameter of
the mating part's pocket (swallowed by the Ø6.5 pocket).

## 4. Measuring an STL WITHOUT trimesh — reliable methods

### bbox + component counting (floating parts)

```python
def components(tris, tol=0.02):
    # union-find over triangles sharing an edge (vertices rounded to tol)
    # -> list of component sizes; expected [N] (a single part)
```

### Hole radii by PLAN INTERSECTION (not by probing vertices)

PITFALL: cylinder walls only have vertices at BOTH ends (the quads are not
subdivided) — probing vertices at an intermediate z finds NOTHING. Always cut with
a plane:

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
# then measure the distances to the expected centre (±26.75, ±42.5) -> radius
```

Also check the ANGULAR COVERAGE (12 sectors of 30°) to tell a full circle from a
hole cut by the part edge (half-moon).

### Watertightness

bmesh (Blender headless): `[e for e in bm.edges if not e.is_manifold]` +
`[e for e in bm.edges if e.is_boundary]` → expected: few non-manifold
(boolean artifacts), 0 free edges. (trimesh 5.0 no longer has `edges_boundary`.)

## 5. Blender render — never render black

- `read_factory_settings(use_empty=True)` = scene WITHOUT light → black.
  Add: world (Background 0.6,0.63,0.7 / 1.4), SUN (energy 4), AREA.
- `film_transparent = True` → background pixels are alpha 0: a luminance check
  reads "black". Disable it for previews.
- Camera: `type='ORTHO'`, `ortho_scale ≈ 0.135` for a 100 mm object, framed on
  the part. Views: iso, ¾ from below (to see a door), top (pocket).
- Automatic check: mean luminance of the PNG (stdlib zlib, IDAT filter)
  > 15/255 otherwise suspect.

## 6. Unibody NOT ASSEMBLABLE → removable top (screen plate)

Symptom (found after 3 "OK" iterations of the generator): the closed shell
(screen pocket milled into the top + bottom + walls) can receive NO module at all.
The 63×95 glass goes into the 63,5×95,5 pocket, but the LCD panel behind it
(~53×78) is LARGER than the active window (49×73,5) → blocked by the pocket floor;
the door opening (62×44) is too small for the board (59×91); no rear access. The
STL was perfect (watertight, 1 component) and completely unusable.

Rule: check the INSERTION PATH of the largest sub-assembly BEFORE generating.
A unibody is assemblable only if the board+module passes through an opening
(top, bottom or rear).

Fix — removable top (phone style), validated on a real part:
- The body stops below the top (`Z1_BODY = Z1 - TOP_PLATE_T`), the cavity is OPEN
  at the top; the body's top rim must stay FLAT (do not use `rounded_box`/bevel on
  that rim: the bevel eats into it and the plate no longer has a bearing surface —
  round corners via cylinders, §1).
- Screen plate (`TOP_PLATE_T ≈ 2.4 mm`) with a **THROUGH** glass pocket
  (63,5×95,5): NO floor under the glass, otherwise it sticks to the panel hanging
  under the plate (0,8 mm of floor = collision). The active window becomes
  pointless (the glass is transparent).
- 4 tapped bosses under the plate (M2.5 screws from below: bottom →
  Ø6 post → board hole → Ø2,2 pilot hole in the boss). They sit UNDER the glass
  hole (the plate is absent there) → connect them to the ring with WINGS
  (thin parallelepipeds ~2×5×6 mm, under the glass hence invisible, above the
  board) penetrating 1 mm into the ring.
- Coplanar UNION pitfall (same family as §2): a boss whose top is coplanar with
  the underside of the plate remains a separate component → overlap vertically by
  0,5 mm into the plate.
- Printability bonus: the body prints bottom-flat WITHOUT a long bridge (open
  roof) and the plate flat. A unibody would force the top (screen pocket frame) to
  bridge over 60-95 mm of cavity — nearly impossible in PETG without supports
  (cf. §6 of the Kimi audit).

Assembly sequence: module (glass+panel+board) dropped into the body (the board
lands on the posts) → plate placed (the glass enters the pocket)
→ 4 screws from below clamping the whole stack.
