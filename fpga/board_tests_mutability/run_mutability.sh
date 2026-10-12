#!/bin/sh
# run_mutability.sh -- ledger #1086 (Linux). Test 1 of the mutability proof on the Tang Nano 20K.
#   sudo ./run_mutability.sh host [PORT]   load mutability1h.fs, wait, then run mutability_host.py (the PC sends each configuration and the data; the bitstream never changes)
#   sudo ./run_mutability.sh self [PORT]   load mutability1.fs (it runs the same seven phases by itself) and print the one line it sends back
# PORT defaults to the highest-numbered /dev/ttyUSB*. The bitstream goes to SRAM only (lost at power-off; the flash is not touched).
# The board has been seen to stop answering after about 5 loads in a row (#1024): if that happens, unplug and replug the USB cable.
cd "$(dirname "$0")" || exit 1
mode=${1:-host}; P=${2:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
case "$mode" in
  host) f=mutability1h.fs ;;
  self) f=mutability1.fs ;;
  *) echo "usage: $0 host|self [PORT]"; exit 2 ;;
esac
openFPGALoader -b tangnano20k "$f" || { echo "load failed"; exit 1; }
echo "loaded $f; waiting 4 s for the board and its serial port to settle"; sleep 4
P=${2:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
echo "serial port: $P"
if [ "$mode" = host ]; then
  python3 mutability_host.py "$P"
else
  stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts
  timeout 7 cat "$P" | tr -d '\r' | head -3
  echo "(expect: UCM mutability1 res=P ok=7F to=00 r=12345678,12345588,EDCBA987,00123456,12345600,88885000,12345678)"
fi
