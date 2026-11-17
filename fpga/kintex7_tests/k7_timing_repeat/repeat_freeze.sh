#!/bin/sh
# repeat_freeze.sh [M] [T ...] -- TEST B. For each freeze count T (default 60 346 700 1000 1400), M times (default 50): restart and freeze at T, read, release, read.
# The clock of the last result must stay what a free run gives. Needs the k7_freeze_load (v3) bitstream.
cd "$(dirname "$0")" || exit 1
M=${1:-50}
[ $# -gt 0 ] && shift
TS=${*:-60 346 700 1000 1400}
mkdir -p results
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source tr_lib.tcl; tr_go 0xFFFFFFFF; after 5; tr_read base; tr_freeze_loop {$TS} $M 5; shutdown" > results/freeze_$M.log 2>&1
python3 check_repeat.py results/freeze_$M.log
