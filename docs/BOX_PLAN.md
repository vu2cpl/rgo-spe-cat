# Box plan: RGO ONE CAT + audio interface

**Status: enclosure draft 7 (2026-11-15).** The model is
`enclosure/rgo_box.scad`. It is not printed yet.

**Decided:**
- The audio dongle goes in the box, kept simple: no transformers, no
  trimpots.
- Power comes from a USB charger.
- The enclosure is 3D-printed.
- **All connectors are on one panel**, except the PC cable: it leaves
  straight back through a notch in the back wall (2026-11-15), so any
  extension socket length up to about 40 mm fits.
- The radio audio goes through a separate cable (a DB15 plug to two 1/8"
  plugs) into the dongle's own jacks.

## What goes in the box

| Part | Job |
|---|---|
| ESP32-S3 board (YD-ESP32-S3 N16R8) | CAT: radio USB ↔ SPE amp, TCP CAT, MQTT (as now) |
| C-Media CM108 USB sound dongle (card 2 or 3, `0D8C:0014`), **left whole in its shell**, jacks facing the panel | Audio to and from the PC for WSJT-X. Mono mic in, stereo out, 48 kHz, no driver needed on macOS |
| Short USB extension (dongle → out of the box) | Dongle's USB to the PC |

PTT was planned on **CAT**, but the RGO ONE ignores CAT `TX;` for real
transmit (shows TX, no RF; found 2026-11-15). **In use: USB RTS PTT** from
the box firmware — radio menu 33 RTS ON, menu 02 LINE IN ON, VOX off;
WSJT-X PTT Method = CAT. Radio and amp key, ACC1 audio passes. VOX also
works as a fallback (see HANDOVER). No PTT wire is needed,
and no GPIO hack on the CM108.

## Panel (front wall, left to right from outside)

| Label | Connector | Goes to |
|---|---|---|
| RIG | S3 native USB-C (through a slot) | Radio USB-B (CAT) |
| PWR | S3 COM USB-C (same slot) | USB charger (USB-A → USB-C cable) |
| IN | CM108 mic jack, 1/8" | Radio audio cable, RX plug |
| OUT | CM108 headphone jack, 1/8" | Radio audio cable, TX plug |
| AMP | 2.5 mm stereo (TRS) jack, panel mount | SPE CAT: 2.5 mm TRS plug → DB15 male cable (see below) |
| PC | **Back wall:** 6 × 14 mm cable notch behind the dongle, closed by a tab on the lid | PC (CM108 audio) |

The status LED shows through a window in the lid. Put a ferrite clamp on
every cable leaving the box (there is 1 kW of RF nearby).

## Radio audio cable (separate from the box)

The radio's audio is only on ACC1 (DB15, female on the radio), so this
cable has a **DB15 male plug** on the radio end and **two 1/8" plugs** on
the other end. It needs only 3 wires: use 2-core screened cable, or two thin
screened leads.

The three resistors go **inside the DB15 plug's hood**:

```
RX:  ACC1 pin 11 ─────────► IN plug (tip)     → CM108 mic jack   (direct, no resistors)
     ACC1 pin 15 ─────────► IN plug (sleeve)

TX:  OUT plug (tip) ───────► ACC1 pin 10 (LINE IN +)   ← CM108 headphone jack (direct)
     OUT plug (sleeve) ─────► ACC1 pin 9 + pin 15
```

| ACC1 pin | Signal | Cable |
|---|---|---|
| 11 | LINE OUT (RX audio) | Core 1 → IN tip, direct (no resistors) |
| 10 | LINE IN + (600 Ω) | Core 2 ← OUT tip, direct |
| 9 | LINE IN − | Joined to 15 in the hood (input driven unbalanced) |
| 15 | Ground | Screen → both plug sleeves |
| 8 | PTT | Not used (PTT is on CAT) |

### ACC1 full pinout (radio, DB15 female on the rear panel)

From the RGO ONE manual §5.5 (rev 1.01b; 2020 rev 2.00A and V6 rev 1.01A
agree). The cable plug is DB15 **male**; on its solder side the numbering
is mirrored, so go by the numbers moulded on the plug.

| Pin | Signal | This cable |
|---|---|---|
| 1 | 13 V | **Leave open** |
| 2 | VC (front panel supply voltage) | **Leave open** |
| 3 | Not in use | — |
| 4 | Not in use | — |
| 5 | Not in use | — |
| 6 | Not in use | — |
| 7 | CWK (CW keying from an external source / PC) | — |
| 8 | PTT | — (PTT is on CAT) |
| 9 | LINE IN − | Joined to 15 in the hood |
| 10 | LINE IN + (600 Ω) | TX audio, direct from the OUT tip |
| 11 | LINE OUT | RX audio, direct to the IN tip |
| 12 | 8 V RX (8 V while receiving) | **Leave open** |
| 13 | 8 V TX (8 V while transmitting) | **Leave open** |
| 14 | External power ON | **Leave open** (switches the radio on) |
| 15 | Ground | Screen, both plug sleeves |

Pins 1, 2, 12 and 13 carry voltage, and 14 switches the radio on. Check
that no strand bridges any of them to 15 or the screen before you plug in.

**Radio setting:** set **menu 02 LINE IN = E** (external), so TX audio comes
from ACC1, not the front mic.

