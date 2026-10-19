#!/bin/sh
# freeze_load.sh FILE [run] -- load the state saved in FILE (a SNAP line from freeze_save.sh) back into the cells and the driver; the grid stays frozen.
# With "run" the grid is released afterwards and read once more.
cd "$(dirname "$0")" || exit 1
F=${1:?usage: sh freeze_load.sh saved_COUNT.txt [run]}
W=$(sed -n 's/^SNAP [^ ]* //p' "$F" | head -1)
RUN=""
[ "$2" = "run" ] && RUN="fz_release; after 150; fz_read after_release;"
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; fz_read before_load; fz_load {$W}; after 10; fz_read after_load; $RUN shutdown" 2>&1 | tee freeze_load.log | grep -v '^SNAP'
python3 decode_freeze.py freeze_load.log
