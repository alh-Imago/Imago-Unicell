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


ONE_LOAD = 'openFPGALoader -b tangnano20k "$1.fs" || exit 1\n'
ONE_READ = 'sleep 3\nstty -F "$PORT" 115200 raw -echo\ntimeout 6 cat "$PORT"\n'
ONE_LOAD_NEW = ('# reader v2 (#1138): open the serial port BEFORE the load and keep it open\n'
                'OUT=$(mktemp); python3 watch_serial.py "$PORT" "$OUT" ${SECS:-12} > /dev/null 2>&1 &\nWPID=$!\nsleep 1\n'
                'openFPGALoader -b tangnano20k "$1.fs" || { kill $WPID 2>/dev/null; rm -f "$OUT" "$OUT.log"; exit 1; }\n')
ONE_READ_NEW = 'wait $WPID\ncat "$OUT"; rm -f "$OUT" "$OUT.log"\n'


def convert_one(txt):
    if txt.count(ONE_LOAD) != 1 or txt.count(ONE_READ) != 1:
        raise SystemExit("run_one.sh does not have the expected lines")
    txt = txt.replace(ONE_LOAD, ONE_LOAD_NEW).replace(ONE_READ, ONE_READ_NEW)
    return "#!/bin/sh\n# run_one_v2.sh -- ledger #1138: clone of run_one.sh, serial read by watch_serial.py opened BEFORE the load.\n" + txt.split("\n", 1)[1]


G_LOAD = '    openFPGALoader -b tangnano20k "groups/group_$G.fs" > "raw/group_$G.loader.txt" 2>&1; rc=$?\n    sleep 3; wait_ports "$1"; sleep 1\n'
G_LOAD_NEW = ('    PRE=${1:-/dev/ttyUSB1}; rm -f "raw/group_$G.pre" "raw/group_$G.pre.log"\n'
              '    python3 watch_serial.py "$PRE" "raw/group_$G.pre" ${SECS:-26} > /dev/null 2>&1 &\n    WPID=$!\n    sleep 1\n'
              '    openFPGALoader -b tangnano20k "groups/group_$G.fs" > "raw/group_$G.loader.txt" 2>&1; rc=$?\n'
              '    wait $WPID; sleep 1\n')
G_READ = ('    : > "raw/group_$G.bin"\n    if [ -n "$P" ]; then\n'
          '      stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts 2>/dev/null\n'
          '      timeout 16 cat "$P" > "raw/group_$G.bin" 2>/dev/null\n    fi\n')
G_READ_NEW = '    cp "raw/group_$G.pre" "raw/group_$G.bin" 2>/dev/null || : > "raw/group_$G.bin"\n'


def convert_groups(txt):
    if txt.count(G_LOAD) != 1 or txt.count(G_READ) != 1:
        raise SystemExit("run_groups.sh does not have the expected lines")
    txt = txt.replace(G_LOAD, G_LOAD_NEW).replace(G_READ, G_READ_NEW)
    txt = txt.replace("sleep 20\n", "sleep ${BOOTWAIT:-20}\n")
    return "#!/bin/sh\n# run_groups_v2.sh -- ledger #1138: clone of run_groups.sh, serial read by watch_serial.py opened BEFORE the load.\n" + txt.split("\n", 1)[1]


M_LOAD = 'openFPGALoader -b tangnano20k "$f" || { echo "load failed"; exit 1; }\necho "loaded $f; waiting 4 s for the board and its serial port to settle"; sleep 4\n'
M_LOAD_NEW = ('# reader v2 (#1138): in self mode the serial port is opened BEFORE the load (host mode talks through mutability_host.py, unchanged)\n'
              'if [ "$mode" = self ]; then\n  PRE=${2:-/dev/ttyUSB1}; OUT=$(mktemp); python3 watch_serial.py "$PRE" "$OUT" 14 > /dev/null 2>&1 &\n  WPID=$!; sleep 1\nfi\n'
              'openFPGALoader -b tangnano20k "$f" || { echo "load failed"; [ -n "$WPID" ] && kill $WPID 2>/dev/null; exit 1; }\n'
              'echo "loaded $f; waiting 4 s for the board and its serial port to settle"; sleep 4\n')
M_READ = '  stty -F "$P" 115200 raw -echo -hupcl clocal -crtscts\n  timeout 7 cat "$P" | tr -d \'\\r\' | head -3\n'
M_READ_NEW = '  wait $WPID\n  tr -d \'\\r\' < "$OUT" | grep -a "^UCM" | head -3; rm -f "$OUT" "$OUT.log"\n'


def convert_mutability(txt):
    if txt.count(M_LOAD) != 1 or txt.count(M_READ) != 1:
        raise SystemExit("run_mutability.sh does not have the expected lines")
    txt = txt.replace(M_LOAD, M_LOAD_NEW).replace(M_READ, M_READ_NEW)
    return "#!/bin/sh\n# run_mutability_v2.sh -- ledger #1138: clone of run_mutability.sh, self mode reads with watch_serial.py opened BEFORE the load.\n" + txt.split("\n", 1)[1]


CONVERTERS = (("run_all.sh", "run_all_v2.sh", None), ("run_one.sh", "run_one_v2.sh", "convert_one"),
              ("run_groups.sh", "run_groups_v2.sh", "convert_groups"), ("run_mutability.sh", "run_mutability_v2.sh", "convert_mutability"))


def main():
    dirs = sys.argv[1:]
    if not dirs:
        raise SystemExit(__doc__)
    for d in dirs:
        done = []
        for src_name, out_name, fn in CONVERTERS:
            src = os.path.join(d, src_name)
            if not os.path.exists(src):
                continue
            conv = convert if fn is None else globals()[fn]
            out = os.path.join(d, out_name)
            open(out, "w").write(conv(open(src).read())); os.chmod(out, 0o755)
            done.append(out_name)
        if done:
            shutil.copy(os.path.join(HERE, "serial_capture_v1.py"), os.path.join(d, "watch_serial.py"))
            print("wrote", ", ".join(done), "+ watch_serial.py in", d)
        else:
            print("skip (no known run script):", d)


if __name__ == "__main__":
    main()
