# Box plan — RGO ONE CAT + audio interface

**Status: planning (2026-11-14).** Nothing built yet. Decided: audio inside
the box, simplified (no transformers, no trimpots); USB-charger power;
3D-printed enclosure; radio ACC1 is female.

## What goes in the box

| Part | Job |
|---|---|
| ESP32-S3 board (YD-ESP32-S3 N16R8) | CAT: radio USB ↔ SPE amp, TCP CAT, MQTT (as now) |
| C-Media CM108 USB sound dongle (card 2 or 3, `0D8C:0014`), **left whole in its shell** | Audio to/from the PC for WSJT-X. Mono mic in, stereo out, 48 kHz, driverless on macOS |
| Short USB extension (dongle → out of the box) | Dongle's USB to the PC |
| Small resistor pad: 3 resistors + two 3.5 mm plugs | Match the radio's line levels to the dongle |

PTT stays on **CAT** (already verified with WSJT-X), so no PTT wire or
GPIO hack on the CM108.

## Connections

### To the radio — ACC1 (DB15, rear panel)

From the RGO ONE manual (2020 rev 2.00A and V6 rev 1.01A agree):

| ACC1 pin | Signal | Box side |
|---|---|---|
| 11 | LINE OUT (RX audio) | → 10 k → CM108 mic plug tip (1 k to ground) |
| 10 | LINE IN + (600 Ω) | ← 1 k ← CM108 phones plug tip |
| 9 | LINE IN − | → ground (input driven unbalanced) |
| 15 | Ground | CM108 plug sleeves, S3 GND |
| 8 | PTT | not used (CAT PTT) |

Radio setting: **menu 02 LINE IN = E** (external), so TX audio comes from
ACC1, not the front mic.

### To the radio — USB (CAT, as now)

S3 native USB → radio USB-B. Unchanged.

### To the SPE — CAT (DB15)

S3 GPIO17 → amp pin 10, amp pin 3 → 10 k → GPIO18 (20 k to GND), GND → pins
4 and 11. Unchanged — just moves from fly wires to a panel connector.

### To the PC

CM108 USB → PC. One cable, audio only.

## Audio circuit (DigiRig-style, no isolation)

```
RX:  ACC1 pin 11 ── 10k ──┬──► CM108 mic plug (tip)
                         1k
     ACC1 pin 15 ─────────┴──► CM108 mic plug (sleeve)

TX:  CM108 phones plug (tip) ── 1k ──► ACC1 pin 10 (LINE IN +)
     CM108 phones plug (sleeve) ─────► ACC1 pin 9 + pin 15
```

- RX: the 10 k / 1 k divider (÷11) brings the line out down to mic level.
  Set the final level with the Mac's input volume (Audio MIDI Setup) so
  WSJT-X shows ~30 dB on a quiet band. If the level is still too high or
  too low, change the 1 k (smaller = quieter).
- TX: Mac output volume + the radio's mic gain. Adjust for no ALC on the
  radio. The 1 k gives the dongle a sane load.
- The mic tip carries the dongle's mic bias; the 1 k shunts it. If it causes
  trouble, add a 1 µF cap in series with the tip.
- No transformer isolation: the box runs on its own charger and the
  radio's USB goes to the S3, not the PC, so the audio cable is the only
  PC ↔ radio path. **If hum or RF shows up in the audio, add two 600:600
  transformers** (see git history of this file for that circuit).

## Power — decided: USB charger

A USB charger into the S3's COM socket (USB-A → USB-C cable). The amp keeps
following band changes with the PC off. Not from the PC through a hub: the
box would be dead whenever the PC is off.

## Panel connectors

| Connector | Goes to |
|---|---|
| **DB15 male** | Radio ACC1 (audio) — a standard DB15 M–F extension cable: male end into the radio's female ACC1, female end onto the box |
| **DB15 female** | SPE CAT — DB15 M–M cable (the amp's socket takes a male plug) |
| USB-C (S3 native port, via cut-out or panel extension) | Radio USB-B (CAT) |
| USB-C (S3 COM port) | Charger (power) |
| USB cable through a grommet | PC (CM108 audio) |
| Light pipe / window | S3 RGB status LED |

The two DB15s are deliberately **opposite genders**, so the radio and amp
cables can't be swapped by mistake.

Ferrite clamps on every cable leaving the box (1 kW of RF nearby).

## Enclosure — decided: 3D-printed

OpenSCAD in `enclosure/` (same approach as `rx888-case`), printed on the
Bambu. If RF gets into the S3 or the audio with the amp keyed, add a
copper-tape lining tied to radio ground later. Needs measured sizes of the
S3 board, the CM108 dongle (in its shell, with plugs in), the USB extension
plug and the panel parts before the model is drawn.

## Build order

1. Bench test: wire the resistor pad between the CM108 and the radio's ACC1
   (a DB15 plug and jumper wires). Check RX decode and TX (into a dummy
   load) with WSJT-X; set levels.
2. Measure the parts; finalise the panel layout.
3. Print the enclosure.
4. Fit, wire, test again: CAT, amp follow, WSJT-X audio, PTT.
5. Update HANDOVER / README with the as-built wiring and photos.

## Parts to source

- 1 × DB15 male panel connector (radio side) and 1 × DB15 female panel
  connector (amp side)
- DB15 M–F extension cable (box ↔ radio) and DB15 M–M cable (box ↔ amp)
- Resistors: 10 k, 1 k, 1 k (plus a spare 1 µF cap)
- Two 3.5 mm plugs (or cut from an old headphone cable)
- Short USB-A extension (dongle → PC) and a grommet
- Ferrite clamps (snap-on, mix 31)
- Standoffs, screws
