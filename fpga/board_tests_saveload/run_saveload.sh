#!/bin/sh
# run_saveload.sh -- ledger #1098 (Linux). Save / load / retarget proof on the Tang Nano 20K (flex family looped CORDIC with a self-stop).
#   sudo ./run_saveload.sh [PORT] [sanity|state|zero]     load saveload.fs, wait, then run saveload_host.py.
#     sanity (default): the four short checks.   state: load tang_state_step300.json and let the card run 300 steps by itself (writes tang_result_A.json).   zero: run 300 steps from the first value.
# The bitstream goes to SRAM only (lost at power-off). If the board stops answering after several loads in a row, unplug and replug the USB cable.
cd "$(dirname "$0")" || exit 1
openFPGALoader -b tangnano20k saveload.fs || { echo "load failed"; exit 1; }
echo "loaded saveload.fs; waiting 4 s for the board and its serial port to settle"; sleep 4
P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
echo "serial port: $P"
case "${2:-sanity}" in
  state)  python3 saveload_host.py "$P" --state tang_state_step300.json --steps 300 --label A ;;
  zero)   python3 saveload_host.py "$P" --from-zero --steps 300 --label Z ;;
  *)      python3 saveload_host.py "$P" --sanity ;;
esac
