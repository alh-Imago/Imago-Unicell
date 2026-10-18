#!/bin/sh
# run_pulse_v1.sh -- ledger #1224: test T4 (pulse width at the input pin), idle and busy builds. Wiring: the T2 jumper only, Tang pin 86 -> pin 72 (nothing in pin 72 but the jumper).
# Usage:   sudo LABEL=a sh ./run_pulse_v1.sh       (each build takes about 40 s after loading; LABEL letters/digits/-/_ only; ONLY=pls_idle runs one build)
cd "$(dirname "$0")" || exit 1
for f in groups/pls_idle.fs groups/pls_busy.fs board_collect_pulse_v1.py watch_serial.py; do
  if [ ! -f "$f" ]; then echo "MISSING FILE: $(pwd)/$f  (unzip the whole zip into this folder)"; exit 1; fi
done
mkdir -p raw; LABEL=${LABEL:-run}; case "$LABEL" in *[!A-Za-z0-9_-]*) echo "LABEL may only use letters, digits, - and _"; exit 1;; esac
find_tang() { if [ -n "$TANGPORT" ]; then [ -e "$TANGPORT" ] && echo "$TANGPORT"; return; fi; ls /dev/serial/by-id/usb-SIPEED*-if01-port0 2>/dev/null | head -1; }
for N in ${ONLY:-pls_idle pls_busy}; do
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- $N: switch the Tang OFF (unplug its USB), wait 5 s, plug it ON, then press Enter ---"
    read dummy
    echo "waiting for the Tang's serial port to appear (up to 90 s) ..."
    i=0; PRE=""
    while [ $i -lt 90 ]; do PRE=$(find_tang); [ -n "$PRE" ] && break; sleep 1; i=$((i+1)); done
    if [ -z "$PRE" ]; then echo "The Tang's serial port did NOT appear."; ls -l /dev/serial/by-id/ 2>&1 | sed 's/^/    /'; attempt=$((attempt+1)); continue; fi
    echo "Tang serial port: $PRE; waiting 20 s for the demo to finish booting ..."; sleep ${BOOTWAIT:-20}
    echo "[$N] loading ..."
    rm -f "raw/${LABEL}_$N.pre" "raw/${LABEL}_$N.pre.log"
    python3 watch_serial.py "$PRE" "raw/${LABEL}_$N.pre" ${SECS:-70} > /dev/null 2>&1 &
    WPID=$!
    sleep 1
    openFPGALoader -b tangnano20k "groups/$N.fs" > "raw/${LABEL}_$N.loader.txt" 2>&1; rc=$?
    wait $WPID; sleep 1
    cp "raw/${LABEL}_$N.pre" "raw/${LABEL}_$N.bin" 2>/dev/null || : > "raw/${LABEL}_$N.bin"
    echo "[$N] $(wc -c < "raw/${LABEL}_$N.bin") bytes read from the Tang (loader exit $rc)"
    [ -s "raw/${LABEL}_$N.bin" ] && break
    echo "silent. Loader said: $(tail -n 2 "raw/${LABEL}_$N.loader.txt" | tr '\n' ' ')"
    echo "Power-cycle the Tang and try again (attempt $attempt of 3)"
    attempt=$((attempt+1))
  done
done
python3 board_collect_pulse_v1.py "$LABEL"
echo
echo "Finished. Results are in $(pwd)/board_results_${LABEL}.txt"
