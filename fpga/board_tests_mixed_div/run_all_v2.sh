#!/bin/sh
# run_all_v2.sh -- ledger #1138: clone of run_all.sh with the serial reader replaced by watch_serial.py (opened BEFORE the load). See tools/board_runner_v2.py.
# run_all.sh -- ledger #1023 (Linux): load each self-checking test bitstream onto the Tang Nano 20K, capture what the board prints on its
# USB serial port, and gather everything into ONE file: board_results.txt (also board_results.csv).
# Plain shell sequence (the same one the diagnostic proved): load, wait 3 s, stty, cat for 7 s. No python serial library involved.
# Needs: openFPGALoader, python3, the board plugged in by USB-C, and root (sudo ./run_all.sh) or the dialout group.
# Usage:  sudo ./run_all.sh              (serial port /dev/ttyUSB1)
#         sudo ./run_all.sh /dev/ttyUSB1 (name it yourself)
cd "$(dirname "$0")" || exit 1
rm -rf raw; mkdir raw

# wait (up to 25 s) until the board's USB serial ports exist again
wait_ports() {
  i=0
  while [ $i -lt 25 ]; do
    if [ -n "$1" ]; then [ -e "$1" ] && return 0; else [ "$(ls /dev/ttyUSB* 2>/dev/null | wc -l)" -ge 2 ] && return 0; fi
    sleep 1; i=$((i+1))
  done
  return 1
}
echo "Waiting 20 s for the board to finish booting its demo ..."; sleep ${BOOTWAIT:-20}
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
    echo "waiting 20 s for the board to finish booting its demo ..."; sleep ${BOOTWAIT:-20}
    count=0
  fi
  count=$((count+1))
  echo "[$n] loading ..."
  # reader v2 (#1138): open the serial port BEFORE the load and keep it open; the watcher re-opens it if the device vanishes
  PRE=${1:-/dev/ttyUSB1}; rm -f "raw/$n.pre" "raw/$n.pre.log"
  python3 watch_serial.py "$PRE" "raw/$n.pre" ${SECS:-12} > "raw/$n.pre.summary" 2>&1 &
  WPID=$!
  sleep 1
  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"
  wait $WPID
  sleep 1
  for try in 1 2 3; do
    wait_ports "$1" || echo "  ports did not come back within 25 s" >> "raw/$n.ports"
    sleep 1
    # the USB ports can change number after many loads: use the one named on the command line, else the highest-numbered ttyUSB
    # read ONLY the serial line (the highest-numbered ttyUSB, or the port named on the command line). Never open the programming port
    # (the other ttyUSB): holding it open while the loader runs broke the next load.
    P=${1:-$(ls /dev/ttyUSB* 2>/dev/null | sort -V | tail -1)}
    echo "ports now: $(ls /dev/ttyUSB* 2>&1 | tr '\n' ' ') -> reading $P (try $try)" >> "raw/$n.ports"
    if [ "$try" = 1 ] && [ -s "raw/$n.pre" ]; then cp "raw/$n.pre" "raw/$n.bin"; else : > "raw/$n.bin"; fi
    # ledger #1121: after a load the serial line can come back on EITHER ttyUSB port (the FTDI re-attaches): read the named port first, then every other ttyUSB, keep the one that talks
    for Q in $P $(ls /dev/ttyUSB* 2>/dev/null | sort -V); do
      [ -s "raw/$n.bin" ] && break
      [ -e "$Q" ] || continue
      python3 watch_serial.py "$Q" "raw/$n.try" ${SECS:-8} > /dev/null 2>>"raw/$n.ports"
      echo "  tried $Q: $(wc -c < "raw/$n.try") bytes" >> "raw/$n.ports"
      if [ -s "raw/$n.try" ]; then cp "raw/$n.try" "raw/$n.bin"; P=$Q; break; fi
    done
    echo "  ${P:-none}: $(wc -c < "raw/$n.bin") bytes" >> "raw/$n.ports"
    [ -s "raw/$n.bin" ] && break
    # silent. Recovery, one step per retry:  after try 1 -> load the SAME bitstream again;  after try 2 -> (only with USBRESET=1) a proper
    # USB device reset (the usbreset ioctl, which makes Linux rebind the serial driver; an earlier attempt by authorize-toggling left the board without ports)
    if [ "$try" = 1 ]; then
      echo "  silent: loading $n again" >> "raw/$n.ports"
      openFPGALoader -b tangnano20k "$f" > "raw/$n.loader2.txt" 2>&1; sleep 5
    elif [ "$try" = 2 ] && [ "$USBRESET" = 1 ]; then
      echo "  silent: USB device reset" >> "raw/$n.ports"
      for d in /sys/bus/usb/devices/*; do
        [ -r "$d/idVendor" ] && [ "$(cat "$d/idVendor")" = "0403" ] || continue
        python3 -c "import fcntl,os,sys;fd=os.open('/dev/bus/usb/%03d/%03d'%(int(open(sys.argv[1]+'/busnum').read()),int(open(sys.argv[1]+'/devnum').read())),os.O_WRONLY);fcntl.ioctl(fd,0x5514)" "$d" >> "raw/$n.ports" 2>&1
      done
      sleep 6
    else
      sleep 2
    fi
  done
  dmesg 2>/dev/null | grep -i -E "ftdi|ttyUSB|usb 3-|usb 1-|usb 2-" | tail -4 >> "raw/$n.ports"
  echo "[$n] $(wc -c < "raw/$n.bin") bytes   $(tail -1 "raw/$n.ports" | tr -d '\n')"
done
python3 board_collect.py
echo
echo "Finished. Results are in $(pwd)/board_results.txt"
