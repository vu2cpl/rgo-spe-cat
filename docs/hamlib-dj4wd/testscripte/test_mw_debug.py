#!/usr/bin/env python3
"""RGO ONE V6 — MW/MR memory channel delete investigation script.

Tests all known approaches to delete a memory channel via CAT, following
the specification in Boris's firmware 1.09 change announcement:

  Point 5: "If both parameters P1=0 and P4=00000000000 then performs
            memory channel P3 delete. (Deletes both TX and RX parts)"

Uses rigctl directly (no rigctld daemon required).

Usage:
  python3 test_mw_debug.py [device] [baud]
  python3 test_mw_debug.py /dev/ttyACM0 9600

MW command format (CAT manual v1.03, p.6):
  MW P1 P2 P3(2) P4(11) P5 P6 P7 P8 P9 P10 P11
     |  |  |     |       |  |  |  |   |  |   |
     |  |  CH    FREQ    MD ST NB PRE ATT AGC FIL
     |  always=0
     0=RX slot, 1=TX slot

MR response format (same layout, 24 chars without semicolon):
  MR P1 P2 P3(2) P4(11) P5 P6 P7 P8 P9 P10 P11
"""
import subprocess
import sys
import time
import datetime

DEVICE  = sys.argv[1] if len(sys.argv) > 1 else "/dev/ttyACM0"
BAUD    = sys.argv[2] if len(sys.argv) > 2 else "9600"
BASE    = ["/usr/local/bin/rigctl", "-m", "43001", "-r", DEVICE, "-s", BAUD]
CH      = 99      # primary test channel
CH2     = 98      # secondary test channel (expected to be empty/unused)
RX_F    = 7074000  # 40 m, FT8 frequency
TX_F    = 7100000  # 40 m, split TX
MODE    = 2        # USB

W = 62   # column width for command field

def raw(cmd, label, timeout=4):
    """Send a raw CAT command and return the response."""
    try:
        r = subprocess.run(BASE + ["w", cmd], capture_output=True,
                           text=True, timeout=timeout)
        resp = r.stdout.replace('\x00', '').rstrip(';').strip()
    except subprocess.TimeoutExpired:
        resp = "(timeout)"
    tag = "SENT" if not label.startswith("[") else label
    print(f"    {label:<28s}  {cmd:<{W}s}  =>  {resp!r}")
    return resp

def note(text):
    print(f"  NOTE: {text}")

def result(ok, text):
    mark = "PASS" if ok else "FAIL"
    print(f"  [{mark}] {text}")

def section(num, title, hypothesis):
    print()
    print("=" * 78)
    print(f"  Test {num}: {title}")
    print("-" * 78)
    print(f"  Hypothesis: {hypothesis}")
    print("-" * 78)

def check_channel(ch, label="Channel content"):
    rx = raw(f"MR00{ch:02d};", f"  MR RX slot (P1=0) ch{ch:02d}")
    tx = raw(f"MR10{ch:02d};", f"  MR TX slot (P1=1) ch{ch:02d}")
    rx_freq = int(rx[6:17]) if len(rx) >= 17 and rx[6:17].isdigit() else None
    tx_freq = int(tx[6:17]) if len(tx) >= 17 and tx[6:17].isdigit() else None
    if not rx:
        print(f"    => {label}: EMPTY (no MR response)")
    elif rx_freq == 0:
        print(f"    => {label}: stored with FREQ=0 (effectively empty)")
    else:
        print(f"    => {label}: RX={rx_freq/1e6:.4f} MHz  TX={tx_freq/1e6:.4f} MHz")
    return rx, tx

def is_deleted(rx):
    """Return True if MR response indicates an empty/deleted channel."""
    if not rx:
        return True   # FW 1.09: empty response for deleted channel
    if len(rx) >= 17 and rx[6:17] == "0" * 11:
        return True   # FW 1.08 style: all-zero freq = empty
    return False

# ======================================================================
print("=" * 78)
print("  RGO ONE V6 — Memory Channel Delete Investigation")
print(f"  Device: {DEVICE}  Baud: {BAUD}")
print(f"  Date  : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  Test channel: {CH}   Reference channel: {CH2}")
print(f"  Test RX freq: {RX_F/1e6:.4f} MHz   Test TX freq (split): {TX_F/1e6:.4f} MHz")
print("=" * 78)

print()
print("  [INIT] Restoring VFO-A mode (MC recall from a previous run may")
print("         have left the radio in memory mode where MW is rejected).")
raw("FA00014000000;", "  FA 14.000 MHz (→ VFO mode)")
time.sleep(0.3)
raw("FR0;",           "  FR0 RX=VFO-A")
time.sleep(0.3)
raw("FT0;",           "  FT0 TX=VFO-A")
time.sleep(0.3)

