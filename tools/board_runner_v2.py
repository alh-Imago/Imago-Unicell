#!/usr/bin/env python3
"""tools/board_runner_v2.py -- ledger #1138: give a board-test folder a run_all_v2.sh that reads the serial line with the Python raw reader
(watch_serial.py = tools/serial_capture_v1.py), opened BEFORE the bitstream is loaded, instead of `stty` + `cat` after the load.
Why: on the Tang Nano 20K the old stty+cat reader stalled after the first ~54 frames while the Python reader ran flat out (#1135-#1137).
It clones the folder's existing run_all.sh (kept untouched) and replaces only the reading lines; everything else (loader, replug prompts, retries,
board_collect.py) is the same.  Handles the two templates in use: the 'loops/designs' one (tries every ttyUSB) and the original 'board_tests' one.
  python3 tools/board_runner_v2.py fpga/board_tests_designs fpga/board_tests_designs_carrier fpga/board_tests_loops [...]
Run it as   sudo ./run_all_v2.sh /dev/ttyUSB1   (env: SECS=12 how long to watch after the load starts, ONLY=, PAUSE=, BATCH=)."""
import os, shutil, sys
HERE = os.path.dirname(os.path.abspath(__file__))

LOAD = '  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"\n  sleep 3\n'
LOAD_NEW = ('  # reader v2 (#1138): open the serial port BEFORE the load and keep it open; the watcher re-opens it if the device vanishes\n'
            '  PRE=${1:-/dev/ttyUSB1}; rm -f "raw/$n.pre" "raw/$n.pre.log"\n'
            '  python3 watch_serial.py "$PRE" "raw/$n.pre" ${SECS:-12} > "raw/$n.pre.summary" 2>&1 &\n'
            '  WPID=$!\n  sleep 1\n'
            '  openFPGALoader -b tangnano20k "$f" > "raw/$n.loader.txt" 2>&1; echo $? > "raw/$n.rc"\n'
            '  wait $WPID\n  sleep 1\n')
CLEAR = '    : > "raw/$n.bin"\n'
CLEAR_NEW = '    if [ "$try" = 1 ] && [ -s "raw/$n.pre" ]; then cp "raw/$n.pre" "raw/$n.bin"; else : > "raw/$n.bin"; fi\n'
QLOOP = '    for Q in $P $(ls /dev/ttyUSB* 2>/dev/null | sort -V); do\n      [ -e "$Q" ] || continue\n'
QLOOP_NEW = '    for Q in $P $(ls /dev/ttyUSB* 2>/dev/null | sort -V); do\n      [ -s "raw/$n.bin" ] && break\n      [ -e "$Q" ] || continue\n'
QREAD = ('      stty -F "$Q" 115200 raw -echo -hupcl clocal -crtscts 2>>"raw/$n.ports"\n'
         '      timeout ${SECS:-5} cat "$Q" > "raw/$n.try" 2>>"raw/$n.ports"\n')
QREAD_NEW = '      python3 watch_serial.py "$Q" "raw/$n.try" ${SECS:-8} > /dev/null 2>>"raw/$n.ports"\n'
PREAD = ('      stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts 2>>"raw/$n.ports"\n'
         '      timeout 7 cat "$P" > "raw/$n.bin" 2>>"raw/$n.ports"\n')
PREAD_NEW = '      [ -s "raw/$n.bin" ] || python3 watch_serial.py "$P" "raw/$n.bin" 8 > /dev/null 2>>"raw/$n.ports"\n'


def convert(txt):
    for a in (LOAD, CLEAR):
        if txt.count(a) != 1:
            raise SystemExit("run_all.sh does not have the expected load/clear lines: " + a.strip()[:50])
    txt = txt.replace(LOAD, LOAD_NEW).replace(CLEAR, CLEAR_NEW)
    txt = txt.replace("sleep 20\n", "sleep ${BOOTWAIT:-20}\n")      # BOOTWAIT=1 lets a simulated board test finish in seconds
    if QLOOP in txt and QREAD in txt:
        txt = txt.replace(QLOOP, QLOOP_NEW).replace(QREAD, QREAD_NEW)
    elif PREAD in txt:
        txt = txt.replace(PREAD, PREAD_NEW)
    else:
        raise SystemExit("run_all.sh: neither known reading block found")
    head = "#!/bin/sh\n# run_all_v2.sh -- ledger #1138: clone of run_all.sh with the serial reader replaced by watch_serial.py (opened BEFORE the load). See tools/board_runner_v2.py.\n"
    return head + txt.split("\n", 1)[1]


def main():
    dirs = sys.argv[1:]
    if not dirs:
        raise SystemExit(__doc__)
    for d in dirs:
        src = os.path.join(d, "run_all.sh")
        if not os.path.exists(src):
            print("skip (no run_all.sh):", d); continue
        out = os.path.join(d, "run_all_v2.sh")
        open(out, "w").write(convert(open(src).read())); os.chmod(out, 0o755)
        shutil.copy(os.path.join(HERE, "serial_capture_v1.py"), os.path.join(d, "watch_serial.py"))
        print("wrote", out, "+ watch_serial.py")


if __name__ == "__main__":
    main()
