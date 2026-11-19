#!/bin/sh
# order_repeat_v1.sh FILE [N] - repeat the wide-first runs (B: width order, D: width order + crit) and the wide-last run (A) N times each, interleaved, to see how
# repeatable the clocks are (ledger #1408: B gave 43,282 and 36,232 on two identical runs).  Run from s-core, 2x8 fusion build loaded:
#   sh order_repeat_v1.sh jobs_order_test2.json 6 2>&1 | tee order_repeat_<date>.txt
F=$1; N=${2:-6}; [ -z "$F" ] && { echo "usage: sh order_repeat_v1.sh JOBFILE [N]"; exit 2; }
run() {   # label args...
  lab=$1; shift
  out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$F" --blocks 1 --unit-lw 3 "$@" 2>&1)
  c=$(echo "$out" | grep -E "^  block 0:" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
  ok=$(echo "$out" | grep -E "jobs correct" | tail -1)
  echo "$lab clocks=$c  $ok"
}
i=1; while [ $i -le $N ]; do
  run "run $i B width-order"            --submit-order width
  run "run $i D width-order + crit"     --submit-order width --crit wide
  run "run $i A kind-order"
  i=$((i+1))
done
