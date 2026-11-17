#!/bin/sh
# runner_repeat.sh FOLDER [N] [VECTORS] -- TEST C. Repeat one vector run N times (default 500) on an ICM runner design that is already loaded on the card,
# FOLDER = that design's own folder (it holds run_lib.tcl, design.json, make_cmd.py, expected.json). Each exit's "clock of the last word" must be identical every time.
# Default VECTORS = vectors.txt. Writes FOLDER/results_repeat/runner_N.log and prints the summary.
F=${1:?usage: sh runner_repeat.sh FOLDER [N] [VECTORS]}
N=${2:-500}
V=${3:-vectors.txt}
HERE=$(cd "$(dirname "$0")" && pwd)
cd "$F" || exit 1
python3 make_cmd.py "$V" cmd.txt || exit 1
mkdir -p results_repeat
openocd -f k7_ft232h.cfg -c "init; irscan xc7.tap 0x02; source run_lib.tcl; source $HERE/rr_loop.tcl; rn_read start; rr_loop $N cmd.txt 300; shutdown" > results_repeat/runner_$N.log 2>&1
python3 "$HERE/check_runner_repeat.py" . results_repeat/runner_$N.log "$V"
