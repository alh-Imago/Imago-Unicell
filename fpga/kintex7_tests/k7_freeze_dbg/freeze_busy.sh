#!/bin/sh
# freeze_busy.sh -- step 1: every single clock count over the three busy stretches of the run (loads at 44-56, 344-356, 1544-1556 and
# the results around 1562). Each stretch is its own file so nothing is overwritten: busy_40_70, busy_340_370, busy_1540_1570 (.log .csv _decoded.txt).
cd "$(dirname "$0")" || exit 1
for R in "40 70" "340 370" "1540 1570"; do
  set -- $R
  openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; for {set T $1} {\$T <= $2} {incr T 1} { fz_go \$T; after 20; fz_read \$T }; shutdown" > busy_$1_$2.log 2>&1
  python3 decode_freeze.py busy_$1_$2.log busy_$1_$2.csv > busy_$1_$2_decoded.txt && echo "wrote busy_$1_$2.csv"
done
