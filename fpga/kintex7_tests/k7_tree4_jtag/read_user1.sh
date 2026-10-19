#!/bin/sh
# read_user1.sh -- step C: read the design's JTAG user register (needs the k7_tree4_jtag bitstream loaded). Selects USER1 (IR 0x02)
# and shifts 96 bits out as three 32-bit words. Reads only: no configuration instruction is sent.
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; set w [drscan xc7.tap 32 0 32 0 32 0]; puts \"USER1 \$w\"; shutdown" 2>&1 | tee read_user1.log
python3 decode_user1.py read_user1.log
