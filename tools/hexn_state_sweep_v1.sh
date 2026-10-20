#!/bin/sh
# Runs the v10 memory sweep on all cores. Usage: sh tools/hexn_state_sweep_v1.sh [OUTDIR] [CORES]   (defaults: ~/hexn_sweep, 4)
# Jobs: delays 0,2,4,7 x memory 0,4,8,16 bits x live off/on (live only with memory 4 and 16), 20 seeds, 1500 tries each.
OUT=${1:-$HOME/hexn_sweep}; CORES=${2:-4}; mkdir -p "$OUT"; cd "$(dirname "$0")/.." || exit 1
for d in 0 2 4 7; do for m in 0 4 8 16; do echo "$d $m 0"; done; for m in 4 16; do echo "$d $m 1"; done; done |
xargs -P "$CORES" -L 1 sh -c 'f="'"$OUT"'/d$0_m$1_live$2.txt"; [ -s "$f" ] && [ "$(wc -l < "$f")" -ge 22 ] && exit 0; python3 tools/hexn_state_v10.py --delay $0 --mem $1 $( [ $2 = 1 ] && echo --live ) > "$f"'
python3 tools/hexn_state_summary_v1.py "$OUT"
