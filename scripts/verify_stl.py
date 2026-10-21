#!/usr/bin/env python3
"""Vérification autonome de STL générés par booléens Blender (aucune dépendance).

Usage:
    python3 verify_stl.py body.stl battery_door.stl ...

Rapporte pour chaque fichier :
  - bbox (vérifier que les pièces emboîtées ont les cotes EXACTES attendues)
  - composantes connexes (détecte les pièces FLOTTANTES / non liées)
  - bords libres (0 = maillage fermé/watertight) + arêtes non-manifold (>2 faces)
  - anneaux à un plan z donné (intersection plan-triangle) pour mesurer des
    trous / fraisages / ouvertures à une altitude intermédiaire

Piège couvert : les parois de cylindre n'ont des sommets QU'aux extrémités —
sonder « sommets à z=-1.8 » ne trouve rien même quand le trou existe. Toujours
couper par plan (rings_at) pour vérifier un trou à mi-hauteur.
"""
import struct
import sys
from collections import defaultdict


def load_tris(path):
    with open(path, 'rb') as f:
        data = f.read()
    n = struct.unpack_from('<I', data, 80)[0]
    tris = []
    for i in range(n):
        off = 84 + i * 50
        vs = []
        for j in range(3):
            vs.append(struct.unpack_from('<3f', data, off + 12 + j * 12))
        tris.append(vs)
    return tris


def bbox(tris):
    xs = [v[0] for t in tris for v in t]
    ys = [v[1] for t in tris for v in t]
    zs = [v[2] for t in tris for v in t]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


def components(tris, tol=0.02):
    """Union-find sur les triangles partageant une arête (clé sommets arrondis)."""
    n = len(tris)
    parent = list(range(n))

    def find(a):
        while parent[a] != a:
            parent[a] = parent[parent[a]]
            a = parent[a]
        return a

    def union(a, b):
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    def key(v):
        return (round(v[0] / tol), round(v[1] / tol), round(v[2] / tol))

    vert_idx = {}
    tri_keys = []
    for t in tris:
        idx = []
        for v in t:
            k = key(v)
            if k not in vert_idx:
                vert_idx[k] = len(vert_idx)
            idx.append(vert_idx[k])
        tri_keys.append(idx)

    edge_map = {}
    for i, (a, b, c) in enumerate(tri_keys):
        for e in ((a, b), (b, c), (c, a)):
            e2 = tuple(sorted(e))
            if e2 in edge_map:
                union(edge_map[e2], i)
            else:
                edge_map[e2] = i

    comps = defaultdict(list)
    for i in range(n):
        comps[find(i)].append(i)
    out = []
    for r, idxs in comps.items():
        vs = [v for t in [tris[i] for i in idxs] for v in t]
        cx = sum(v[0] for v in vs) / len(vs)
        cy = sum(v[1] for v in vs) / len(vs)
        cz = sum(v[2] for v in vs) / len(vs)
        out.append((len(idxs), cx, cy, cz))
    out.sort(reverse=True)
    return out


def edge_stats(tris):
    """Compte les occurrences d'arêtes: 1 = bord libre (trou), >2 = non-manifold."""
    counts = defaultdict(int)
    for t in tris:
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            k = tuple(sorted((round(v, 3) for v in a + b)))
            counts[k] += 1
    free = sum(1 for c in counts.values() if c == 1)
    nm = sum(1 for c in counts.values() if c > 2)
    return free, nm


def rings_at(tris, z):
    """Points d'intersection plan-triangle à z (pour mesurer trous/fraisages)."""
    pts = []
    for t in tris:
        seg = []
        for a, b in ((t[0], t[1]), (t[1], t[2]), (t[2], t[0])):
            if (a[2] - z) * (b[2] - z) <= 0 and abs(a[2] - b[2]) > 1e-9:
                tt = (z - a[2]) / (b[2] - a[2])
                seg.append((a[0] + (b[0] - a[0]) * tt, a[1] + (b[1] - a[1]) * tt))
        if len(seg) == 2:
            pts += seg
    return pts


def main():
    for path in sys.argv[1:]:
        tris = load_tris(path)
        b = bbox(tris)
        comps = components(tris)
        free, nm = edge_stats(tris)
        print(f"=== {path}")
        print(f"  triangles: {len(tris)}")
        print(f"  bbox: x {b[0]:.1f}..{b[1]:.1f} | y {b[2]:.1f}..{b[3]:.1f} | z {b[4]:.1f}..{b[5]:.1f}")
        print(f"  composantes: {len(comps)} " +
              ("(OK, 1 pièce)" if len(comps) == 1 else " *** PIÈCES FLOTTANTES ***"))
        for c in comps[:5]:
            print(f"    {c[0]} tris, centre ({c[1]:.1f}, {c[2]:.1f}, {c[3]:.1f})")
        print(f"  bords libres: {free} {'(watertight OK)' if free == 0 else ' *** MESH OUVERT ***'} | non-manifold: {nm}")
        print("  ex. d'anneau à z=0.5:", len(rings_at(tris, 0.5)), "pts d'intersection")


if __name__ == '__main__':
    main()
