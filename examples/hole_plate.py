#!/usr/bin/env python3
"""Example part: a 60 x 40 x 6 mm plate with a Ø12 bearing bore and four M3 pilots.

No Blender needed — this is the `trimesh` + `manifold3d` path (stage 2b of the chain),
which is the fastest way to prove your measuring stack works.

    python3 hole_plate.py --out plate.stl

Design constants are at the top on purpose: change a dimension there, never in the
resulting STL, and re-run.
"""
from __future__ import annotations

import argparse

import trimesh

# --- design constants (mm) -------------------------------------------------
PLATE = (60.0, 40.0, 6.0)      # x, y, z
BORE_D = 12.0                  # bearing bore
BOSS_D, BOSS_H = 18.0, 4.0     # boss around the bore
PILOT_D = 3.5                  # M3 through-hole (hole = shaft + clearance)
PILOT_INSET = 6.0              # distance from the plate edge
CLEARANCE = 0.3                # generic FDM clearance, unused here but kept visible


def build() -> trimesh.Trimesh:
    plate = trimesh.creation.box(PLATE)

    bore = trimesh.creation.cylinder(radius=BORE_D / 2, height=PLATE[2] + 2 * BOSS_H)
    # the cutting tool must OVERSHOOT both faces by 1-2 mm: a coplanar cap leaves a
    # zero-thickness membrane that no slicer likes
    plate = plate.difference(bore, engine="manifold")

    boss = trimesh.creation.cylinder(radius=BOSS_D / 2, height=BOSS_H)
    boss.apply_translation((0, 0, PLATE[2] / 2 + BOSS_H / 2 - 0.1))   # 0.1 mm overlap
    plate = plate.union(boss, engine="manifold")
    plate = plate.difference(bore, engine="manifold")                  # re-open the bore

    for sx in (-1, 1):
        for sy in (-1, 1):
            pilot = trimesh.creation.cylinder(radius=PILOT_D / 2, height=PLATE[2] + 2)
            pilot.apply_translation((
                sx * (PLATE[0] / 2 - PILOT_INSET),
                sy * (PLATE[1] / 2 - PILOT_INSET),
                0.0,
            ))
            plate = plate.difference(pilot, engine="manifold")

    return plate


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default="plate.stl")
    args = ap.parse_args()

    part = build()
    part.export(args.out)
    extents = ", ".join(f"{float(v):.2f}" for v in part.extents)
    print(f"{args.out}: {len(part.faces)} triangles, "
          f"volume {part.volume / 1000:.2f} cm3, bbox [{extents}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
