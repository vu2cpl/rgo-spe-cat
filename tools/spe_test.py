#!/usr/bin/env python3
"""Bench-test the SPE Expert's Kenwood CAT input from a Mac/Pi, no ESP32 needed.

The script plays the radio's part through a USB-serial cable on the amp's CAT
DB15, the same job the ESP32 will do.

  sniff     print everything the amp sends (shows whether it polls, and what)
  emulate   act as a Kenwood TS-480: answer FA;/IF;/ID;/AI; and push FA…; on
            each change. Steps through the HF bands so you can watch the amp
            follow, or holds one frequency with --freq.

Usage (pyserial is in PlatformIO's penv):
  ~/.platformio/penv/bin/python tools/spe_test.py sniff   [--port P] [--baud 9600]
  ~/.platformio/penv/bin/python tools/spe_test.py emulate [--port P] [--baud 9600]
        [--freq 14074000] [--step 5] [--mode 2] [--push-if]

Wiring (DB15 on the amp):
  5 V TTL cable : cable TX → pin 10 (RX TTL), cable RX ← pin 3 (TX TTL),
                  GND ↔ pin 4, pin 11 (KEN TTL) → GND
  RS-232 cable  : cable TX → pin 1 (RX 232), cable RX ← pin 9 (TX 232),
                  GND ↔ pin 4, pin 11 open
Opening a port can toggle DTR/RTS; this script drives both low.
"""
import argparse
import glob
import sys
import time

import serial

# One frequency per HF band (Hz), roughly the FT8 spots.
BANDS = [
    ("160m", 1840000), ("80m", 3573000), ("40m", 7074000), ("30m", 10136000),
    ("20m", 14074000), ("17m", 18100000), ("15m", 21074000), ("12m", 24915000),
    ("10m", 28074000), ("6m", 50313000),
]


def pick_port(port):
    if port:
        return port
    ports = sorted(glob.glob("/dev/cu.usbserial*") + glob.glob("/dev/cu.usbmodem*")
                   + glob.glob("/dev/ttyUSB*") + glob.glob("/dev/ttyACM*"))
    if not ports:
        sys.exit("No USB-serial ports found.")
    if len(ports) == 1:
        return ports[0]
    for i, p in enumerate(ports, 1):
        print(f"  {i}) {p}")
    return ports[int(input("Port number: ")) - 1]


def open_port(port, baud):
    s = serial.Serial()
    s.port, s.baudrate, s.timeout = port, baud, 0.05
    s.dtr = False
    s.rts = False
    s.open()
    return s


def fa(freq):
    return f"FA{freq:011d};"


def if_frame(freq, mode, tx=False):
    # TS-480 IF; — same layout the RGO ONE returns (see src/rig.cpp).
    # freq(11) 5sp RIT(-0000) RIT-on XIT-on mem(3) TX mode VFO scan split tone tone#(2) sp
    return (f"IF{freq:011d}" + " " * 5 + "-0000" + "0" + "0" + "000"
            + ("1" if tx else "0") + str(mode) + "0" + "0" + "0" + "0" + "00" + " ;")


def ts():
    return time.strftime("%H:%M:%S")


def sniff(s):
    print(f"[{ts()}] sniffing {s.port} @ {s.baudrate} — Ctrl-C to stop")
    buf = b""
    while True:
        data = s.read(256)
        if not data:
            continue
        buf += data
        while b";" in buf:
            msg, buf = buf.split(b";", 1)
            print(f"[{ts()}] amp → {msg.decode(errors='replace')};")
        if len(buf) > 64:
            print(f"[{ts()}] raw  → {buf!r}  (no ';' — wrong baud or not Kenwood?)")
            buf = b""


def emulate(s, freq, step, mode, push_if):
    seq = list(BANDS) if freq is None else [("fixed", freq)]
    idx, last_change, last_push = 0, 0.0, 0.0
    cur = seq[0][1]
    print(f"[{ts()}] emulating TS-480 on {s.port} @ {s.baudrate} — Ctrl-C to stop")
    buf = b""

    def push(reason):
        out = fa(cur) + (if_frame(cur, mode) if push_if else "")
        s.write(out.encode())
        print(f"[{ts()}] → amp {out}  ({reason})")

    push(seq[0][0])
    last_push = last_change = time.time()
    while True:
        data = s.read(256)
        if data:
            buf += data
            while b";" in buf:
                cmd, buf = buf.split(b";", 1)
                cmd = cmd.decode(errors="replace").strip() + ";"
                reply = {"FA;": fa(cur), "IF;": if_frame(cur, mode),
                         "ID;": "ID020;", "AI;": "AI0;"}.get(cmd)
                print(f"[{ts()}] amp → {cmd}" + (f"   reply {reply}" if reply else "   (ignored)"))
                if reply:
                    s.write(reply.encode())
        now = time.time()
        if len(seq) > 1 and now - last_change >= step:
            idx = (idx + 1) % len(seq)
            cur = seq[idx][1]
            last_change = now
            push(f"band → {seq[idx][0]}")
            last_push = now
        elif now - last_push >= 2.0:
            push("keepalive")
            last_push = now


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("action", choices=["sniff", "emulate"])
    ap.add_argument("--port")
    ap.add_argument("--baud", type=int, default=9600)
    ap.add_argument("--freq", type=int, help="hold this frequency (Hz) instead of stepping bands")
    ap.add_argument("--step", type=float, default=5.0, help="seconds per band when stepping")
    ap.add_argument("--mode", type=int, default=2, help="Kenwood mode digit (1 LSB, 2 USB, 3 CW)")
    ap.add_argument("--push-if", action="store_true", help="also push IF frames")
    a = ap.parse_args()
    s = open_port(pick_port(a.port), a.baud)
    try:
        if a.action == "sniff":
            sniff(s)
        else:
            emulate(s, a.freq, a.step, a.mode, a.push_if)
    except KeyboardInterrupt:
        print()
    finally:
        s.close()


if __name__ == "__main__":
    main()
