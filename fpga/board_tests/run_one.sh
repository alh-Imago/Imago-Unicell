#!/bin/sh
# run_one.sh NAME [PORT] -- the manual sequence, for ONE test: load NAME.fs, set the serial port, show what the board prints for 6 seconds.
# e.g.   sudo ./run_one.sh adder_stream        (you may need sudo for the loader; the port is /dev/ttyUSB1 unless you name it)
cd "$(dirname "$0")" || exit 1
PORT=${2:-/dev/ttyUSB1}
openFPGALoader -b tangnano20k "$1.fs" || exit 1
sleep 1.5
stty -F "$PORT" 115200 raw -echo
timeout 6 cat "$PORT"
