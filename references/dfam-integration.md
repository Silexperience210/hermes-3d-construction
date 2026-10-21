# DfAM integration in enclosure generators (August 2026)

## Validated pattern (gen_v2.py and gen_v3.py of a parametric enclosure generator)

After every STL export, the generator calls `dfam_check(path)`, which runs the
dedicated virtualenv in a subprocess and parses the resulting JSON. Golden rules:

1. **Non-blocking**: the DfAM check NEVER makes the generation fail.
   `try/except` + message "DfAM: ... — ignoré". A wall/overhang issue prints as a
   warning, and the part is still generated for visual inspection.
2. **Factual JSON**: the tool (`dfam_tool.py measure`) returns raw measurements —
   the verdict (pass/fail) belongs to the workflow, not to the tool.

```python
def dfam_check(path):
    try:
        py = os.path.expanduser("python3")
        tool = os.path.expanduser(
            "scripts/dfam_tool.py")
        if not (os.path.exists(py) and os.path.exists(tool)):
            print("    DfAM: outil indisponible — ignoré")
            return
        import json
        raw = subprocess.run([py, tool, "measure", path, "--angle-limit", "45"],
                             capture_output=True, text=True, timeout=120)
        if raw.returncode != 0:
            print(f"    DfAM: échec ({raw.stderr.strip()[-120:]}) — ignoré")
            return
        d = json.loads(raw.stdout)
        mesh = d.get("mesh", {})
        walls = d.get("wall_thickness", {})
        over = d.get("overhangs", {})
        wt = mesh.get("watertight")
        wt_txt = "OK" if wt else "not closed (expected for an assembled part)"
        print(f"    DfAM  watertight {wt_txt} | {mesh.get('triangle_count', '?')} tris | "
              f"{mesh.get('body_count', '?')} corps")
        if walls:
            print(f"    DfAM  murs: min {walls.get('min_mm')} mm | p05 {walls.get('p05_mm')} mm | "
                  f"médiane {walls.get('median_mm')} mm (FDM ≥1,2)")
        if over:
            pct = over.get("down_facing_area_below_limit_pct")
            print(f"    DfAM  surplombs <45°: {over.get('down_facing_area_below_limit_mm2')} mm² "
                  f"({pct}%)")
    except Exception as exc:
        print(f"    DfAM: erreur ({exc}) — ignoré")
```

## Reading the output (pitfalls seen in the field)

- **`watertight: true` + `body_count > 1` = NORMAL** for a boolean construction:
  PCB bosses, screw posts and ribs unioned to the main shell form separate closed
  shells. Real example: v3 PUPITRE case → `watertight OK | 5 corps`, walls p05
  1,5 mm ✅. Do not raise the alarm.
- **`watertight: false` = normal for an assembled part** (shell open by design,
  separate lid). Blender `check_watertight.py` is the topological authority
  (0 non-manifold edges); trimesh is stricter.
- **Wall `min_mm` = possibly a spurious sample** (0,011 mm seen) → look at
  `p05_mm` and the median. `p05_mm` below the limit = real violation.
- **`units_suspect: true`** → source in meters/inches, every overhang measurement
  is zero. Check the units before comparing.

## Documented real cases

| Part | p05 walls | Verdict |
|---|---|---|
| body v2 (flat case) | 3,18 mm | ✅ far above 1,2 |
| battery_door v2 (skirt 1,0) | 1,0 mm | ❌ → thicken to 1,5 → ✅ |
| top_plate v2 | 1,89 mm | ✅ watertight, 1 body |
| v3 body (PUPITRE) | 1,5 mm | ✅ watertight OK, 5 bodies |
| v3 bezel | 1.95 mm | ✅ (overhangs 32.7% = bosses, worth noting) |
| v3 tray | 1.6 mm | ✅ 0% overhangs |

## Standalone wrapper

`~/.local/bin/dfam-check.sh <fichier.stl> [--angle-limit 45] [--orientations]`
— measures any STL without touching the generator.
