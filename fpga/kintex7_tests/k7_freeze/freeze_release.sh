#!/bin/sh
# freeze_release.sh -- unfreeze; the run carries on from the frozen state. Reads after 200 ms.
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; fz_read before; fz_release; after 200; fz_read after; shutdown" 2>&1 | tee freeze_release.log
python3 decode_freeze.py freeze_release.log
