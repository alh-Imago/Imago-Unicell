#!/bin/sh
# measure_clock.sh -- read the design's clock counter twice, 10 s apart (OpenOCD's own sleep), and work out the real clock frequency.
# Needs the k7_tree4_jtag bitstream loaded. Reads only. The two scans are separated by a 10,000 ms host sleep plus the time of one scan
# (a few milliseconds at most through USB), so the result is good to roughly 0.1 %, not better.
cd "$(dirname "$0")" || exit 1
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; set a [drscan xc7.tap 32 0 32 0 32 0]; sleep 10000; set b [drscan xc7.tap 32 0 32 0 32 0]; puts \"CLK1 \$a\"; puts \"CLK2 \$b\"; shutdown" 2>&1 | tee measure_clock.log
python3 decode_clock.py measure_clock.log 10.0
