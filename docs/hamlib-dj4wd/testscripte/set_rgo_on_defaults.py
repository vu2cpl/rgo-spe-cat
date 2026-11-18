#!/usr/bin/env python3
"""Setzt den RGO ONE V6 per rigctl auf einen definierten Ursprungszustand.

Alle Sollwerte stehen als Variablen im Abschnitt SOLLWERTE. None = diese
Einstellung wird nicht angefasst. Das Script sendet NIE (kein PTT, kein
KY/PB/TX); es setzt nur Pegel, Funktionen, Frequenz, Mode und Split.
NICHT setzbar per CAT: die FLT-Taste (Anzeige "NAR", variabler Filter);
das CAT-Manual 1.04 kennt dafuer keinen Befehl. Von Hand am Geraet einstellen.

Ablauf: laeuft rigctld schon auf HOST:PORT, wird er benutzt, sonst wird er
gestartet und am Ende wieder beendet. Gesetzt wird per rigctl, danach wird
jeder Wert zurueckgelesen und verglichen.

  python3 -I set_rgo_on_defaults.py            # setzen + pruefen
  python3 -I set_rgo_on_defaults.py --check    # nur lesen und vergleichen
  python3 -I set_rgo_on_defaults.py --dry-run  # nur anzeigen, was gesetzt wuerde
"""
import argparse
import socket
import subprocess
import sys
import time

# ----------------------------------------------------------------- SOLLWERTE
# Stand 2026-10-07 (Backend 20261007.0, FW 1.10). None = nicht setzen.

VFO         = "VFOA"
FREQ_HZ     = 7030000
MODE        = "CW"
PASSBAND_HZ = 200
SPLIT       = False       # True/False

# Pegel (Hamlib-Namen, 0.0-1.0 bzw. ganze Zahlen laut Caps)
RFPOWER      = 0.02       # 0.02 = 1 W (Maximum 50 W = 1.0)
MICGAIN      = 0.1
MONITOR_GAIN = 0.1
NB_LEVEL     = 0.3125
PREAMP       = 0
ATT          = 0
COMP         = 0.0
VOXGAIN      = 0.0
VOXDELAY     = 5
BKIN_DLYMS   = 500
KEYSPD       = 20
AGC          = 2          # 0=aus 2=schnell 3=langsam
RF_GAIN      = 1.0
AF_GAIN      = 0.0        # AG ist per CAT nicht lesbar: kein Readback
SQL          = 0.0        # SQ ist per CAT nicht lesbar: kein Readback
METER        = "SWR"      # SWR, COMP oder ALC (RM2/RM3/RM1)

# Funktionen an/aus
F_NB    = False
F_FBKIN = False
F_MON   = True
F_LOCK  = False
F_RIT   = False
F_XIT   = False
F_TUNER = True

RIT_OFFSET_HZ = 0
XIT_OFFSET_HZ = 0

# Ab dieser Leistung wird vor dem Setzen nachgefragt (ausser mit --yes)
RFPOWER_CONFIRM_ABOVE = 0.2

# Meter: Name -> (Hamlib RIG_METER_*, RGO RM-Ziffer)
METER_CODES = {"SWR": (1, 2), "COMP": (2, 3), "ALC": (4, 1)}
# Pegel, die die Firmware nicht zuruecklesen laesst (nur Setzen wird geprueft)
UNREADABLE = {"AF", "SQL"}

# ------------------------------------------------------------- Verbindung
DEFAULT_DEVICE = "/dev/ttyACM0"
DEFAULT_BAUD = 9600
DEFAULT_HOST = "localhost"
DEFAULT_PORT = 4532
RIGCTL = "/usr/local/bin/rigctl"
RIGCTLD = "/usr/local/bin/rigctld"


