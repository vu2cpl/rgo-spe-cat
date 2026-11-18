# DJ4WD's patched Hamlib for the RGO ONE (reference copy)

Patched Hamlib 4.7.1 by Joerg DJ4WD, posted in the RGO-ONE groups.io files
section (`hamlib-4.7.1-rgo-one-patch-20261007.zip`, build 2026-10-09, backend
20261007.0). It adds native backends: model 43001 "RGO ONE V6" and 43002
"RGO ONE V1-V5", manufacturer "LZ2JR".

Kept here for reference only:

- `README.txt` — DJ4WD's install notes, unchanged.
- `rgo-one-*.png` — his WSJT-X settings screenshots (renamed from the originals).

The Windows binaries (`libhamlib-4.dll`, `libhamlib-5.dll`, `libwinpthread-1.dll`,
`rigctl.exe`, `rigctld.exe`, ~60 MB) are not copied. They do not run on the Mac
or the Pi, and the full archive is in the groups.io files section.

Why this project does not use it: the S3 presents a TS-480 on TCP 4533, so stock
Hamlib model 2028 works. The V1-V5 backend's PTT is `TX0;` / `RX;`, which gives
display-only TX on our radio (no RF). RTS PTT stays. See HANDOVER "Known gotchas".
