#!/bin/sh
# run_c1_v3.sh -- ledger #1218 (clone of run_c1_v2.sh, which is left unchanged): finds the Tang's serial port and the ESP32's by their fixed names in /dev/serial/by-id, so port numbers can shift when a board is replugged without breaking the run.
# Same wiring and sketch as v2 (Tang 86 -> ESP32 IO16, ESP32 IO17 -> Tang 72, Tang 53 -> ESP32 IO21, GND-GND; sketch unicell_c1_interrupts_v2).
# Usage:   sudo LABEL=on ESPPORT=auto ./run_c1_v3.sh        (ESPPORT=auto records the ESP32's lines from its CP210x port; close the Arduino Serial Monitor first. Leave ESPPORT unset to skip it.)
#          ONLY=c1_quiet runs just one build. TANGPORT=/dev/ttyUSBn overrides the Tang's serial port.
cd "$(dirname "$0")" || exit 1
for f in groups/c1_quiet.fs groups/c1_storm.fs board_collect_c1_v2.py watch_serial.py; do
  if [ ! -f "$f" ]; then echo "MISSING FILE: $(pwd)/$f  (unzip the whole zip into this folder)"; exit 1; fi
done
mkdir -p raw; LABEL=${LABEL:-run}; case "$LABEL" in *[!A-Za-z0-9_-]*) echo "LABEL may only use letters, digits, - and _"; exit 1;; esac
find_tang() { if [ -n "$TANGPORT" ]; then [ -e "$TANGPORT" ] && echo "$TANGPORT"; return; fi; ls /dev/serial/by-id/usb-SIPEED*-if01-port0 2>/dev/null | head -1; }
find_esp() { if [ "$ESPPORT" = "auto" ]; then ls /dev/serial/by-id/usb-Silicon_Labs_CP210*-port0 2>/dev/null | head -1; else echo "$ESPPORT"; fi; }
show_ports() { echo "  serial ports now:"; ls -l /dev/serial/by-id/ 2>&1 | sed 's/^/    /'; }
for N in ${ONLY:-c1_quiet c1_storm}; do
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
    python3 watch_serial.py "$PRE" "raw/${LABEL}_$N.pre" ${SECS:-50} > /dev/null 2>&1 &
    WPID=$!
    EPID=""
    if [ -n "$ESP" ]; then python3 watch_serial.py "$ESP" "raw/${LABEL}_$N.esp32" ${SECS:-50} > /dev/null 2>&1 & EPID=$!; fi
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
python3 board_collect_c1_v2.py "$LABEL"
echo
echo "Finished. Results are in $(pwd)/board_results_${LABEL}.txt"
