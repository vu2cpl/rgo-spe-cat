# RGO ONE SPE CAT Server — Project Handover
*For continuation in a new Claude session*

**Created:** 2026-11-14 · **Last updated:** 2026-11-15 · **Type:** ESP firmware (ESP32-S3 N16R8)

---

## Current state

- **In service 2026-11-15:** box built and installed; radio CAT, RX audio
  (35 dB, preamp on), TX audio (ALC 1–2 dots, Mac output max), RTS PTT and
  the SPE CAT link all working. Wiring: `docs/wiring.svg`.

- **Firmware written and builds** (RAM 15.8 %, flash 17.3 %). All modules are in
  place: FT232R USB host driver, radio poller, SPE output, TCP CAT, MQTT, OTA.
- **Flashed and running on an S3 N16R8** (16 MB
  flash, 8 MB PSRAM). On Wi-Fi at a DHCP-reserved IoT-VLAN address (`<box-ip>`, `rgo-spe-cat.local`); TCP
  CAT on 4533 answers in ~5 ms (`?;` with no radio attached, as designed).
- **Radio link verified 2026-11-14:** RGO ONE enumerates (0403:6001), FTDI
  configured at 19200, `[RIG] 7095250 Hz 40m LSB RX`, LED green. Over TCP
  4533: `FA;`/`IF;` from cache, `FB;` forwarded live, ~7 ms round trip.
- **Hamlib verified 2026-11-14:** `rigctl -m 2028 -r <box-ip>:4533`
  reads freq / mode / VFO / PTT and sets freq; opens in ~3 s with no timeouts.
- **WSJT-X verified 2026-11-14:** rig Kenwood TS-480, Serial Port field
  `<box-ip>:4533`, follows tuning and band changes. Tested with a
  separate config (`--rig-name=RGO`, `~/Library/Preferences/WSJT-X - RGO.ini`)
  so the main WSJT-X setup is untouched. Lag is at most WSJT-X's poll
  interval (1 s minimum); the S3 side adds ~7 ms.
- **PTT via CAT does NOT work (found 2026-11-15).** `TX;` / `TX0;` / `TX1;`
  (and `rigctl T 1`, WSJT-X Tune) make the radio *show* TX and set the TX
  flag in `IF;`, but it gives **no RF and does not key the amp**. The
  2026-11-14 "verified" note was based on the display/flag only; RF was
  never checked. Manoj confirmed on air: the hand-mic PTT keys the radio
  properly (RF out, amp keys), CAT TX does not — it is a display-only TX
  state, and ACC1 LINE IN audio is not passed in it. Real PTT has to come
  from a hardware/RTS line. **First workaround (2026-11-15), now the fallback: VOX.** Radio menu 10
  VOX GAIN on, menu 9 delay 0.5 s (default), WSJT-X PTT Method = VOX (CAT
  still does frequency/mode). Tune keys the radio with RF out and the amp
  keys. Caution: any sound sent to the USB Audio Device keys the
  transmitter. The manual's PC PTT route is the USB **RTS** line
  (menu 33). **RTS PTT works (2026-11-15) — in use.** Firmware
  (`RADIO_PTT_RTS`, `PTT_ALSO_CAT` in config.h): `TX…;` from a TCP client
  raises FTDI RTS (and also goes to the radio as CAT), `RX;` drops it;
  fail-safes drop RTS on client disconnect, radio USB loss and after 3 min.
  Polarity as configured: RTS asserted = TX. **Radio settings: menu 33 RTS
  ON, menu 02 LINE IN ON, VOX off; WSJT-X PTT Method = CAT.** The first RTS
  test gave no audio only because menu 02 LINE IN was off (the radio then
  used the hand mic); not a radio limitation. Whether the extra CAT TX
  (`PTT_ALSO_CAT`) is needed is untested. VOX also works as a
  fallback.
