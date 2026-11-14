# RGO ONE SPE CAT Server

ESP32-S3 CAT bridge: polls the RGO ONE over USB host and feeds Kenwood-format
frequency to the SPE amp, so the amp follows band changes. Also serves Kenwood
CAT over TCP for Hamlib / WSJT-X and publishes rig state to MQTT.

**Status:** firmware written and builds; not yet tested on hardware.

## How it works

```
RGO ONE ──USB (FT232R, 19200)──► ESP32-S3 ──UART1 TTL (Kenwood FA;/IF;)──► SPE amp
                                    │
                                    ├── TCP :4533 Kenwood CAT ──► Hamlib / WSJT-X
                                    └── MQTT shack/rgo-spe-cat/rig ──► Node-RED
```

The S3 is the only device on the radio's CAT port. It polls `IF;` every
150 ms. If the radio stops answering, it stops feeding the amp rather than hold
a stale band.

## Hardware

- ESP32-S3 N16R8 board. Native USB port → radio's USB-B (OTG port must supply
  5 V on VBUS). Flash and monitor via the board's COM port.
- GPIO17 → SPE CAT in, GPIO18 ← SPE CAT out (only if the amp polls; check its
  voltage first), GND ↔ SPE ground.

## Quick start

```bash
python3 install.py     # bootstraps PlatformIO (macOS/Pi aware), verifies the build
./flash.sh             # build + upload (picks the serial port)
./monitor.sh           # serial monitor
```

1. On first boot the node opens Wi-Fi AP **`vu2cpl-rgo-spe-cat-setup`**
   (password `vu2cpl1234`). Join it, pick your network, enter its password.
   Creds persist in NVS.
2. Copy `include/secrets.h.example` → `include/secrets.h` and set the MQTT role
   password (from the shack password manager) and an OTA password.
   `secrets.h` is git-ignored.
3. Set `SPE_BAUD` in `include/config.h` to match the amp's CAT setting.

## PC software

Hamlib / WSJT-X: rig **Kenwood TS-480**, network port
`rgo-spe-cat.local:4533`, PTT via CAT.

## MQTT

- Broker: `192.168.1.169:1883` (auth required — role account in `secrets.h`).
- `shack/rgo-spe-cat/status` — retained; LWT `{"event":"offline"}`, 30 s heartbeat.
- `shack/rgo-spe-cat/rig` — retained; `{"ok","freq_hz","band","mode","tx"}`.

## Layout

```
platformio.ini         env:rgo-spe-cat (ESP32-S3 N16R8, pioarduino)
include/config.h        pins, baud rates, timings, broker, topics (+ git-ignored secrets.h)
src/ftdi_host.*         USB host driver for the radio's FT232R
src/rig.*               radio task: owns the CAT port, rig state
src/spe.*               Kenwood emulation to the SPE
src/tcp_cat.*           Kenwood CAT over TCP
src/main.cpp            Wi-Fi, MQTT, OTA, status LED
flash.sh / monitor.sh   serial-port pickers (never pin the port)
install.py              toolchain bootstrap, macOS/Pi branch
```

See `HANDOVER.md` for the full design, measured radio facts and open items.
