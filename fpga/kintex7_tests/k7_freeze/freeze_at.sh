#!/bin/sh
# freeze_at.sh T -- restart the run, let the card freeze itself at clock count T, read all cells. Writes only the design's own control register (not flash).
cd "$(dirname "$0")" || exit 1
T=${1:?usage: sh freeze_at.sh COUNT}
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; fz_go $T; after 50; fz_read $T; after 200; fz_read ${T}_again; shutdown" 2>&1 | tee freeze_at_$T.log
python3 decode_freeze.py freeze_at_$T.log
