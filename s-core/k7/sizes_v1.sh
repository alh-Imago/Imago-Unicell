#!/bin/sh
# sizes_v1.sh - build the size sweep (S=4, 8, 16 by default) one after another, same seed and clock for all, one log per size.
# Run in the nix shell, in this folder copied into demo-projects/ (so ../openXC7.mk is found), after  S_CORE=... sh stage.sh  and  python3 make_sizes_v1.py:
#   sh sizes_v1.sh              (S = 4 8 16)        sh sizes_v1.sh 8 16        (only those)
# Logs: build_sN.log.  A big size can take a long time and a lot of memory (the N=32 Kintex build needed a lot): start with 4 and 8, 16 last, overnight.
# Then:  python3 sizetable_v1.py   (reads the logs, prints the table and the cost per slice).  Loads nothing, never touches the card or its flash.
SIZES=${*:-4 8 16}
for s in $SIZES; do
  echo "=== S=$s  $(date)"
  [ -f Makefile.s$s ] || { echo "Makefile.s$s missing: run  python3 make_sizes_v1.py $s"; continue; }
  make -f Makefile.s$s PNR_ARGS="--freq 50 --seed 2" > build_s$s.log 2>&1
  echo "S=$s finished (exit $?)  $(date)"; grep -E "Max frequency|ERROR|Error" build_s$s.log | tail -4
done
