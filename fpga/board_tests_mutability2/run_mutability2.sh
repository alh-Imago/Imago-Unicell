#!/bin/sh
# run_mutability2.sh -- ledger #1088 (Linux). Test 2 of the mutability proof on the Tang Nano 20K: mixed-family card, command cell reconfigures the carrier, sequencer streams, clocks counted.
#   sudo ./run_mutability2.sh [PORT]    load mutability2.fs, wait, then run mutability2_host.py. Keep mutability2_results.txt and mutability2_results.json.
# The bitstream goes to SRAM only (lost at power-off). If the board stops answering after several loads in a row, unplug and replug the USB cable.
cd "$(dirname "$0")" || exit 1
openFPGALoader -b tangnano20k mutability2.fs || { echo "load failed"; exit 1; }
echo "loaded mutability2.fs; waiting 4 s for the board and its serial port to settle"; sleep 4
P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
echo "serial port: $P"
python3 mutability2_host.py "$P"
