# Box plan: RGO ONE CAT + audio interface

**Status: enclosure draft 6 (2026-11-14).** The model is
`enclosure/rgo_box.scad`. It is not printed yet.

**Decided:**
- The audio dongle goes in the box, kept simple: no transformers, no
  trimpots.
- Power comes from a USB charger.
- The enclosure is 3D-printed.
- **All connectors are on one panel.**
- The radio audio goes through a separate cable (a DB15 plug to two 1/8"
  plugs) into the dongle's own jacks.

## What goes in the box

| Part | Job |
|---|---|
| ESP32-S3 board (YD-ESP32-S3 N16R8) | CAT: radio USB ↔ SPE amp, TCP CAT, MQTT (as now) |
| C-Media CM108 USB sound dongle (card 2 or 3, `0D8C:0014`), **left whole in its shell**, jacks facing the panel | Audio to and from the PC for WSJT-X. Mono mic in, stereo out, 48 kHz, no driver needed on macOS |
| Short USB extension (dongle → out of the box) | Dongle's USB to the PC |

PTT stays on **CAT** (already verified with WSJT-X). No PTT wire is needed,
and no GPIO hack on the CM108.

## Panel (back wall, left to right from outside)

| Label | Connector | Goes to |
|---|---|---|
| RIG | S3 native USB-C (through a slot) | Radio USB-B (CAT) |
| PWR | S3 COM USB-C (same slot) | USB charger (USB-A → USB-C cable) |
| IN | CM108 mic jack, 1/8" | Radio audio cable, RX plug |
| OUT | CM108 headphone jack, 1/8" | Radio audio cable, TX plug |
| AMP | 2.5 mm stereo (TRS) jack, panel mount | SPE CAT: 2.5 mm TRS plug → DB15 male cable (see below) |
| PC | Cable notch, closed by a tab on the lid | PC (CM108 audio) |

The status LED shows through a window in the lid. Put a ferrite clamp on
every cable leaving the box (there is 1 kW of RF nearby).

## Radio audio cable (separate from the box)

The radio's audio is only on ACC1 (DB15, female on the radio), so this
cable has a **DB15 male plug** on the radio end and **two 1/8" plugs** on
the other end. It needs only 3 wires: use 2-core screened cable, or two thin
screened leads.

The three resistors go **inside the DB15 plug's hood**:

```
RX:  ACC1 pin 11 ── 10k ──┬──► IN plug (tip)    → CM108 mic jack
                         1k
     ACC1 pin 15 ─────────┴──► IN plug (sleeve)

TX:  OUT plug (tip) ── 1k ──► ACC1 pin 10 (LINE IN +)   ← CM108 headphone jack
     OUT plug (sleeve) ─────► ACC1 pin 9 + pin 15
```

| ACC1 pin | Signal | Cable |
|---|---|---|
| 11 | LINE OUT (RX audio) | Core 1 → 10 k → IN tip (with 1 k to ground) |
| 10 | LINE IN + (600 Ω) | Core 2 ← 1 k ← OUT tip |
| 9 | LINE IN − | Joined to 15 in the hood (input driven unbalanced) |
| 15 | Ground | Screen → both plug sleeves |
| 8 | PTT | Not used (PTT is on CAT) |

The ACC1 pinout comes from the RGO ONE manual (2020 rev 2.00A and V6 rev
1.01A agree).

**Radio setting:** set **menu 02 LINE IN = E** (external), so TX audio comes
from ACC1, not the front mic.

**RX level:** the 10 k / 1 k divider (÷11) brings the line out down to mic
level. Set the final level with the Mac's input volume (Audio MIDI Setup),
so WSJT-X shows about 30 dB on a quiet band. If the level is still too high
or too low, change the 1 k. A smaller value makes it quieter.

**TX level:** set it with the Mac's output volume and the radio's mic gain,
so the radio shows no ALC. The 1 k gives the dongle a proper load.

