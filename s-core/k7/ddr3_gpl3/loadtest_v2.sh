#!/bin/sh
# loadtest_v2.sh - clone of loadtest.sh (v1 kept unchanged).  Same test per load, but a USB drop is told apart from a design failure.
# v1 counted a dropped USB cable (FT232H falls off the bus, "usb bulk write failed") as a failed load.  v2 waits for the FT232H to
# come back (lsusb 0403:6014), retries that load up to TRIES times (default 3), and counts USB retries separately.
# A load only counts as a design failure if the load itself finished and the tests still failed with no USB error in the logs.
# Run in the nix shell (make, openFPGALoader, openocd on the path):
#   sh loadtest_v2.sh /home/alan/openFPGALoader/build/demo-projects/sc_k7_ddr3_fix 10
# Logs: $HOME/loadtest_logs/ (loadI_tT.log = load I, try T).  Loads SRAM only, never the flash.
D=${1:?usage: sh loadtest_v2.sh BUILD_DIR N}; N=${2:-10}; MK=${MK:-Makefile.v2}; TRIES=${TRIES:-3}
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}; L=$HOME/loadtest_logs; mkdir -p "$L"
which openocd >/dev/null || { echo "openocd not on the path: run  nix shell nixpkgs#openocd  first"; exit 1; }
USBERR="usb bulk write failed|unable to claim|No such device|Input/output error|LIBUSB|libusb|wrong mark|unable to open"
wait_usb() { n=0; while [ $n -lt 30 ]; do lsusb 2>/dev/null | grep -q "0403:6014" && return 0; sleep 1; n=$((n+1)); done; return 1; }
clean=0; usb_retries=0; design_fail=0; gave_up=0; i=1
while [ $i -le $N ]; do
  t=1; result=""
  while [ $t -le $TRIES ]; do
    P="$L/load${i}_t$t"
    wait_usb || { echo "load $i try $t: FT232H not on the USB bus (replug the cable)"; usb_retries=$((usb_retries+1)); t=$((t+1)); sleep 5; continue; }
    pkill -9 openocd 2>/dev/null; sleep 1
    ( cd "$D" && make -f $MK program JTAG_LINK="-c ft232" ) > "$P.log" 2>&1
    if ! grep -q "done 1" "$P.log"; then
      if grep -q -E "$USBERR" "$P.log"; then echo "load $i try $t: USB drop during load, retrying"; usb_retries=$((usb_retries+1)); t=$((t+1)); sleep 5; continue
      else result="design:load not done without USB error"; break; fi
    fi
    sleep 4
    ( cd "$S_CORE" && python3 ddr3test.py jtag 2048 ) > "$P.normal.log" 2>&1; pkill -9 openocd 2>/dev/null
    ( cd "$S_CORE" && python3 ddr3test.py jtag 2048 stride ) > "$P.stride.log" 2>&1; pkill -9 openocd 2>/dev/null
    a=$(grep -q "ALL OK" "$P.normal.log" && echo ok || echo FAIL); b=$(grep -q "ALL OK" "$P.stride.log" && echo ok || echo FAIL)
    c=-
    if [ $((i % 5)) -eq 0 ]; then ( cd "$S_CORE" && python3 scbatch.py jtag jobs_telemetry.json ) > "$P.batch.log" 2>&1; pkill -9 openocd 2>/dev/null; c=$(grep -o "[0-9]* of [0-9]* jobs correct" "$P.batch.log" | tail -1); [ -n "$c" ] || c=FAIL; fi
    if [ $a = ok ] && [ $b = ok ] && [ "$c" != FAIL ]; then result="clean  normal $a  stride $b  batch $c"; break; fi
    if cat "$P.normal.log" "$P.stride.log" "$P.batch.log" 2>/dev/null | grep -q -E "$USBERR"; then echo "load $i try $t: USB error in the tests, retrying"; usb_retries=$((usb_retries+1)); t=$((t+1)); sleep 5; continue; fi
    result="design:tests failed with no USB error  normal $a  stride $b  batch $c"; break
  done
  [ -n "$result" ] || result="gaveup:USB failed $TRIES times"
  case "$result" in
    clean*) clean=$((clean+1)) ;;
    design*) design_fail=$((design_fail+1)) ;;
    gaveup*) gave_up=$((gave_up+1)) ;;
  esac
  echo "load $i: $result  (tries used: $t)"
  i=$((i+1))
done
echo "$N loads: $clean clean, $design_fail design failures, $gave_up given up on USB, $usb_retries USB retries in total"
