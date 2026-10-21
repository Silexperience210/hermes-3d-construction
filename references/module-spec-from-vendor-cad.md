# Module specs from vendor CAD — no hand-measuring

For catalog modules (LilyGO T-Display, sensors, dev boards…) the user expects specs to be
FETCHED, not measured by them (« Bordel cherche les specs »). Makers publish official 3D
models; measure those instead of asking.

## Where to look

Maker GitHub repos ship a `dimensions/` folder per product. LilyGO T-Display-S3 example:
`dimensions/t-display-s3-full.stp` (module assembly), `t-display-s3-pcb.stp` (bare board),
`CapacitiveTouchScreen.stp` (touch panel), `PCB.dwg` (2D cotes), plus community model zips.
Raw fetch: `https://raw.githubusercontent.com/<org>/<repo>/main/dimensions/<file>`
(URL-encode spaces in filenames, e.g. `Lilygo_T-DisplayS3_Touch_from%20Stuttgart.zip`).

## Measure a STEP with cadquery (throwaway venv)

```bash
python3 -m venv /tmp/cq
/tmp/cq/bin/pip install cadquery
# write the analysis to a .py file and run it — long heredocs in a terminal command can
# trip Hermes' gateway filter
/tmp/cq/bin/python analyse.py
```

```python
import cadquery as cq
shape = cq.importers.importStep("/tmp/module.stp")
for i, s in enumerate(shape.solids().vals()):
    bb = s.BoundingBox()
    print(i, f"{bb.xlen:.2f} x {bb.ylen:.2f} x {bb.zlen:.2f}",
          f"orig ({bb.xmin:.2f}, {bb.ymin:.2f}, {bb.zmin:.2f})")
```

- `BoundingBox` has NO `.Volume()` — compute `xlen*ylen*zlen` if you need a sort key.
- Vendor STL files (when present) read directly with trimesh; `split()` gives components.
- STEP solids may sit in different frames per file — only compare offsets between solids of
  the SAME file (the assembly one).

## Read the numbers — T-Display-S3 Touch (measured 2026-09)

- Full-module and bare-PCB solids: ~61.98 × 26.09 mm → PCB 62×26 ×1.2 mm; module ~7.9 mm
  thick incl. components.
- Glass/dalle solid ~49.9×26×1.5 (STL) or ~56.2×25.5 (STP): covers almost the whole PCB.
- Centre offset PCB vs glass along the length ≈ 1.2-1.8 mm = the window « déport » (more bare
  PCB at the USB/button end, ~8 mm, vs ~4 mm at the other end). The face window must follow
  this offset, not the PCB centre.
- `CapacitiveTouchScreen.stp`: touch glass ~55×32×1.4 — WIDER than the 26 mm PCB → overhangs
  ~3 mm per side; the pocket/rails must clear the overhang, not just the board.
- Variants differ ~1 mm (classic 62×26 vs AMOLED ~60.2×25.6): confirm WHICH variant with the
  user, then size pocket = board + ≥0.5 mm and rails for the board width + overhang.
