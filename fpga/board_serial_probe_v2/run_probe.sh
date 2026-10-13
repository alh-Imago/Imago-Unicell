#!/bin/sh
# run_probe.sh -- ledger #1131: load each serial-probe bitstream ONCE (no reload on silence), capture the line for SECS seconds (default 20), judge it with check_probe.py.
# Usage:  sudo ./run_probe.sh [/dev/ttyUSB1]      options (env):  SECS=20  ONLY="serial_probe2_fast"  PAUSE=0
cd "$(dirname "$0")" || exit 1
rm -rf raw; mkdir raw; : > probe_results.txt
echo "Waiting 20 s for the board to finish booting its demo ..."; sleep 20
for f in serial_probe*.fs; do
  n=${f%.fs}
  if [ -n "$ONLY" ]; then case " $ONLY " in *" $n "*) ;; *) continue ;; esac; fi
  [ -n "$PAUSE" ] && sleep "$PAUSE"
  echo "[$n] loading ..."
  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  sleep 3
  i=0; while [ $i -lt 25 ]; do [ -e "${1:-/dev/ttyUSB1}" ] && break; sleep 1; i=$((i+1)); done
  sleep 1
  P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
  stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts 2>>"raw/$n.ports"
  timeout ${SECS:-20} cat "$P" > "raw/$n.bin" 2>>"raw/$n.ports"
  echo "[$n] $(wc -c < "raw/$n.bin") bytes from $P"
  if [ ! -s "raw/$n.bin" ]; then      # silent: look at every other ttyUSB for 6 s, keep the first that talks
    for Q in $(ls /dev/ttyUSB* 2>/dev/null | sort -V); do
      [ "$Q" = "$P" ] && continue
      stty -F "$Q" 115200 raw -echo -hupcl clocal -crtscts 2>>"raw/$n.ports"
      timeout 6 cat "$Q" > "raw/$n.alt" 2>>"raw/$n.ports"
      echo "[$n] other port $Q: $(wc -c < "raw/$n.alt") bytes"
      [ -s "raw/$n.alt" ] && cp "raw/$n.alt" "raw/$n.bin" && break
    done
  fi
  echo "[$n] LED check: is LED1 toggling about every second (card is transmitting)? LED0 blinking, LED3 on?"
  { echo "== $n"; python3 check_probe.py "raw/$n.bin"; } | tee -a probe_results.txt
  dmesg 2>/dev/null | grep -i -E "ftdi|ttyUSB" | tail -3 >> "raw/$n.ports"
done
echo; echo "Finished. Results are in $(pwd)/probe_results.txt  (keep the raw/ folder if anything is not CLEAN)"
