#!/bin/sh
# run_one.sh NAME [PORT] -- the manual sequence, for ONE test: load NAME.fs, set the serial port, show what the board prints for 6 seconds.
# e.g.   sudo ./run_one.sh adder_stream        (you may need sudo for the loader; the port is /dev/ttyUSB1 unless you name it)
cd "$(dirname "$0")" || exit 1
PORT=${2:-/dev/ttyUSB1}
# a second load onto a running design did not take effect on the real board: send the chip back to power-up state first
openFPGALoader -b tangnano20k --reset
sleep 2
openFPGALoader -b tangnano20k "$1.fs" || exit 1
sleep 1.5
stty -F "$PORT" 115200 raw -echo
timeout 6 cat "$PORT"
