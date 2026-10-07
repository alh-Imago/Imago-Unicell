#!/bin/sh
# run_groups.sh -- ledger #1025 (Linux): the ten on-board tests as TWO bitstreams of five (groups/group_A.fs, groups/group_B.fs).
# Each is loaded ONCE after a fresh power-up of the board (on this PC the board's USB-serial path went silent after the 2nd-4th load, but the
# first load after a power-up always worked). Each bitstream prints the five result lines in turn (one test every 2.5 s, 12.5 s per round).
# Needs: openFPGALoader, python3, root (sudo). Usage:  sudo ./run_groups.sh [/dev/ttyUSB1]
cd "$(dirname "$0")" || exit 1
rm -rf raw; mkdir raw
wait_ports() { i=0; while [ $i -lt 25 ]; do
    if [ -n "$1" ]; then [ -e "$1" ] && return 0; else [ "$(ls /dev/ttyUSB* 2>/dev/null | wc -l)" -ge 2 ] && return 0; fi
    sleep 1; i=$((i+1)); done; return 1; }
for G in A B; do
  names=$(python3 -c "import json,sys;print(' '.join(json.load(open('groups/group_$G.json'))['tests']))")
  attempt=1
  while [ $attempt -le 3 ]; do
    echo "--- group $G: switch the board OFF (hub switch), wait 5 s, switch it ON, then press Enter ---"
    read dummy
    echo "waiting 20 s for the board to finish booting its demo ..."; sleep 20
    wait_ports "$1" || echo "ports did not come back"
    echo "[group $G] loading ($names) ..."
    openFPGALoader -b tangnano20k "groups/group_$G.fs" > "raw/group_$G.loader.txt" 2>&1; rc=$?
    sleep 3; wait_ports "$1"; sleep 1
    P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
    : > "raw/group_$G.bin"
    if [ -n "$P" ]; then
      stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts 2>/dev/null
      timeout 16 cat "$P" > "raw/group_$G.bin" 2>/dev/null
    fi
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
python3 board_collect.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