- **MQTT 2026-11-14:** logs in to the broker as `iot` (broker log: `New
  client connected … as rgo-spe-cat (u'iot')`). The broker ACL gained
  `topic write shack/rgo-spe-cat/#` under `user iot` (see
  `vu2cpl-shack/MQTT_AUTH.md`). Verified in MQTT Explorer: `status`
  `{"event":"heartbeat","uptime_s":…,"rssi":-55,"radio":true}` and `rig`
  `{"ok":true,"freq_hz":7088020,"band":"40m","mode":"LSB","tx":false}`.
- `OTA_PASS` is set in `secrets.h` (same as the mains monitor), so OTA
  uploads need it; COM flashing doesn't.
- **SPE amp follows band changes — verified 2026-11-14** (amp in standby).
  Polled wiring: pins 10, 3 (via 10 k / 20 k divider), 4 and 11. The amp's
  TTL CAT is **inverted** (idles low); `SPE_INVERT` runs UART1 inverted on
  both pins. The amp polls `IF;` about every 240 ms at 9600; the S3
  answers from the cached radio state.
- **All parts verified** (radio link, TCP CAT / Hamlib / WSJT-X / PTT, MQTT,
  SPE). Keyed up with the amp in operate on 3 bands 2026-11-14 — amp
  band matched each time. **Ready for service.**
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
| SPE TX data | S3 GPIO17 (UART1 TX, 3.3 V) | SPE DB15 pin 10 (RX TTL) | Amp input is 5 V TTL, **inverted polarity** (idles low). The S3's 3.3 V levels read fine (verified) |
| SPE RX data | SPE DB15 pin 3 (TX TTL, **5 V**) | S3 GPIO18 (UART1 RX) | Carries the amp's `IF;` polls (inverted, 9600). **Needs a divider** — pin 3 → 10 k → GPIO18, GPIO18 → 20 k → GND (as built): the S3 is not 5 V tolerant. Required in practice: the amp works polled |
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
- **Measured 2026-11-14:** in Kenwood TTL mode the amp polls **`IF;` every
  ~240 ms at 9600 baud, inverted polarity** (line idles low, start bit
  high — RS-232 sense at TTL levels), with ~3 ms between characters. Its
  input on pin 10 expects the same polarity: non-inverted pushes were
  ignored, inverted replies work. Listen-only (pin 3 open) with inversion
  is untested.

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
| SPE output | `src/spe.*` | UART1 Kenwood emulation, **inverted** (`SPE_INVERT`). Answers the amp's `IF;` polls (and `FA;` `AI;` `ID;`) from cache; also pushes `FA…;` + `IF…;` on change plus a 2 s keepalive. **Fail-safe:** sends nothing while state is invalid. `SPE_LOG` / `SPE_DIAG` switches for bench debugging |
| TCP CAT | `src/tcp_cat.*` | Port 4533, up to 3 clients. `FA;`/`IF;` from cache. Answered locally for Hamlib: `MD;` (mode digit from the cached IF), `FW;` → `FW0000;`, `PS;` → `PS1;`, `AI;` → `AI0;`; `AI` set commands are absorbed, never sent to the radio. Everything else forwarded to the radio via the queue; replies `?;` if the radio is absent |
| Main | `src/main.cpp` | WiFiManager (no restart on portal timeout — would cut the SPE feed), MQTT, ArduinoOTA, RGB status LED |

Tunables are in `include/config.h` (baud rates, pins, poll/stale timings,
push behaviour, TCP port).

**Status LED (on-board RGB):** green = radio OK · amber = USB up, no replies ·
red = no radio on USB · blinking blue = no Wi-Fi.

**Hamlib / WSJT-X:** rig model Kenwood TS-480 (2028), serial port / rig path
`rgo-spe-cat.local:4533` (network). PTT via CAT.

## MQTT

- Broker `<broker-ip>:1883` (`MQTT_HOST` in `secrets.h`), auth required; role `iot`, password in
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

