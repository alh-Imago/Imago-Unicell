#!/bin/sh
# estimate_test_v1.sh - does the length estimate (--estimate, ledger #1411/#1412) choose widths that are as fast as the fixed widths?  Runs on the card.
# Load the build the profile was made on first: sc_k7_fu2s8u8n3.bit (2 blocks x 8 slices, 3 fusion units); the profile is example_2x8_nu3_v2.
# Usage from s-core:  sh estimate_test_v1.sh 2>&1 | tee estimate_test_19nov.txt
PROFILE=${PROFILE:-example_2x8_nu3_v2}
for spec in "jobs_order_test.json 1" "jobs_order_test2.json 1" "jobs_many_small.json 2"; do
  set -- $spec; f=$1; nb=$2
  for mode in "lw0:--lw 0" "lw2:--lw 2" "lw3:--lw 3" "simple:--lw auto" "profile:--lw auto --profile $PROFILE" "estimate:--lw auto --profile $PROFILE --estimate"; do
    name=${mode%%:*}; args=${mode#*:}
    out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$f" --blocks $nb --unit-lw 3 $args 2>&1)
    clk=$(echo "$out" | grep -E "^  block [0-9]" | sed -E 's/.*steps, ([0-9]+) clocks.*/\1/' | sort -n | tail -1)
    ok=$(echo "$out" | grep -E "correct" | tail -1)
    echo "$f $name clocks=$clk  $ok"
    [ "$name" = estimate ] && echo "$out" | grep -E "^estimate" | cut -c1-400
  done
done
