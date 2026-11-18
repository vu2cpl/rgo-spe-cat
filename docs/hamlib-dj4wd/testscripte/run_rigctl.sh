#!/bin/bash

PIDFILE="/tmp/rigctld.pid"
RIGCTLD="/usr/local/bin/rigctld"
RIGCTL="/usr/local/bin/rigctl"
BASE_CMD="$RIGCTLD -m 43001 -r /dev/ttyACM0 -s 57600 -t 4532"
RIGCTL_PORT=4532

check_binary() {
    if [ ! -x "$1" ]; then
        echo "Fehler: $1 nicht gefunden oder nicht ausführbar."
        echo "Ist Hamlib mit dem RGO-ONE-Patch installiert? (bash scripts/build-linux.sh)"
        exit 1
    fi
}

do_stop() {
    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill "$PID" 2>/dev/null; then
            echo "rigctld (PID $PID) gestoppt."
            rm -f "$PIDFILE"
        else
            echo "Prozess $PID nicht gefunden. PID-Datei wird entfernt."
            rm -f "$PIDFILE"
        fi
    else
        echo "Kein laufender rigctld-Prozess gefunden (keine PID-Datei)."
    fi
}

do_start() {
    check_binary "$RIGCTLD"
    if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
        echo "rigctld läuft bereits (PID $(cat "$PIDFILE"))."
        exit 1
    fi
    $BASE_CMD &
    PID=$!
    echo $PID > "$PIDFILE"
    sleep 0.5
    if ! kill -0 "$PID" 2>/dev/null; then
        echo "rigctld (PID $PID) konnte nicht gestartet werden (TRX ausgeschaltet oder Port belegt?)."
        rm -f "$PIDFILE"
        exit 1
    fi
    echo "rigctld gestartet (PID $PID)."
}

case "$1" in
    -stop)
        do_stop
        ;;
    -start|"")
        do_start
        ;;
    -restart)
        do_stop
        sleep 0.3
        do_start
        ;;
    -status)
        # Prozess-Check
        if [ -f "$PIDFILE" ] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
            echo "rigctld läuft (PID $(cat "$PIDFILE"))."
        else
            echo "rigctld läuft nicht."
            exit 1
        fi
        # Erreichbarkeits-Check via rigctl
        check_binary "$RIGCTL"
        FREQ=$(timeout 2 "$RIGCTL" -m 2 -r "localhost:$RIGCTL_PORT" f 2>/dev/null)
        if [ $? -eq 0 ] && [ -n "$FREQ" ]; then
            echo "rigctld ist ansprechbar. Aktuelle Frequenz: ${FREQ} Hz"
        else
            echo "rigctld ist NICHT ansprechbar (Port $RIGCTL_PORT antwortet nicht. TRX ausgeschaltet?)."
            exit 2
        fi
        ;;
    -v*)
        # Verbosity-Parameter direkt weitergeben, Foreground
        check_binary "$RIGCTLD"
        exec $BASE_CMD "$1"
        ;;
    *)
        echo "Verwendung: $(basename "$0") [-start | -stop | -restart | -status | -v[v...]]"
        exit 1
        ;;
esac
