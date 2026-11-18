#!/usr/bin/env python3
"""
RGO ONE V6 CAT Command Test Suite
Tests all documented CAT commands via rigctld + rigctl.

Usage:
    python3 test_rgo_one.py [options]

Examples:
    python3 test_rgo_one.py -r /dev/ttyACM0 -s 9600
    python3 test_rgo_one.py -r /dev/ttyACM0 -s 9600 --ptt    # with PTT (transmits!)
    python3 test_rgo_one.py -r /dev/ttyACM0 -s 9600 --tune   # with antenna tuner tune (TX2, transmits!)
    python3 test_rgo_one.py -r /dev/ttyACM0 -s 9600 --test-mem  # also attempt MR/MW channel test
    python3 test_rgo_one.py -r /dev/ttyACM0 -s 9600 --test-if-frame  # also run raw CAT / IF-frame test
    python3 test_rgo_one.py --port 4532                       # use running rigctld

The default run covers only the "normal" CAT functions that go through the
standard Hamlib get/set API. Two categories are opt-in and disabled by
default:

  --test-mem        MR/MW channel read/write test (test_channel). MR/MW have
                     been observed to leave the rig in memory mode on some
                     firmware versions, with no confirmed CAT command to exit
                     it again (only the M/V button on the rig does -- see
                     CLAUDE.md). The read-only MC status check (test_mem)
                     always runs regardless -- it is confirmed safe.

  --test-if-frame   Raw CAT / IF-frame test (test_raw_cat: AI/FS/PB). These
                     commands have no Hamlib API mapping, so the test sends
                     raw CAT strings and manually parses the raw response
                     frames instead of using the normal get/set calls.

If rigctld is not yet running it will be started automatically.
Commands are sent to rigctld via "rigctl -m 2" (NET rigctl).
"""

import argparse
import datetime
import math
import os
import subprocess
import sys
import time
import traceback

DEFAULT_MODEL   = "43001"
DEFAULT_DEVICE  = "/dev/ttyACM0"
DEFAULT_BAUD    = "9600"
DEFAULT_HOST    = "localhost"
DEFAULT_PORT    = 4532
DEFAULT_RIGCTLD = "/usr/local/bin/rigctld"
DEFAULT_RIGCTL  = "/usr/local/bin/rigctl"

# Backend version expected after rebuild
EXPECTED_BACKEND_VERSION = "20261007.0"
# rigctld binary: minimum mtime for current build
EXPECTED_BUILD_AFTER = datetime.datetime(2026, 10, 7, 0, 0, 0)

FLOAT_TOL = 0.025   # 1.25 steps at 50-step resolution (PC)


