#!/usr/bin/env bash
# ============================================================
#  ota.sh — build and upload over WiFi (Arduino OTA).
#
#  The board calls back to this host on a fixed TCP port, because the
#  UniFi policy that lets IoT reach the Mac allows only that port
#  (IoT 192.168.30.191 -> Trusted 192.168.10.226, TCP 48266).
#  The OTA password is read from the git-ignored include/secrets.h.
#  Copied from power-management/mains-monitor/ota.sh.
#
#    ./ota.sh                  # build and upload to 192.168.30.191
#    OTA_IP=1.2.3.4 ./ota.sh   # another address
# ============================================================
set -euo pipefail
# Prefer PlatformIO's own venv: a stray pip-installed `pio` (Python 3.9) earlier on PATH can't build espressif32.
PIO="$HOME/.platformio/penv/bin/pio"; [ -x "$PIO" ] || PIO=pio
PY="$HOME/.platformio/penv/bin/python"; [ -x "$PY" ] || PY=python3
ESPOTA="$HOME/.platformio/packages/framework-arduinoespressif32/tools/espota.py"
cd "$(dirname "$0")"

ENV="${PIO_ENV:-rgo-spe-cat}"
IP="${OTA_IP:-192.168.30.191}"
HOST_PORT=48266

PASS=$(sed -n 's/^#define OTA_PASS[[:space:]]*"\(.*\)".*/\1/p' include/secrets.h)

"$PIO" run -e "$ENV"
echo "→ OTA to $IP (call-back on TCP $HOST_PORT)"
exec "$PY" "$ESPOTA" -r -i "$IP" -P "$HOST_PORT" ${PASS:+-a "$PASS"} -f ".pio/build/$ENV/firmware.bin"
