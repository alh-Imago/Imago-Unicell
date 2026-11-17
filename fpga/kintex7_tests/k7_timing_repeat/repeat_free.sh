#!/bin/sh
# repeat_free.sh [N] -- TEST A. Restart the Tang tree on the card N times (default 2000) with no freeze and read the result clock each time.
# Needs the k7_freeze_load (v3) bitstream loaded (magic 46525A33). Writes results/free_N.log and prints the summary.
cd "$(dirname "$0")" || exit 1
N=${1:-2000}
mkdir -p results
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source tr_lib.tcl; tr_read start; tr_free_loop $N 5; shutdown" > results/free_$N.log 2>&1
python3 check_repeat.py results/free_$N.log
