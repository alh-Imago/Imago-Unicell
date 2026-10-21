#!/bin/bash
# Hex-N state-machine comparison, for Alan's machine.  Run from the Hex-N folder:  bash tools/hexn_run_sm_v1.sh
# 4 arms x 25 seeds, 1000 tries each: plain table (baseline) and state machine with commit threshold T=2,4,8.
# Uses every core; safe to stop (Ctrl-C) and re-run: finished seed files are skipped.  Results: ~/hexn_sm_out/<arm>_<seed>.txt
OUT=$HOME/hexn_sm_out; mkdir -p "$OUT"
jobs_list() { for s in $(seq 0 24); do
  echo "table1000 $s python3 tools/hexn_cluster_v21.py --tries 1000 --first $s --runs 1"
  for T in 2 4 8; do echo "sm_T$T $s python3 tools/hexn_cluster_v22.py --T $T --P 1 --tries 1000 --first $s --runs 1"; done; done; }
run_one() { arm=$1; s=$2; shift 2; f="$OUT/${arm}_$s.txt"
  if grep -q "^mean learned" "$f" 2>/dev/null; then return; fi
  "$@" > "$f.tmp" 2>&1 && mv "$f.tmp" "$f"; }
export -f run_one; export OUT
jobs_list | xargs -P "$(nproc)" -L 1 bash -c 'run_one "$@"' _
echo "done: $(ls $OUT/*.txt | wc -l) of 100 files in $OUT"
