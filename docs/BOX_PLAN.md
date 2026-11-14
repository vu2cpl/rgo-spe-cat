# Box plan — RGO ONE CAT + audio interface

**Status: planning (2026-11-14).** Nothing built yet. Decided: USB-charger
power, 3D-printed enclosure, radio ACC1 is female.

## What goes in the box

| Part | Job |
|---|---|
| ESP32-S3 board (YD-ESP32-S3 N16R8) | CAT: radio USB ↔ SPE amp, TCP CAT, MQTT (as now) |
| C-Media CM108 USB sound dongle (card 2 or 3, `0D8C:0014`) | Audio to/from the PC for WSJT-X. Mono mic in, stereo out, 48 kHz, driverless on macOS |
| 2 × 600:600 Ω audio isolation transformers | Break the ground path between PC and radio; keep RF off the audio |
| 2 × 10 kΩ trimpots + a few resistors/caps | Set RX and TX audio levels once |

PTT stays on **CAT** (already verified with WSJT-X), so no PTT wire or
GPIO hack on the CM108.

## Connections

### To the radio — ACC1 (DB15, rear panel)

From the RGO ONE manual (2020 rev 2.00A and V6 rev 1.01A agree):

| ACC1 pin | Signal | Box side |
|---|---|---|
| 11 | LINE OUT (RX audio) | → transformer T1 → level trimpot → DC-block cap → CM108 **mic in** |
| 10 | LINE IN + (600 Ω, balanced) | ← transformer T2 secondary |
| 9 | LINE IN − | ← transformer T2 secondary (other end) |
| 15 | Ground | T1 primary return only — not tied to the CM108 side |
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

## Audio circuit (per channel)

```
RX:  ACC1 pin 11 ──┐                ┌── 10k trim ──┬── 1 µF ──► CM108 mic (tip)
                   T1 600:600       │              │
     ACC1 pin 15 ──┘                └──────────────┴── 1k ──► CM108 GND
                     (radio side)      (PC side)

TX:  CM108 phones L ── 1k ──┐               ┌──► ACC1 pin 10 (LINE IN +)
                            T2 600:600
     CM108 GND ─────────────┘               └──► ACC1 pin 9  (LINE IN −)
```

- The CM108 mic input is sensitive (tens of mV) and carries a bias voltage,
  hence the trimpot pad and the 1 µF DC block. Set the trimpot so WSJT-X
  shows ~30 dB on a quiet band.
- TX level: Mac output volume + the radio's own mic gain; the 1 k sets a
  sane load. Adjust for no ALC on the radio.
- **Ground isolation rule:** the CM108's ground (= PC ground) must not touch
  the S3 / radio ground anywhere in the box. Mount the CM108 board on its
  own standoffs, keep wiring apart.

## Power — decided: USB charger

| Option | Pros | Cons |
|---|---|---|
| **USB charger into the S3 COM socket (chosen)** | Amp follows band changes with the PC off; keeps PC ground isolated from radio ground | One more cable (charger) |
| Power from the PC through a small hub inside | One USB cable to the PC | Box dead when the PC is off; the hub would join PC ground to the S3/radio ground and undo the transformer isolation |

## Panel connectors (draft)

| Connector | Goes to |
|---|---|
| **DB15 male** | Radio ACC1 (audio) — a standard DB15 M–F extension cable: male end into the radio's female ACC1, female end onto the box |
| **DB15 female** | SPE CAT — DB15 M–M cable (the amp's socket takes a male plug) |
| USB-C (S3 native port, via cut-out or panel extension) | Radio USB-B (CAT) |
| USB-C (S3 COM port) | Charger (power) |
| USB cable through a strain relief | PC (CM108 audio) |
| Light pipe / window | S3 RGB status LED |

The two DB15s are deliberately **opposite genders**, so the radio and amp
cables can't be swapped by mistake.

Ferrite clamps on every cable leaving the box (1 kW of RF nearby).

## Enclosure — decided: 3D-printed

| Option | Pros | Cons |
|---|---|---|
| 3D-printed (OpenSCAD like `rx888-case`, Bambu) | Exact cut-outs, fast, cheap | No shielding near the amp |
| Aluminium box (drilled) | Shields the S3 and audio from RF | Panel cut-outs by hand; template from the plan |

Chosen: 3D-printed, OpenSCAD in `enclosure/` (same approach as
`rx888-case`), printed on the Bambu. If RF gets into the S3 or the audio
with the amp keyed, add a copper-tape lining tied to radio ground later.
Needs measured sizes of the S3 board, the stripped CM108 board, the
transformers and the panel parts before the model is drawn.

## Build order

1. Bench-wire the audio circuit on a breadboard to the radio's ACC1; test RX
   decode and TX (into a dummy load) with WSJT-X. Set the trimpots.
2. Measure the boards and connectors; finalise the panel layout.
3. Make the enclosure.
4. Fit, wire, test again: CAT, amp follow, WSJT-X audio, PTT.
5. Update HANDOVER / README with the as-built wiring and photos.

## Parts to source

- 2 × 600:600 Ω audio isolation transformers (e.g. small PCB type)
- 2 × 10 kΩ trimpots, 2 × 1 µF caps, 1 k and misc resistors
- 2 × DB15 panel connectors + DB15 plug for the radio ACC1 cable
- Panel USB-C extension (optional), strain relief / cable gland
- Ferrite clamps (snap-on, mix 31)
- Standoffs, screws
