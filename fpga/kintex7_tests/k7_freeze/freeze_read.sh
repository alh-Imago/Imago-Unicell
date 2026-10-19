#!/bin/sh
# freeze_read.sh -- read the grid snapshot, change nothing (the command valid bit is clear).
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; fz_read live; shutdown" 2>&1 | tee freeze_read.log
python3 decode_freeze.py freeze_read.log
