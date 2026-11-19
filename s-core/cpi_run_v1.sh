#!/bin/sh
# cpi_run_v1.sh - one job of each kind at width 0 on one block: gives the clocks per instruction of each kind (ledger #1411, for lengthest_v1.py fit-kinds).
# Run in s-core with the build loaded; any build works (width 0).  Usage:  sh cpi_run_v1.sh 2>&1 | tee cpi_run_<date>.txt
for k in vsum vgain vmax vprefix; do
  for rep in 1 2; do
    out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag jobs_cpi_$k.json --blocks 1 --lw 0 2>&1)
    clk=$(echo "$out" | grep -E "^  block 0" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
    ok=$(echo "$out" | grep -E "correct" | tail -1)
    echo "jobs_cpi_$k.json lw0 clocks=$clk  $ok"
  done
done
