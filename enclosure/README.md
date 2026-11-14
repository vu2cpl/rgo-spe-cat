# Enclosure

3D-printed box for the S3 board and the CM108 audio dongle. Plan and
wiring: [`docs/BOX_PLAN.md`](../docs/BOX_PLAN.md).

![preview](preview.png)

**Status: draft 4 (2026-11-14), not printed.** Outer size 121 × 79 ×
27.8 mm. The base and lid render without errors and all layout checks pass.
Some sizes are datasheet values or guesses. They are marked `CHECK` in
`rgo_box.scad`; measure the parts and correct those values before printing.

## Panel

All connectors are on one panel, the back wall. Seen from outside, left to
right:

| Label | What | Cable |
|---|---|---|
| RIG | S3 native USB-C | → radio USB-B (CAT) |
| PWR | S3 COM USB-C | ← USB charger (USB-A → USB-C cable) |
| IN | CM108 mic jack (1/8") | ← radio RX audio |
| OUT | CM108 headphone jack (1/8") | → radio TX audio |
| AMP | DB9 female | → SPE amp (DB9 male → DB15 male cable, 3 wires; pinout in `docs/BOX_PLAN.md`) |
| PC | Notch for the dongle's USB extension cable | → PC |

The radio audio cable has a DB15 male plug on ACC1, with the resistors
inside its hood, and two 1/8" plugs on the other end. It is not part of the
box. See `docs/BOX_PLAN.md`.

## Inside

- **S3 board:** its two USB-C sockets show through one slot. It sits on a
  rib between its header rows, held with foam tape. A stop block behind it
  keeps it from moving back when a cable is plugged in.
- **CM108 dongle:** lies in a cradle with its jack end against the panel. A
  zip tie through the cradle floor holds it. The USB extension socket sits
  behind it on a zip-tie anchor.
- **DB9 for the amp:** the wall is thinned to 1.6 mm around it, so the jack
  screws reach.
- **PC cable notch:** a tab on the lid closes it down to cable size, so the
  USB-A plug never has to go through a hole.
- **Lid:** 4 × M3 countersunk screws into heat-set inserts in the corner
  posts. A 3.2 mm window sits over the status LED.

## Check before printing

| Parameter | Default | Measure |
|---|---|---|
| `dongle_l`, `dongle_w`, `dongle_h` | 50 × 20 × 10 | CM108 dongle, from the jack end to the end of its USB plug |
| `jack_pitch`, `jack_z`, `mic_left` | 10, 5, true | Centre-to-centre of the dongle's jacks, jack centre above its underside, and which side the mic jack is on |
| `pcb_l`, `pcb_w` | 63.5 × 28 | S3 board outline |
| `pin_clear` | 10 | Floor to board underside. The default assumes wires soldered to the pins. Dupont jumpers on downward pins need about 20 (raise `in_h` too) |
| `usbc_z_above_pcb` | 1.6 | Height of the USB-C socket centre above the board's top face |
| `led_x`, `led_y` | 14, 12 | Position of the RGB LED on the board |
| `notch_w` | 6.5 | USB extension cable diameter + 1 |
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
