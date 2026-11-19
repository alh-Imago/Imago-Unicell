#!/bin/sh
# order_test_v2.sh FILE - one batch, one block: one 4-slice job (vsum, lw 2) and eight single-slice jobs (vgain, lw 0).  Submit order and critical flag compared.
# (ledger #1407).  Run from s-core with a 2x8 fusion build loaded (the wide job needs a unit):
#   sh order_test_v2.sh jobs_order_test2.json 2>&1 | tee order_test2_<date>.txt
F=$1; [ -z "$F" ] && { echo "usage: sh order_test_v2.sh JOBFILE"; exit 2; }
run() {   # label args...
  lab=$1; shift
  out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$F" --blocks 1 "$@" 2>&1)
  c=$(echo "$out" | grep -E "^  block 0:" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
  ok=$(echo "$out" | grep -E "jobs correct" | tail -1)
  echo "$lab clocks=$c  $ok"
}
run "ref all-lw0"                         --lw 0
run "ref all-lw2"                         --lw 2 --unit-lw 3
run "A kind-order (wide last)"            --unit-lw 3
run "B width-order (wide first)"          --unit-lw 3 --submit-order width
run "C kind-order + crit on wide"         --unit-lw 3 --crit wide
run "D width-order + crit on wide"        --unit-lw 3 --submit-order width --crit wide
run "A again"                             --unit-lw 3
run "B again"                             --unit-lw 3 --submit-order width
