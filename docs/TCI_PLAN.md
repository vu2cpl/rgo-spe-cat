# TCI audio over Wi-Fi: hardware plan

**Status: plan only (2026-11-19).** Board chosen (Waveshare WM8960 Audio
Board, see below); nothing bought, wired or written yet.

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

### Chosen board: Waveshare WM8960 Audio Board (2026-11-19)

Checked against Waveshare's [wiki](https://www.waveshare.com/wiki/WM8960_Audio_Board),
schematic, manual and dimension drawing. Not bought yet.

**Sources (same board, same specs):**

| Source | Price (2026-11-19) | Notes |
|---|---|---|
| [Robu.in](https://robu.in/product/waveshare-wm8960-stereo-codec-audio-module-playrecord/) | ₹1,979 incl. GST | Out of stock on 2026-11-19. Brand Waveshare, 1-year warranty, Indian seller |
| [AliExpress, Integrated Solution Company Limited Store](https://www.aliexpress.com/item/1005012787457523.html) | SGD 20.20 (about ₹1,428) | Photo shows the Waveshare logo on the back, so likely genuine. Store rated 4.6 |

Avoid the cheaper AliExpress listing 1005008591238771 (Senlltop Store,
1 review). It only reuses Waveshare's photos and may be a copy.

**Specs:** WM8960, 3.3 V, I2C control, I2S audio, 8–48 kHz. SNR: DAC
98 dB, ADC 94 dB. Headphone output 40 mW into 16 Ω, speaker output 1 W per
channel into 8 Ω (BTL). Onboard MEMS mic, 4-pole 3.5 mm headset jack
(PJ-342), 2×8 header at 2.54 mm. Size **58 × 24 mm**, plus the right-angle
header pins at one end and the jack lip.

**How it meets the requirement:**

- **RX gain:** PGA up to +30 dB, plus boost up to +29 dB. Passes.
- **TX drive:** the headphone driver goes through 100 µF caps (C5/C6),
  about 1 V RMS full scale, and drives 600 Ω easily. Passes.
- **MCLK:** onboard 24 MHz oscillator, and the codec PLL makes 48 kHz from
  it. The S3 does not need an MCLK pin, so GPIO 4 stays free. Header P1
  selects which header pin carries MCLK; leave the S3 side unconnected.
  The codec runs as I2S master, so its clock paces the audio.

**Changes needed (from the schematic):**

1. **One 4-pole headset jack.** Headphone L/R (pins 2/3) and the mic
   contact (pin 1) share one jack, but the ACC1 cable ends in two separate
   3.5 mm plugs. Use a headset-to-mic/headphone splitter, or rewire the
   cable to one 4-pole plug. The jack standard (CTIA or OMTP) is not
   documented. Before buying a splitter, power the board with R1 still
   fitted and find the mic contact with a meter: it reads about 3.3 V
   through 2.2 kΩ.
2. **Fixed mic bias.** The jack's mic contact goes to RINPUT1 through C4
   (1 µF), with **R1 (2.2 kΩ) pulled up to 3.3 V**. This bias can't be
   switched off in software. The radio's C26 (1 µF) blocks the DC, as
   with the CM108 today, but R1 also loads LINE OUT (620 Ω source) and
   costs about 2 dB. **Remove R1.**
3. **Size.** 58 × 24 mm is over the 40 × 40 mm target, but it should fit
   the 101 × 79 mm box. The dongle-A cradle needs redesigning.
4. **Onboard MEMS mic** is on LINPUT1. The firmware leaves it off and uses
   only RINPUT1 for RX. TX audio goes out on HP_L (tip). LINE IN is mono.

## 2. S3 pins (I2S 5 + I2C 2)

**Pins that are already taken or unsafe:** 17/18 (SPE), 19/20 (USB host to
the radio), 43/44 (console UART), 0/3/45/46 (strapping), 26–37 (flash /
octal PSRAM on N16R8), 48 (RGB LED).

| Signal | GPIO |
|---|---|
| MCLK | 4 (not needed with the Waveshare board: onboard 24 MHz clock) |
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
