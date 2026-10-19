#!/bin/sh
# freeze_saveload_test.sh T [D] -- the round trip: freeze at T and save; run to D (default 1400, a different state); load the saved state; read back; release; check.
cd "$(dirname "$0")" || exit 1
T=${1:?usage: sh freeze_saveload_test.sh COUNT [OTHER_COUNT]}
D=${2:-1400}
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; fz_saveload $T $D; shutdown" 2>&1 | tee freeze_saveload_$T.log | grep -v '^SNAP'
python3 check_saveload.py freeze_saveload_$T.log
