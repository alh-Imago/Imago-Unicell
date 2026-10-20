#!/bin/sh
# Hex-N frozen-model test, for Alan's machine: 4 processes x 3 seeds (seeds 0-11), trained on CLEAN data (noise 0), tested at noise 0 / 0.05 / 0.15 / 0.25, frozen vs offset-adapted.
# Results go to ~/hexn_frozen_out/part_*.txt  (each line: seed noise frozen adapted ceiling).  Run from the repository folder:  sh tools/hexn_run_frozen_v1.sh
OUT="$HOME/hexn_frozen_out"; mkdir -p "$OUT"
for first in 0 3 6 9; do
  python3 tools/hexn_cluster_v20.py --train-noise 0 --score --first $first --runs 3 > "$OUT/part_$first.txt" 2>&1 &
done
wait
echo "done: results in $OUT"; cat "$OUT"/part_*.txt | grep -E "^ +[0-9]+ " | wc -l
