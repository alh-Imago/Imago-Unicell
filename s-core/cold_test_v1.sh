#!/bin/sh
# cold_test_v1.sh - the pool keeps its learned job durations across a reset and orders the bulk queue by them (LONGEST=1 in every card build; ledger #1415).
# A freshly loaded bitstream starts with nothing learned.  This reloads the bitstream before each group of runs and shows how the clocks change from the first run on.
# Run in the openXC7 shell.  Usage from s-core:  sh cold_test_v1.sh 2>&1 | tee cold_test_19nov.txt
BITDIR=${BITDIR:-$HOME/openFPGALoader/build/demo-projects/sc_k7_sizes}; BIT=${BIT:-sc_k7_fu2s8u8n3.bit}
PROFILE=${PROFILE:-example_2x8_nu3_v2}; F=${1:-jobs_order_test2.json}; HERE=$(pwd)
load() { (cd "$BITDIR" && openFPGALoader -c ft232 "$BIT" 2>&1 | grep -E "done|DONE|FAIL" | tail -2); }
runs() {   # label then run specs
  label=$1; shift; n=0
  for mode in "$@"; do
    n=$((n+1)); name=${mode%%:*}; args=${mode#*:}
    out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$F" --blocks 1 --unit-lw 3 $args 2>&1)
    clk=$(echo "$out" | grep -E "^  block 0" | grep steps | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
    ok=$(echo "$out" | grep -E "correct" | tail -1)
    echo "$label run $n $F $name clocks=$clk  $ok"
  done
}
L2="lw2:--lw 2"; L0="lw0:--lw 0"; L3="lw3:--lw 3"; ES="estimate:--lw auto --profile $PROFILE --estimate"
echo "== A: fresh load, then lw2 x4";            load; runs A "$L2" "$L2" "$L2" "$L2"
echo "== B: fresh load, then estimate x4";       load; runs B "$ES" "$ES" "$ES" "$ES"
echo "== C: fresh load, lw0, then lw2 x3";       load; runs C "$L0" "$L2" "$L2" "$L2"
echo "== D: fresh load, lw3 x2, then lw2 x2";    load; runs D "$L3" "$L3" "$L2" "$L2"