OTA after first flash: `./ota.sh` (box on IoT VLAN; the UniFi rule allows
its call-back to the Mac on TCP 48266 only).

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
- [x] ~~Choose polled vs listen-only wiring; confirm which query the amp sends~~ — polled; amp sends `IF;` inverted at 9600
- [x] ~~Final check with the amp in operate~~ — keyed on 3 bands, amp followed (2026-11-14)
- [x] ~~How the S3 board enables 5 V on the OTG port's VBUS~~ — `USB-OTG` solder jumper on the back, behind the USB socket; bridged 2026-11-14 (it bypasses the diode between the native port's VBUS and the 5 V rail)
- [x] ~~Final power feed~~ — COM socket via a USB-A cable (it lacks USB-C CC resistors), or 5 V into 5Vin
- [x] ~~MQTT: put the `iot` password in `secrets.h`~~ — done; broker ACL grant `shack/rgo-spe-cat/#` added 2026-11-14
- [x] ~~Confirm `shack/rgo-spe-cat/status` and `/rig` arrive~~ — seen in MQTT Explorer 2026-11-14
- [x] ~~Set `OTA_PASS` in `secrets.h`~~ — done 2026-11-14
- [ ] Optional: small status web page (deferred; MQTT + LED cover it for now)

## Next steps

1. ~~Flash an S3~~ (done). Check the USB link: power the board from its 5V
   pin (or COM port), native USB → radio. LED goes green; `FA;` over TCP
   4533 returns the VFO.
2. ~~Test TCP CAT with Hamlib, WSJT-X and PTT via CAT~~ (done).
3. ~~Make the DB15 cable and bench test in standby~~ (done — amp follows).
4. ~~Key up with the amp in operate on a few bands~~ (done). ~~Box it up~~ (done 2026-11-15: printed, installed, audio wired direct with no pad, RTS PTT working).

## Known gotchas

- **The SPE's TTL CAT is inverted** (idles low). With a normal UART the
  S3 read its `IF;` polls as `62 5B 2E` (`b[.`) and the amp ignored the S3's
  frequency. Found with `SPE_DIAG 1` (times edges on GPIO18: 104 µs bits,
  idle 0). Fix: `SPE_INVERT true` → `HardwareSerial::begin(..., invert)`,
  which inverts both RX and TX. `SPE_LOG 1` logs each amp poll, and
  undecodable bytes in hex.

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
  `FW;` (filter width) gets no reply either. WSJT-X asks for it on every
  poll after `MD;`, so it timed out 4 × ~1 s, declared a rig failure and
  reconnected every ~9 s ("Test CAT goes green, then fails"). Answered
  locally as `FW0000;`. Set `CAT_TCP_LOG 1` in `config.h` to log every TCP
  command, reply and time on the console when chasing the next one.
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
- **The broker drops publishes it has no ACL grant for**, without an
  error: the login succeeds and nothing arrives. A new topic tree needs a
  `topic write` line under `user iot` in `/etc/mosquitto/aclfile` on
  noderedpi4, then `sudo systemctl reload mosquitto`.
- **Homebrew `pio` fails** with "Python version must be 3.10+" (it runs on
  Python 3.9). `flash.sh`, `monitor.sh` and `install.py` prefer
  `~/.platformio/penv/bin/pio`, which works.
- Opening the radio's FTDI port from a Mac can briefly raise DTR/RTS. The
  firmware forces both low right after enumeration; on the Mac, check the
  radio's DTR/RTS PTT/key setting before probing.

## What changed

- **2026-11-15** — **Repo made public** (Manoj: scrub IPs, then public).
  Shack addresses moved to the git-ignored `secrets.h` (`MQTT_HOST`,
  `OTA_HOST`) first; older commits still hold private-range LAN IPs, no
  passwords. Added to vu2cpl.com (Shack Firmware & Field Devices, top
  card). Write-up for the RGO ONE group is hosted at
  https://vu2cpl.com/projects/rgo-spe-cat/ (the card's Read more link). Photos of the finished box added: `docs/photos/`
  (front, inside), shown in README and BOX_PLAN.
- **2026-11-15** — **SPE CAT cable wired through the new box and tested:
  working** (Manoj). Box now fully in service: radio CAT, RX/TX audio, RTS
  PTT, SPE follow. As-built wiring diagram added: `docs/wiring.svg`, shown
  in BOX_PLAN.
