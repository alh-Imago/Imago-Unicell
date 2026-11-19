#!/bin/sh
# profile_compare_v1.sh - on the build that is loaded on the card: calibrate (quick), then run two job sets at every fixed width, with the
# old automatic rule (#1388) and with the card profile (#1401), and print one line per run.  (ledger #1401)
# Usage (from s-core, inside the nix shell, after loading the bitstream):
#   sh profile_compare_v1.sh NAME UNIT_LW UNITS WMAX SLICES [BLOCKS] 2>&1 | tee compare_NAME_<date>.txt
#   NAME = a name for this build's profile (e.g. s4u4n1), UNIT_LW = log2 of the unit lanes (2 for 4 lanes, 3 for 8), UNITS = fusion units per block,
#   WMAX = the widest fixed width to try (min(UNIT_LW, log2 of slices per block)), SLICES = slices per block of the build you loaded
#   (checked against the board: the run stops if the wrong bitstream is loaded), BLOCKS default 2.
NAME=$1; U=$2; NU=$3; WMAX=$4; SL=$5; NB=${6:-2}
[ -z "$SL" ] && { echo "usage: sh profile_compare_v1.sh NAME UNIT_LW UNITS WMAX SLICES [BLOCKS]"; exit 2; }
echo "=== calibrate $NAME (quick) ==="
nix shell nixpkgs#openocd --command python3 sc_calibrate_v1.py run --name "$NAME" --blocks $NB --unit-lw $U --units $NU --expect-slices $SL --quick | tail -8
run() {   # file label args...
  f=$1; lab=$2; shift 2
  out=$(nix shell nixpkgs#openocd --command python3 scblocks.py jtag "$f" --blocks $NB "$@" 2>&1)
  c=$(echo "$out" | grep -E "^  block [0-9]+:" | sed -E 's/^  block ([0-9]+):.*steps, ([0-9]+) clocks.*/b\1=\2/' | tr '\n' ' ')
  ok=$(echo "$out" | grep -E "jobs correct" | tail -1)
  echo "$f $lab $c $ok"
}
for f in jobs_many_small.json jobs_telemetry.json; do
  w=0; while [ $w -le $WMAX ]; do run $f "lw$w" --lw $w --unit-lw $U; w=$((w+1)); done
  run $f "auto-old-rule" --lw auto --unit-lw $U
  run $f "auto-profile" --lw auto --profile "$NAME"
done
