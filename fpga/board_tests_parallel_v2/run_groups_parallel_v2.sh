#!/bin/sh
# run_groups_parallel_v2.sh -- ledger #1182: clone of run_groups_parallel_v1.sh. New: sudo ONLY=P ./run_groups_parallel_v2.sh runs just those groups (v2 rebuilds P only; Q and R are the v1 bitstreams, unchanged).
# run_groups.sh -- ledger #1025 (Linux): the ten on-board tests as TWO bitstreams of five (groups/group_A.fs, groups/group_B.fs).
# Each is loaded ONCE after a fresh power-up of the board (on this PC the board's USB-serial path went silent after the 2nd-4th load, but the
# first load after a power-up always worked). Each bitstream prints the five result lines in turn (one test every 2.5 s, 12.5 s per round).
# Needs: openFPGALoader, python3, root (sudo). Usage:  sudo ./run_groups.sh [/dev/ttyUSB1]
cd "$(dirname "$0")" || exit 1
for f in groups/group_P.fs groups/group_P.json board_collect_parallel_v1.py watch_serial.py; do
  if [ ! -f "$f" ]; then
    echo "MISSING FILE: $(pwd)/$f"
    echo "Unzip the whole unicell_board_tests_parallel.zip into this folder (it contains a 'groups' folder), then run this again."
    exit 1
  fi
done
rm -rf raw; mkdir raw
wait_ports() { i=0; while [ $i -lt 25 ]; do
    if [ -n "$1" ]; then [ -e "$1" ] && return 0; else [ "$(ls /dev/ttyUSB* 2>/dev/null | wc -l)" -ge 2 ] && return 0; fi
    sleep 1; i=$((i+1)); done; return 1; }
for G in ${ONLY:-P Q R}; do
  names=$(python3 -c "import json,sys;print(' '.join(json.load(open('groups/group_$G.json'))['tests']))")
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- group $G: switch the board OFF (hub switch), wait 5 s, switch it ON, then press Enter ---"
    read dummy
    echo "waiting 20 s for the board to finish booting its demo ..."; sleep ${BOOTWAIT:-20}
    wait_ports "$1" || echo "ports did not come back"
    echo "[group $G] loading ($names) ..."
    PRE=${1:-/dev/ttyUSB1}; rm -f "raw/group_$G.pre" "raw/group_$G.pre.log"
    python3 watch_serial.py "$PRE" "raw/group_$G.pre" ${SECS:-40} > /dev/null 2>&1 &
    WPID=$!
    sleep 1
    openFPGALoader -b tangnano20k "groups/group_$G.fs" > "raw/group_$G.loader.txt" 2>&1; rc=$?
    wait $WPID; sleep 1
    P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
    cp "raw/group_$G.pre" "raw/group_$G.bin" 2>/dev/null || : > "raw/group_$G.bin"
    echo "[group $G] $(wc -c < "raw/group_$G.bin") bytes read from ${P:-no port} (loader exit $rc)"
    [ -s "raw/group_$G.bin" ] && break
    echo "silent: power-cycle and try again (attempt $attempt of 3)"
    attempt=$((attempt+1))
  done
  for n in $names; do
    cp "raw/group_$G.bin" "raw/$n.bin"; echo "$rc" > "raw/$n.rc"; cp "raw/group_$G.loader.txt" "raw/$n.loader.txt"
    echo "group $G, ${P:-no port}, attempt $attempt" > "raw/$n.ports"
  done
done
python3 board_collect_parallel_v1.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
