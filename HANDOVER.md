# RGO ONE SPE CAT Server — Project Handover
*For continuation in a new Claude session*

**Created:** 2026-11-14 · **Last updated:** 2026-11-14 · **Type:** ESP firmware (ESP32-S3 N16R8)

---

## Current state

- **Firmware written and builds** (RAM 15.8 %, flash 17.3 %). All modules are in
  place: FT232R USB host driver, radio poller, SPE output, TCP CAT, MQTT, OTA.
- **Flashed and running on an S3 N16R8** (MAC `ac:27:6e:a5:97:2c`, 16 MB
  flash, 8 MB PSRAM). On Wi-Fi at `192.168.30.191` (`rgo-spe-cat.local`); TCP
  CAT on 4533 answers in ~5 ms (`?;` with no radio attached, as designed).
- **Radio link verified 2026-11-14:** RGO ONE enumerates (0403:6001), FTDI
  configured at 19200, `[RIG] 7095250 Hz 40m LSB RX`, LED green. Over TCP
  4533: `FA;`/`IF;` from cache, `FB;` forwarded live, ~7 ms round trip.
- **Hamlib verified 2026-11-14:** `rigctl -m 2028 -r 192.168.30.191:4533`
  reads freq / mode / VFO / PTT and sets freq; opens in ~3 s with no timeouts.
- **WSJT-X verified 2026-11-14:** rig Kenwood TS-480, Serial Port field
  `192.168.30.191:4533`, follows tuning and band changes. Tested with a
  separate config (`--rig-name=RGO`, `~/Library/Preferences/WSJT-X - RGO.ini`)
  so the main WSJT-X setup is untouched. PTT over CAT not yet keyed.
- **Not yet tested:** the SPE output, MQTT (no password in `secrets.h` yet),
  PTT via CAT.
