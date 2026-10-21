# Preparing 3D meshes for printing

Takes any 3D model (downloaded, AI-generated, WebAR GLB, Blender OBJ)
through to a slice-ready STL: decoding, units, shell repair,
cutting into printable pieces, assembly dowels.

Complementary: `dfam-check` VALIDATES the result (walls/overhangs/watertight);
`bambu-lab-printing` slices and sends. This skill transforms the mesh first.

## General pipeline

1. **Identify the format and the source** (file header):
   - `# Blender X.Y.Z OBJ File` → Blender export, scale in **meters** by default
   - `KHR_draco_mesh_compression` in a GLB → compressed vertices, trimesh reads them as zero
   - `o tripo_...` → AI-generated mesh (Tripo/AI) → multi-shell, NOT watertight
2. **Decode**: GLB Draco → **Blender** (`import_scene.gltf`) decodes it natively;
   trimesh returns zero vertices without a handler. Then export OBJ/STL.
3. **Units**: Blender exports in meters, slicers read in mm. If the bbox
   is ~0,1-1,0 (meters) instead of 20-300 (mm): **scale ×1000** before any computation.
   The tell: `volume ≈ 0` and `walls ≈ 0.001 mm` at DfAM.
4. **Analyse** (`trimesh`): verts/faces, bbox, volume, `is_watertight`, `split()`
   → number of bodies. An AI mesh = often 100-400 bodies + microscopic fragments.
5. **Repair** if not printable:
   - Blender **voxel remesh** (~3 mm voxel for a 24 cm model) → closed
     shell, removes the fragments; `use_remove_disconnected=True`
   - **Decimate** ratio ~0,25 to lighten it (the slicer does not need 1M faces)
6. **Scale** to the target height (e.g. 240 mm = Bambu max bed), center Z=0.
7. **Cut** into pieces if too tall or too many supports (see below).
8. **Export STL** + **verify** each piece: watertight, dims, volume, DfAM.

## Cutting into pieces — pitfall #1: booleans

**Boolean operations (Blender AND trimesh) fail on AI-generated
multi-shell meshes.** Symptoms: 1 hole drilled out of 4, destroyed mesh
("0 verts", 84-byte STL), or `ValueError: Not all meshes are volumes!`
(trimesh delegates to Blender and requires closed volumes).

**What works reliably: cutting with planes (bisect)**
```python
# Blender, bmesh: keep the slice [z0, z1]
bmesh.ops.bisect_plane(bm, geom=..., plane_co=(0,0,z), plane_no=(0,0,1),
                       clear_inner=keep_above, clear_outer=not keep_above)
bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=0.02)
bmesh.ops.holes_fill(bm, edges=[e for e in bm.edges if abs(e.verts[0].co.z-z0)<0.6 or ...])
```
→ each piece is watertight and slices cleanly.

## Alignment dowels (multi-piece assembly)

- Print the dowels **separately** (Ø5,8 mm × 20 mm for Ø6 holes)
- **Drill the holes WITH A DRILL BIT after printing** (Ø6, 2 holes per joint,
  x = ±18 mm, through both joined faces) — PLA drills perfectly
- This is the pro method when booleans refuse the mesh; do not get
  stuck on integrated holes if the mesh resists.
- Glue: epoxy or cyanoacrylate, dowel + pieces, alignment guaranteed.

## Final verification

- `trimesh`: each piece watertight, dims consistent with the sum of the pieces
- Section to count the holes: `mesh.section(plane_origin, plane_normal)` →
  `to_planar()[0].polygons_full` (needs `shapely` in the venv)
- `dfam-check` on each piece before slicing

## References

- `mesh-drill-then-slice.md`: full case — a 1 m statue (WebAR Draco GLB
  → 24 cm printable in 3 pieces), 4 failed boolean attempts, bisect solution.