class Rig:
    def __init__(self, host, port):
        self.target = f"{host}:{port}"

    def run(self, *args):
        p = subprocess.run([RIGCTL, "-m", "2", "-r", self.target, *args],
                           capture_output=True, text=True, timeout=15)
        out = [ln for ln in p.stdout.splitlines() if ln.strip()]
        bad = p.returncode != 0 or any("error" in ln.lower() or ln.startswith("RPRT -")
                                       for ln in out)
        return out, bad

    def get_level(self, name):
        out, bad = self.run("l", name)
        return None if bad or not out else float(out[0])

    def get_func(self, name):
        out, bad = self.run("u", name)
        return None if bad or not out else int(out[0])


def port_open(host, port):
    try:
        with socket.create_connection((host, port), timeout=1):
            return True
    except OSError:
        return False


def start_rigctld(device, baud, port):
    proc = subprocess.Popen([RIGCTLD, "-m", "43001", "-r", device, "-s", str(baud),
                             "-t", str(port)],
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(40):
        if proc.poll() is not None:
            sys.exit("rigctld konnte nicht gestartet werden (TRX aus? Port belegt?)")
        if port_open(DEFAULT_HOST, port):
            return proc
        time.sleep(0.25)
    proc.terminate()
    sys.exit("rigctld antwortet nicht")


def build_items():
    """(Bezeichnung, Art, Name, Sollwert, Toleranz). Reihenfolge = Setzreihenfolge."""
    items = []
    # Leistung zuerst: nie hoeher als noetig stehen lassen
    levels = [
        ("RFPOWER", RFPOWER, 0.011), ("MICGAIN", MICGAIN, 0.011),
        ("MONITOR_GAIN", MONITOR_GAIN, 0.011), ("NB", NB_LEVEL, 0.06),
        ("PREAMP", PREAMP, 0), ("ATT", ATT, 0), ("COMP", COMP, 0.06),
        ("VOXGAIN", VOXGAIN, 0.06), ("VOXDELAY", VOXDELAY, 0),
        ("BKIN_DLYMS", BKIN_DLYMS, 0), ("KEYSPD", KEYSPD, 0), ("AGC", AGC, 0),
        ("RF", RF_GAIN, 0.011), ("AF", AF_GAIN, 0.011), ("SQL", SQL, 0.011),
    ]
    funcs = [("LOCK", F_LOCK), ("NB", F_NB), ("FBKIN", F_FBKIN), ("MON", F_MON),
             ("RIT", F_RIT), ("XIT", F_XIT), ("TUNER", F_TUNER)]
    for name, val, tol in levels[:1]:
        items.append((f"Level {name}", "level", name, val, tol))
    items.append(("VFO", "vfo", None, VFO, 0))
    items.append(("Mode", "mode", None, MODE, 0))
    items.append(("Frequenz", "freq", None, FREQ_HZ, 0))
    items.append(("Split", "split", None, SPLIT, 0))
    for name, val, tol in levels[1:]:
        items.append((f"Level {name}", "level", name, val, tol))
    items.append(("Meter", "meter", None, METER, 0))
    for name, val in funcs:
        items.append((f"Funktion {name}", "func", name, val, 0))
    items.append(("RIT-Offset", "rit", None, RIT_OFFSET_HZ, 0))
    items.append(("XIT-Offset", "xit", None, XIT_OFFSET_HZ, 0))
    return [i for i in items if i[3] is not None]


def apply_item(rig, kind, name, val):
    if kind == "level":
        return rig.run("L", name, str(val))[1]
    if kind == "func":
        return rig.run("U", name, "1" if val else "0")[1]
    if kind == "mode":
        return rig.run("M", val, str(PASSBAND_HZ))[1]
    if kind == "vfo":
        return rig.run("V", val)[1]
    if kind == "meter":
        return rig.run("L", "METER", str(METER_CODES[val][0]))[1]
    if kind == "freq":
        return rig.run("F", str(val))[1]
    if kind == "split":
        return rig.run("S", "1" if val else "0", "VFOA")[1]
    if kind == "rit":
        return rig.run("J", str(val))[1]
    if kind == "xit":
        return rig.run("Z", str(val))[1]
    return True


def read_item(rig, kind, name):
    """Gibt den gelesenen Wert zurueck (None = nicht lesbar)."""
    if kind == "level":
        return rig.get_level(name)
    if kind == "func":
        v = rig.get_func(name)
        return None if v is None else bool(v)
    if kind == "mode":
        out, bad = rig.run("m")
        return None if bad or len(out) < 2 else (out[0], int(out[1]))
    if kind == "vfo":
        out, bad = rig.run("v")
        return None if bad or not out else out[0].strip()
    if kind == "meter":
        out, bad = rig.run("w", "RM;")
        raw = out[0].replace("\x00", "").strip() if out else ""
        return None if bad or not raw.startswith("RM") or len(raw) < 3 else int(raw[2])
    if kind == "freq":
        out, bad = rig.run("f")
        return None if bad or not out else int(float(out[0]))
    if kind == "split":
        out, bad = rig.run("s")
        return None if bad or not out else out[0].strip() == "1"
    if kind in ("rit", "xit"):
        out, bad = rig.run("j" if kind == "rit" else "z")
        return None if bad or not out else int(float(out[0]))
    return None


def matches(kind, want, got, tol):
    if got is None:
        return False
    if kind == "meter":
        return got == METER_CODES[want][1]
    if kind == "mode":
        return got[0] == want and got[1] == PASSBAND_HZ
    if kind == "level":
        return abs(float(got) - float(want)) <= tol
    return got == want


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--check", action="store_true", help="nur lesen und vergleichen")
    ap.add_argument("--dry-run", action="store_true", help="nur anzeigen")
    ap.add_argument("--yes", action="store_true", help="keine Rueckfrage bei hoher Leistung")
    ap.add_argument("-r", "--device", default=DEFAULT_DEVICE)
    ap.add_argument("-s", "--baud", type=int, default=DEFAULT_BAUD)
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    items = build_items()

    if args.dry_run:
        for label, kind, name, val, tol in items:
            print(f"  {label:<22} -> {val}")
        return 0

    if (not args.check and RFPOWER is not None and RFPOWER > RFPOWER_CONFIRM_ABOVE
            and not args.yes):
        if input(f"RFPOWER {RFPOWER} ({RFPOWER * 50:.0f} W) ist hoch. Fortfahren? [j/N] "
                 ).strip().lower() != "j":
            print("Abgebrochen.")
            return 2

    proc = None
    if port_open(args.host, args.port):
        print(f"rigctld auf {args.host}:{args.port} wird benutzt.")
    else:
        print(f"Starte rigctld ({args.device}, {args.baud} Baud) ...")
        proc = start_rigctld(args.device, args.baud, args.port)

    rig = Rig(args.host, args.port)
    failed = 0
    try:
        for label, kind, name, val, tol in items:
            set_err = False
            if not args.check:
                set_err = apply_item(rig, kind, name, val)
                time.sleep(0.15)
            if kind == "level" and name in UNREADABLE:
                ok = not set_err and not args.check
                if not ok:
                    failed += 1
                print(f"  [{'GESETZT' if ok else 'FEHLER'}] {label:<22} soll={val} "
                      f"(nicht lesbar, kein Readback)")
                continue
            got = read_item(rig, kind, name)
            ok = matches(kind, val, got, tol)
            if not ok:
                failed += 1
            note = " (Setzen meldete Fehler)" if set_err else ""
            print(f"  [{'OK' if ok else 'ABWEICHUNG'}] {label:<22} soll={val} ist={got}{note}")
    finally:
        if proc:
            proc.terminate()
            proc.wait(timeout=5)
            print("rigctld beendet.")

    print(f"\nErgebnis: {len(items) - failed}/{len(items)} wie Sollwert"
          + ("" if not failed else f", {failed} Abweichung(en)"))
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