- **2026-11-15** — PTT: CAT TX is display-only. RTS PTT added to the
  firmware (flashed by OTA) and working with menu 33 ON + menu 02 LINE IN
  ON; that is now the PTT method (VOX also works). TX level: Mac output at max
  gives ALC 1–2 dots (OK, no headroom). OTA now via `./ota.sh` (call-back pinned to TCP 48266;
  Manoj added the box to the UniFi IoT → Mac OTA rule).
- **2026-11-15** — Draft-7 box printed and installed. Radio CAT through it
  verified (TCP 4533: `FA` 7.0278 MHz LSB, `FB` live). **RX audio far too
  low** (WSJT-X ~0 dB at full Mac input gain): the 10 k / 1 k divider was
  Claude's unmeasured guess and the cable was never level-tested before it
  was closed. Fixed the same day: both RX resistors removed, LINE OUT now
  goes straight to the dongle mic input, WSJT-X shows ~25 dB (usable).
  RX level 35 dB with the radio preamp on. TX audio reaches the dongle
  output (headphone check) but the radio does not transmit when keyed over
  CAT — see "PTT via CAT does NOT work" above. (Later the same day: RTS
  PTT working, and the SPE CAT cable wired and tested — see below.)
- **2026-11-15** — `docs/BOX_PLAN.md` now has both full DB15 pinouts:
  RGO ONE ACC1 (manual §5.5) and SPE CAT (1.5K-FA manual §12.1), each
  marked with what the cable uses and which pins must stay open.
- **2026-11-15** — LED window in the lid is now a 4 mm hole at the
  measured LED centre: 23 mm from the box's outer left edge, 20 mm from the
  outer front (panel) edge. Draft 6's slot sat ~13 mm in and missed it.
- **2026-11-15** — PC cable now leaves through a 6 × 14 mm notch in the
  BACK wall, straight behind the dongle (Manoj cut this into the draft-6
  box). The cable no longer U-turns to the front panel, so extension
  sockets up to ~40 mm long fit; the front-panel notch is gone. Socket
  width (`ext_sock_w` 18) confirmed OK. A panel-mount USB-B pigtail
  (PSG03801) was considered and dropped: its 37 mm flange and ~45–50 mm
  female-A end would grow the box to ~135 × 100 mm.
- **2026-11-15** — Enclosure draft 7, after a draft-6 test fit failed:
  the S3 board slid around (foam tape on a rib held nothing), and the two
  1/8" plugs could not seat in the dongle because the 2.5 mm wall stood
  between plug body and jack. Now the dongle's jack end sits in a panel
  window, flush with the outside, with stop posts behind it. The board is
  boxed in by corner fences, the stop block and two lid fingers (module
  shield pad, USB-C socket bar), no tape. USB-C slot stays 7 mm (plugs
  seated fine in the test fit). Module shield 3.2 mm and press point 46 mm
  confirmed by Manoj; `ext_sock_w` is still CHECK. The draft-6 print was
  made usable by drilling out the IN/OUT holes.
- **2026-11-14** — Enclosure: S3 board measured 63.5 × 28 mm (with the
  antenna end); the LED is just behind the USB-C sockets, so the lid has a
  3.2 × 18 mm slot across the board there.
- **2026-11-14** — Enclosure: wires are soldered to the S3 header pins, so
  the board sits 12 mm above the floor (clears downward headers + joints).
- **2026-11-14** — Enclosure draft 6: real dongle sizes (28 × 29 × 11.3 mm
  body + 14 mm USB-A plug, jacks 12.4 mm apart at 6.35 mm up, mic on the
  left). Box
  107 × 75 × 27.8 mm. Looked at a USB-B panel lead (Pro Signal PSG03801)
  for the PC side: works, but its 37 mm flange and 48 mm A-socket end would
  grow the box to roughly 120 × 85 mm; kept the cable notch for now.
- **2026-11-14** — Enclosure draft 5: amp connector is now a **2.5 mm TRS
  panel jack** (tip = GPIO17 via 220 Ω → amp 10, ring = amp 3 → divider →
  GPIO18, sleeve = GND → amp 4; amp 11 joined to 4 in the DB15 hood).
  2.5 mm so it can't be confused with the 1/8" audio jacks. Box 101 × 79 ×
  27.8 mm.
