# Sound card: C-Media USB dongle ("Cable Creation")

The box's audio interface is a C-Media CM108-class USB sound dongle. It
carries RX audio from the radio's ACC1 LINE OUT to the PC, and TX audio
from the PC to ACC1 LINE IN. Wiring and levels are in
[`BOX_PLAN.md`](BOX_PLAN.md). This page records how the dongle appears
on the Mac.

## As detected on the Mac (2026-11-17)

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
  `Cable Creation`. Input channel Mono (or Left), output channel Mono or
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
  to this device keys the transmitter. Keep system sounds off it.

## How to check it again

```bash
system_profiler SPUSBHostDataType | grep -A10 -i 'cable creation'
```

```bash
system_profiler SPAudioDataType | grep -A8 -i 'cable creation'
```

On Linux (for example a Pi), it shows as `0d8c:0014` in `lsusb` and as a
USB audio card in `aplay -l` / `arecord -l`. The card number depends on
what else is plugged in.
