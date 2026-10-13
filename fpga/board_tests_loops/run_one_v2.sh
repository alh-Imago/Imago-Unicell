#!/bin/sh
# run_one_v2.sh -- ledger #1138: clone of run_one.sh, serial read by watch_serial.py opened BEFORE the load.
# run_one.sh NAME [PORT] -- the manual sequence, for ONE test: load NAME.fs, set the serial port, show what the board prints for 6 seconds.
# e.g.   sudo ./run_one.sh adder_stream        (you may need sudo for the loader; the port is /dev/ttyUSB1 unless you name it)
cd "$(dirname "$0")" || exit 1
PORT=${2:-/dev/ttyUSB1}
# reader v2 (#1138): open the serial port BEFORE the load and keep it open
OUT=$(mktemp); python3 watch_serial.py "$PORT" "$OUT" ${SECS:-12} > /dev/null 2>&1 &
WPID=$!
sleep 1
openFPGALoader -b tangnano20k "$1.fs" || { kill $WPID 2>/dev/null; rm -f "$OUT" "$OUT.log"; exit 1; }
# the loader re-attaches the USB port for about 2 s after loading; reading earlier gives silence or the old design
wait $WPID
cat "$OUT"; rm -f "$OUT" "$OUT.log"
