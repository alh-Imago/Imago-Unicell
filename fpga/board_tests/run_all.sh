#!/bin/sh
# run_all.sh -- ledger #1023 (Linux): load each self-checking test bitstream onto the Tang Nano 20K, capture what the board prints on its
# USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
# Plain shell sequence (the same one the diagnostic proved): load, wait 3 s, stty, cat for 7 s. No python serial library involved.
# Needs: openFPGALoader, python3, the board plugged in by USB-C, and root (sudo ./run_all.sh) or the dialout group.
# Usage:  sudo ./run_all.sh              (serial port /dev/ttyUSB1)
#         sudo ./run_all.sh /dev/ttyUSB1 (name it yourself)
cd "$(dirname "$0")" || exit 1

rm -rf raw; mkdir raw
for f in *.fs; do
  n=${f%.fs}
  echo "[$n] loading ..."
  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  sleep 3
  for try in 1 2 3; do
    # the USB ports can change number after many loads: use the one named on the command line, else the highest-numbered ttyUSB
    P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
    echo "$(ls /dev/ttyUSB* 2>&1 | tr '\n' ' ') -> using $P (try $try)" >> "raw/$n.ports"
    stty -F "$P" 115200 raw -echo 2>>"raw/$n.ports"
    timeout 7 cat "$P" > "raw/$n.bin" 2>>"raw/$n.ports"
    [ -s "raw/$n.bin" ] && break
    sleep 2
  done
  echo "[$n] $(wc -c < "raw/$n.bin") bytes   ($(tail -1 "raw/$n.ports"))"
done
python3 board_collect.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
