# RGO ONE SPE CAT Server — Project Handover
*For continuation in a new Claude session*

**Created:** 2026-11-14 · **Last updated:** 2026-11-14 · **Type:** ESP firmware (ESP32-S3 N16R8)

---

## Current state

- **Firmware written and builds** (RAM 15.8 %, flash 17.3 %). All modules are in
  place: FT232R USB host driver, radio poller, SPE output, TCP CAT, MQTT, OTA.
- **Not yet run on hardware.** Nothing has been flashed; the USB host link and
  the SPE output are untested on a real S3, radio and amp.
- Radio facts measured on the Mac (see "Radio — measured facts" below).
- Git: local repo, no GitHub remote yet.

## Purpose and scope

An ESP32-S3 sits between the RGO ONE and the SPE amplifier. It is the only
device that talks to the radio's CAT port, and it passes frequency and mode to
the amp so the SPE follows band changes automatically.

- **In scope:** CAT polling of the RGO ONE over USB, Kenwood-format frequency
  output to the SPE over TTL serial, and Wi-Fi TCP CAT for PC software
  (Hamlib / WSJT-X).
- **Optional:** MQTT publishing of frequency, band and TX state to the shack's
  Node-RED.
- **Out of scope:** TCI, audio, IQ and panadapter. Any IF-out panadapter work
  is a separate SDR box, not this ESP32.

## Decisions

| Topic | Decision | Reason |
| --- | --- | --- |
| Radio connection | USB host from the ESP32-S3 to the RGO ONE's USB Type B socket | The radio exposes CAT on USB only; this avoids opening the radio |
| Internal TTL tap | Not used | Needs the radio opened and handling of contention with the internal USB-serial chip |
| Board | ESP32-S3 N16R8 | Has USB OTG host; flash and PSRAM leave room for OTA |
| USB driver | Own minimal FT232R driver on the IDF USB host stack (`src/ftdi_host.cpp`) | The radio's chip is FTDI, not CDC-ACM. Espressif's VCP drivers are managed components the Arduino core doesn't ship; a hybrid IDF build would be slow and fragile. FTDI needs only ~7 vendor control requests |
| Platform | pioarduino 55.03.311 (Arduino-ESP32 3.3.11, IDF 5.5) | Ships `usb/usb_host.h` + `libusb.a` |
| SPE connection | Direct TTL from an ESP32 UART, no MAX3232 | The SPE accepts TTL-level CAT |
| Protocol to SPE | Kenwood emulation (`FA;`, `IF;`) | Common format the SPE understands |
| TCI | Dropped | No IQ or audio from the RGO ONE, and the SPE and WSJT-X don't use it |
| Bluetooth serial | Dropped | The S3 has BLE only, so no SPP COM port; macOS SPP is unreliable anyway |
| Audio over network | Dropped | Would need I2S ADC/DAC and Wi-Fi buffering; out of scope |

## Radio — measured facts (2026-11-14, radio on the Mac)

- **USB chip:** FTDI FT232R, VID `0x0403`, PID `0x6001`, serial `AK08K5JO`
  (`/dev/cu.usbserial-AK08K5JO` on the Mac).
- **CAT baud:** 19200 8N1 (no reply at 9600).
- **Command set:** TS-480-style Kenwood confirmed.
  - `FA;` → `FA00007117850;`
  - `IF;` → `IF00007117850     -00000000001000000 ;` (standard 35-field TS-480
    frame; mode 1 = LSB, RX)
  - `ID;` → **no reply**. Don't use it to identify the radio. The SPE side
    answers `ID020;` (TS-480) itself.

## Hardware and wiring

| Link | From | To | Notes |
| --- | --- | --- | --- |
| USB CAT | S3 native USB port (host) | RGO ONE USB Type B | USB-C to USB-B cable. OTG port must supply 5 V on VBUS: set the board's jumper/solder pad or feed 5 V in |
| Console / flashing | S3 "COM" port (UART0 bridge) | Mac | The native port is busy as USB host, so flash and monitor via COM |
| SPE TX data | S3 GPIO17 (UART1 TX, 3.3 V) | SPE CAT input | Usually reads fine at 3.3 V; add a 74AHCT125 buffer if the amp misses characters |
| SPE RX data | SPE CAT output | S3 GPIO18 (UART1 RX) | Only if the amp polls. Measure first: 5 V needs a divider, RS-232 ±12 V needs a proper level shifter. Leave unconnected if the amp only listens |
| Ground | S3 GND | SPE ground | Required |

RF hardening: shielded enclosure, ferrites on the USB, CAT and power leads.
The radio runs 100 W with the SPE close by.

## Firmware design

One task owns the radio and holds its state; every output reads from that
state. The radio → SPE path starts before Wi-Fi and never depends on it.

