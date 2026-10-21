# Mesh Print Prep — preparing a 3D mesh (often AI-generated) for printing

Pipeline validated on a 1 m statue (WebAR GLB → 3 printable pieces with
dowels, 24 cm). AI-generated models (Tripo — `tripo_node_` prefix, Meshy…)
are "artistic" meshes for WebAR, NOT CAD models: multi-shell,
open shells, 100-400 exploded bodies. The slicer either refuses them or
produces empty output.

## Order of operations (validated)

1. **Convert GLB → OBJ via Blender** if the GLB uses
   `KHR_draco_mesh_compression`: trimesh then reads ZERO vertices
   (bbox 0,0,0). `bpy.ops.import_scene.gltf` decodes Draco natively, then
   `wm.obj_export` with `transform_apply` (otherwise the transform is not applied).
2. **Repair/scale**: `m.apply_scale(1000.0)` if the Blender export is in
   METERS (bbox 0,077 instead of 77 mm) → otherwise zero volume at DfAM.
3. **Drill BEFORE cutting**: the through-holes (Ø6) drilled on the
   complete mesh end up aligned in the 2 adjacent pieces after
   cutting. Do NOT drill after remesh (the remesh destroys the holes).
4. **Cut into pieces** with `bmesh.ops.bisect_plane` (see below).
5. **Alignment dowels**: Ø5,8 for Ø6 holes (0,2 mm clearance), height
   20 mm (10 mm overlap per piece). Printed separately.

## ⚠️ Boolean fails on these meshes — use manifold3d

- **Blender boolean**: fails silently (partial holes, 1/4 drilled)
  or **destroys the mesh** ("0 verts" export, corrupted 84-byte STL files).
- **trimesh default engine** (Blender backend): `ValueError: Not all meshes
  are volumes!` — even on a mesh that is `is_watertight=True` (multiple shells).
- **SOLUTION**: `pip install manifold3d` then
  `mesh.difference(cyl, engine='manifold')` — Google's solver repairs the
  shells along the way and drills cleanly (tested: 4/4 holes, watertight).

## Bisect cutting (reliable, unlike booleans)

```python
def bisect_at(bm, z, keep_above):
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    bmesh.ops.bisect_plane(bm, geom=geom, dist=0.02,
                           plane_co=(0, 0, z), plane_no=(0, 0, 1),
                           clear_inner=keep_above, clear_outer=not keep_above)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
# keep the slice [z0, z1]: bisect_at(z0, True) then bisect_at(z1, False)
# then bmesh.ops.holes_fill on the boundary edges at z0/z1 (closes the planes)
```

## Verifying the drilled holes (the shapely section is misleading)

Count the wall faces: horizontal normal (`|nz| < 0.3`) AND centroid
~3 mm from the expected positions (x=±18, y=0), threshold > 20 faces = hole present.
`m.section().to_planar()` undercounts (1 hole instead of 2, 0 instead of 4).

## Pitfalls

- The file sent by the user may carry a different name than the one
  announced (90 MB "eef8f…obj" = actually `Fred_statue.obj`) — always
  list the real folder (`ls -b` for special characters) before acting.
- A path containing an accented character (`~/Státue/`) makes trimesh fail (`ValueError:
  string is not a file`) — copy to an ASCII path for the analysis.
- Blender 5.0 OBJ with vertex colors (`v x y z r g b` lines): trimesh loads
  it with `process=False`, or go through Blender.
- Microscopic bodies (1-2 faces) = debris to ignore/remove; the main
  body is often the only one with non-zero volume.
- A "409 bodies" mesh is not necessarily lost: Blender voxel remesh
  (3 mm, `use_remove_disconnected=True`) closes it into a single solid shell — useful
  for printing in one go — and then drill AFTER the remesh. Not a contradiction of step 3: that rule
  forbids drilling before an OPTIONAL remesh (which eats the holes). When a remesh is the only way to
  get a printable solid it must come first, so drill after it and re-verify every hole.

## Tools

- dedicated venv: `python3 -m venv .venv` then `pip install trimesh manifold3d shapely mapbox-earcut`
- Blender headless: `blender --background --factory-startup --python script.py`
- Final validation: `dfam-check` skill (walls, overhangs, watertight).

## References

- `mesh-glb-to-printable.md`: the full repair pipeline (scripts).
