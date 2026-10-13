#!/bin/sh
# run_scan.sh -- ledger #1147 (Linux). In-flight capture / restore on the Tang Nano 20K.
#   sudo ./run_scan.sh [PORT] [scan.fs|scan_pure.fs] [extra options for scan_card_host.py, e.g. --damage]
# The script opens the serial port FIRST, then loads the bitstream, then runs the demonstration (Python reader: do not use cat/stty, ledger #1133-#1141).
# The bitstream goes to SRAM only. Power the card off between sessions; if it stops answering after several loads in a row, unplug and replug the USB cable.
cd "$(dirname "$0")" || exit 1
P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
B=${2:-scan.fs}
shift 2 2>/dev/null
echo "serial port: $P   bitstream: $B"
python3 scan_card_host.py "$P" --load "$B" "$@"
