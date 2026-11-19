# TCI audio over Wi-Fi: hardware plan

**Status: plan only (2026-11-19).** Nothing bought, wired or written yet.

## Goal

Remove the USB audio cable between the box and the PC. The S3 runs a TCI
server (Expert Electronics protocol, WebSocket, port 40001) that carries
CAT, PTT and RX/TX audio over Wi-Fi. An I2S codec in the box replaces the
C-Media dongle.

- TCI `vfo` / `modulation` → the existing radio CAT code.
- TCI `trx` → RTS PTT, with the existing fail-safes (client disconnect,
  radio USB loss, 3 min limit).
- RX audio: ACC1 LINE OUT → codec ADC → TCI binary frames to the client.
- TX audio: the S3 sends TX_CHRONO requests, the client returns samples,
  codec DAC → ACC1 LINE IN. The S3's I2S clock paces both directions, so
  there is no clock drift between PC and box. Wi-Fi buffering of
  100–200 ms only gives a small fixed DT offset in FT8/FT4.
- The Kenwood TCP CAT server on 4533 stays for Hamlib-only apps.

**Client support:** JTDX supports TCI with audio (so JTDX-VU should). WSJT-X
Improved and MSHV have TCI in some versions; check against the builds in use.
**Mainline WSJT-X has no TCI** and would still need a sound card.

## 1. Audio codec board (the only new part)

| Requirement | Value | Why |
|---|---|---|
| Digital interface | I2S audio + I2C control, 3.3 V logic | Direct to the S3 |
| Sample rate / depth | 48 kHz, 16-bit minimum (24-bit preferred) | TCI's standard rate |
| **RX input gain** | **Programmable gain of +30 dB or more** | LINE OUT is near mic level: the CM108 mic preamp at full gain gave only 25–35 dB in WSJT-X (`BOX_PLAN.md`). A line-level ADC would be far too quiet |
| RX input | Mono, AC-coupled, ≥ 10 kΩ, **mic bias switchable off** | LINE OUT is 620 Ω + 1 µF; keep DC off the radio output |
| **TX output drive** | **Drives 600 Ω at about 1 V RMS or more, with volume control** | ACC1 LINE IN+ is 600 Ω. The CM108 at full output gave only ALC 1–2 dots, with no headroom; the new board needs some to spare |
| TX output | Mono is enough, AC-coupled | Feeds LINE IN+; LINE IN− stays tied to ground |
| Power | 3.3 V (or 5 V with onboard regulator), under 100 mA | From the box's USB charger via the S3 board |
| Size | About 40 × 40 mm or less | Must fit the 101 × 79 mm box; the dongle-A cradle needs re-cutting |
| Connections | 3.5 mm jacks, or pads | The ACC1 cable ends in 3.5 mm plugs; jacks let it plug in unchanged |

**Preferred chip: WM8960.** Input PGA up to +30 dB plus up to +29 dB boost,
a headphone driver that handles 600 Ω easily, and switchable mic bias.
**Alternative: ES8388** (mic PGA up to +24 dB; may be marginal on RX gain).
**Avoid PCM1808 + PCM5102A.** No input gain, and the PCM5102A is not
specified for 600 Ω loads; it would also need an extra preamp and buffer.

## 2. S3 pins (I2S 5 + I2C 2)

**Pins that are already taken or unsafe:** 17/18 (SPE), 19/20 (USB host to
the radio), 43/44 (console UART), 0/3/45/46 (strapping), 26–37 (flash /
octal PSRAM on N16R8), 48 (RGB LED).

| Signal | GPIO |
|---|---|
| MCLK | 4 |
| BCLK | 5 |
| WS (LRCLK) | 6 |
| DOUT → codec DAC | 7 |
| DIN ← codec ADC | 15 |
| I2C SDA | 8 |
| I2C SCL | 9 |

## 3. What goes away

- The C-Media dongle and its USB cable to the Mac. The box has no wired
  link to the PC any more.
- The planned 600:600 isolation transformers. With no PC cable there is
  no ground loop to break.

## 4. What stays the same

- The ACC1 audio cable, RTS PTT over the radio's USB, the SPE link and
  the USB charger.
- Radio menus: 02 LINE IN ON, 33 RTS ON, VOX off.

## 5. Wi-Fi

- 2.4 GHz at −70 dBm or better at the box (−55 dBm measured; passes).
- About 0.8 Mb/s each way for mono 16-bit audio, up to about 3 Mb/s if a
  client asks for float32 stereo. The S3 handles this easily.
- Firmware must turn Wi-Fi power save off.

## Before buying

Measure the LINE OUT voltage with a scope or AC millivoltmeter on a loud
signal. So far it is known only as a WSJT-X dB reading, not in volts. That
number decides whether +30 dB of codec gain is enough or whether a small
preamp is still needed.

## Firmware work (later)

WebSocket server; the TCI command subset the clients use (about 15
commands plus the audio stream header, TX_CHRONO); I2S codec driver and
I2C setup; ring buffers in PSRAM; Wi-Fi power save off; then remeasure RX
and TX levels.
