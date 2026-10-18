#!/bin/sh
# run_pulse_esp32_v1.sh -- ledger #1227: test P1 (pulse width into the ESP32), clone of run_c1_v3.sh. Wiring as C1: Tang 86 -> ESP32 IO16, ESP32 IO17 -> Tang 72, Tang 53 -> ESP32 IO21, GND-GND. ESP32 sketch: esp32/unicell_pulse_v1.
cd "$(dirname "$0")" || exit 1
# Usage:   sudo LABEL=a ESPPORT=auto sh ./run_pulse_esp32_v1.sh     (send z in the Serial Monitor first, then CLOSE it; ESPPORT=auto records the ESP32 lines; each build takes about 15 s after loading; ONLY=pe_quiet runs one build)
for f in groups/pe_quiet.fs groups/pe_storm.fs board_collect_pulse_esp32_v1.py watch_serial.py; do
  if [ ! -f "$f" ]; then echo "MISSING FILE: $(pwd)/$f  (unzip the whole zip into this folder)"; exit 1; fi
done
mkdir -p raw; LABEL=${LABEL:-run}; case "$LABEL" in *[!A-Za-z0-9_-]*) echo "LABEL may only use letters, digits, - and _"; exit 1;; esac
find_tang() { if [ -n "$TANGPORT" ]; then [ -e "$TANGPORT" ] && echo "$TANGPORT"; return; fi; ls /dev/serial/by-id/usb-SIPEED*-if01-port0 2>/dev/null | head -1; }
find_esp() { if [ "$ESPPORT" = "auto" ]; then ls /dev/serial/by-id/usb-Silicon_Labs_CP210*-port0 2>/dev/null | head -1; else echo "$ESPPORT"; fi; }
show_ports() { echo "  serial ports now:"; ls -l /dev/serial/by-id/ 2>&1 | sed 's/^/    /'; }
for N in ${ONLY:-pe_quiet pe_storm}; do
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- $N: switch the Tang OFF (unplug its USB), wait 5 s, plug it ON, then press Enter ---"
    read dummy
    echo "waiting for the Tang's serial port to appear (up to 90 s) ..."
    i=0; PRE=""
    while [ $i -lt 90 ]; do PRE=$(find_tang); [ -n "$PRE" ] && break; sleep 1; i=$((i+1)); done
    if [ -z "$PRE" ]; then echo "The Tang's serial port did NOT appear."; show_ports; attempt=$((attempt+1)); continue; fi
    echo "Tang serial port: $PRE; waiting 20 s for the demo to finish booting ..."; sleep ${BOOTWAIT:-20}
    ESP=$(find_esp)
    if [ "$ESPPORT" = "auto" ] && [ -z "$ESP" ]; then echo "(the ESP32's CP210x port was not found: its lines will not be recorded)"; fi
    echo "[$N] loading ..."
    rm -f "raw/${LABEL}_$N.pre" "raw/${LABEL}_$N.pre.log" "raw/${LABEL}_$N.esp32" "raw/${LABEL}_$N.esp32.log"
    python3 watch_serial.py "$PRE" "raw/${LABEL}_$N.pre" ${SECS:-40} > /dev/null 2>&1 &
    WPID=$!
    EPID=""
    if [ -n "$ESP" ]; then python3 watch_serial.py "$ESP" "raw/${LABEL}_$N.esp32" ${SECS:-40} > /dev/null 2>&1 & EPID=$!; fi
    sleep 1
    openFPGALoader -b tangnano20k "groups/$N.fs" > "raw/${LABEL}_$N.loader.txt" 2>&1; rc=$?
    wait $WPID; [ -n "$EPID" ] && wait $EPID; sleep 1
    cp "raw/${LABEL}_$N.pre" "raw/${LABEL}_$N.bin" 2>/dev/null || : > "raw/${LABEL}_$N.bin"
    echo "[$N] $(wc -c < "raw/${LABEL}_$N.bin") bytes read from the Tang (loader exit $rc)"
    [ -s "raw/${LABEL}_$N.bin" ] && break
    echo "silent. Loader said: $(tail -n 2 "raw/${LABEL}_$N.loader.txt" | tr '\n' ' ')"
    show_ports
    echo "Power-cycle the Tang (unplug, wait 5 s, plug in) and try again (attempt $attempt of 3)"
    attempt=$((attempt+1))
  done
done
python3 board_collect_pulse_esp32_v1.py "$LABEL"
echo
echo "Finished. Results are in $(pwd)/board_results_${LABEL}.txt"