class RigCtl:
    """Sends commands to rigctld via 'rigctl -m 2' subprocess."""

    def __init__(self, host, port, rigctl_bin=DEFAULT_RIGCTL):
        self.addr = f"{host}:{port}"
        self.bin  = rigctl_bin
        self._base = [rigctl_bin, "-m", "2", "-r", self.addr]

    def _run(self, *args, timeout=10):
        try:
            r = subprocess.run(
                self._base + [str(a) for a in args],
                capture_output=True, text=True, timeout=timeout,
            )
            return r.returncode, r.stdout.strip()
        except subprocess.TimeoutExpired:
            return -1, ""

    def get(self, *args):
        """Get command. Returns (value_str, code); None on error."""
        code, out = self._run(*args)
        if code != 0:
            return None, code
        # rigctl writes "error = ..." to stdout while exit code stays 0
        if "error =" in out or out.lower().startswith("error"):
            return None, -2
        return out, 0

    def set(self, *args):
        """Set command. Returns return_code."""
        code, out = self._run(*args)
        if code != 0:
            return code
        if "error =" in out or out.lower().startswith("error"):
            return -2
        return 0

    def send_no_response(self, cmd, timeout=2):
        """Send a raw CAT set command that produces no rig response.

        For Kenwood set commands without a response (e.g. FS0; FS1;),
        rigctld waits indefinitely for a ';'-terminated reply that never arrives.
        We give the subprocess a short timeout and treat TimeoutExpired as success --
        the bytes were delivered to the rig, which processed them silently.
        After calling this, sleep briefly before the next command so rigctld
        detects the client disconnect and is ready for the next connection.
        """
        try:
            subprocess.run(self._base + ["w", cmd],
                           capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired:
            pass  # expected: rig does not respond to set commands


class TestSuite:
    def __init__(self, rig, delay=0.5):
        self.rig     = rig
        self.delay   = delay    # pause between set and get (seconds)
        self.passed  = []
        self.failed  = []
        self.skipped = []

    def ok(self, name, detail=""):
        suffix = f"  ({detail})" if detail else ""
        print(f"  [OK]   {name}{suffix}")
        self.passed.append(name)

    def fail(self, name, detail=""):
        suffix = f"  -- {detail}" if detail else ""
        print(f"  [FAIL] {name}{suffix}")
        self.failed.append((name, detail))

    def skip(self, name, reason=""):
        suffix = f"  ({reason})" if reason else ""
        print(f"  [SKIP] {name}{suffix}")
        self.skipped.append(name)

    # ---------------------------------------------------------------- helpers

    def _set_get_float(self, name, set_args, get_args, set_val, expected, tol=FLOAT_TOL):
        code = self.rig.set(*set_args, f"{set_val:.6f}")
        if code != 0:
            self.fail(name, f"set {set_args} {set_val:.3f} -> error {code}")
            return False
        if self.delay > 0:
            time.sleep(self.delay)
        val, code = self.rig.get(*get_args)
        if code != 0:
            self.fail(name, f"get {get_args} -> error {code}")
            return False
        try:
            got = float(val)
        except (TypeError, ValueError):
            self.fail(name, f"unexpected response: {val!r}")
            return False
        if math.isnan(got):
            self.fail(name, "NaN received (firmware/implementation error?)")
            return False
        if abs(got - expected) > tol:
            self.fail(name, f"set={set_val:.3f}, expected~{expected:.3f}, got={got:.6f}")
            return False
        self.ok(name, f"{got:.4f}")
        return True

    def _set_get_int(self, name, set_args, get_args, set_val, expected=None):
        if expected is None:
            expected = set_val
        code = self.rig.set(*set_args, set_val)
        if code != 0:
            self.fail(name, f"set {set_args} {set_val} -> error {code}")
            return False
        if self.delay > 0:
            time.sleep(self.delay)
        val, code = self.rig.get(*get_args)
        if code != 0:
            self.fail(name, f"get {get_args} -> error {code}")
            return False
        try:
            got = int(val.split()[0])
        except (TypeError, ValueError, AttributeError):
            self.fail(name, f"unexpected response: {val!r}")
            return False
        if got != expected:
            self.fail(name, f"set={set_val}, expected={expected}, got={got}")
            return False
        self.ok(name, str(got))
        return True

    @staticmethod
    def _parse_if_frame(raw):
        """Parse a TS-480/RGO ONE IF frame.

        Format (0-based positions in the full string):
          [0-1]  "IF"
          [2-12] VFO A frequency, 11 digits (Hz)
          [13]   space
          [14-22] RIT/XIT offset area (kenwood.c: memcpy(&info[17], 6))
          [23]   XIT on/off
          [24]   RIT on/off
          [25]   (padding / memory)
          [26-27] memory channel (2 digits)
          [28]   TX state  (0=RX, 1=TX)   -- kenwood.c info[28]
          [29]   mode      (1-7)           -- kenwood.c info[29]
          ...

        Returns (freq_hz, mode, tx_state) or None on parse error.
        mode: 1=LSB 2=USB 3=CW 4=FM 5=AM 6=Digi 7=CW-R
        tx_state: 0=RX 1=TX
        """
        # rigctl may append a trailing \x00 -- strip it along with ; and whitespace
        s = raw.replace('\x00', '').rstrip(';').strip() if raw else ""
        if not s.startswith("IF") or len(s) < 32:
            return None
        try:
            freq_hz  = int(s[2:13])
            tx_state = int(s[28:29])   # kenwood.c priv->info[28]
            mode     = int(s[29:30])   # kenwood.c priv->info[29]
        except (ValueError, IndexError):
            return None
        if not (1_000_000 <= freq_hz <= 30_000_000):
            return None
        if mode not in range(1, 8) or tx_state not in (0, 1):
            return None
        return freq_hz, mode, tx_state

    def _read_only(self, name, *get_args, label=""):
        val, code = self.rig.get(*get_args)
        if code != 0:
            self.fail(name, f"error {code}")
            return None
        self.ok(name, f"{label}{val}")
        return val

    # ------------------------------------------------------- TX safety helpers
    #
    # A real hardware incident (CW keyed while the rig was still in SSB)
    # destroyed a driver transistor. The firmware does not reliably guard
    # against this, so this test script must not trust any prior set_mode()
    # call just because it returned success -- the mode must be re-read live
    # from the rig immediately before every single TX-triggering command.

    def _read_mode(self):
        """Live read of the current mode. Returns the mode string, or None on error."""
        val, code = self.rig.get("m")
        if code != 0 or not val:
            return None
        return val.split()[0]

    def _verify_mode(self, expected_mode, context):
        """Confirm (live CAT read) that the rig is really in expected_mode right now."""
        got = self._read_mode()
        if got is None:
            self.fail(context, "SAFETY ABORT: could not read current mode")
            return False
        if got != expected_mode:
            self.fail(context,
                       f"SAFETY ABORT: expected mode={expected_mode}, rig reports={got!r}")
            return False
        return True

    def _set_and_verify_mode(self, mode, context):
        """Explicitly set `mode` and confirm by readback that it actually took effect."""
        code = self.rig.set("M", mode, "0")
        if code != 0:
            self.fail(context, f"could not set mode {mode} -> error {code}")
            return False
        if self.delay > 0:
            time.sleep(self.delay)
        return self._verify_mode(mode, context)

    # ---------------------------------------------------------------- tests

    # ID code -> model name (from RGO ONE CAT manual)
    RGO_MODELS = {
        "006": "RGO ONE V6",
        "005": "RGO ONE V5",
        "004": "RGO ONE V4",
        "003": "RGO ONE V3",
    }

    def test_id(self):
        """ID/FW/SN: Radio identification (FW 1.08+ format)"""
        print("\n--- Identification (ID / FW / SN) ---")

        # ID: FW 1.08+ returns short "ID006" (model only)
        # Old FW returns long "ID006 <fw> <sn1> <sn2>" -- we accept both but note the difference
        raw, code = self.rig.get("w", "ID;")
        if code != 0:
            self.fail("ID: raw ID command", f"error {code}")
            return
        if not raw or not raw.startswith("ID") or len(raw) < 5:
            self.fail("ID: parse model code", f"unexpected response: {raw!r}")
            return
        id_code = raw[2:5]
        model = self.RGO_MODELS.get(id_code, f"unknown (ID{id_code})")
        if id_code != "006":
            self.fail("ID: model code", f"expected 006, got {id_code} ({model})")
            return

        id_short = raw.replace('\x00', '').rstrip(';').strip()
        if len(id_short) == 5:
            self.ok("ID: model code (FW 1.08+ format)", f"ID{id_code} = {model}")
        else:
            self.ok("ID: model code (old FW format -- FW/SN commands not available)",
                    id_short)
            self.skip("FW: firmware version", "old firmware -- FW; not available")
            self.skip("SN: serial numbers",   "old firmware -- SN; not available")
            return

        # FW: firmware version -- "FW0108" = v1.08
        raw, code = self.rig.get("w", "FW;")
        fw_clean = raw.replace('\x00', '').rstrip(';').strip() if raw else ""
        if code != 0:
            self.fail("FW: firmware version", f"error {code}")
        elif not fw_clean.startswith("FW") or len(fw_clean) != 6:
            self.fail("FW: response format", f"unexpected: {raw!r}")
        else:
            fw_raw = fw_clean[2:]   # "0108"
            try:
                major = int(fw_raw[:2])
                minor = int(fw_raw[2:])
                self.ok("FW: firmware version", f"v{major}.{minor:02d}  ({fw_clean})")
            except ValueError:
                self.fail("FW: parse version digits", f"got: {fw_raw!r}")

        # SN: serial numbers -- "SN 20303656 32435013 005D0069"
        raw, code = self.rig.get("w", "SN;")
        sn_clean = raw.replace('\x00', '').rstrip(';').strip() if raw else ""
        if code != 0:
            self.fail("SN: serial numbers", f"error {code}")
        elif not sn_clean.startswith("SN") or len(sn_clean) < 4:
            self.fail("SN: response format", f"unexpected: {raw!r}")
        else:
            self.ok("SN: serial numbers", sn_clean)

    def test_frequency(self):
        """FA/FB: VFO A frequency"""
        print("\n--- VFO A Frequency (FA) ---")
        orig, code = self.rig.get("f")
        if code != 0:
            self.fail("FA: read original frequency", f"error {code}")
            orig = None

        for freq, desc in [
            (14074000, "20m 14.074 MHz"),
            ( 7074000, "40m  7.074 MHz"),
            ( 3573000, "80m  3.573 MHz"),
            (21074000, "15m 21.074 MHz"),
        ]:
            self._set_get_int(f"FA: {desc}", ["F"], ["f"], freq)

        if orig:
            try:
                self._set_get_int("FA: restore original frequency", ["F"], ["f"], int(orig))
            except ValueError:
                pass

    # Modes actually usable on this firmware line. The user manual
    # (Manual-RGO-One-V6-v1.01.pdf) is explicit about this:
    #   "Working modes: LSB, USB, CW, CW-R"
    #   "RTTY -- Digital modes (not active with sw ver. 1.XXX)"
    #   "AM -- Amplitude modulation mode (not active with s/w ver. 1.XXX)"
    #   "FM -- Frequency modulation mode (not active with s/w ver. 1.XXX)"
    # AM/FM/RTTY are documented in the CAT manual's MD command, but the user
    # manual says plainly they are not active in the whole 1.x firmware line
    # (not an installed-option question). Confirmed via raw CAT: MD4;/MD5;/MD6;
    # do not change the mode even after a 1s delay -- not a backend bug.
    # Tested separately, opt-in, via test_mode_extended().
    PANEL_MODES = ["USB", "LSB", "CW", "CWR"]
    EXTENDED_MODES = ["AM", "FM", "RTTY"]

    def _test_mode_list(self, modes, label):
        for mode in modes:
            code = self.rig.set("M", mode, "0")
            if code != 0:
                self.fail(f"MD: set {mode}", f"error {code}")
                continue
            if self.delay > 0:
                time.sleep(self.delay)
            val, code = self.rig.get("m")
            if code != 0:
                self.fail(f"MD: read {mode}", f"error {code}")
                continue
            got = val.split()[0] if val else ""
            if got == mode:
                self.ok(f"MD: {mode}{label}", got)
            else:
                self.fail(f"MD: {mode}{label}", f"expected={mode}, got={got!r}")

    def test_mode(self):
        """MD: Operating mode (front-panel-selectable modes only)"""
        print("\n--- Operating Mode (MD) ---")
        orig_val, _ = self.rig.get("m")
        orig_mode = orig_val.split()[0] if orig_val else None

        self._test_mode_list(self.PANEL_MODES, "")

        if orig_mode:
            if self._set_and_verify_mode(orig_mode, "MD: restore original mode"):
                self.ok("MD: restore original mode", orig_mode)
            else:
                print("  !!! WARNING: rig may still be left in a test mode (e.g. CW) --")
                print("  !!! verify the mode on the rig display before any TX test !!!")

    def test_mode_extended(self):
        """MD: Operating mode -- CAT-documented modes not active in this FW line (AM/FM/RTTY)

        Listed in the CAT manual's MD command, but the user manual states
        plainly these are "not active" in the 1.x firmware line. Failures
        here are expected/informational, not a backend bug -- this is
        exactly why it is opt-in and separate from test_mode(). Worth
        re-running once a firmware version activates them.
        """
        print("\n--- Operating Mode, extended/optional (MD: AM/FM/RTTY) ---")
        orig_val, _ = self.rig.get("m")
        orig_mode = orig_val.split()[0] if orig_val else None

        self._test_mode_list(self.EXTENDED_MODES, " (extended)")

        if orig_mode:
            if self._set_and_verify_mode(orig_mode, "MD: restore original mode (extended)"):
                self.ok("MD: restore original mode (extended)", orig_mode)
            else:
                print("  !!! WARNING: rig may still be left in a test mode --")
                print("  !!! verify the mode on the rig display before any TX test !!!")

    def test_agc(self):
        """GT: AGC speed (off/fast/slow)"""
        print("\n--- AGC (GT) ---")
        orig, _ = self.rig.get("l", "AGC")
        # hamlib: 0=off, 2=fast, 3=slow  |  RGO: 000=off, 001=fast, 002=slow
        for val, label in [(0, "OFF"), (2, "FAST"), (3, "SLOW")]:
            self._set_get_int(f"GT: AGC {label}", ["L", "AGC"], ["l", "AGC"], val)
        if orig:
            try:
                self._set_get_int("GT: restore original AGC", ["L", "AGC"], ["l", "AGC"], int(orig))
            except ValueError:
                pass

    def test_rf_gain(self):
        """RG: RF gain (000-100)"""
        print("\n--- RF Gain (RG) ---")
        orig, _ = self.rig.get("l", "RF")
        self._set_get_float("RG: 100%", ["L", "RF"], ["l", "RF"], 1.0, 1.0, tol=0.02)
        self._set_get_float("RG:  50%", ["L", "RF"], ["l", "RF"], 0.5, 0.5, tol=0.02)
        self._set_get_float("RG:   0%", ["L", "RF"], ["l", "RF"], 0.0, 0.0, tol=0.02)
        if orig:
            try:
                orig_f = float(orig)
                self._set_get_float("RG: restore original", ["L", "RF"], ["l", "RF"], orig_f, orig_f, tol=0.02)
            except ValueError:
                pass

    def test_rf_power(self):
        """PC: RF output power (000-050 = 0-50 W)"""
        print("\n--- RF Output Power (PC) ---")
        orig, _ = self.rig.get("l", "RFPOWER")
        # RGO: 50 steps, step = 0.02
        self._set_get_float("PC: 100% (50W)", ["L", "RFPOWER"], ["l", "RFPOWER"], 1.0, 1.0, tol=0.022)
        self._set_get_float("PC:  50% (25W)", ["L", "RFPOWER"], ["l", "RFPOWER"], 0.5, 0.5, tol=0.022)
        self._set_get_float("PC:  20% (10W)", ["L", "RFPOWER"], ["l", "RFPOWER"], 0.2, 0.2, tol=0.022)
        if orig:
            try:
                orig_f = float(orig)
                self._set_get_float("PC: restore original", ["L", "RFPOWER"], ["l", "RFPOWER"], orig_f, orig_f, tol=0.022)
            except ValueError:
                pass

    def test_mic_gain(self):
        """MG: Microphone gain (000-010)"""
        print("\n--- Microphone Gain (MG) ---")
        orig, _ = self.rig.get("l", "MICGAIN")
        # RGO: 10 steps, step = 0.1
        self._set_get_float("MG: 50%", ["L", "MICGAIN"], ["l", "MICGAIN"], 0.5, 0.5, tol=0.11)
        self._set_get_float("MG:  0%", ["L", "MICGAIN"], ["l", "MICGAIN"], 0.0, 0.0, tol=0.11)
        if orig:
            try:
                orig_f = float(orig)
                self._set_get_float("MG: restore original", ["L", "MICGAIN"], ["l", "MICGAIN"], orig_f, orig_f, tol=0.11)
            except ValueError:
                pass

    def test_monitor_gain(self):
        """ML: TX monitor level (000-010)"""
        print("\n--- TX Monitor Level (ML) ---")
        orig, _ = self.rig.get("l", "MONITOR_GAIN")
        self._set_get_float("ML: 50%", ["L", "MONITOR_GAIN"], ["l", "MONITOR_GAIN"], 0.5, 0.5, tol=0.11)
        self._set_get_float("ML:  0%", ["L", "MONITOR_GAIN"], ["l", "MONITOR_GAIN"], 0.0, 0.0, tol=0.11)
        if orig:
            try:
                orig_f = float(orig)
                self._set_get_float("ML: restore original", ["L", "MONITOR_GAIN"], ["l", "MONITOR_GAIN"], orig_f, orig_f, tol=0.11)
            except ValueError:
                pass

    def test_nb(self):
        """NB: Noise blanker on/off"""
        print("\n--- Noise Blanker (NB) ---")
        orig, _ = self.rig.get("u", "NB")
        self._set_get_int("NB: on",  ["U", "NB"], ["u", "NB"], 1)
        self._set_get_int("NB: off", ["U", "NB"], ["u", "NB"], 0)
        if orig:
            try:
                self._set_get_int("NB: restore original", ["U", "NB"], ["u", "NB"], int(orig))
            except ValueError:
                pass

    def test_nb_level(self):
        """NL: Noise blanker level (000-016)"""
        print("\n--- Noise Blanker Level (NL) ---")
        orig, _ = self.rig.get("l", "NB")
        # RGO: 16 steps, step = 1/16 = 0.0625
        NL_MIN = 1.0 / 16.0     # NL001 -- lowest step above zero
        self._set_get_float("NL: 50%",  ["L", "NB"], ["l", "NB"], 0.5,    0.5,    tol=0.07)
        self._set_get_float("NL:  min", ["L", "NB"], ["l", "NB"], NL_MIN, NL_MIN, tol=0.07)
        if orig:
            try:
                orig_f = float(orig)
                self._set_get_float("NL: restore original", ["L", "NB"], ["l", "NB"], orig_f, orig_f, tol=0.07)
            except ValueError:
                pass

    def test_preamp(self):
        """PA: Preamp on/off (SET: PA1/PA0 -- no P2, doc is wrong)"""
        print("\n--- Preamp (PA) ---")
        orig, _ = self.rig.get("l", "PREAMP")
        self._set_get_int("PA: on",  ["L", "PREAMP"], ["l", "PREAMP"], 1)
        self._set_get_int("PA: off", ["L", "PREAMP"], ["l", "PREAMP"], 0)
        if orig:
            try:
                self._set_get_int("PA: restore original", ["L", "PREAMP"], ["l", "PREAMP"], int(orig))
            except ValueError:
                pass

    def test_att(self):
        """RA: Attenuator on/off"""
        print("\n--- Attenuator (RA) ---")
        orig, _ = self.rig.get("l", "ATT")
        self._set_get_int("RA: on",  ["L", "ATT"], ["l", "ATT"], 1)
        self._set_get_int("RA: off", ["L", "ATT"], ["l", "ATT"], 0)
        if orig:
            try:
                self._set_get_int("RA: restore original", ["L", "ATT"], ["l", "ATT"], int(orig))
            except ValueError:
                pass

    def test_comp(self):
        """PL: Speech processor level (000-010)"""
        print("\n--- Speech Processor / COMP (PL) ---")
        orig, _ = self.rig.get("l", "COMP")
        # RGO: 10 steps, step = 0.1
        self._set_get_float("PL: 50%", ["L", "COMP"], ["l", "COMP"], 0.5, 0.5, tol=0.11)
        self._set_get_float("PL:  0%", ["L", "COMP"], ["l", "COMP"], 0.0, 0.0, tol=0.11)
        if orig:
            try:
                orig_f = float(orig)
                self._set_get_float("PL: restore original", ["L", "COMP"], ["l", "COMP"], orig_f, orig_f, tol=0.11)
            except ValueError:
                pass

    def test_vox(self):
        """VG/VD: VOX gain and VOX delay"""
        print("\n--- VOX Gain (VG) ---")
        orig_vg, _ = self.rig.get("l", "VOXGAIN")
        self._set_get_float("VG: 50%", ["L", "VOXGAIN"], ["l", "VOXGAIN"], 0.5, 0.5, tol=0.11)
        self._set_get_float("VG:  0%", ["L", "VOXGAIN"], ["l", "VOXGAIN"], 0.0, 0.0, tol=0.11)
        if orig_vg:
            try:
                orig_vg_f = float(orig_vg)
                self._set_get_float("VG: restore original", ["L", "VOXGAIN"], ["l", "VOXGAIN"], orig_vg_f, orig_vg_f, tol=0.11)
            except ValueError:
                pass

        print("\n--- VOX Delay (VD) ---")
        orig_vd, _ = self.rig.get("l", "VOXDELAY")
        # VOXDELAY: val.i in 100ms steps (0-12 = 0-1200ms)
        # hardware minimum: 500ms (val.i=5), skip test for 0
        self._set_get_int("VD: 500ms  (val.i= 5)", ["L", "VOXDELAY"], ["l", "VOXDELAY"],  5)
        self._set_get_int("VD: 1200ms (val.i=12)", ["L", "VOXDELAY"], ["l", "VOXDELAY"], 12)
        if orig_vd:
            try:
                self._set_get_int("VD: restore original", ["L", "VOXDELAY"], ["l", "VOXDELAY"], int(orig_vd))
            except ValueError:
                pass

    def test_bkin_dly(self):
        """SD: CW break-in delay (0000-1200 ms)"""
        print("\n--- CW Break-in Delay (SD) ---")
        orig, _ = self.rig.get("l", "BKIN_DLYMS")
        self._set_get_int("SD:    0ms", ["L", "BKIN_DLYMS"], ["l", "BKIN_DLYMS"],    0)
        self._set_get_int("SD:  500ms", ["L", "BKIN_DLYMS"], ["l", "BKIN_DLYMS"],  500)
        # 1200ms is the manual maximum; older firmware versions may
        # be limited to ~500ms -- failure here is firmware-related.
        self._set_get_int("SD: 1200ms", ["L", "BKIN_DLYMS"], ["l", "BKIN_DLYMS"], 1200)
        if orig:
            try:
                self._set_get_int("SD: restore original", ["L", "BKIN_DLYMS"], ["l", "BKIN_DLYMS"], int(orig))
            except ValueError:
                pass

    def test_keyspd(self):
        """KS: Electronic keyer speed (005-045 WPM)"""
        print("\n--- Keyer Speed (KS) ---")
        orig, _ = self.rig.get("l", "KEYSPD")
        self._set_get_int("KS: 20 WPM", ["L", "KEYSPD"], ["l", "KEYSPD"], 20)
        self._set_get_int("KS:  5 WPM", ["L", "KEYSPD"], ["l", "KEYSPD"],  5)
        self._set_get_int("KS: 45 WPM", ["L", "KEYSPD"], ["l", "KEYSPD"], 45)
        if orig:
            try:
                self._set_get_int("KS: restore original", ["L", "KEYSPD"], ["l", "KEYSPD"], int(orig))
            except ValueError:
                pass

    def test_lock(self):
        """LK: Key lock"""
        print("\n--- Key Lock (LK) ---")
        orig, _ = self.rig.get("u", "LOCK")
        self._set_get_int("LK: lock",   ["U", "LOCK"], ["u", "LOCK"], 1)
        self._set_get_int("LK: unlock", ["U", "LOCK"], ["u", "LOCK"], 0)
        if orig:
            try:
                self._set_get_int("LK: restore original", ["U", "LOCK"], ["u", "LOCK"], int(orig))
            except ValueError:
                pass

    def test_rit(self):
        """RT/RD/RU/RC: RIT on/off and offset"""
        print("\n--- RIT (RT/RD/RU/RC) ---")
        orig_on, _ = self.rig.get("u", "RIT")
        orig_off, _ = self.rig.get("j")

        self._set_get_int("RT: RIT on",    ["U", "RIT"], ["u", "RIT"], 1)
        self._set_get_int("RIT: +500 Hz",  ["J"],        ["j"],      500)
        self._set_get_int("RIT: -200 Hz",  ["J"],        ["j"],     -200)
        self._set_get_int("RIT:    0 Hz",  ["J"],        ["j"],        0)
        self._set_get_int("RT: RIT off",   ["U", "RIT"], ["u", "RIT"], 0)

        if orig_off:
            try:
                self._set_get_int("RIT: restore original offset", ["J"], ["j"], int(orig_off))
            except ValueError:
                pass
        if orig_on:
            try:
                self._set_get_int("RT: restore original on/off", ["U", "RIT"], ["u", "RIT"], int(orig_on))
            except ValueError:
                pass

    def test_xit(self):
        """XT: XIT on/off"""
        print("\n--- XIT (XT) ---")
        orig, _ = self.rig.get("u", "XIT")
        self._set_get_int("XT: XIT on",  ["U", "XIT"], ["u", "XIT"], 1)
        self._set_get_int("XT: XIT off", ["U", "XIT"], ["u", "XIT"], 0)
        if orig:
            try:
                self._set_get_int("XT: restore original", ["U", "XIT"], ["u", "XIT"], int(orig))
            except ValueError:
                pass

    def test_tuner(self):
        """AC: Antenna tuner on/off"""
        print("\n--- Tuner (AC) ---")
        orig, _ = self.rig.get("u", "TUNER")
        self._set_get_int("AC: Tuner on",  ["U", "TUNER"], ["u", "TUNER"], 1)
        self._set_get_int("AC: Tuner off", ["U", "TUNER"], ["u", "TUNER"], 0)
        if orig:
            try:
                self._set_get_int("AC: restore original", ["U", "TUNER"], ["u", "TUNER"], int(orig))
            except ValueError:
                pass

    def test_band_ops(self):
        """BD/BU: Band up/down -- verifies frequency change"""
        print("\n--- Band Ops (BD/BU) ---")
        orig, code = self.rig.get("f")
        if code != 0:
            self.skip("BD/BU: Band-Ops", "frequency not readable")
            return
        orig_freq = int(orig)

        # BAND_UP
        code = self.rig.set("G", "BAND_UP")
        if code != 0:
            self.fail("BU: Band up", f"set error {code}")
            self._set_get_int("F: restore original frequency after failed BU", ["F"], ["f"], orig_freq)
            return
        if self.delay > 0:
            time.sleep(self.delay)
        after_up, code = self.rig.get("f")
        if code != 0:
            self.fail("BU: Band up verify", f"frequency not readable after BU ({code})")
            after_up_freq = orig_freq
        else:
            after_up_freq = int(after_up)
            if after_up_freq != orig_freq:
                self.ok("BU: Band up", f"{orig_freq} -> {after_up_freq}")
            else:
                self.fail("BU: Band up", f"frequency unchanged: {orig_freq}")

        # BAND_DOWN
        code = self.rig.set("G", "BAND_DOWN")
        if code != 0:
            self.fail("BD: Band down", f"set error {code}")
        else:
            if self.delay > 0:
                time.sleep(self.delay)
            after_down, code = self.rig.get("f")
            if code != 0:
                self.fail("BD: Band down verify", f"frequency not readable after BD ({code})")
            else:
                after_down_freq = int(after_down)
                if after_down_freq != after_up_freq:
                    self.ok("BD: Band down", f"{after_up_freq} -> {after_down_freq}")
                else:
                    self.fail("BD: Band down", f"frequency unchanged: {after_up_freq}")

        self._set_get_int("F: restore original frequency", ["F"], ["f"], orig_freq)

    def test_smeter(self):
        """SM: S-meter reading"""
        print("\n--- S-Meter (SM) ---")
        val = self._read_only("SM: signal strength", "l", "STRENGTH", label="Value: ")
        if val is not None:
            try:
                v = int(val)
                if not (-100 <= v <= 60):
                    self.fail("SM: signal strength range", f"{v} out of range -100..60 dBm")
            except ValueError:
                pass

    def test_meters(self):
        """RM: Meter functions (SWR, ALC, COMP) -- saves and restores the active meter"""
        print("\n--- Meters (RM) ---")

        # Save current meter selection before switching through all types
        orig_meter = None
        raw, code = self.rig.get("w", "RM;")
        if code == 0 and raw and raw.startswith("RM") and len(raw) >= 3:
            try:
                orig_meter = int(raw.replace('\x00', '').rstrip(';').strip()[2:3])
            except (ValueError, IndexError):
                pass

        self._read_only("RM: SWR",        "l", "SWR",        label="SWR: ")
        self._read_only("RM: ALC",        "l", "ALC",        label="ALC: ")
        self._read_only("RM: COMP meter", "l", "COMP_METER", label="COMP: ")

        # Restore previous meter selection, verified by readback
        if orig_meter is not None:
            self.rig.send_no_response(f"RM{orig_meter};")
            time.sleep(0.2)
            raw_rb, code = self.rig.get("w", "RM;")
            rb = raw_rb.replace('\x00', '').rstrip(';').strip() if raw_rb else ""
            if code == 0 and rb.startswith("RM") and len(rb) >= 3 and rb[2:3] == str(orig_meter):
                self.ok("RM: restore original meter selection", rb)
            else:
                self.fail("RM: restore original meter selection",
                          f"expected RM{orig_meter}, got {raw_rb!r}")

    def test_split(self):
        """FR/FT: Split VFO"""
        print("\n--- Split VFO (FR/FT) ---")
        code = self.rig.set("S", "1", "VFOB")
        if code != 0:
            self.fail("FT: Split on", f"error {code}")
        else:
            val, code = self.rig.get("s")
            got = val.split()[0] if val else ""
            if code == 0 and got == "1":
                self.ok("FT: Split on", "confirmed")
            else:
                self.fail("FT: Split on", f"response: {val!r}")

        code = self.rig.set("S", "0", "VFOA")
        if code != 0:
            self.fail("FR: Split off", f"error {code}")
        else:
            val, code = self.rig.get("s")
            got = val.split()[0] if val else ""
            if code == 0 and got == "0":
                self.ok("FR: Split off", "confirmed")
            else:
                self.fail("FR: Split off", f"response: {val!r}")

    def test_tune(self):
        """TX2 / G TUNE: Antenna tuner tune cycle (tune carrier + tuner)"""
        print("\n--- Antenna Tuner Tune (TX2 / G TUNE) ---")
        print("    TX2 = transmit in tune mode (RGO built-in tuner cycle).")
        print("    Radio transmits a carrier and returns to RX after tuning.")

        POWER_1W = 1.0 / 50.0

        orig_power, code = self.rig.get("l", "RFPOWER")
        if code != 0:
            self.fail("PC: read power before tune", f"error {code}")
            orig_power = None

        ok = self._set_get_float(
            "PC: set 1W before tune (PC001)",
            ["L", "RFPOWER"], ["l", "RFPOWER"],
            POWER_1W, POWER_1W,
            tol=1.0 / 50.0,
        )
        if not ok:
            self.skip("TX2: Tuner tune", "power could not be set to 1W")
            return

        # Safety net: read the mode NOW and re-confirm live right before
        # keying TX2. Never trust an earlier set_mode() call alone -- a
        # stale/wrong mode assumption here is exactly what destroyed a
        # driver transistor in the field (CW keyed while actually still
        # in SSB).
        safety_mode = self._read_mode()
        if safety_mode is None:
            self.fail("TX2: Tuner tune", "could not read current mode -- aborting for safety")
            return
        print(f"    Safety check: current mode is {safety_mode!r} -- re-verified immediately before TX")
        if not self._verify_mode(safety_mode, "TX2: pre-TX mode check"):
            self.fail("TX2: Tuner tune", "mode changed unexpectedly before TX -- aborting for safety")
            return

        print("    (WARNING: radio transmits tune carrier, approx. 1W!)")
        code = self.rig.set("G", "TUNE")
        if code != 0:
            self.fail("TX2: start tune", f"G TUNE error {code}")
        else:
            print("    (waiting 5s for tuner cycle ...)")
            time.sleep(5.0)
            ptt_val, code = self.rig.get("t")
            if code == 0 and ptt_val is not None and int(ptt_val.split()[0]) == 0:
                self.ok("TX2: Tuner tune", "RX after tuning")
            else:
                self.fail("TX2: Tuner tune",
                          f"PTT state after tuning: {ptt_val!r} (expected 0=RX)")
                # Emergency fallback: force RX and verify it actually took effect --
                # this is the one command in the whole suite that matters most.
                self.rig.set("T", "0")
                time.sleep(0.3)
                rx_val, rx_code = self.rig.get("t")
                if rx_code == 0 and rx_val and int(rx_val.split()[0]) == 0:
                    self.ok("TX2: emergency force RX", "confirmed RX")
                else:
                    self.fail("TX2: emergency force RX",
                              f"SAFETY ABORT: rig may still be transmitting! state: {rx_val!r}")

        if orig_power:
            try:
                orig_power_f = float(orig_power)
                self._set_get_float("PC: restore original power", ["L", "RFPOWER"], ["l", "RFPOWER"],
                                    orig_power_f, orig_power_f, tol=1.0 / 50.0)
            except ValueError:
                pass

    def test_ptt(self):
        """TX/RX: PTT -- sets power to 1W first (PC001)"""
        print("\n--- Set RF power to 1W before PTT test (PC) ---")

        POWER_1W = 1.0 / 50.0          # PC001 = 1/50 = 0.02

        orig_power, code = self.rig.get("l", "RFPOWER")
        if code != 0:
            self.fail("PC: read original power", f"error {code}")
            orig_power = None

        ok = self._set_get_float(
            "PC: set 1W (PC001)",
            ["L", "RFPOWER"], ["l", "RFPOWER"],
            POWER_1W, POWER_1W,
            tol=1.0 / 50.0,
        )
        if not ok:
            self.skip("TX/RX: PTT", "power could not be set to 1W")
            return

        print("\n--- PTT TX/RX (WARNING: transmitter active, approx. 1W!) ---")

        # Safety net: read the mode NOW and re-confirm live right before
        # every single TX trigger below. Never trust an earlier set_mode()
        # call alone -- a stale/wrong mode assumption here is exactly what
        # destroyed a driver transistor in the field (CW keyed while
        # actually still in SSB). Re-checked before each TX-on below since
        # time passes and state can drift between them.
        safety_mode = self._read_mode()
        if safety_mode is None:
            self.fail("TX/RX: PTT", "could not read current mode -- aborting PTT test for safety")
            return
        print(f"    Safety check: current mode is {safety_mode!r} -- will be re-verified before every TX")

        if not self._verify_mode(safety_mode, "TX: PTT on (TX0) -- pre-TX mode check"):
            self.fail("TX/RX: PTT", "mode changed unexpectedly before TX -- aborting for safety")
            return

        code = self.rig.set("T", "1")
        if code != 0:
            self.fail("TX: PTT on (TX0)", f"error {code}")
        else:
            val, code = self.rig.get("t")
            if code == 0 and val and int(val.split()[0]) == 1:
                self.ok("TX: PTT on (TX0)", "confirmed")
            else:
                self.fail("TX: PTT on (TX0)", f"state: {val!r}")

        time.sleep(0.3)

        code = self.rig.set("T", "0")
        ptt_off_confirmed = False
        if code != 0:
            self.fail("RX: PTT off", f"error {code}")
        else:
            val, code = self.rig.get("t")
            if code == 0 and val and int(val.split()[0]) == 0:
                self.ok("RX: PTT off", "confirmed")
                ptt_off_confirmed = True
            else:
                self.fail("RX: PTT off", f"state: {val!r}")

        if not ptt_off_confirmed:
            self.fail("TX/RX: PTT",
                      "SAFETY ABORT: could not confirm RX after first TX -- "
                      "not triggering further TX until this is verified manually")
            return

        time.sleep(0.3)

        # RIG_PTT_ON_DATA (T 3) -- mapped to TX0, not documented as TX1
        if not self._verify_mode(safety_mode, "TX: PTT on data (TX0 mapped) -- pre-TX mode check"):
            self.fail("TX/RX: PTT", "mode changed unexpectedly before data TX -- aborting for safety")
            return

        code = self.rig.set("T", "3")
        if code != 0:
            self.fail("TX: PTT on data (TX0 mapped)", f"error {code}")
        else:
            val, code = self.rig.get("t")
            if code == 0 and val and int(val.split()[0]) != 0:
                self.ok("TX: PTT on data (TX0 mapped)", "confirmed")
            else:
                self.fail("TX: PTT on data (TX0 mapped)", f"state: {val!r}")

        time.sleep(0.3)

        code = self.rig.set("T", "0")
        if code != 0:
            self.fail("RX: PTT off after data", f"error {code}")
        else:
            val, code = self.rig.get("t")
            if code == 0 and val and int(val.split()[0]) == 0:
                self.ok("RX: PTT off after data", "confirmed")
            else:
                self.fail("RX: PTT off after data", f"state: {val!r}")
                # Emergency fallback: this is the one command that matters
                # most -- retry and verify before giving up.
                self.rig.set("T", "0")
                time.sleep(0.3)
                rx_val, rx_code = self.rig.get("t")
                if rx_code == 0 and rx_val and int(rx_val.split()[0]) == 0:
                    self.ok("TX/RX: PTT emergency force RX", "confirmed RX")
                else:
                    self.fail("TX/RX: PTT emergency force RX",
                              f"SAFETY ABORT: rig may still be transmitting! state: {rx_val!r}")

        if orig_power:
            try:
                orig_power_f = float(orig_power)
                self._set_get_float("PC: restore original power", ["L", "RFPOWER"], ["l", "RFPOWER"],
                                    orig_power_f, orig_power_f, tol=1.0 / 50.0)
            except ValueError:
                pass

    def test_mem(self):
        """MC: Memory channel recall (00-99)"""
        print("\n--- Memory Channel Recall (MC) ---")
        orig, code = self.rig.get("e")
        if code != 0:
            self.skip("MC: memory channel recall", f"get_mem error {code}")
            return
        try:
            orig_ch = int(orig.split()[0])
        except (TypeError, ValueError, AttributeError):
            orig_ch = 0

        # Verify get_mem returns a valid channel number (0-99)
        if 0 <= orig_ch <= 99:
            self.ok("MC: get_mem (current channel)", f"ch={orig_ch:02d}")
        else:
            self.fail("MC: get_mem range", f"expected 0-99, got {orig_ch}")
            return

        # Raw CAT: verify MC; response format "MC000"--"MC099"
        # (read-only -- set_mem / MC recall switches the TRX to memory mode
        #  and there is no reliable CAT command to exit it in FW 1.09)
        raw, rcode = self.rig.get("w", "MC;")
        rc = raw.replace('\x00', '').rstrip(';').strip() if raw else ""
        if rcode != 0 or not rc.startswith("MC") or len(rc) != 5:
            self.fail("MC: raw CAT response format", f"got: {raw!r}")
        else:
            self.ok("MC: raw CAT format MC<3digits>", rc)

    def test_channel(self):
        """MR/MW: Memory channel read/write (get_channel / set_channel)

        MR response format: MR[P1][P2][CH2][FREQ11][MODE][STEP][NB][PRE][ATT][AGC][FIL]
        = 24 chars without ';'.  Empty channel: FREQ=0 -> RIG_ENAVAIL.
        MW: same layout, no rig response.  Split: TX slot (P1=1) != RX slot (P1=0).

        Note: get_channel / set_channel via rigctld/netrigctl returns -RIG_ENIMPL
        (upstream Hamlib limitation; netrigctl does not forward channel ops).
        Test the Hamlib API directly, without rigctld:
            rigctl -m 43001 -r /dev/ttyACM0 -s 9600 h 0 1
        """
        TEST_CH = 99    # channel used for write tests (will be cleaned up)
        print(f"\n--- Memory Channel Read/Write (MR/MW), test channel {TEST_CH} ---")

        # ----------------------------------------------------------------
        # 1. Raw MR format check on channel 0 (expected to be stored)
        # ----------------------------------------------------------------
        raw, code = self.rig.get("w", "MR0000;")
        raw = (raw or "").replace('\x00', '').rstrip(';').strip()
        if code != 0 or len(raw) != 24 or not raw.startswith("MR"):
            self.fail("MR: raw response format ch0", f"len={len(raw)} raw={raw!r}")
            return
        self.ok("MR: raw response format (24 chars)", raw[:6] + "...")

        try:
            raw_freq_0 = int(raw[6:17])
        except ValueError:
            self.fail("MR: frequency field parse ch0", raw[6:17])
            return

        if raw_freq_0 == 0:
            self.skip("MR: channel 0 empty (no reference data)", "skip MR/MW tests")
            return

        self.ok("MR: channel 0 has data", f"freq={raw_freq_0/1e6:.4f} MHz")

        # Hamlib get_channel works when using rigctl directly (not via rigctld):
        #   rigctl -m 43001 -r /dev/ttyACM0 -s 9600 h 0 1
        # netrigctl (model 2 / rigctld proxy) always returns -RIG_ENIMPL for
        # channel ops -- upstream limitation, not a backend bug.
        self.skip("MR: get_channel via Hamlib API",
                  "netrigctl returns -ENIMPL; run: rigctl -m 43001 h 0 1")

        # ----------------------------------------------------------------
        # 2. Write channel TEST_CH via MW (no split), verify via MR readback
        # ----------------------------------------------------------------
        test_freq = 7074000   # 7.074 MHz
        test_mode = 2         # USB
        # MW00<ch><freq11><mode><step><NB><PRE><ATT><AGC><FIL>
        mw_rx = f"MW00{TEST_CH:02d}{test_freq:011d}{test_mode}000020;"
        # TX slot mirrors RX freq for non-split (TX freq=0 clears the channel)
        mw_tx_nosplit = f"MW10{TEST_CH:02d}{test_freq:011d}{test_mode}000020;"
        self.rig.send_no_response(mw_rx)
        time.sleep(0.2)
        self.rig.send_no_response(mw_tx_nosplit)
        time.sleep(self.delay)

        raw_rb, code = self.rig.get("w", f"MR00{TEST_CH:02d};")
        raw_rb = (raw_rb or "").replace('\x00', '').rstrip(';').strip()
        if code != 0 or len(raw_rb) != 24:
            self.fail(f"MR: ch{TEST_CH} readback after MW write",
                      f"len={len(raw_rb)} raw={raw_rb!r}")
        else:
            try:
                rb_freq = int(raw_rb[6:17])
                rb_mode = int(raw_rb[17])
            except (ValueError, IndexError):
                rb_freq, rb_mode = None, None

            if rb_freq == test_freq and rb_mode == test_mode:
                self.ok(f"MR: ch{TEST_CH} MW write + MR readback",
                        f"freq={rb_freq/1e6:.4f} MHz mode={rb_mode} (USB)")
            else:
                self.fail(f"MR: ch{TEST_CH} MW write + MR readback mismatch",
                          f"freq={rb_freq}(exp={test_freq}) mode={rb_mode}(exp={test_mode})")

        # ----------------------------------------------------------------
        # 3. Write split channel: RX 7.074 MHz, TX 7.100 MHz
        #    Verify by reading both P1=0 (RX) and P1=1 (TX) slots via MR
        # ----------------------------------------------------------------
        tx_freq = 7100000   # 7.100 MHz
        mw_rx   = f"MW00{TEST_CH:02d}{test_freq:011d}{test_mode}000020;"
        mw_tx   = f"MW10{TEST_CH:02d}{tx_freq:011d}{test_mode}000020;"
        self.rig.send_no_response(mw_rx)
        time.sleep(0.2)
        self.rig.send_no_response(mw_tx)
        time.sleep(self.delay)

        raw_rx, code_rx = self.rig.get("w", f"MR00{TEST_CH:02d};")
        raw_rx = (raw_rx or "").replace('\x00', '').rstrip(';').strip()
        raw_tx, code_tx = self.rig.get("w", f"MR10{TEST_CH:02d};")
        raw_tx = (raw_tx or "").replace('\x00', '').rstrip(';').strip()

        try:
            rx_f = int(raw_rx[6:17]) if len(raw_rx) == 24 else None
            tx_f = int(raw_tx[6:17]) if len(raw_tx) == 24 else None
        except (ValueError, IndexError):
            rx_f, tx_f = None, None

        if rx_f == test_freq and tx_f == tx_freq:
            self.ok(f"MR: ch{TEST_CH} split MW write (RX+TX slots)",
                    f"RX={rx_f/1e6:.3f} TX={tx_f/1e6:.3f} MHz")
        else:
            self.fail(f"MR: ch{TEST_CH} split MW write mismatch",
                      f"RX={rx_f}(exp={test_freq}) TX={tx_f}(exp={tx_freq})")

        # ----------------------------------------------------------------
        # Cleanup: delete via MW P1=0 FREQ=0 (FW 1.10, same format as the
        # backend's rgo_one_delete_channel), then verify via MR that the RX
        # slot is empty. FW 1.09 rejected this with '?'.
        mw_del = f"MW00{TEST_CH:02d}{0:011d}0000000;"
        self.rig.send_no_response(mw_del)
        time.sleep(self.delay)
        raw_del, code_del = self.rig.get("w", f"MR00{TEST_CH:02d};")
        raw_del = (raw_del or "").replace('\x00', '').rstrip(';').strip()
        try:
            del_f = int(raw_del[6:17]) if len(raw_del) == 24 else None
        except (ValueError, IndexError):
            del_f = None
        if del_f == 0:
            self.ok(f"MW: delete ch{TEST_CH} (P1=0 FREQ=0) + MR readback empty")
        else:
            self.fail(f"MW: delete ch{TEST_CH} (P1=0 FREQ=0) not empty after MR",
                      f"len={len(raw_del)} freq={del_f} raw={raw_del!r}")

        # MR commands can leave the rig in memory mode on some firmware versions.
        # NOTE: FR0 does NOT reliably exit memory mode (confirmed experimentally,
        # see CLAUDE.md "Memory/Channel-Modus") -- it only switches the RX VFO
        # A/B. No known CAT command exits memory mode. Sending FR0 is a
        # best-effort, low-cost no-op for the VFO A/B case only.
        self.rig.send_no_response("FR0;")
        time.sleep(0.3)
        print("    WARNING: FR0 does not reliably exit memory mode -- verify the rig "
              "display shows normal VFO operation (not 'CH nn') before any TX test. "
              "Press M/V on the rig if needed.")

    def test_raw_cat(self):
        """AI/FS/PB: CAT commands documented in the manual, no Hamlib API mapping.
        Tested via raw 'w' (send_raw) since there is no corresponding rigctl command.
        """
        print("\n--- Raw CAT commands (not in Hamlib API): AI, FS, PB ---")

        # -- AI: Auto-Info / Transceive mode --------------------------
        #
        # AI set commands (AI0; AI1;) produce no direct rig response and need
        # send_no_response().  For AI2 and AI1+BU, the rig sends a spontaneous
        # IF frame which rigctld reads as the "response" -- this is how we
        # capture and verify real AI frames while rigctld is running.
        #
        # Step 1: AI should be off -- kenwood_open() disables it on connect.
        raw, code = self.rig.get("w", "AI;")
        if code != 0:
            self.fail("AI: query auto-info", f"error {code}")
        elif not (raw and raw.startswith("AI") and len(raw) >= 3):
            self.fail("AI: response format", f"unexpected: {raw!r}")
        else:
            if raw[2:3] == "0":
                self.ok("AI: off (disabled by Hamlib on connect)", raw.rstrip(";"))
            else:
                self.fail("AI: expected AI0 (Hamlib must turn AI off on connect)",
                          f"got: {raw!r}")

        # Step 2+3: AI2 -- periodic IF every 1.5 s.
        # get("w","AI2;") sends the command; the rig sends a spontaneous IF
        # frame after ~1.5 s which rigctld reads as the "response".  No
        # separate send_no_response needed here.
        print("       (waiting ~1.5 s for AI2 periodic IF frame ...)")
        raw, code = self.rig.get("w", "AI2;")
        if code != 0:
            self.fail("AI2: set periodic + wait for IF frame", f"error {code}")
        elif not (raw and raw.startswith("IF")):
            self.fail("AI2: expected IF frame as response", f"got: {raw!r}")
        else:
            parsed = self._parse_if_frame(raw)
            if parsed:
                freq_hz, mode, tx_state = parsed
                MODE_NAMES = {1:"LSB",2:"USB",3:"CW",4:"FM",5:"AM",6:"Digi",7:"CW-R"}
                self.ok("AI2: periodic IF frame received and parsed",
                        f"freq={freq_hz/1e6:.4f} MHz  mode={MODE_NAMES.get(mode,mode)}"
                        f"  tx={tx_state}")
            else:
                self.fail("AI2: IF frame parse error", f"raw: {raw[:50]!r}")

        # Disable AI immediately; restore takes effect before the next IF would arrive.
        self.rig.send_no_response("AI0;")
        time.sleep(0.5)
        raw, code = self.rig.get("w", "AI;")
        if code == 0 and raw and raw[2:3] == "0":
            self.ok("AI2: restored AI0", raw.rstrip(";"))
        else:
            self.fail("AI2: restore AI0 failed", f"got: {raw!r} code={code}")

        # Steps 4+5: AI1 -- IF on freq/mode/band change.
        # AI1 set has no response, use send_no_response; then verify via read.
        self.rig.send_no_response("AI1;")
        time.sleep(0.5)
        raw, code = self.rig.get("w", "AI;")
        if code != 0:
            self.fail("AI1: verify AI1 set", f"error {code}")
        elif raw and raw[2:3] == "1":
            self.ok("AI1: change-notification mode set", raw.rstrip(";"))
        else:
            self.fail("AI1: expected AI1", f"got: {raw!r}")

        # Step 6: BU (band up) triggers an immediate AI1 IF frame.
        # rigctld reads it as the "response" to BU -- no timeout.
        raw, code = self.rig.get("w", "BU;")
        if code != 0:
            self.fail("AI1: BU + wait for IF frame", f"error {code}")
        elif not (raw and raw.startswith("IF")):
            self.fail("AI1: expected IF frame after BU (band up)", f"got: {raw!r}")
        else:
            parsed = self._parse_if_frame(raw)
            if parsed:
                freq_hz, mode, tx_state = parsed
                self.ok("AI1: IF frame received after BU (band up)",
                        f"freq={freq_hz/1e6:.4f} MHz  mode={MODE_NAMES.get(mode,mode)}")
            else:
                self.fail("AI1: IF frame parse error after BU", f"raw: {raw[:50]!r}")

        # Step 7: BD (band down) to restore -- also triggers AI1 IF frame.
        raw, code = self.rig.get("w", "BD;")
        if code == 0 and raw and raw.startswith("IF"):
            parsed = self._parse_if_frame(raw)
            detail = f"freq={parsed[0]/1e6:.4f} MHz" if parsed else "received"
            self.ok("AI1: IF frame received after BD (band restored)", detail)
        elif code != 0:
            self.skip("AI1: BD band-restore IF frame",
                      "no IF frame (already at lowest band?)")
        else:
            self.fail("AI1: IF frame after BD", f"got: {raw!r}")

        # Steps 8+9: disable AI and final verify.
        self.rig.send_no_response("AI0;")
        time.sleep(0.5)
        raw, code = self.rig.get("w", "AI;")
        if code == 0 and raw and raw[2:3] == "0":
            self.ok("AI: final verify AI0 (auto-info disabled)", raw.rstrip(";"))
        else:
            self.fail("AI: final verify AI0", f"got: {raw!r} code={code}")

        # -- FS: Fine Tuning (1 Hz step) ------------------------------
        # FS set commands (FS0; / FS1;) produce no rig response, so rigctld
        # would hang waiting for a reply. send_no_response() handles this by
        # capping the subprocess timeout at 2 s (TimeoutExpired = sent OK).
        # Flow: read → set opposite → verify → restore → verify.
        raw, code = self.rig.get("w", "FS;")
        if code != 0:
            self.fail("FS: query fine tuning", f"error {code}")
        elif not (raw and raw.startswith("FS") and len(raw) >= 3):
            self.fail("FS: response format", f"unexpected: {raw!r}")
        else:
            orig_fs = raw[2:3]
            toggled = "1" if orig_fs == "0" else "0"
            self.ok("FS: query fine tuning", raw.rstrip(";"))

            # set to opposite value and verify
            self.rig.send_no_response(f"FS{toggled};")
            time.sleep(0.5)
            verify, vcode = self.rig.get("w", "FS;")
            if vcode != 0:
                self.fail(f"FS: set {'on' if toggled == '1' else 'off'} (FS{toggled})",
                          f"query error {vcode}")
            elif verify and verify[2:3] == toggled:
                self.ok(f"FS: set {'on' if toggled == '1' else 'off'} (FS{toggled})",
                        verify.rstrip(";"))
            else:
                self.fail(f"FS: set {'on' if toggled == '1' else 'off'} (FS{toggled})",
                          f"got: {verify!r}")

            # restore original value and verify
            self.rig.send_no_response(f"FS{orig_fs};")
            time.sleep(0.5)
            verify, vcode = self.rig.get("w", "FS;")
            if vcode != 0:
                self.fail(f"FS: restore (FS{orig_fs})", f"query error {vcode}")
            elif verify and verify[2:3] == orig_fs:
                self.ok(f"FS: restore (FS{orig_fs})", verify.rstrip(";"))
            else:
                self.fail(f"FS: restore (FS{orig_fs})", f"got: {verify!r}")

        # -- PB: CW/SSB Memory Playback (read-only, no channel triggered) --
        # Response: PBP1P2P2P2;  P1=0 stop / 1-4 channel,  P2=000 inactive / NNN playing
        raw, code = self.rig.get("w", "PB;")
        if code != 0:
            self.fail("PB: query memory playback status", f"error {code}")
        elif not (raw and raw.startswith("PB") and len(raw) >= 5):
            self.fail("PB: response format", f"unexpected: {raw!r}")
        else:
            r      = raw.replace('\x00', '').rstrip(';')
            pb_ch  = r[2:3]
            pb_buf = r[3:6]
            state  = "stop" if pb_ch == "0" else f"playing ch{pb_ch}"
            self.ok("PB: query memory playback", f"ch={pb_ch} buf={pb_buf} ({state})")

    # ---------------------------------------------------------------- summary

    def report(self):
        total = len(self.passed) + len(self.failed) + len(self.skipped)
        print("\n" + "=" * 60)
        print(f"RESULT: {len(self.passed)}/{total} passed")
        print(f"  OK:      {len(self.passed)}")
        print(f"  FAILED:  {len(self.failed)}")
        print(f"  SKIPPED: {len(self.skipped)}")
        if self.failed:
            print("\nFailed tests:")
            for name, detail in self.failed:
                print(f"  - {name}: {detail}")
        return len(self.failed) == 0


# ------------------------------------------------------------------ version check

def check_rigctld_version(rigctld_bin):
    """Checks if the rigctld binary is newer than EXPECTED_BUILD_AFTER."""
    try:
        mtime = os.path.getmtime(rigctld_bin)
        build_time = datetime.datetime.fromtimestamp(mtime)
        if build_time < EXPECTED_BUILD_AFTER:
            print(f"WARNING: {rigctld_bin}")
            print(f"         built:    {build_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"         expected: after {EXPECTED_BUILD_AFTER.strftime('%Y-%m-%d')}"
                  f" (backend version {EXPECTED_BACKEND_VERSION})")
            print("         Please rebuild and reinstall: sudo make install")
            return False
        else:
            print(f"  rigctld build: {build_time.strftime('%Y-%m-%d %H:%M:%S')}  [OK]")
            return True
    except OSError as e:
        print(f"  rigctld version check: {e}")
        return True   # continue anyway


# ------------------------------------------------------------------ startup

def is_rigctld_ready(host, port, rigctl_bin, timeout=3):
    """Checks if rigctld responds (not just whether the port is open)."""
    try:
        r = subprocess.run(
            [rigctl_bin, "-m", "2", "-r", f"{host}:{port}", "f"],
            capture_output=True, timeout=timeout,
        )
        return r.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return False


def start_rigctld(model, device, baud, host, port, rigctld_bin, rigctl_bin):
    """Starts rigctld and waits until it responds to commands."""
    cmd = [rigctld_bin, "-m", model, "-r", device, "-s", baud, "-t", str(port)]
    print(f"Starting rigctld: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    print("Waiting for rigctld ...", end="", flush=True)
    for _ in range(30):          # wait up to 9 seconds
        time.sleep(0.3)
        print(".", end="", flush=True)
        if is_rigctld_ready(host, port, rigctl_bin):
            print(f" ready (PID {proc.pid})")
            return proc

    print(" Timeout!")
    proc.terminate()
    return None


def confirm_tx_safety():
    """Mandatory operator confirmation before any TX-triggering test.

    CAT cannot verify or reliably exit memory/channel mode on this rig
    (no known command does it -- see CLAUDE.md). A past hardware incident
    (CW keyed while the rig was still in SSB) destroyed a driver
    transistor -- the firmware itself does not reliably guard against
    this either. Since software cannot fully verify rig state here, ask
    the human who can actually look at the front panel.
    """
    print("\n" + "=" * 60)
    print("SAFETY CHECK before TX tests (--ptt / --tune)")
    print("=" * 60)
    print("  CAT cannot verify or reliably exit memory/channel mode.")
    print("  Please confirm on the radio BEFORE continuing:")
    print("    1. Display shows normal VFO operation, NOT 'CH nn' (memory mode).")
    print("       If it shows 'CH nn': press the M/V button on the rig now.")
    print("    2. A dummy load or safe antenna is connected.")
    print("    3. You are physically present and ready to switch off power if needed.")
    try:
        answer = input("  Type 'yes' to confirm and continue: ").strip().lower()
    except EOFError:
        answer = ""
    return answer == "yes"


def main():
    parser = argparse.ArgumentParser(
        description="RGO ONE V6 CAT Command Test Suite",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("-r", "--device",    default=DEFAULT_DEVICE,   help=f"serial port (default: {DEFAULT_DEVICE})")
    parser.add_argument("-s", "--baud",      default=DEFAULT_BAUD,     help=f"baud rate (default: {DEFAULT_BAUD})")
    parser.add_argument("-m", "--model",     default=DEFAULT_MODEL,    help=f"hamlib model ID (default: {DEFAULT_MODEL})")
    parser.add_argument("--host",            default=DEFAULT_HOST,     help=f"rigctld host (default: {DEFAULT_HOST})")
    parser.add_argument("--port", type=int,  default=DEFAULT_PORT,     help=f"rigctld port (default: {DEFAULT_PORT})")
    parser.add_argument("--rigctld",         default=DEFAULT_RIGCTLD,  help=f"path to rigctld (default: {DEFAULT_RIGCTLD})")
    parser.add_argument("--rigctl",          default=DEFAULT_RIGCTL,   help=f"path to rigctl  (default: {DEFAULT_RIGCTL})")
    parser.add_argument("--delay", type=float, default=0.5,            help="delay between set and get in seconds (default: 0.5)")
    parser.add_argument("--ptt",   action="store_true", help="run PTT test (transmitter active!)")
    parser.add_argument("--tune",  action="store_true", help="run antenna tuner tune (TX2, transmitter active!)")
    parser.add_argument("--test-mem", action="store_true",
                         help="attempt the MR/MW memory channel read/write test (test_channel). "
                              "Disabled by default: MR/MW have been observed to leave the rig in "
                              "memory mode on some firmware versions, with no confirmed CAT "
                              "command to exit it again (see CLAUDE.md) -- only the M/V button "
                              "on the rig does. The read-only MC status check (test_mem) always "
                              "runs regardless of this flag -- it is confirmed safe (no mode "
                              "change). Only enable --test-mem if you are prepared to exit "
                              "memory mode manually afterwards.")
    parser.add_argument("--test-if-frame", action="store_true",
                         help="run the raw CAT / IF-frame test (test_raw_cat: AI/FS/PB). "
                              "Disabled by default -- this bypasses the normal Hamlib get/set "
                              "API and sends/parses raw CAT frames for commands with no Hamlib "
                              "mapping. The default test run covers only the 'normal' CAT "
                              "functions that go through the standard Hamlib API.")
    parser.add_argument("--test-all-modes", action="store_true",
                         help="also test AM/FM/RTTY modes (test_mode_extended). Disabled by "
                              "default: these are documented in the CAT manual's MD command, but "
                              "the RGO ONE user manual states they are 'not active' in the 1.x "
                              "firmware line, and this hardware's front panel only offers "
                              "LSB/USB/CW/CW-R. Failures here are expected/informational on such "
                              "units, not a backend bug.")
    parser.add_argument("--no-stop", action="store_true", help="do not stop rigctld after test")
    args = parser.parse_args()

    rigctld_proc    = None
    started_by_us   = False

    addr = f"{args.host}:{args.port}"

    print("=" * 60)
    print("RGO ONE V6 - CAT Command Test Suite")
    print(f"  Expected backend version: {EXPECTED_BACKEND_VERSION}")
    print("=" * 60)

    print("\n--- Version check ---")
    check_rigctld_version(args.rigctld)

    if is_rigctld_ready(args.host, args.port, args.rigctl):
        print(f"rigctld already running on {addr} and responding.")
    else:
        if not os.path.exists(args.device):
            print(f"ERROR: serial port {args.device} not found.", file=sys.stderr)
            sys.exit(1)
        if not os.path.exists(args.rigctld):
            print(f"ERROR: rigctld not found: {args.rigctld}", file=sys.stderr)
            sys.exit(1)
        rigctld_proc = start_rigctld(
            args.model, args.device, args.baud,
            args.host, args.port, args.rigctld, args.rigctl,
        )
        if rigctld_proc is None:
            print("ERROR: rigctld did not respond.", file=sys.stderr)
            sys.exit(1)
        started_by_us = True

    rig   = RigCtl(args.host, args.port, args.rigctl)
    suite = TestSuite(rig, delay=args.delay)

    print(f"\nConnected to rigctld ({addr}), delay between tests: {args.delay}s")

    # FR0 only switches the RX VFO (A/B) -- it does NOT reliably exit
    # memory/channel mode (confirmed experimentally, see CLAUDE.md
    # "Memory/Channel-Modus"). No known CAT command does. Sending it anyway
    # is a harmless best-effort for the VFO A/B case, but if the rig was
    # ever put into memory mode (front panel, a previous MC recall), only
    # the operator can confirm/fix that -- see the confirmation gate before
    # --ptt/--tune below.
    rig.send_no_response("FR0;")
    time.sleep(0.5)

    print("=" * 60)

    unexpected_error = False
    try:
        suite.test_id()
        suite.test_frequency()
        suite.test_mode()

        if args.test_all_modes:
            suite.test_mode_extended()
        else:
            suite.skip("MD: extended modes (AM/FM/RTTY, test_mode_extended)",
                       "--test-all-modes not specified (not active in this FW line per "
                       "user manual, and not on this hardware's front panel)")

        suite.test_agc()
        suite.test_rf_gain()
        suite.test_rf_power()
        suite.test_mic_gain()
        suite.test_monitor_gain()
        suite.test_nb()
        suite.test_nb_level()
        suite.test_preamp()
        suite.test_att()
        suite.test_comp()
        suite.test_vox()
        suite.test_bkin_dly()
        suite.test_keyspd()
        suite.test_lock()
        suite.test_rit()
        suite.test_xit()
        suite.test_tuner()
        suite.test_band_ops()
        suite.test_smeter()
        suite.test_meters()
        suite.test_split()

        # test_mem() only uses get_mem ("e") and the raw "MC;" query -- both
        # confirmed read-only, no mode change (see CLAUDE.md). Always run it
        # so the TRX's memory-channel state is still checked every time, even
        # when the riskier MR/MW test below is disabled.
        suite.test_mem()

        # test_channel() uses MR/MW, which -- unlike plain MC queries -- has
        # been observed to leave the rig in memory mode on some firmware
        # versions with no confirmed CAT exit. Opt-in only.
        if args.test_mem:
            suite.test_channel()
        else:
            suite.skip("MR/MW: Memory channel read/write (test_channel)",
                       "--test-mem not specified (MR/MW can leave the rig in memory mode "
                       "with no confirmed CAT exit -- see CLAUDE.md)")

        if args.test_if_frame:
            suite.test_raw_cat()
        else:
            suite.skip("Raw CAT / IF-frame test (AI/FS/PB, test_raw_cat)",
                       "--test-if-frame not specified (default run covers only "
                       "normal Hamlib-API CAT functions)")

        if args.tune or args.ptt:
            if not confirm_tx_safety():
                print("  Aborted by operator -- skipping PTT/tune tests.")
                args.ptt = False
                args.tune = False

        if args.tune:
            suite.test_tune()
        else:
            suite.skip("TX2: Tuner tune", "--tune not specified")

        if args.ptt:
            suite.test_ptt()
        else:
            suite.skip("TX/RX: PTT", "--ptt not specified")

    except KeyboardInterrupt:
        print("\nAborted.")
    except Exception:
        unexpected_error = True
        print("\n" + "=" * 60)
        print("UNEXPECTED ERROR during test run -- treating as failure:")
        print("=" * 60)
        traceback.print_exc()
        print("=" * 60)
        print("Attempting emergency PTT-off as a last-resort safety measure ...")
        try:
            rig.set("T", "0")
        except Exception:
            pass
    finally:
        if rigctld_proc and not args.no_stop and started_by_us:
            print("Stopping rigctld ...")
            rigctld_proc.terminate()
            try:
                rigctld_proc.wait(timeout=3)
            except subprocess.TimeoutExpired:
                rigctld_proc.kill()

    ok = suite.report()
    sys.exit(0 if (ok and not unexpected_error) else 1)


if __name__ == "__main__":
    main()
