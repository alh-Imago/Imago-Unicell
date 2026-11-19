#!/bin/sh
# curve_run_v2.sh - like curve_run_v1.sh but runs only the job files given as arguments (ledger #1397).
# Usage from s-core:  sh curve_run_v2.sh jobs_curve_L8_N3.json jobs_curve_L8_N5.json ... 2>&1 | tee curve_run2_<date>.txt
for f in "$@"; do
  for lw in 0 1 2 3; do
    out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$f" --blocks 1 --lw $lw --unit-lw 3 2>&1)
    clk=$(echo "$out" | grep -E "^  block 0" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
    ok=$(echo "$out" | grep -E "correct" | tail -1)
    echo "$f lw$lw clocks=$clk  $ok"
  done
done
