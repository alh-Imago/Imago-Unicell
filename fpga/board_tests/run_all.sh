#!/bin/sh
# run_all.sh -- ledger #1023 (Linux): load each self-checking test bitstream onto the Tang Nano 20K, capture what the board prints on its
# USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
# Plain shell sequence (the same one the diagnostic proved): load, wait 3 s, stty, cat for 7 s. No python serial library involved.
# Needs: openFPGALoader, python3, the board plugged in by USB-C, and root (sudo ./run_all.sh) or the dialout group.
# Usage:  sudo ./run_all.sh              (serial port /dev/ttyUSB1)
#         sudo ./run_all.sh /dev/ttyUSB1 (name it yourself)
cd "$(dirname "$0")" || exit 1

rm -rf raw; mkdir raw
count=0
# optional controls (use:  sudo env ONLY="relay_chain ram_hold" PAUSE=10 ./run_all.sh )
#   ONLY  = run just these tests;   PAUSE = seconds to wait before each load (default 0);   BATCH = tests between replug prompts (default 4)
for f in *.fs; do
  n=${f%.fs}
  if [ -n "$ONLY" ]; then case " $ONLY " in *" $n "*) ;; *) continue ;; esac; fi
  [ -n "$PAUSE" ] && sleep "$PAUSE"
  # the real board stops answering after about 5 loads in a row (ledger #1024): ask for an unplug/replug every BATCH tests (default 4)
  if [ "$count" -ge "${BATCH:-4}" ]; then
    echo "--- $count tests done. UNPLUG the board's USB cable, plug it back in, wait 5 seconds, then press Enter ---"
    read dummy
    count=0
  fi
  count=$((count+1))
  echo "[$n] loading ..."
  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  sleep 3
  for try in 1 2 3; do
    # the USB ports can change number after many loads: use the one named on the command line, else the highest-numbered ttyUSB
    # listen on EVERY ttyUSB port at once (or only the one named on the command line) and keep the capture of whichever one speaks
    PORTS=${1:-$(ls /dev/ttyUSB* 2>/dev/null)}
    echo "ports now: $(echo $PORTS) (try $try)" >> "raw/$n.ports"
    : > "raw/$n.bin"
    for P in $PORTS; do
      stty -F "$P" 115200 raw -echo 2>>"raw/$n.ports"
      ( timeout 7 cat "$P" > "raw/$n.$(basename $P).bin" 2>/dev/null ) &
    done
    wait
    for P in $PORTS; do
      b=$(wc -c < "raw/$n.$(basename $P).bin" 2>/dev/null || echo 0)
      echo "  $(basename $P): $b bytes" >> "raw/$n.ports"
      [ "$b" -gt "$(wc -c < "raw/$n.bin")" ] && cp "raw/$n.$(basename $P).bin" "raw/$n.bin" && echo "  data came on $(basename $P)" >> "raw/$n.ports"
    done
    [ -s "raw/$n.bin" ] && break
    sleep 2
  done
  dmesg 2>/dev/null | grep -i -E "ftdi|ttyUSB|usb 3-|usb 1-|usb 2-" | tail -4 >> "raw/$n.ports"
  echo "[$n] $(wc -c < "raw/$n.bin") bytes   $(grep -h 'data came on' "raw/$n.ports" | tail -1)"
done
python3 board_collect.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
