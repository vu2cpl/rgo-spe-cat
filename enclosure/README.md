# Enclosure

3D-printed box for the S3 board and the CM108 audio dongle. Plan and
wiring: [`docs/BOX_PLAN.md`](../docs/BOX_PLAN.md).

![preview](preview.png)

**Status: draft 7 (2026-11-15), not printed.** Draft 6 was test-fitted: the board moved around, and the 1/8" plugs could not seat through the 2.5 mm wall. Draft 7 fixes both. Outer size 107 × 75 ×
27.8 mm. The base and lid render without errors and all layout checks pass.
The dongle is measured (28 × 29 × 11.3 mm body + 14 mm USB plug, jacks
12.4 mm apart, centres 6.35 mm up). Other sizes are datasheet values or guesses. They are marked `CHECK` in
`rgo_box.scad`; measure the parts and correct those values before printing.

## Panel

All connectors are on the front panel, except the PC cable, which leaves
through a notch in the back wall straight behind the dongle. Front panel seen from outside, left to
right:

| Label | What | Cable |
|---|---|---|
| RIG | S3 native USB-C | → radio USB-B (CAT) |
| PWR | S3 COM USB-C | ← USB charger (USB-A → USB-C cable) |
| IN | CM108 mic jack (1/8") | ← radio RX audio |
| OUT | CM108 headphone jack (1/8") | → radio TX audio |
| AMP | 2.5 mm stereo (TRS) jack | → SPE amp (2.5 mm plug → DB15 male cable, 3 wires; pinout in `docs/BOX_PLAN.md`) |
| PC (back wall) | 6 × 14 mm notch behind the dongle for its USB extension cable | → PC |

The radio audio cable has a DB15 male plug on ACC1, with the resistors
inside its hood, and two 1/8" plugs on the other end. It is not part of the
box. See `docs/BOX_PLAN.md`.

## Inside

- **S3 board:** held on all sides, no tape. It sits on a rib between its
  header rows. The wall is in front of it, a stop block behind it, and four
  corner fences at its sides. Two fingers on the lid press it down: a pad on
  the ESP32 module shield and a bar on the USB-C socket shells. Its two
  USB-C sockets show through one 7 mm slot (plugs seated fine in the draft-6
  test fit).
- **CM108 dongle:** its jack end sits in a window in the panel, flush with
  the outside, so the 1/8" plugs go fully home whatever their body size.
  It lies in a cradle; two stop posts behind its body take the push when a
  plug goes in. A zip tie through the cradle floor holds it down. The USB
  extension socket sits behind it on a zip-tie anchor.
- **AMP jack:** a 2.5 mm stereo panel jack, a different size from the 1/8"
  audio jacks so the cables can't be swapped.
- **PC cable notch (back wall):** in line with the dongle, so the cable
  runs straight out of the extension socket with no U-turn. A tab on the lid
  closes it down to cable size, so the USB-A plug never has to go through a
  hole.
- **Lid:** 4 × M3 countersunk screws into heat-set inserts in the corner
  posts. A 3.2 × 18 mm slot sits over the status LED, just behind the USB-C
  sockets.

## Check before printing

| Parameter | Default | Measure |
|---|---|---|
| `amp_jack_body` | 11 | The AMP jack's body width behind the panel (the 6.2 mm hole is confirmed for its ~5.8 mm thread) |
| `insert_hole_d` | 4.0 | The bore your M3 heat-set inserts need |

## Use

1. Open `rgo_box.scad` in OpenSCAD and set the parameters in the Customizer.
2. `part = "assembly"` shows the box with ghost parts and prints the outer
   size. Asserts stop the render if parts collide.
3. Export each part as STL:
   - `part = "base"` prints upright;
   - `part = "lid"` is already flipped, lip up.

   No supports are needed. Use PETG or PLA with a 0.2 mm layer height.
4. Melt the 4 inserts into the posts. The lid screws are M3 × 8 flat-head.

Rendered STLs go in `stl/`, which git ignores.

## RF

The box is plastic and does not shield anything. If RF gets into the S3 or
the audio with the amp keyed, line the inside with copper tape connected to
ground. Put a ferrite clamp on every cable.
