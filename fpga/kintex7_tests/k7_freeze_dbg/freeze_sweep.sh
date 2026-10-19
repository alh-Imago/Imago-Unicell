#!/bin/sh
# freeze_sweep.sh START STOP STEP -- for each count T: restart, freeze at T, read. About 60 ms per count; writes sweep.log and sweep.csv.
cd "$(dirname "$0")" || exit 1
A=${1:?usage: sh freeze_sweep.sh START STOP STEP}; B=${2:?}; S=${3:?}
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; for {set T $A} {\$T <= $B} {incr T $S} { fz_go \$T; after 20; fz_read \$T }; shutdown" 2>&1 | tee sweep.log | grep -v SNAP
python3 decode_freeze.py sweep.log sweep.csv > sweep_decoded.txt && echo "wrote sweep_decoded.txt and sweep.csv"
