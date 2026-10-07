#!/bin/sh
# run_all.sh -- ledger #1023 (Linux): load each self-checking test bitstream onto the Tang Nano 20K, capture what the board prints on its
# USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
# Plain shell sequence (the same one the diagnostic proved): load, wait 3 s, stty, cat for 7 s. No python serial library involved.
# Needs: openFPGALoader, python3, the board plugged in by USB-C, and root (sudo ./run_all.sh) or the dialout group.
# Usage:  sudo ./run_all.sh              (serial port /dev/ttyUSB1)
#         sudo ./run_all.sh /dev/ttyUSB1 (name it yourself)
cd "$(dirname "$0")" || exit 1
PORT=${1:-/dev/ttyUSB1}
rm -rf raw; mkdir raw
for f in *.fs; do
  n=${f%.fs}
  echo "[$n] loading ..."
  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  sleep 3
  stty -F "$PORT" 115200 raw -echo 2>/dev/null
  timeout 7 cat "$PORT" > "raw/$n.bin" 2>/dev/null
  echo "[$n] $(wc -c < "raw/$n.bin") bytes"
done
python3 board_collect.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
