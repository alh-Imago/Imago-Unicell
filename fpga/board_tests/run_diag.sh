#!/bin/sh
# run_diag.sh [PORT] -- ONE-OFF diagnostic: records what the USB serial port does around a load. Writes diag.txt (attach it).
# Use it right after a fresh unplug/replug of the board.  Needs sudo.
cd "$(dirname "$0")" || exit 1
PORT=${1:-/dev/ttyUSB1}
OUT=diag.txt; : > $OUT
note() { echo "$@" | tee -a $OUT; }
snap() { # name
  note "---- $1: ports: $(ls /dev/ttyUSB* 2>&1 | tr '\n' ' ')"
  note "---- $1: dmesg (last 6 usb/tty lines):"; dmesg | grep -i -E "ftdi|ttyUSB|usb 1-|usb 2-" | tail -6 | tee -a $OUT
}
readport() { # name seconds
  stty -F "$PORT" 115200 raw -echo 2>&1 | tee -a $OUT
  timeout $2 cat "$PORT" > /tmp/diag_raw.bin 2>>$OUT
  note "---- $1: bytes read in $2 s: $(wc -c < /tmp/diag_raw.bin)"
  note "---- $1: first line: $(tr -c '[:print:]\n' '?' < /tmp/diag_raw.bin | grep -a -m1 UCT | cut -c1-90)"
  note "---- $1: other text: $(tr -c '[:print:]\n' '?' < /tmp/diag_raw.bin | grep -a -v UCT | head -3 | tr '\n' '|' | cut -c1-120)"
}
note "== start $(date)"; snap start
note "== step 1: plain load of adder_stream"; openFPGALoader -b tangnano20k adder_stream.fs >> $OUT 2>&1; sleep 2; snap after-load-1; readport step1 6
note "== step 2: plain load of relay_chain (no reset)"; openFPGALoader -b tangnano20k relay_chain.fs >> $OUT 2>&1; sleep 2; snap after-load-2; readport step2 6
note "== step 3: plain load of adder_stream again, then wait 8 s before reading"; openFPGALoader -b tangnano20k adder_stream.fs >> $OUT 2>&1; sleep 8; snap after-load-3; readport step3 6
note "== LOOK AT THE LEDs NOW and write down: LED0 (blinking?) LED1 LED2 LED3 (on/off) ==" 
note "== done: please attach diag.txt and tell me the LED states"
