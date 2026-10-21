# Sizing a printed load-bearing part (torque, torsion, orientation)

When the user says “this looks fragile”, the answer is a calculation, not an opinion. This
file gives the order of operations that held up on an articulated lamp arm (two 20 kg·cm
servos, ~110 mm levers) and the sizing rules that came out of it.

## 1. Read the REAL cross-section from the generator, not off the screen

- `grep` the generator's constants (`T`, `BAR_W`, thicknesses): a 12 × 8 mm “bar” is not a
  tube, and it is often the first time anyone looks at the cross-section.
- Bending: `W = b·h²/6` (mm³) → `M_adm = W × σ_adm`. Torsion of a rectangle `a ≥ b`:
  `J = a·b³/3 × [1 − 0,63·(b/a) + 0,052·(b/a)⁵]` (≈ **1 200 mm⁴** for 12 × 8, not 2 050) and
  `W_t = b·h²/(3 + 1,8·h/b)`.
- **Never produce a J off the top of your head**: check it with two concordant formulas, then
  have the calculation re-checked by a second agent. A J overestimated by 70% leads to the
  wrong conclusion that the part is sound; here the exact value was even lower than the
  auditor's, so the conclusion grew stronger instead of weaker.
- Compare against the **real event**, not the nominal one: servo torque × the margin read in
  the controller, **plus** a use case (a hand leaning on the head: 20 N at 20 mm ≈ **40 kg·cm**).
- An arm heavily oversized in bending can be marginal in torsion — that is the normal case for
  a solid bar, and it is what the eye reads as “fragile”.

## 2. In torsion, shear runs ALONG the layers

- On an FDM part, τ applies to the **layer interfaces**: the allowable stress is that of
  inter-layer adhesion (~50-60% of Z tension), not the in-plane strength (~45 MPa for PETG).
  On a 12 × 8 bar: capacity ≈ **28 kg·cm** — below the use case above: the part will delaminate
  in torsion **before** it breaks in bending.
- Torsional stiffness lives in the **perimeter**, not in the infill. The solid bar is the worst
  shape, the **closed** shell the best: measured order of magnitude (Ø32 × 2.5 mm against
  12 × 8, PETG) → **×8 in bending, ×42 in torsion**, with 29% of the material of a solid Ø32.
- Lightening is only justified by the load: **closed beads** (solid rings every 10-15 mm, dense
  near the joints, open only at mid-span), no hole closer than ~1.5× the local moment height.
  Decorative lightening cuts the perimeter into unconnected ribbons and **destroys** torsion —
  the opposite of the intent.

## 3. Print orientation is part of the calculation

- Lay the part so that bending stresses work **in the plane of the layers** (long axis
  horizontal), never so that the layers become cross-sections. Printing a bending-loaded beam
  upright pulls directly on the adhesion.
- Split a load-bearing shell at the **neutral plane** (zero stress) into two half-shells and
  join them with **bolted flanges** (M3 + heat-set inserts) every 20-30 mm: two screws do not
  exploit a ×42 gain. Glue is a complement, never the load path.
- Working walls: ≥3 perimeters (~1.2 mm); ≥4 perimeters and 4-5 mm of material around each
  insert; ≥40% infill in bosses and edge rings. A wall < 0.8 mm in torsion vibrates and becomes
  noisy.
- Without supports: bridges ≤ 10 mm, slots ≤ 8 mm, Ø ≤ 6 mm in a vertical wall; a cable
  pass-through = a rounded rectangle 8 × 3 mm.
- Joint housings print in their **in-use position**, so that the clamping screws pinch in the
  plane of the layers (that is where printed knobs split).

## 4. Do not turn a bought component into a structural member

- A servo's case is not a clamping zone: bear on pads, retain through the mounting ears,
  0.2-0.3 mm clearance.
- **PETG creeps under permanent clamping and near 50 °C**: the clamp loosens, the clearance
  appears. Prefer **geometric** locking over friction locking.
- A **closed** volume around a servo that holds the load permanently heats up: provide discreet
  ventilation openings (holes outside loaded zones do ventilate — lightening then wins on both
  counts), otherwise prove on the bench that the joint holds on its own once the servo is
  released. Also check the **total play** of the articulated chain: above ~0.5° it destroys any
  “jump-free” recovery strategy at wake-up (starting from the persisted position).

## 5. A safety device is judged on its FUNCTION, not on its presence

- Measure the **actual guard**: stop angle − contact angle, with the safety device **removed**.
  A pin whose guard is finer than the actuator's overshoot protects nothing and consumes play
  in every posture — it is an alibi. A PETG pin does not stop 20 kg·cm.
- When two constraints are **arithmetically incompatible** (holding 0.4 mm of clearance *and*
  stopping before contact, at 0.38 mm closed per degree), it is not a threshold to adjust: it is
  the **geometry** that moves, or the function that gets dropped. Compute the impossibility
  BEFORE running an agent on it — two whole steps were lost adjusting an impossible stop, and
  two more discovering the contact chain that too coarse a sweep was hiding (see the
  `coding-agent-delegation` skill, section on verifying a delegate's work).