- **2026-11-14** — Enclosure draft 4: amp panel connector DB15 → **DB9
  female** (only 3 wires: DB9 2 → amp 10, 3 ← amp 3, 5 GND → amp 4, amp
  11 joined to 4 in the DB15 hood). Box 121 × 79 × 27.8 mm.
- **2026-11-14** — Enclosure draft 3: shrunk to 129 × 79 × 27.8 mm (was
  137 × 83 × 36.8) — lower lid (in_h 23), parts packed closer. The panel
  DB15's 39 mm flange is now the main thing setting the length.
- **2026-11-14** — Enclosure draft 2: all connectors on ONE panel (RIG/PWR
  USB-C slot, IN/OUT = the CM108's own 1/8" jacks through the wall, AMP
  DB15 female, PC cable notch). The radio panel DB15 is gone: radio audio is
  now a separate cable (DB15 male on ACC1 with the 3 resistors in its hood →
  two 1/8" plugs), only 3 wires. 137 × 83 × 36.8 mm; dongle sizes still
  `CHECK`.
- **2026-11-14** — Enclosure first draft: `enclosure/rgo_box.scad` (125 ×
  105 × 36.8 mm, base + screw-down lid, M3 heat-set inserts). S3 USB-Cs
  through a back-wall slot, PC cable through a notch the lid closes, both
  DB15s on the end wall, zip-tie anchors for the dongle, LED window. Not
  printed: sizes marked `CHECK` need measuring first (see
  `enclosure/README.md`).
- **2026-11-14** — Box plan simplified (`docs/BOX_PLAN.md`): audio inside
  the box, DigiRig-style — CM108 dongle kept whole, 3 resistors to ACC1,
  no transformers or trimpots; levels set on the Mac. Charger power,
  3D-printed, DB15 male for the radio / female for the amp.

- **2026-11-14** — Started planning a box with a USB audio interface:
  `docs/BOX_PLAN.md` (CM108 card + 2 isolation transformers on the radio's
  ACC1 line in/out; PTT stays on CAT). Open: power, enclosure, connector
  genders. ACC1 pinout taken from the RGO ONE manuals (pins 9/10 LINE IN,
  11 LINE OUT, 8 PTT, 15 GND; V6 adds TTL CAT on 4–6).

- **2026-11-14** — Operate test: keyed up on 3 bands with the amp in
  operate; the amp's band matched every time. Project ready for service.

- **2026-11-14** — **SPE amp follows the radio.** The amp ignored the S3
  until the UART was inverted: its TTL CAT idles low. Edge timing on GPIO18
  (`SPE_DIAG`) showed 9600 baud, inverted, `IF;` every ~240 ms. Pin 3 is
  now wired through a 10 k / 20 k divider so the amp's polls are answered.
  Added `SPE_INVERT`, `SPE_LOG` (hex dump of undecodable bytes) and
  `SPE_DIAG`; `SPE_PUSH_IF` now on.

- **2026-11-14** — **MQTT connected.** `iot` and OTA passwords in the local
  `secrets.h`; the broker accepts the login. The broker silently drops
  `iot` publishes outside its ACL, so `topic write shack/rgo-spe-cat/#` was
  added on noderedpi4 and mosquitto reloaded (`vu2cpl-shack` 67e5269).
  Both topics confirmed in MQTT Explorer.

- **2026-11-14** — **WSJT-X stays connected; Test PTT works.** The radio
  never answers `FW;`; WSJT-X timed out on it and reconnected every ~9 s.
  The TCP server now answers `FW0000;`. Added `CAT_TCP_LOG` (off by
  default) to log TCP commands with reply and timing; it found this one.

- **2026-11-14** — PTT via CAT verified over TCP (`rigctl T 1` / `T 0`; the
  radio's IF TX digit follows). WSJT-X lag measured: bounded by its 1 s
  minimum poll, not the S3.

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
