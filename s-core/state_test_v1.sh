#!/bin/sh
# state_test_v1.sh - does the same job image give the same clocks whatever ran before it?  (ledger #1414: all lw2 on jobs_order_test2.json gave 48,261 and,
# with an IDENTICAL image, 35,494 in another run of estimate_test_v1.sh.)  Runs on the card, build sc_k7_fu2s8u8n3.bit, one block.
# Usage from s-core:  sh state_test_v1.sh 2>&1 | tee state_test_19nov.txt
F=${1:-jobs_order_test2.json}
PROFILE=${PROFILE:-example_2x8_nu3_v2}
n=0
for mode in "lw2:--lw 2" "lw2:--lw 2" "lw2:--lw 2" "lw3:--lw 3" "lw2:--lw 2" "profile:--lw auto --profile $PROFILE" "lw2:--lw 2" "lw3:--lw 3" "profile:--lw auto --profile $PROFILE" "profile:--lw auto --profile $PROFILE" "estimate:--lw auto --profile $PROFILE --estimate" "estimate:--lw auto --profile $PROFILE --estimate" "lw0:--lw 0" "estimate:--lw auto --profile $PROFILE --estimate" "lw2:--lw 2" "lw2:--lw 2"; do
  n=$((n+1)); name=${mode%%:*}; args=${mode#*:}
  out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$F" --blocks 1 --unit-lw 3 $args 2>&1)
  clk=$(echo "$out" | grep -E "^  block 0" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/')
  ok=$(echo "$out" | grep -E "correct" | tail -1)
  echo "run $n $F $name clocks=$clk  $ok"
done