| Module | File | What it does |
| --- | --- | --- |
| USB link | `src/ftdi_host.*` | IDF USB host + client + driver tasks. Matches 0403:6001, forces **DTR/RTS low** first, sets 19200 8N1, no flow, 4 ms latency. Strips the 2 FTDI status bytes per IN packet into a stream buffer. Handles hot unplug/replug |
| Rig state | `src/rig.*` | Radio task: polls `IF;` every 150 ms, parses freq / mode / TX, keeps the raw IF frame. PC commands go through one queue; a set command triggers an immediate re-poll. State goes invalid after 1.5 s without a good reply |
| SPE output | `src/spe.*` | UART1 Kenwood emulation. Answers `FA;` `IF;` `AI;` `ID;` from cache; pushes `FA…;` on change plus a 2 s keepalive. **Fail-safe:** sends nothing while state is invalid |
| TCP CAT | `src/tcp_cat.*` | Port 4533, up to 3 clients. `FA;`/`IF;` from cache, everything else forwarded to the radio via the queue; replies `?;` if the radio is absent |
| Main | `src/main.cpp` | WiFiManager (no restart on portal timeout — would cut the SPE feed), MQTT, ArduinoOTA, RGB status LED |

Tunables are in `include/config.h` (baud rates, pins, poll/stale timings,
push behaviour, TCP port).

**Status LED (on-board RGB):** green = radio OK · amber = USB up, no replies ·
red = no radio on USB · blinking blue = no Wi-Fi.

**Hamlib / WSJT-X:** rig model Kenwood TS-480 (2028), serial port / rig path
`rgo-spe-cat.local:4533` (network). PTT via CAT.

## MQTT

- Broker `192.168.1.169:1883`, auth required; role `iot`, password in
  `include/secrets.h` (git-ignored; from the shack password manager).
- `shack/rgo-spe-cat/status` — retained; `{"event":"online"}` on connect, LWT
  `{"event":"offline"}`, heartbeat every 30 s (`uptime_s`, `rssi`, `radio`).
- `shack/rgo-spe-cat/rig` — retained, on change (max 4/s):
  `{"ok":true,"freq_hz":7117850,"band":"40m","mode":"LSB","tx":false}`, or
  `{"ok":false}` when the radio stops answering.

## Flash

```bash
./flash.sh              # firmware (picks port) — use the board's COM port
./monitor.sh            # serial monitor
```

OTA after first flash: `pio run -t upload --upload-port rgo-spe-cat.local`.

## Wi-Fi onboarding

First boot opens AP **`vu2cpl-rgo-spe-cat-setup`** (password `vu2cpl1234`,
hostname `rgo-spe-cat`). Join it → captive portal → pick network. Creds persist
in NVS. If the portal times out (180 s) the box keeps running offline — the
radio → SPE path doesn't need Wi-Fi.

## Open items

- [x] ~~RGO ONE USB-serial chip VID/PID~~ — FT232R 0403:6001
- [x] ~~RGO ONE CAT baud rate~~ — 19200
- [x] ~~Confirm the RGO ONE's CAT command set~~ — TS-480 style (`ID;` unsupported)
- [ ] Does the SPE poll the radio or only listen? Its CAT baud setting? (`SPE_BAUD` is a 9600 placeholder)
- [ ] SPE CAT output voltage, if it polls
- [ ] How the S3 board enables 5 V on the OTG port's VBUS
- [ ] Set `OTA_PASS` in `secrets.h` before the box goes into the shack
- [ ] Optional: small status web page (deferred; MQTT + LED cover it for now)

## Next steps

1. Flash an S3 and check the USB link on the bench: radio on USB, serial
   monitor shows `[USB] FTDI ready` and `[RIG] … Hz` lines tracking the VFO.
2. Test TCP CAT with Hamlib (`rigctl -m 2028 -r rgo-spe-cat.local:4533 f`)
   and WSJT-X.
3. Close the SPE open items, set `SPE_BAUD`, wire the amp, bench test with the
   amp in standby before keying up.

## Known gotchas

- **Homebrew `pio` fails** with "Python version must be 3.10+" (it runs on
  Python 3.9). `flash.sh`, `monitor.sh` and `install.py` prefer
  `~/.platformio/penv/bin/pio`, which works.
- Opening the radio's FTDI port from a Mac can briefly raise DTR/RTS. The
  firmware forces both low right after enumeration; on the Mac, check the
  radio's DTR/RTS PTT/key setting before probing.

## What changed

- **2026-11-14** — Project scaffolded (shack ESP template) and the original
  design handover merged in. Radio probed: FT232R, 19200, TS-480 set. Full
  firmware written: FT232R host driver, radio poller, SPE output with
  fail-safe, TCP CAT, MQTT rig topic, OTA, status LED. Builds clean; not yet
  run on hardware. Wrappers made to prefer the penv `pio`.

## Conventions (see ~/.claude/CLAUDE.md)

- **CDP** — Commit, Document, Push together on every substantive change.
- Never pin `upload_port`/`monitor_port` — use `flash.sh`/`monitor.sh`.
- Never commit secrets — they live in git-ignored `secrets.h`.
- GitHub repos are **private** unless explicitly published.
