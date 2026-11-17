#!/bin/sh
# loadtest.sh - load the same bitstream onto the card N times and test it after every load (does the DDR3 calibrate and work every time?).
# Per load: make program, wait, ddr3test.py (normal order), ddr3test.py (stride order), and every 5th load also the scbatch telemetry job.  One line per load.
# Run in the nix shell (make, openFPGALoader, openocd on the path), nothing heavy running on the PC:
#   sh loadtest.sh /home/alan/openFPGALoader/build/demo-projects/sc_k7_ddr3_fix 10          (Makefile.v2 is the default; MK=Makefile to change)
# Full output of each run goes to $HOME/loadtest_logs/.  Loads SRAM only, never the flash.
D=${1:?usage: sh loadtest.sh BUILD_DIR N}; N=${2:-10}; MK=${MK:-Makefile.v2}
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}; L=$HOME/loadtest_logs; mkdir -p "$L"
which openocd >/dev/null || { echo "openocd not on the path: run  nix shell nixpkgs#openocd  first"; exit 1; }
ok=0; i=1
while [ $i -le $N ]; do
  pkill -9 openocd 2>/dev/null; sleep 1
  ( cd "$D" && make -f $MK program JTAG_LINK="-c ft232" ) > "$L/load$i.log" 2>&1
  if grep -q "done 1" "$L/load$i.log"; then ld=done; else ld="NOT DONE"; fi
  sleep 4
  ( cd "$S_CORE" && python3 ddr3test.py jtag 2048 ) > "$L/normal$i.log" 2>&1; pkill -9 openocd 2>/dev/null
  ( cd "$S_CORE" && python3 ddr3test.py jtag 2048 stride ) > "$L/stride$i.log" 2>&1; pkill -9 openocd 2>/dev/null
  a=$(grep -q "ALL OK" "$L/normal$i.log" && echo ok || echo FAIL); b=$(grep -q "ALL OK" "$L/stride$i.log" && echo ok || echo FAIL)
  c=-
  if [ $((i % 5)) -eq 0 ]; then ( cd "$S_CORE" && python3 scbatch.py jtag jobs_telemetry.json ) > "$L/batch$i.log" 2>&1; pkill -9 openocd 2>/dev/null; c=$(grep -o "[0-9]* of [0-9]* jobs correct" "$L/batch$i.log" | tail -1); [ -n "$c" ] || c=FAIL; fi
  echo "load $i: $ld  normal $a  stride $b  batch $c"
  [ "$ld" = done ] && [ $a = ok ] && [ $b = ok ] && ok=$((ok+1))
  i=$((i+1))
done
echo "$ok of $N loads fully clean"