**Mic bias:** the mic tip carries the dongle's mic bias, and the 1 k shunts
it. If that causes trouble, add a 1 µF capacitor in series with the tip.

**Isolation:** the box runs on its own charger, and the radio's USB goes to
the S3, not the PC. So the audio cable is the only PC ↔ radio path. **If
hum or RF shows up in the audio, add two 600:600 transformers.** The git
history of this file has that circuit.

You can build and bench-test this cable before the box exists: plug it into
the dongle and the radio, and run WSJT-X.

## Other connections (unchanged)

- **Radio USB:** S3 native USB → radio USB-B.
- **SPE CAT:**
  - S3 GPIO17 → amp pin 10.
  - Amp pin 3 → 10 k → GPIO18, with 20 k from GPIO18 to GND.
  - GND → pins 4 and 11.

  These wires now go to the panel AMP jack instead of loose wires (see
  the amp cable below).

## Amp cable (2.5 mm jack on the box → DB15 on the amp)

The amp needs only 3 wires, so the box has a **2.5 mm stereo (TRS) panel
jack**. It is a different size from the 1/8" audio jacks, so the amp and
audio cables can't be mixed up. The cable is a **2.5 mm TRS plug → DB15
male** (the amp's socket takes a male plug). Pin 11 (KEN TTL select) is
joined to pin 4 inside the DB15 hood, so it needs no wire of its own.

| Box jack | Inside the box | Wire | Amp DB15 pin |
|---|---|---|---|
| Tip | S3 GPIO17 (TX) through **220 Ω** | Core 1 | 10 (RX TTL) |
| Ring | 10 k → GPIO18, 20 k GPIO18 → GND | Core 2 | 3 (TX TTL, 5 V) |
| Sleeve | GND | Screen | 4 (GND), and 11 joined to 4 in the hood |

A jack shorts its contacts for a moment as a plug goes in. The 220 Ω keeps
GPIO17 safe during that short (the ring line already has its 10 k). Plug
and unplug the amp cable with the box powered off, to be safe.

## Power: USB charger

A USB charger goes into the S3's PWR (COM) socket with a USB-A → USB-C
cable. Don't power it from the PC through a hub: the box would be dead
whenever the PC is off. With the charger, the amp keeps following band
changes when the PC is off.

## Enclosure

Draft 6: 107 × 75 × 27.8 mm, OpenSCAD in `enclosure/`, to be printed on the
Bambu. `enclosure/README.md` lists the values to measure before printing,
The dongle (black aluminium "USB Audio Adapter")
is measured: body 28 × 29 × 11.3 mm plus a 14 mm USB plug, jacks 12.4 mm
apart (centres), 6.35 mm above its underside, mic (pink) on the left.

If RF gets into the S3 or the audio with the amp keyed, add a copper-tape
lining later.

## Build order

1. Make the radio audio cable. Bench-test RX decode, and TX into a dummy
   load, with WSJT-X. Set the levels.
2. Measure the dongle, the board and the cable; set the `CHECK` values.
3. Print the enclosure.
4. Fit, wire and test again: CAT, amp follow, WSJT-X audio, PTT.
5. Update HANDOVER and README with the as-built wiring and photos.

## Parts to source

- **Panel connector:** 1 × 2.5 mm stereo (TRS) panel jack (amp side), and a
  220 Ω resistor for GPIO17.
- **Amp cable:** 2.5 mm stereo plug + DB15 male plug with hood, and about
  1 m of 2-core screened cable.
- **Radio audio cable:**
  - 1 × DB15 male plug with hood;
  - two 1/8" (3.5 mm) mono or stereo plugs;
  - about 1 m of 2-core screened cable;
  - resistors: 10 k, 1 k, 1 k (plus a spare 1 µF capacitor).
- **Short USB-A extension** (dongle → PC).
- **Ferrite clamps** (snap-on, mix 31).
- **Assembly:**
  - 4 × M3 heat-set inserts;
  - 4 × M3 × 8 flat-head screws;
  - zip ties;
  - foam tape.
