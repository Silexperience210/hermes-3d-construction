# Headless 3D renders: exploded view, hero image, cinematics

Recipe validated on a multi-part printed chassis (shells + wheels + board + servos)
rebuilt from its real STLs and the project dimensions.

## 1. Rebuild the assembly, don't draw it

Import the **real parts** (`bpy.ops.wm.stl_import`) and add only the components
missing from the STLs (servos, boards, sensors, battery) as simple volumes, with their
**manufacturer dimensions** — never guessed proportions:

- 9 g servo: body 22.8 × 12.2 × 22.5; flange at 15.9 from the base, thickness 2.5,
  mounting-lug spacing 32,2; shaft Ø4,8 on a Ø11,8 boss, height 1,5; pilot holes Ø1,7.
- T-Display-S3 Touch board: 62 × 26 × 1,2; M2 hole spacing = 20,01.
- HC-SR04: PCB 45 × 20 × 1,6; transducers Ø16, spacing 26.

Place each sub-assembly by its **mechanical joint** (the servo shaft is on the wheel
axis; the wheel hub gives the stated length; the component rests on its bearing face),
then verify the render visually (§5): it is the only judge of "this looks correctly
assembled".

## 2. A readable exploded view

- One offset **per part** along its **real assembly direction** (shells ±Y, wheels
  ±X outwards, board/slabs forward, servos sideways), not a uniform radial explosion:
  the reader must understand in which order the parts nest together.
- Labels: TEXT objects created **after** the camera and oriented toward it
  (`(cam.location - pos).to_track_quat("Z", "Y").to_euler()`), size ≥ 9 mm within a
  600 mm frame. Labels lying flat in the ground plane are unreadable.
- Two complementary renders: **exploded iso** (understand the order) and **internal**
  (front shell hidden, parts in place — this is the view used for assembly).
- "Technical drawing" render: Workbench (light background, `show_object_outline`,
  `show_cavity`, ORTHO camera) or Cycles + `view_settings.view_transform = "Standard"`.

## 3. Metal hero image

- Principled materials: `metallic = 1`, `roughness` 0.22-0.35, lighter for the shell,
  very dark for the wheels; tread in "rubber" (`metallic` 0,15, `roughness` 0,65).
- **Emissive screen**: near-black base + orange `Emission Color` at `Emission Strength`
  10-15 for the eyes; without emission the screen stays a black rectangle and the render
  looks "switched off".
- **Environment**: metal reads in what it REFLECTS → flat black background = dead metal.
  A dark grey (0.05) + 3-4 area lights (warm orange key, cool backlight, warm grazing
  light, cool top light) give the orange & black metal look.
- **`view_transform = "Standard"`**: AgX crushes saturation — a vivid orange comes out
  brown/coppery. Don't try to compensate through the base color.
- Mind the scale: a 240 mm area light on a 200 mm object at 10⁶ W lights it correctly;
  energies sized for a human-scale studio give black.

## 4. Cinematic (orbit → explosion → reassembly → running)

Timeline that works (30 fps, ~26 s):

| Phase | Frames | Content |
|---|---|---|
| Orbit | 0-240 | slow turn around the assembled object |
| Explosion | 240-420 | parts toward their assembly direction, camera pulling back |
| Reassembly | 420-570 | back to the assembled position |
| Running | 570-780 | the object *works*: moving parts animated, blinks |

- **Orbit** = empty parent + child camera, rotate the empty; distance/height as
  keyframes on the camera's LOCAL location (§ frame-of-reference pitfall in SKILL.md).
- **Explosion** = store the assembled position and the offset position, keyframe both
  at the phase boundaries (assembled → exploded → assembled): the intermediate value is
  interpolated, no curve to write by hand.
- **"Running"**: animate what proves the object is alive — wheel rotation (keyframes on
  `rotation_euler`), **body pitch about the real axis** (parent the body parts to an
  empty placed on the wheel axis, rotate ONLY that empty), head sensor sweep, eye
  blinking (vertical scaling of the eye shapes).
- Keep the default interpolation (Bézier): `action.fcurves` no longer exists in Blender 5.

## 5. Quality control without being able to look

Send the image (downscaled to ~1600 px, JPEG q≈88, never the 3-4 MB PNG) to a
multimodal model with closed questions: "dominant hue / metal look?", "two glowing eyes
visible?", "whole subject and centered?", "visible defect?". The answers catch what no
numeric check sees: cropped framing, screen off, unreadable labels, duplicated part.
Iterate until "no defect" before delivering. This loop costs a few minutes and avoids
presenting a failed render.

## 6. Performance and encoding

- Order of magnitude for arbitrating: `seconds/image ≈ k × (Mpx) × (samples)`. Measure
  on 20-30 images rather than extrapolating from the first one.
- Reduce samples first (32 + denoising is more than enough for an animation), then
  resolution: a delivered 1280×720 video beats an announced 1080p that never got
  rendered. Keep the still image in high definition — that's what gets printed/looked at.
- `scene.render.use_persistent_data = True` reuses the scene between frames.
- Encoding without system ffmpeg (Playwright ffmpeg, VP8/WebM):
  `ffmpeg -y -framerate 30 -i frames/f_%04d.png -c:v libvpx -b:v 8M -crf 10 -deadline good -cpu-used 3 -pix_fmt yuv420p sortie.webm`

## 7. Measuring an opening in a printed part

- **Version comparison**: bbox / volume / vertex count / face count (trimesh).
  A volume that drops exactly by the material removed by widening an opening
  (`Δsurface × wall thickness`) **proves** that only that opening changed — this is the
  check to present to the user (an md5 fingerprint proves nothing, Blender reorders
  vertices).
- **Probing an opening along a ray is unreliable on a shell left open at the joint
  plane**: the ray crosses the opening then exits through the joint without hitting
  anything, and the "no material" test confuses the opening with the outside void (glyph
  silhouette, part edge). Prefer the **project verification script** (which measures the
  nominal dimensions) or reading the generator parameters, and use probing only for a
  yes/no ("does this opening go through?").
