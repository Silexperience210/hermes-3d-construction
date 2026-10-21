#!/usr/bin/env python3
"""Audit impression d'un lot de STL : topologie, masse, orientations, surplombs REELS.

Usage:
    python3 audit_print_batch.py fichier.stl [...] [--material petg|tpu|pla]
    python3 audit_print_batch.py --compare export/v31/plate1.stl chassis/v3/b_front.stl

Pour chaque fichier : bbox, volume, masse, composantes (avec detection des pieces a
etendue NULLE = voiles/slivers flottants laisses par les booleens), boucles de bord,
non-manifold, puis les 6 orientations axe-alignees (contact plateau / aire descendante)
et le detail des faces plates descendantes groupees par altitude AU-DESSUS du plateau.

PIEGE COUVERT : les faces posees sur le plateau sont descendantes -> elles polluent tout
compte de surplomb. Le script les exclut (contact) et ne rapporte que le reste.
"""
import sys

import numpy as np
import trimesh

DENSITY = {"petg": 1.27, "pla": 1.24, "tpu": 1.21, "abs": 1.04}


def load(path):
    m = trimesh.load(path, process=False)
    m.merge_vertices()
    return m


def boundary_loops(m):
    from collections import Counter

    counts = Counter(map(tuple, m.edges_sorted))
    bnd = [e for e, n in counts.items() if n == 1]
    parent = {}

    def find(a):
        while parent.setdefault(a, a) != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for a, b in bnd:
        union(int(a), int(b))
    groups = {}
    for a, b in bnd:
        groups.setdefault(find(int(a)), []).append((int(a), int(b)))
    loops = []
    for edges in groups.values():
        vids = sorted({v for e in edges for v in e})
        pts = m.vertices[vids]
        length = sum(float(np.linalg.norm(m.vertices[a] - m.vertices[b])) for a, b in edges)
        loops.append({
            "edges": len(edges),
            "length_mm": round(length, 2),
            "size": [round(float(x), 2) for x in (pts.max(axis=0) - pts.min(axis=0))],
            "center": [round(float(x), 2) for x in pts.mean(axis=0)],
        })
    return sorted(loops, key=lambda r: -r["length_mm"])


def rotation(axis, sign):
    if axis == 0:
        return trimesh.transformations.rotation_matrix(np.radians(90 if sign > 0 else -90), [0, 1, 0])
    if axis == 1:
        return trimesh.transformations.rotation_matrix(np.radians(-90 if sign > 0 else 90), [1, 0, 0])
    return np.eye(4) if sign > 0 else trimesh.transformations.rotation_matrix(np.pi, [1, 0, 0])


def orientation_report(mesh, contact_tol=0.1, flat_deg=3.0, overhang_deg=45.0):
    rows = []
    for axis in (0, 1, 2):
        for sign in (1, -1):
            m = mesh.copy()
            m.apply_transform(rotation(axis, sign))
            n, area = m.face_normals, m.area_faces
            angle = np.degrees(np.arccos(np.clip(-n[:, 2], -1, 1)))
            down = n[:, 2] < -0.05
            zmin = m.bounds[0][2]
            zc = m.triangles[:, :, 2].mean(axis=1)
            contact = down & (angle < flat_deg) & ((zc - zmin) < contact_tol)
            flat = down & (angle < flat_deg) & ~contact
            below45 = down & (angle < overhang_deg) & ~contact
            buckets = {}
            for i in np.where(flat)[0]:
                key = round(float(zc[i] - zmin), 1)
                buckets.setdefault(key, {"area_mm2": 0.0, "faces": 0})
                buckets[key]["area_mm2"] += float(area[i])
                buckets[key]["faces"] += 1
            rows.append({
                "orientation": f"{'xyz'[axis]}{'+' if sign > 0 else '-'} down",
                "bbox": [round(float(x), 1) for x in (m.bounds[1] - m.bounds[0])],
                "contact_mm2": round(float(area[contact].sum())),
                "overhang_below45_mm2": round(float(area[below45].sum())),
                "flat_ceiling_by_altitude": {
                    str(k): {"area_mm2": round(v["area_mm2"]), "faces": v["faces"]}
                    for k, v in sorted(buckets.items())
                },
            })
    return sorted(rows, key=lambda r: (r["overhang_below45_mm2"], -r["contact_mm2"]))


def audit(path, material="petg"):
    raw = trimesh.load(path, process=False)
    m = load(path)
    parts = m.split(only_watertight=False)
    floating = []
    for i, p in enumerate(parts):
        size = p.bounds[1] - p.bounds[0]
        if float(size.min()) < 0.05 or len(p.faces) <= 4:
            floating.append({
                "component": i,
                "faces": len(p.faces),
                "size_mm": [round(float(x), 2) for x in size],
                "min": [round(float(x), 2) for x in p.bounds[0]],
                "max": [round(float(x), 2) for x in p.bounds[1]],
            })
    volume = None
    try:
        volume = float(m.volume)
    except Exception:
        pass
    return {
        "file": path,
        "triangles": len(raw.faces),
        "watertight": bool(m.is_watertight),
        "winding_consistent": bool(m.is_winding_consistent),
        "components": len(parts),
        "floating_or_zero_extent": floating,
        "bbox_mm": [round(float(x), 2) for x in (m.bounds[1] - m.bounds[0])],
        "volume_cm3": round(volume / 1000.0, 1) if volume else None,
        "mass_g": round(volume * DENSITY[material] / 1000.0, 1) if volume else None,
        "material": material,
        "boundary_loops": boundary_loops(m)[:12],
        "orientations": orientation_report(m),
    }


def main(argv):
    material = "petg"
    if "--material" in argv:
        i = argv.index("--material")
        material = argv[i + 1].lower()
        del argv[i:i + 2]
    files = [a for a in argv[1:] if not a.startswith("--")]
    if not files:
        print(__doc__)
        return 1
    for path in files:
        rep = audit(path, material)
        print("=" * 70)
        print(path)
        print(f"  triangles {rep['triangles']} | watertight {rep['watertight']} | "
              f"components {rep['components']} | bbox {rep['bbox_mm']}")
        print(f"  volume {rep['volume_cm3']} cm3 | masse {rep['mass_g']} g ({material.upper()})")
        for f in rep["floating_or_zero_extent"]:
            print(f"  !! composante {f['component']} a etendue nulle: {f['faces']} tris, "
                  f"size {f['size_mm']} de {f['min']} a {f['max']}")
        for b in rep["boundary_loops"][:5]:
            kind = "micro-defaut" if b["length_mm"] < 30 else ("ouverture de conception" if b["length_mm"] > 500 else "a qualifier")
            print(f"  boucle L={b['length_mm']} mm ({kind}) size {b['size']} centre {b['center']}")
        print("  orientations (surplomb REEL = hors contact plateau):")
        for o in rep["orientations"]:
            print(f"    {o['orientation']:<9} contact {o['contact_mm2']:>7} mm2  "
                  f"surplomb<45 {o['overhang_below45_mm2']:>7} mm2  bbox {o['bbox']}")
        best = rep["orientations"][0]
        print(f"  -> orientation la moins gourmande en support: {best['orientation']}")
        print("     plafonds plats par altitude:", best["flat_ceiling_by_altitude"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
