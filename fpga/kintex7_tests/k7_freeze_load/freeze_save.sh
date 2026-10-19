#!/bin/sh
# freeze_save.sh T -- restart the run, freeze at count T, read the whole state and keep it in saved_T.txt (one SNAP line).
cd "$(dirname "$0")" || exit 1
T=${1:?usage: sh freeze_save.sh COUNT}
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source freeze_lib.tcl; fz_go $T; after 30; fz_read saved_$T; shutdown" 2>&1 | tee freeze_save_$T.log | grep -v '^SNAP'
grep '^SNAP' freeze_save_$T.log > saved_$T.txt && echo "saved the state frozen at count $T in saved_$T.txt"
python3 decode_freeze.py saved_$T.txt
