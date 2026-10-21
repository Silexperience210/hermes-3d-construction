# Parametric enclosure generation (Blender headless)

Generate a 3D-printed enclosure (case/housing) from exact hardware dimensions with a single parametric `bpy` script run headless. Proven building a countertop payment-terminal shell for an ESP32 board (56×86 mm portrait) + RC522 NFC module (60×40) + 10000 mAh battery (126×65×10). 1 Blender unit = 1 mm.

## Run commands

```bash
blender --background --python gen.py                 # export body.stl + door.stl, print bbox+tris
blender --background --python gen.py -- --preview    # + render front/back 3/4 views
blender --background --python gen.py -- --section    # + render a cutaway to verify internal routing
```

Blender 5.x export operator: `bpy.ops.wm.stl_export(filepath=..., export_selected_objects=True, global_scale=1.0, ascii_format=False, apply_modifiers=True)` with an `AttributeError` fallback to `bpy.ops.export_mesh.stl(...)`. Confirm the name with `[o for o in dir(bpy.ops.wm) if "stl" in o.lower()]` if it errors.

## Script structure that works

1. **All dimensions as named CONSTANTS at top** (board W/L/T, module dims, wall thickness, clearance, fillet radius). A `DERIVED` banner below computes the rest (slopes, brow/top-rear points, cavity sizes). One tweak + re-run = new variant.
2. **Shell = 2D side-profile prism**, then subtract cavities with boolean DIFFERENCE, then re-add retention features with boolean UNION.
3. **Fit-check on every run**: print each component's slope length vs its required minimum (`NFC face slope 60.0 mm (module needs 40.6)`). A bad constant combo is visible immediately, not at print time.
4. **Export + report bbox and triangle count** to confirm the part stayed inside the intended envelope.

## Reusable bpy helpers (all booleans `solver='EXACT'`)

- `prism(name, poly, axis, a0, a1)` — extrude a 2D polygon (the side profile) into a solid.
- `panel_rect(name, u0, u1, hw, w0, w1, origin, ang)` — a box on a TILTED panel in panel coordinates (u = along slope, w = into panel, negative w = into body). This is how you cut a board pocket / screen window / NFC recess on an angled face. The panel's angle sign sets which way it faces: `ang` positive = face points up-and-forward, `-ang` = up-and-back.
- `boolean(target, cutter, op)` — DIFFERENCE for cavities, UNION for retention; apply the modifier then delete the cutter.
- `fillet(ob, width, segments, angle_deg)` — BEVEL with `limit_method='ANGLE'` + `clamp_overlap=True`. `FILLET_SEG` 4→8 for a visibly smooth silhouette.

## Tolerances + printability rules

- **0.3 mm clearance per side** on every cavity, exposed as one `CLEAR` constant (0.2 tight / 0.45 loose).
- **PCB friction retention**: make the last ~16 mm of the slot 0.4 mm narrower (`PINCH`) so the board clicks in. Add a **positive snap bump** (UNION box protruding ~0.6 mm into the slot at the board's trailing edge) — friction alone wears out.
- **Battery anti-rattle**: 4 thin UNION ribs (0.5 mm) on the bay side walls.
- **No supports**: every DOWNWARD-facing outer surface ≥45° from horizontal (rear rake, void roof). Bottom corners chamfered. A top panel's tilt only matters for supports if that face is downward-facing.
- **Wire ducts ≥ Ø12 mm** for a 7-wire SPI bundle + 2 battery leads. A duct can dead-end ~1 mm short and still look fine until assembly — verify by cutaway render.

## Preview + section rendering

- Multiple ortho camera views: front 3/4 + back 3/4 (flip azimuth ~180°). Front `rotation_euler = (radians(66), 0, radians(-49))`, back `(66, 0, 131)`. Aim at the body centre `tgt = Vector((0, D/2, H/2))` so it survives D/H edits.
- **Cutaway**: AFTER exporting the STLs (so they stay whole), `boolean(body, box(cut half), 'DIFFERENCE')` then render from the cut side to verify ducts/spine actually connect.

## Driving Blender via Claude Code — pitfalls that cost real time

- **blender-mcp architecture is inverted from intuition**: the Blender *addon* is the SERVER (binds 9876, listens); `uvx blender-mcp` (what Claude spawns) is the CLIENT that connects. So Blender must be running with the addon started FIRST, else Claude's MCP startup hangs for minutes at 0% CPU. A leftover claude session holding port 9876 hangs a second one too — check `ss -tlnp | grep 9876`.
- `claude -p --allowedTools 'Read,Write,Bash'` **blocks the MCP tools** (they are `mcp__blender__*`, not in the list) → Claude can't drive Blender. Drop `--allowedTools` to let MCP tools through.
- **Claude's Write/Bash sandbox can refuse to write to the workdir** even while reporting it allowed. Workaround: Claude still emits the full script in its output → extract with `re.search(r'```python\n(.*?)\n```', log, re.DOTALL)` and write it yourself, then run Blender headless yourself.
- **Backticks in a `claude -p` prompt break bash** (command substitution) — use plain double quotes for filenames.
- `--mcp-config file.json` must be `{"mcpServers": {...}}`; a bare `{}` fails with "expected record, received undefined".
- Claude Code has a monthly spend limit that can kill a session mid-task; capture partial output before it dies.