> **Fixed fault (2026-11-15): RX audio was far too low.** The first build
> had a 10 k / 1 k divider (÷11), chosen without knowing the line-out level
> and not bench-tested before the cable was closed. The RGO ONE's LINE OUT
> is already low, near mic level (see below). With ÷11, WSJT-X showed ~0 dB at full Mac input
> gain. Both RX resistors are now removed.

**RX level (measured 2026-11-15):** LINE OUT direct to the CM108 mic input,
no resistors: WSJT-X shows **about 25 dB**. That is usable (WSJT-X wants
roughly 20–40 dB; decoding does not depend on the exact level). To confirm
there is enough level, disconnect the antenna: if the reading drops by
10 dB or more, band noise is above the dongle's own noise floor and the
level is fine. **Measured: 25 dB with the antenna on, 15 dB with it off**
(a 10 dB drop). That just passes: band noise sets the noise floor, not the
dongle. If you ever want more margin, a small audio preamp before the
dongle would add it. The cable itself needs no further changes.

**With the radio preamp on (RF gain at max): about 35 dB** — inside the
WSJT-X range with margin. Run with the preamp on for digital modes.

**Where LINE OUT comes from** (tech supplement v2.30A, IF/AF board p. 49,
main board p. 4): IF/AF U4.A "BUF AMP" (½ MC33079), a fixed gain of
1 + 120 k/3.3 k ≈ 37 (R25/R34), then R53 620 Ω, C26 1 µF and an
L13/C34/C35 RF filter on the main board to ACC1 pin 11. It is after the
AGC and before the volume control. **There is no level trimmer.** The four
2 k trimmers on the IF/AF board (R26, R31, R40, R60) are factory AGC
settings (threshold and timing); don't use them to set audio level. What
does change the line-out level is the radio's **RF gain** (keep it fully
up), **preamp on** and **ATT off**. The only hardware route to more level
inside the radio is a larger R25 (SMD rework); an external preamp is
simpler.

**TX level (measured 2026-11-15):** OUT tip direct to LINE IN + (the 1 k
was removed). With the Mac output at max, ALC shows just 1–2 dots, which is
right, so there is no headroom to spare: run the Mac output at max and trim
with the radio's mic gain / power if needed.

**Mic bias:** the mic tip carries the dongle's mic bias, and with no shunt
it now sits on the radio's LINE OUT. If you hear clicks or distortion, add
a 1 µF capacitor in series with the tip.

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

### SPE DB15 CAT full pinout (amp, IN 1 / IN 2 "CAT" socket)

From the Expert 1.5K-FA manual §12.1 (same on the 1K-FA, 1.3K-FA and
2K-FA). The amp's socket takes a DB15 **male** cable plug.

| Pin | Name | Function | This cable |
|---|---|---|---|
| 1 | RX 232 | RS-232 CAT (Kenwood / Yaesu) | — |
| 2 | /TX-INH | Open collector, stops TX when grounded | — |
| 3 | TX TTL | 5 V TTL CAT, amp → radio (the amp's `IF;` polls) | **Core 2** → box jack ring |
| 4 | GND | Signal ground | **Screen** → box jack sleeve |
| 5 | ALC | Parallel with the ALC phono socket | — |
| 6 | DATA A | Band data bit A | — |
| 7 | DATA C | Band data bit C | — |
| 8 | REMOTE ON | 9–15 V turns the amp on | **Leave open** |
| 9 | TX 232 | RS-232 CAT | — |
| 10 | RX TTL | 5 V TTL CAT, radio → amp | **Core 1** → box jack tip |
| 11 | KEN TTL | Ground it to select 5 V TTL Kenwood CAT | **Joined to 4** in the hood |
| 12 | RELAY | Parallel with the RELAY phono socket | **Leave open** |
| 13 | TX-INH | Normally to ground (550 Ω); +12 V stops TX | — |
| 14 | DATA B | Band data bit B | — |
| 15 | DATA D | Band data bit D | — |

The amp's TTL CAT runs **inverted** (idles low); the firmware sets
`SPE_INVERT`. Set the amp to SET → CAT → KENWOOD, 9600 baud, and
power-cycle it after any CAT change. Pin 12 (RELAY) is the amp's keying
line: keep it isolated, or the amp could key unexpectedly.

A jack shorts its contacts for a moment as a plug goes in. The 220 Ω keeps
GPIO17 safe during that short (the ring line already has its 10 k). Plug
and unplug the amp cable with the box powered off, to be safe.

## Power: USB charger

A USB charger goes into the S3's PWR (COM) socket with a USB-A → USB-C
cable. Don't power it from the PC through a hub: the box would be dead
whenever the PC is off. With the charger, the amp keeps following band
changes when the PC is off.

## Enclosure

Draft 7: 107 × 75 × 27.8 mm (draft 6 failed a test fit: loose board, plugs could not seat through the wall), OpenSCAD in `enclosure/`, to be printed on the
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
  - no resistors (both lines run direct); a spare 1 µF capacitor.
- **Short USB-A extension** (dongle → PC).
- **Ferrite clamps** (snap-on, mix 31).
- **Assembly:**
  - 4 × M3 heat-set inserts;
  - 4 × M3 × 8 flat-head screws;
  - zip ties.
