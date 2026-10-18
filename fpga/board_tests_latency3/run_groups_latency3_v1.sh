#!/bin/sh
# run_groups_latency3_v1.sh -- ledger #1209: runs the two T3 two-input latency bitstreams (groups/lt3_idle.fs, groups/lt3_busy.fs), one load per power-up of the Tang.
# Wiring needed: TWO jumpers: Tang pin 86 -> pin 72 AND pin 53 -> pin 71 (right header, far end). Nothing else on 72 or 71 (take the tilt switch and hand jumper out).
# Each bitstream runs for about 10 s after loading, then prints its result line every 1.5 s.
# Needs: openFPGALoader, python3, root (sudo). Usage:  sudo ./run_groups_latency3_v1.sh [/dev/ttyUSB1]      (ONLY=lt3_idle runs just one)
cd "$(dirname "$0")" || exit 1
for f in groups/lt3_idle.fs groups/lt3_busy.fs board_collect_latency3_v1.py watch_serial.py; do
  if [ ! -f "$f" ]; then echo "MISSING FILE: $(pwd)/$f  (unzip the whole zip into this folder)"; exit 1; fi
done
rm -rf raw; mkdir raw
wait_ports() { i=0; while [ $i -lt 25 ]; do
    if [ -n "$1" ]; then [ -e "$1" ] && return 0; else [ "$(ls /dev/ttyUSB* 2>/dev/null | wc -l)" -ge 2 ] && return 0; fi
    sleep 1; i=$((i+1)); done; return 1; }
for N in ${ONLY:-lt3_idle lt3_busy}; do
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- $N: switch the board OFF (unplug USB), wait 5 s, plug it ON, then press Enter ---"
    read dummy
    echo "waiting 20 s for the board to finish booting its demo ..."; sleep ${BOOTWAIT:-20}
    wait_ports "$1" || echo "ports did not come back"
    echo "[$N] loading ..."
    PRE=${1:-/dev/ttyUSB1}; rm -f "raw/$N.pre" "raw/$N.pre.log"
    python3 watch_serial.py "$PRE" "raw/$N.pre" ${SECS:-50} > /dev/null 2>&1 &
    WPID=$!
    sleep 1
    openFPGALoader -b tangnano20k "groups/$N.fs" > "raw/$N.loader.txt" 2>&1; rc=$?
    wait $WPID; sleep 1
    cp "raw/$N.pre" "raw/$N.bin" 2>/dev/null || : > "raw/$N.bin"
    echo "[$N] $(wc -c < "raw/$N.bin") bytes read (loader exit $rc)"
    [ -s "raw/$N.bin" ] && break
    echo "silent: power-cycle and try again (attempt $attempt of 3)"
    attempt=$((attempt+1))
  done
done
python3 board_collect_latency3_v1.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
