#!/bin/bash
# Sweep for the Hex-N size/timing figures on the Kintex card. Run from the repo folder:  bash fpga/hexn_kintex_sweep_v1.sh   (finds the tools in /nix/store itself)
# Each configuration is one build (minutes to an hour for the larger ones). Paste back the "RESULT" lines (also in build_hexn_kintex/summary.txt).
cd "$(dirname "$0")/.." || exit 1
for c in "hex7 7 1" "hex7 7 7" "hex19 19 1" "hex19 19 7" "hex19 19 19"; do bash fpga/build_hexn_kintex_v1.sh $c | grep RESULT; done
