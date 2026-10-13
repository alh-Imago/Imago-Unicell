#!/bin/sh
# run_scan.sh -- ledger #1151 (Linux). In-flight capture / restore on the Tang Nano 20K.
#   sudo ./run_scan.sh [PORT] [scan.fs|scan_pure.fs] [extra options for scan_card_host.py, e.g. --damage]
# The script opens the serial port FIRST, then loads the bitstream, then runs the demonstration (Python reader: do not use cat/stty, ledger #1133-#1141).
# The bitstream goes to SRAM only. Power the card off between sessions; if it stops answering after several loads in a row, unplug and replug the USB cable.
cd "$(dirname "$0")" || exit 1
P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
B=${2:-scan_latex.fs}
[ $# -ge 2 ] && shift 2 || shift $#
echo "serial port: $P   bitstream: $B"
echo "running scan_card_host.py (a PASS/FAIL line per cut follows)"
python3 scan_card_host.py "$P" --load "$B" "$@"
