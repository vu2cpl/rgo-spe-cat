# Sound cards: C-Media USB dongles

The box's audio interface is a C-Media CM108-class USB sound dongle. It
carries RX audio from the radio's ACC1 LINE OUT to the PC, and TX audio
from the PC to ACC1 LINE IN. Wiring and levels are in
[`BOX_PLAN.md`](BOX_PLAN.md).

Two dongles with the same chip ID (`0D8C:0014`) have been used on the
Mac. They differ in the name they report, and apps select by that name:

| | Dongle A: tested in the box | Dongle B: detected 2026-11-17 |
|---|---|---|
| Name in macOS / WSJT-X | `USB Audio Device` | `Cable Creation` |
| Manufacturer string | C-Media Electronics Inc. | C-Media Electronics Inc. |
| Vendor ID : Product ID | `0D8C:0014` | `0D8C:0014` |
| Device version (bcdDevice) | not recorded | `0x0100` |
| USB speed | not recorded (CM108-class: full speed) | USB 1.1 full speed, 12 Mb/s |
| Serial number | not recorded | none |
| Audio interfaces (CoreAudio UID suffix) | `2,1` | `2,1` |
| Input | mono, 16-bit LPCM, 48 kHz | mono, 16-bit LPCM, 44.1 / 48 kHz |
| Output | stereo, 16-bit LPCM, 48 kHz | stereo, 16-bit LPCM, 44.1 / 48 kHz |
| Mic gain range | not recorded | −12 to +23 dB |
| Output volume range | not recorded | −37 to 0 dB |
| Mac settings last saved | input max, output max, not muted (as used for the 2026-11-15 levels) | now: input −2 dB, output −10 dB, not muted |
| Body size | 28 × 29 × 11.3 mm + 14 mm USB plug, jacks 12.4 mm apart, mic left | not measured |
| Shell | black aluminium, labelled "USB Audio Adapter" | not recorded |
| Used for | All on-air tests 2026-11-15: RX ~25 dB (35 dB with radio preamp), TX ALC 1–2 dots at full Mac output | Not tested on the radio yet |
| Saved in | `WSJT-X.ini` and `JTDX-VU - RGO one.ini` (Sound In/Out = `USB Audio Device`) | No app config yet |

Dongle A is not plugged in, so its column comes from the repo docs and
from what macOS cached the last time it was connected
(`/Library/Preferences/Audio/com.apple.audio.DeviceSettings.plist`).
"Not recorded" fields need dongle A plugged in to read.


A CM108-class chip reports its name from its own EEPROM, so the
different names mean different physical dongles. Dongle A was not
plugged into the Mac when dongle B was detected.

**If dongle B replaces dongle A:**

- Pick `Cable Creation` as Sound In and Sound Out in WSJT-X / JTDX. The
  saved `USB Audio Device` setting will not find it.
- Set Mac input and output to max, as with dongle A, then measure the
  levels again (RX dB with antenna on and off, TX ALC). Mic
  gain and output level can differ between dongle makes, so the 2026-11-15
  figures may not carry over.
- Check its size before fitting it in the box. The enclosure cradle is
  cut for dongle A (28 × 29 × 11.3 mm body, jacks 12.4 mm apart).

## Dongle B as detected on the Mac (2026-11-17)

Read from the Mac mini (macOS) with the dongle plugged in, using
`system_profiler SPUSBHostDataType SPAudioDataType`, `ioreg` and a
CoreAudio query.

### USB

| Field | Value |
|---|---|
| Product name | `Cable Creation` |
| Manufacturer | C-Media Electronics Inc. |
| Vendor ID : Product ID | `0x0D8C : 0x0014` (CM108-class) |
| Device version (bcdDevice) | `0x0100` |
| USB version (bcdUSB) | 1.1 (`0x0110`) |
| Link speed | Full speed, 12 Mb/s |
| Serial number | None (not provided) |
| Location ID (this Mac) | `0x00133000`, behind the GenesysLogic USB2.1 hub chain |

### CoreAudio

| Field | Value |
|---|---|
| Device name (what apps show) | **`Cable Creation`** |
| Device UID | `AppleUSBAudioEngine:C-Media Electronics Inc.:Cable Creation:133000:2,1` |
| Input | 1 channel (mono), 16-bit |
| Output | 2 channels (stereo), 16-bit |
| Sample rates | 44.1 kHz and 48 kHz (both directions) |
| Current rate | 48 kHz |
| Driver | Built-in USB Audio class driver; no install needed |

It is the only C-Media device on this Mac. The other audio devices listed
(MorCoNI, Rogue Amoeba Loopback, AetherSDR DAX, CommonRadioAudio) are
unrelated to this box.

## Notes

- **Name to pick in WSJT-X:** Settings → Audio → Input and Output =
  `Cable Creation` for dongle B, `USB Audio Device` for dongle A. Input channel Mono (or Left), output channel Mono or
  Left. Keep the Mac's Audio MIDI Setup rate at 48 kHz.
- **The UID contains the USB location (`133000`).** Moving the dongle to
  another USB port or hub changes the UID. WSJT-X stores the device by
  name, so it keeps working. Apps that store the UID may lose the
  selection after a port change; pick the device again.
- **No serial number.** Two identical dongles on one Mac can only be told
  apart by location ID. Keep one per Mac, or keep each on a fixed port.
- **USB 1.1 full speed** is normal for this chip and is plenty for one
  mono 48 kHz input and one stereo 48 kHz output.
- **VOX caution still applies:** if radio VOX is on, any Mac sound routed
  to the dongle in use keys the transmitter. Keep system sounds off it.

## How to check it again

```bash
system_profiler SPUSBHostDataType | grep -B2 -A10 -i '0x0d8c'
```

```bash
system_profiler SPAudioDataType | grep -A8 -iE 'cable creation|usb audio device'
```

On Linux (for example a Pi), it shows as `0d8c:0014` in `lsusb` and as a
USB audio card in `aplay -l` / `arecord -l`. The card number depends on
what else is plugged in.
