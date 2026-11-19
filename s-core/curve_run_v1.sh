#!/bin/sh
# curve_run_v1.sh - width curve on the card (ledger #1396): every curve job file at widths 0..3, one block, one batch.
# Run from s-core after loading the 2x8 bitstream:  sh curve_run_v1.sh 2>&1 | tee curve_run_<date>.txt
# Prints one line per run: file, width, clocks, correct.
for f in jobs_curve_L*_N*.json; do
  for lw in 0 1 2 3; do
    out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$f" --blocks 1 --lw $lw --unit-lw 3 2>&1)
    clk=$(echo "$out" | grep -E "^  block 0" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
    ok=$(echo "$out" | grep -E "jobs correct|correct" | tail -1)
    echo "$f lw$lw clocks=$clk  $ok"
  done
done
