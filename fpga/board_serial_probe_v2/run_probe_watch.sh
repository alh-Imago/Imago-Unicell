#!/bin/sh
# run_probe_watch.sh -- ledger #1133: the port is opened and watched BEFORE the load; every chunk's arrival time is logged. One variant per run.
# Usage:  sudo ./run_probe_watch.sh [/dev/ttyUSB1]      env: ONLY=serial_probe2_fast (default) | serial_probe2_gap   SECS=30   LATE=7 (open the port 7 s AFTER the load instead of before)   READER=cat (with LATE: read with the old stty+cat instead of the Python reader)
cd "$(dirname "$0")" || exit 1
rm -rf raw; mkdir -p raw
n=${ONLY:-serial_probe2_fast}; P=${1:-/dev/ttyUSB1}; S=${SECS:-30}
echo "Waiting 20 s for the board to finish booting its demo ..."; sleep 20
if [ -z "$LATE" ]; then
  python3 watch_serial.py "$P" "raw/$n.watch" "$S" > "raw/$n.watch.summary" 2>&1 &
  W=$!
  sleep 2
  echo "[$n] loading while the port is being watched ..."
  openFPGALoader -b tangnano20k "$n.fs" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  wait $W
else   # LATE=N: load first, open the port N seconds after the load (the old run_probe.sh order, but with this watcher)
  echo "[$n] loading with the port NOT open ..."
  openFPGALoader -b tangnano20k "$n.fs" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  sleep "$LATE"
  if [ "$READER" = "cat" ]; then   # the old reader of run_probe.sh: stty then cat (no arrival log)
    stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts 2>"raw/$n.ports"
    timeout "$S" cat "$P" > "raw/$n.watch"; echo "cat: $(wc -c < "raw/$n.watch") bytes" > "raw/$n.watch.summary"; : > "raw/$n.watch.log"
  else
    python3 watch_serial.py "$P" "raw/$n.watch" "$S" > "raw/$n.watch.summary" 2>&1
  fi
fi
cat "raw/$n.watch.summary"
python3 check_probe.py "raw/$n.watch" | tee probe_watch_results.txt
echo "--- arrival log (time since start, bytes): first 12 and last 6 lines"; head -12 "raw/$n.watch.log"; echo ...; tail -6 "raw/$n.watch.log"
dmesg 2>/dev/null | grep -i -E "ftdi|ttyUSB" | tail -6 > "raw/$n.dmesg"; ls -l /dev/ttyUSB* >> "raw/$n.dmesg" 2>&1
echo; echo "Finished. Keep the raw/ folder and probe_watch_results.txt. LED1 toggling? (card transmitting)"
