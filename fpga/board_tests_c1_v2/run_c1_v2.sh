#!/bin/sh
# run_c1_v2.sh -- ledger #1217: runs the two C1 ESP32 interrupt bitstreams (groups/c1_quiet.fs, groups/c1_storm.fs), one load per power-up of the Tang.
# Wiring needed (ESP32 sketch tools/esp32/unicell_c1_interrupts running): Tang 86 -> ESP32 IO16, ESP32 IO17 -> Tang 72, Tang 53 -> ESP32 IO21, GND-GND. Remove the T2/T3 jumpers first.
# Run once per ESP32 state, giving it a name:   sudo LABEL=loopON ./run_c1_v2.sh      then after typing l0 in the ESP32 serial monitor:   sudo LABEL=loopOFF ./run_c1_v2.sh
# Each bitstream runs for about 10 s after loading, then prints its result line every 1.5 s.
# Optional: ESPPORT=/dev/ttyUSBn  also records the ESP32's own status lines (close the Arduino Serial Monitor first: only one program can use the port).
# Needs: openFPGALoader, python3, root (sudo). Usage:  sudo ./run_c1_v2.sh [/dev/ttyUSB1]      (ONLY=c1_quiet runs just one; LABEL names the ESP32 state)
cd "$(dirname "$0")" || exit 1
for f in groups/c1_quiet.fs groups/c1_storm.fs board_collect_c1_v2.py watch_serial.py; do
  if [ ! -f "$f" ]; then echo "MISSING FILE: $(pwd)/$f  (unzip the whole zip into this folder)"; exit 1; fi
done
mkdir -p raw; LABEL=${LABEL:-run}; case "$LABEL" in *[!A-Za-z0-9_-]*) echo "LABEL may only use letters, digits, - and _"; exit 1;; esac
wait_ports() { i=0; while [ $i -lt 25 ]; do
    if [ -n "$1" ]; then [ -e "$1" ] && return 0; else [ "$(ls /dev/ttyUSB* 2>/dev/null | wc -l)" -ge 2 ] && return 0; fi
    sleep 1; i=$((i+1)); done; return 1; }
for N in ${ONLY:-c1_quiet c1_storm}; do
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- $N: switch the board OFF (unplug USB), wait 5 s, plug it ON, then press Enter ---"
    read dummy
    echo "waiting 20 s for the board to finish booting its demo ..."; sleep ${BOOTWAIT:-20}
    wait_ports "$1" || echo "ports did not come back"
    echo "[$N] loading ..."
    PRE=${1:-/dev/ttyUSB1}; rm -f "raw/${LABEL}_$N.pre" "raw/${LABEL}_$N.pre.log"
    python3 watch_serial.py "$PRE" "raw/${LABEL}_$N.pre" ${SECS:-50} > /dev/null 2>&1 &
    WPID=$!
    if [ -n "$ESPPORT" ]; then python3 watch_serial.py "$ESPPORT" "raw/${LABEL}_$N.esp32" ${SECS:-50} > /dev/null 2>&1 & EPID=$!; fi
    sleep 1
    openFPGALoader -b tangnano20k "groups/$N.fs" > "raw/${LABEL}_$N.loader.txt" 2>&1; rc=$?
    wait $WPID; [ -n "$EPID" ] && wait $EPID; sleep 1
    cp "raw/${LABEL}_$N.pre" "raw/${LABEL}_$N.bin" 2>/dev/null || : > "raw/${LABEL}_$N.bin"
    echo "[$N] $(wc -c < "raw/${LABEL}_$N.bin") bytes read (loader exit $rc)"
    [ -s "raw/${LABEL}_$N.bin" ] && break
    echo "silent: power-cycle and try again (attempt $attempt of 3)"
    attempt=$((attempt+1))
  done
done
python3 board_collect_c1_v2.py "$LABEL"
echo
echo "Finished. Results are in $(pwd)/board_results_${LABEL}.txt"