# ======================================================================
section(1, "Write SIMPLEX channel, verify readback",
        "MW with valid frequency works correctly — baseline sanity check.")

note(f"Writing simplex: RX slot (P1=0) + TX slot (P1=1), both at {RX_F/1e6:.4f} MHz")
raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot = RX)")
time.sleep(0.4)
rx, tx = check_channel(CH, "After write")
result(not is_deleted(rx) and int(rx[6:17]) == RX_F,
       f"Simplex write ch{CH}: RX={RX_F/1e6:.4f} MHz stored")

# ======================================================================
section(2, "Delete simplex channel: MW P1=0, FREQ=00000000000",
        "Per Boris's spec point 5: P1=0 AND P4=00000000000 should delete the channel.")

note("Sending: MW00 99 00000000000 0000000  (all fields zero except channel)")
resp = raw(f"MW00{CH:02d}{'0'*11}0000000;", "  MW P1=0 FREQ=0 (delete)")
time.sleep(0.6)
rx, tx = check_channel(CH, "After delete attempt")
deleted = is_deleted(rx)
result(resp != "?", f"Delete command accepted (expected: no '?' response)  => got: {resp!r}")
result(deleted,     f"Channel {CH} is empty after delete")

# ======================================================================
section(3, "Write SPLIT channel, verify readback",
        "MW split: RX slot at one frequency, TX slot at a different frequency.")

note(f"Writing split: RX={RX_F/1e6:.4f} MHz (P1=0), TX={TX_F/1e6:.4f} MHz (P1=1)")
raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{TX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot, split)")
time.sleep(0.4)
rx, tx = check_channel(CH, "After write")
rx_ok = not is_deleted(rx) and len(rx) >= 17 and int(rx[6:17]) == RX_F
tx_ok = len(tx) >= 17 and int(tx[6:17]) == TX_F
result(rx_ok, f"Split write ch{CH}: RX={RX_F/1e6:.4f} MHz stored")
result(tx_ok, f"Split write ch{CH}: TX={TX_F/1e6:.4f} MHz stored")

# ======================================================================
section(4, "Delete SPLIT channel: MW P1=0, FREQ=00000000000",
        "Same delete command as test 2, but applied to a split channel.")

note("Sending: MW00 99 00000000000 0000000")
resp = raw(f"MW00{CH:02d}{'0'*11}0000000;", "  MW P1=0 FREQ=0 (delete)")
time.sleep(0.6)
rx, tx = check_channel(CH, "After delete attempt")
deleted = is_deleted(rx)
result(resp != "?", f"Delete command accepted  => got: {resp!r}")
result(deleted,     f"Channel {CH} is empty after delete")

# ======================================================================
section(5, "Delete SPLIT: first set TX to simplex (P1=1 FREQ=0), then delete",
        "Two-step: MW P1=1 FREQ=0 first (→ simplex per point 4), then MW P1=0 FREQ=0 (delete).")

raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{TX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot, split)")
time.sleep(0.4)
note("Step 1: set TX slot to simplex (MW P1=1 FREQ=0 per Boris point 4)")
raw(f"MW10{CH:02d}{'0'*11}0000000;", "  MW P1=1 FREQ=0 (→simplex)")
time.sleep(0.4)
rx, tx = check_channel(CH, "After simplex step")
note("Step 2: now delete with MW P1=0 FREQ=0")
resp = raw(f"MW00{CH:02d}{'0'*11}0000000;", "  MW P1=0 FREQ=0 (delete)")
time.sleep(0.6)
rx, tx = check_channel(CH, "After delete step")
deleted = is_deleted(rx)
result(resp != "?", f"Delete command accepted  => got: {resp!r}")
result(deleted,     f"Channel {CH} is empty after two-step delete")

# ======================================================================
section(6, "Delete with FREQ=0 but valid mode and AGC fields",
        "Maybe FW rejects FREQ=0 due to invalid P5 (mode=0) or P10 (AGC=0). "
        "Test with mode=2 (USB) and AGC=2 (fast) — only FREQ differs from a valid write.")

raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{TX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot, split)")
time.sleep(0.4)
del_cmd = f"MW00{CH:02d}{'0'*11}{MODE}000020;"
note(f"Delete command: {del_cmd}  (FREQ=0, mode=USB, AGC=fast — all other fields valid)")
resp = raw(del_cmd, "  MW P1=0 FREQ=0 valid-mode")
time.sleep(0.6)
rx, tx = check_channel(CH, "After delete attempt")
deleted = is_deleted(rx)
result(resp != "?", f"Delete command accepted  => got: {resp!r}")
result(deleted,     f"Channel {CH} is empty after delete")

# ======================================================================
section(7, "Delete using old FW behavior: MW P1=1 FREQ=0 (sent twice)",
        "In FW < 1.09, MW P1=1 FREQ=0 deleted the whole channel. "
        "Test if this still works in FW 1.09 (sent twice in case one sets simplex).")

raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{TX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot, split)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{'0'*11}0000000;", "  MW P1=1 FREQ=0 (1st send)")
time.sleep(0.4)
raw(f"MW10{CH:02d}{'0'*11}0000000;", "  MW P1=1 FREQ=0 (2nd send)")
time.sleep(0.6)
rx, tx = check_channel(CH, "After 2x MW P1=1 FREQ=0")
deleted = is_deleted(rx)
result(deleted, f"Channel {CH} is empty after 2x MW P1=1 FREQ=0")

# ======================================================================
section(8, f"Delete an empty/unused channel (ch{CH2:02d})",
        f"Verify the delete command also fails on a channel that was never written "
        f"(rules out the hypothesis that only occupied channels are rejected).")

note(f"Channel {CH2} should be unused — reading it first:")
rx, tx = check_channel(CH2, f"Ch{CH2:02d} before delete attempt")
resp = raw(f"MW00{CH2:02d}{'0'*11}0000000;", f"  MW P1=0 FREQ=0 ch{CH2:02d}")
time.sleep(0.6)
rx2, _ = check_channel(CH2, f"Ch{CH2:02d} after delete attempt")
result(resp != "?", f"Delete command accepted on empty ch{CH2:02d}  => got: {resp!r}")

# ======================================================================
section(9, "Short MW format: P1+P2+CH+FREQ only (no P5..P11)",
        "The full 24-char MW format is always rejected when FREQ=0. "
        "Test a shortened form (17 chars, omitting mode/step/NB/PRE/ATT/AGC/FIL) "
        "to see if the firmware accepts and acts on it differently.")

raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot, full fmt)")
time.sleep(0.5)
raw(f"MW10{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot, full fmt)")
time.sleep(0.5)
rx, tx = check_channel(CH, f"Ch{CH:02d} before short-format delete")
short_cmd = f"MW00{CH:02d}{'0'*11};"
note(f"Short delete: {short_cmd}  ({len(short_cmd)-1} chars, no P5-P11)")
resp = raw(short_cmd, "  MW short (P1+P2+CH+FREQ only)")
time.sleep(1.0)
rx, tx = check_channel(CH, f"Ch{CH:02d} after short-format delete")
deleted = is_deleted(rx)
result(resp != "?", f"Short delete command accepted  => got: {resp!r}")
result(deleted,     f"Channel {CH} is empty after short-format delete")

# ======================================================================
section(10, "Long pause (2 s) between write and delete",
        "Timing hypothesis: FW needs time to commit the write before accepting delete.")

raw(f"MW00{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=0 (RX slot)")
time.sleep(0.5)
raw(f"MW10{CH:02d}{RX_F:011d}{MODE}000020;", "  MW P1=1 (TX slot)")
note("Waiting 2 seconds before sending delete ...")
time.sleep(2.0)
resp = raw(f"MW00{CH:02d}{'0'*11}0000000;", "  MW P1=0 FREQ=0 (delete)")
time.sleep(0.8)
rx, tx = check_channel(CH, "After delete (2 s pause)")
deleted = is_deleted(rx)
result(resp != "?", f"Delete command accepted after 2 s pause  => got: {resp!r}")
result(deleted,     f"Channel {CH} is empty after delete")

# ======================================================================
print()
print("=" * 78)
print("  SUMMARY")
print("=" * 78)
print()
print("  MW command format reference:")
print(f"    Full write (24 chars):  MW00{CH:02d}{RX_F:011d}{MODE}000020")
print(f"    Delete attempt (24ch):  MW00{CH:02d}{'0'*11}0000000")
print(f"    Short format  (15ch):   MW00{CH:02d}{'0'*11}")
print()
print("  Expected per Boris FW 1.09 spec (point 5):")
print("    MW P1=0, FREQ=00000000000  =>  channel deleted, MR returns empty")
print()
print("  Observed:  MW P1=0, FREQ=0  =>  '?' (rejected by firmware)")
print()
