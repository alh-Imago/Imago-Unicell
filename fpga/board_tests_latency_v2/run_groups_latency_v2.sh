#!/bin/sh
# run_groups_latency_v2.sh -- ledger #1207: runs the two T2 latency bitstreams (groups/lat_idle.fs, groups/lat_busy.fs), one load per power-up of the Tang.
# Wiring needed: ONE jumper from Tang pin 86 (right header) to Tang pin 72 (input 1). Nothing on pin 71 is used. Remove the hand jumper from 72.
# Each bitstream runs for about 10 s after loading, then prints its result line every 1.5 s.
# Needs: openFPGALoader, python3, root (sudo). Usage:  sudo ./run_groups_latency_v2.sh [/dev/ttyUSB1]      (ONLY=lat_idle runs just one)
cd "$(dirname "$0")" || exit 1
for f in groups/lat_idle.fs groups/lat_busy.fs board_collect_latency_v2.py watch_serial.py; do
  if [ ! -f "$f" ]; then echo "MISSING FILE: $(pwd)/$f  (unzip the whole zip into this folder)"; exit 1; fi
done
rm -rf raw; mkdir raw
wait_ports() { i=0; while [ $i -lt 25 ]; do
    if [ -n "$1" ]; then [ -e "$1" ] && return 0; else [ "$(ls /dev/ttyUSB* 2>/dev/null | wc -l)" -ge 2 ] && return 0; fi
    sleep 1; i=$((i+1)); done; return 1; }
for N in ${ONLY:-lat_idle lat_busy}; do
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- $N: switch the board OFF (unplug USB), wait 5 s, plug it ON, then press Enter ---"
    read dummy
    echo "waiting 20 s for the board to finish booting its demo ..."; sleep ${BOOTWAIT:-20}
    wait_ports "$1" || echo "ports did not come back"
    echo "[$N] loading ..."
    PRE=${1:-/dev/ttyUSB1}; rm -f "raw/$N.pre" "raw/$N.pre.log"
    python3 watch_serial.py "$PRE" "raw/$N.pre" ${SECS:-40} > /dev/null 2>&1 &
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
python3 board_collect_latency_v2.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