- Radio facts measured on the Mac (see "Radio — measured facts" below).
- Git: private repo [vu2cpl/rgo-spe-cat](https://github.com/vu2cpl/rgo-spe-cat), branch `master`.

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
| SPE TX data | S3 GPIO17 (UART1 TX, 3.3 V) | SPE DB15 pin 10 (RX TTL) | Amp input is 5 V TTL. 3.3 V high is above standard TTL V<sub>IH</sub> (2.0 V) so it should read; add a 74AHCT125 buffer if the amp misses characters |
| SPE RX data | SPE DB15 pin 3 (TX TTL, **5 V**) | S3 GPIO18 (UART1 RX) | Optional — carries the amp's polls. **Needs a divider** (e.g. 10 k / 20 k): the S3 is not 5 V tolerant. Leave unconnected for listen-only mode |
| TTL select | SPE DB15 pin 11 (KEN TTL) | GND | Selects the 5 V TTL Kenwood interface instead of RS-232 (pins 1/9) |
| Ground | S3 GND | SPE DB15 pin 4 (GND) | Required |

The SPE CAT connector (one per exciter input, IN 1 / IN 2) takes a **DB15
male** cable plug. Pinout from the Expert 1.5K-FA manual rev 3.2 §12.1.

### SPE CAT behaviour (manual rev 3.2, §11 "CAT", §12.3, §14)

- **Kenwood mode:** set SET → CAT → KENWOOD, then the baud (manual: "almost
  always 9600"). Power-cycle the amp after any CAT change. Check with SET →
  MANUAL TUNE.
- **Two ways to wire it**, both supported by the firmware:
  - *Polled* (two wires, the amp's standard direct mode): the amp interrogates
    the radio cyclically on pin 3; the ESP32 answers `FA;` / `IF;`. Needs the
    5 V → 3.3 V divider on GPIO18.
  - *Listen-only* (one wire, as in SPE's "transceiver controlled by PC" §14):
    only pin 10 + GND, pin 3 left open; the amp "analyzes only the data
    exchanged". The ESP32's unsolicited `FA…;` pushes and 2 s keepalive feed it.
    No 5 V reaches the S3. Consider `SPE_PUSH_IF 1` here, in case the amp
    parses `IF` frames rather than `FA`.
- The manual doesn't say which Kenwood commands the amp sends when polling;
  sniff pin 3 to confirm (expect `FA;` or `IF;`).

**Board = VCC-GND YD-ESP32-S3 (N16R8).** Seen from the front with the
sockets at the top: left USB-C = **COM** (CH343, console), right USB-C =
**USB** (native, → radio). Power, measured 2026-11-14:
- The **COM socket has no USB-C CC pull-down resistors**, so a USB-C→USB-C
  cable from a Mac never gets 5 V (board dark, nothing enumerates). With a
  **USB-A→USB-C cable** it powers the whole board *and* carries the console
  (CH343 at `/dev/cu.usbmodem5C371795401`, auto-reset works). Verified
  2026-11-14: boot log clean, Wi-Fi joins, TCP CAT up.
- `USB-OTG` is **bridged**, so the board's 5 V rail is on the USB socket's
  VBUS — that is what powers the radio's FT232R side. Consequence: never
  connect the USB socket to a Mac/PC while 5Vin is also fed (two supplies
  tied with no diode). On the bench with the Mac on the USB socket as the
  only supply, it's fine.
- **VBUS on the USB socket (FNB58, 2026-11-14):** 4.02 V with COM fed from
  the Mac's USB-A port; **4.7 V with COM fed from an external 5 V charger**.
  The drop is mostly diode D1 (COM → rail). 4.7 V is within USB device
  spec; 4.0 V is marginal for a bus-powered FT232R.
- In service: power the COM socket from a **5 V USB-A charger** (or a
  powered hub between S3 and radio); USB socket → radio. Use the Mac on COM
  only for logs/flashing on the bench.

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
| TCP CAT | `src/tcp_cat.*` | Port 4533, up to 3 clients. `FA;`/`IF;` from cache. Answered locally for Hamlib: `MD;` (mode digit from the cached IF), `PS;` → `PS1;`, `AI;` → `AI0;`; `AI` set commands are absorbed, never sent to the radio. Everything else forwarded to the radio via the queue; replies `?;` if the radio is absent |
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

**First flash / no COM port (what worked 2026-11-14):** unplug everything,
hold BOOT, plug the *native* USB port into the Mac, release BOOT. The board
appears as `USB JTAG/serial debug unit` (303A:1001). Flash with
`pio run -t upload --upload-port /dev/cu.usbmodemXXXX`. esptool's RTS reset
afterwards leaves it in download mode (`boot:0x0 … waiting for download`), so
finish with a watchdog reset:
`~/.platformio/penv/bin/python -m esptool --port /dev/cu.usbmodemXXXX --before no-reset --after watchdog-reset chip-id`.
Once the firmware runs, the native port becomes the USB host and vanishes
from the Mac.

**Serial console:** only on the COM port (CH343, 1A86:55D3). Its bridge is
powered from the board, not its own socket, so it only enumerates while the
board has power from elsewhere — and needs a data-capable cable (a
charge-only cable left it invisible on 2026-11-14).

## Wi-Fi onboarding

First boot opens AP **`vu2cpl-rgo-spe-cat-setup`** (password `vu2cpl1234`,
hostname `rgo-spe-cat`). Join it → captive portal → pick network. Creds persist
in NVS. If the portal times out (180 s) the box keeps running offline — the
radio → SPE path doesn't need Wi-Fi.

## Open items

- [x] ~~RGO ONE USB-serial chip VID/PID~~ — FT232R 0403:6001
- [x] ~~RGO ONE CAT baud rate~~ — 19200
- [x] ~~Confirm the RGO ONE's CAT command set~~ — TS-480 style (`ID;` unsupported)
- [x] ~~Does the SPE poll or only listen? Baud?~~ — polls in direct Kenwood mode; listen-only also supported. Baud set in SET → CAT, default 9600 (manual rev 3.2)
- [x] ~~SPE CAT output voltage~~ — 5 V TTL (pin 3); divider needed if wired
- [ ] Choose polled vs listen-only wiring; confirm which query the amp sends (sniff pin 3)
- [x] ~~How the S3 board enables 5 V on the OTG port's VBUS~~ — `USB-OTG` solder jumper on the back, behind the USB socket; bridged 2026-11-14 (it bypasses the diode between the native port's VBUS and the 5 V rail)
- [x] ~~Final power feed~~ — COM socket via a USB-A cable (it lacks USB-C CC resistors), or 5 V into 5Vin
- [ ] MQTT: put the `iot` password in `secrets.h` (boot log shows `rc=5`, not authorised)
- [ ] Set `OTA_PASS` in `secrets.h` before the box goes into the shack
- [ ] Optional: small status web page (deferred; MQTT + LED cover it for now)

## Next steps

1. ~~Flash an S3~~ (done). Check the USB link: power the board from its 5V
   pin (or COM port), native USB → radio. LED goes green; `FA;` over TCP
   4533 returns the VFO.
2. ~~Test TCP CAT with Hamlib and WSJT-X~~ (done). Still to do: PTT via
   CAT (amp in standby first).
3. Make the DB15 cable (pins 10, 4, 11→GND, optional 3 via divider), check the
   amp's CAT baud matches `SPE_BAUD`, bench test with the
   amp in standby before keying up.

## Known gotchas

- **USB enumeration needs `enum_filter_cb`.** The Arduino libs build the IDF
  with `CONFIG_USB_HOST_ENABLE_ENUM_FILTER_CALLBACK=1`; with no callback set,
  enumeration silently stalls after port reset (controller shows conn=1
  en=1, stack shows 0 devices). `ftdi_host.cpp` sets one that picks config 1
  and logs the descriptor. Don't remove it.
- **IDF logs are compiled out** (`CONFIG_LOG_MAXIMUM_LEVEL 1` in the Arduino
  libs), so USB stack problems are silent. The driver's 2 s scan prints the
  device count and raw DWC `HPRT` port state when it changes.
- **RGO ONE answers `MD;` with a bare `MD;`** (no mode digit), and gives no
  reply to `PS;` or `AI;`. Hamlib's TS-480 backend sends all three, so
  `get_mode` failed with "Protocol error" and the open took ~7 s of
  timeouts. The TCP server now answers these locally (see Firmware design).
  It also absorbs `AI1;`/`AI2;`: auto-info would make the radio send
  unsolicited frames and break the poll.
- **Wi-Fi modem-sleep adds up to ~200 ms per reply.** The ESP32 default
  (`WIFI_PS_MIN_MODEM`) made CAT round trips ~210 ms and WSJT-X lag
  visibly. `main.cpp` calls `WiFi.setSleep(false)`; ping went from avg 87 ms
  to 7 ms.
- **WSJT-X with a Hamlib network rig reads the address from the "Serial
  Port" field** (`CATSerialPort` in the ini), not `CATNetworkPort`.
- **Mac shared-memory limits:** WSJT-X needs `kern.sysv.shmmax=52428800`.
  On this Mac the JTDX launch daemon set 32 MB at boot and WSJT-X failed
  with "shared memory error"; fixed by raising `shmmax` (and aligning
  `com.jtdx.sysctl.plist`).
- **Homebrew `pio` fails** with "Python version must be 3.10+" (it runs on
  Python 3.9). `flash.sh`, `monitor.sh` and `install.py` prefer
  `~/.platformio/penv/bin/pio`, which works.
- Opening the radio's FTDI port from a Mac can briefly raise DTR/RTS. The
  firmware forces both low right after enumeration; on the Mac, check the
  radio's DTR/RTS PTT/key setting before probing.

## What changed

- **2026-11-14** — **WSJT-X works; Wi-Fi sleep disabled.** WSJT-X follows
  the radio over TCP CAT. The lag the operator saw came from ESP32 Wi-Fi
  modem-sleep (~210 ms per reply); `WiFi.setSleep(false)` brings CAT round
  trips back to ~7 ms. WSJT-X's own poll interval (Settings → Radio) adds
  the rest.

- **2026-11-14** — **Hamlib works over TCP CAT.** The TCP server answers
  `MD;`, `PS;` and `AI;` locally and absorbs `AI` set commands. `rigctl -m
  2028` reads freq / mode / VFO / PTT and sets freq; open time ~3 s, down
  from ~7 s. Tuning-follow verified over 64 polls (band jump, mode changes).

- **2026-11-14** — **Radio link working.** Root cause of "radio shows PC but
  S3 sees no device": the IDF enumeration filter (enabled in the Arduino
  libs) needs a callback. Added it, plus a 2 s device scan with raw port
  registers and connect/disconnect logging. Spliced USB-C→USB-B cable
  works; radio enumerates on 4.0 V VBUS from the Mac-powered COM socket.

- **2026-11-14** — Measured VBUS on the USB socket: 4.02 V from the Mac's
  USB-A port, 4.7 V from an external charger. In-service power = charger on
  COM.

- **2026-11-14** — Bridged the `USB-OTG` pad (back of board, behind the USB
  socket) so the board can power the radio's USB side. The COM socket only
  powers the board from a USB-A cable (no CC resistors on it). Board identified as
  VCC-GND YD-ESP32-S3; socket roles documented.

- **2026-11-14** — First flash on a real S3 N16R8: boots, joins Wi-Fi, TCP
  CAT answers. `platformio.ini` now sets flash size for build and upload
  plus `maximum_size` (as esp32-vukeyer does). Added `tools/spe_test.py`
  (sniff / emulate a TS-480 toward the SPE from a Mac). Flashing procedure
  and COM-port power gotcha documented under "Flash".

- **2026-11-14** — SPE side pinned down from the Expert 1.5K-FA manual rev 3.2:
  DB15 pinout, 5 V TTL Kenwood (KEN TTL to GND), polled vs listen-only
  wiring, baud menu (default 9600). Wiring table and config comments updated.

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
