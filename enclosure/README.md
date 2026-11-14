# Enclosure

3D-printed box for the S3 board, the CM108 audio dongle and the two DB15
panel connectors. Plan and wiring: [`docs/BOX_PLAN.md`](../docs/BOX_PLAN.md).

![preview](preview.png)

**Status: first draft (2026-11-14), not printed.** Outer size 125 × 105 ×
36.8 mm. The base and lid render without errors. Several sizes are datasheet
values or guesses. They are marked `CHECK` in `rgo_box.scad`. Measure the
parts and correct the values before printing.

## Parts

- **Base:** the floor and walls, with everything mounted in it.
  - **Back wall:** one slot over both USB-C sockets of the S3. RIG (native)
    is on the left, PWR (COM) on the right, seen from outside. It also has a
    notch at the top for the PC cable.
  - **Right end wall:** DB15 male (RADIO) and DB15 female (AMP). The wall is
    thinned to 1.6 mm around each one, so the jack screws reach.
  - **Board mounting:** the S3 sits on a rib between its header rows, held
    with foam tape. A stop block behind it stops the board moving back when a
    cable is plugged in.
  - **Zip-tie anchors:** three, for the dongle and the USB extension socket.
  - **Corner posts:** four, with M3 heat-set inserts.
- **Lid:** a flat plate with a locating lip and 4 countersunk M3 holes.
  - A tab closes the cable notch down to cable size, so the USB-A plug never
    has to go through a hole.
  - A 3.2 mm window sits over the status LED.

## Check before printing

| Parameter | Default | Measure |
|---|---|---|
| `pcb_l`, `pcb_w` | 63.5 × 28 | S3 board outline |
| `pin_clear` | 10 | Floor to board underside. The default assumes wires soldered to the pins. Dupont jumpers on downward pins need about 20 (raise `in_h` too) |
| `usbc_z_above_pcb` | 1.6 | Height of the USB-C socket centre above the board's top face |
| `led_x`, `led_y` | 14, 12 | Position of the RGB LED on the board |
| `notch_w` | 6.5 | USB extension cable diameter + 1 |
| `ties` | 3 anchors | Positions to suit the dongle and the extension socket |
| `insert_hole_d` | 4.0 | The bore your M3 heat-set inserts need |

## Use

1. Open `rgo_box.scad` in OpenSCAD and set the parameters in the Customizer.
2. `part = "assembly"` shows the box with ghost parts and prints the outer
   size.
3. Export each part as STL. `part = "base"` prints upright. `part = "lid"` is
   already flipped, lip up. No supports are needed. Use PETG or PLA with a
   0.2 mm layer height.
4. Melt the 4 inserts into the posts. The lid screws are M3 × 8 flat-head.

Rendered STLs go in `stl/`, which git ignores.

## Print notes

The box is plastic and does not shield anything. If RF gets into the S3 or
the audio with the amp keyed, line the inside with copper tape connected to
radio ground. Put a ferrite clamp on every cable.
