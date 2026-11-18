# DJ4WD's patched Hamlib for the RGO ONE (reference copy)

Patched Hamlib 4.7.1 by Joerg DJ4WD, from the RGO-ONE groups.io files section.
It adds native backends: model 43001 "RGO ONE V6" and 43002 "RGO ONE V1-V5",
manufacturer "LZ2JR", backend version 20261007.0.

## What is here

| File | Source | What it is |
| --- | --- | --- |
| `rgo-one-hamlib.patch` | source zip `hamlib-4.7.1-rgo-one-patch-20261007.zip` | Patch for Hamlib tag 4.7.1: backends in `rigs/rgo/`, their READMEs (DE/EN), and small core changes (`rig.c`, `rig.h`, `riglist.h`, `register.c`, `configure.ac`) |
| `README-source.txt` | source zip | Build steps for Linux / Pi (apply patch, autotools) and the test script options |
| `testscripte/` | source zip | DJ4WD's test scripts (`test_rgo_one.py` etc.). `--ptt` and `--tune` transmit |
| `README-windows.txt` | Windows zip (2026-10-09) | Install notes for the prebuilt WSJT-X / JTDX DLLs |
| `rgo-one-*.png` | Windows zip | WSJT-X settings screenshots (renamed) |

Not copied: the Windows DLLs and `.exe` files (~60 MB), and the source zip's
`hamlib-4.7.1/` folder, which holds the same changes as the patch in full-file form.

Build on a Pi or Mac (not done here):

```bash
git clone https://github.com/Hamlib/Hamlib.git && cd Hamlib && git checkout tags/4.7.1
patch -p1 < /path/to/rgo-one-hamlib.patch
autoreconf -fi && ./configure && make
```

## Why this project does not use it

- Our radio is a **V1-V5** (FT232R, `ID020`). DJ4WD's own README says the
  V1-V5 backend was not tested against real V1-V5 hardware. It is built from
  Don WB8YQJ's command list (firmware 2.51a). His hardware tests are on a V6.
- V1-V5 PTT is `TX0;` / `RX;` only (no `TX2`). On our radio `TX0;` gives
  display-only TX: no RF, amp not keyed (2026-11-15). RTS PTT stays.
- The S3 already presents a TS-480 on TCP 4533, so stock Hamlib model 2028 works.
- His README confirms our menu 33 gotcha: with RTS-as-PTT on, opening the
  serial port on Linux asserts RTS and keys the radio. Our S3 firmware drives
  RTS low right after enumeration.
