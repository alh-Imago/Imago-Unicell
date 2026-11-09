#!/usr/bin/env bash
# run_speech.sh: builds the speech chain (self-checking replay of 300 spoken-digit recordings) for the Kintex card and prints size and estimated clock.
# Run from ~/ypcb-00338-1p1 inside the openXC7 nix shell, CHIPDB exported, NO sudo, /mnt/hdd mounted, after:
#   git -C ~/hexn-wt pull origin Hex-N
#   ln -sfn ~/hexn-wt/fpga/ypcb/hexn_speech designs/hexn_speech
# Usage:  bash ~/hexn-wt/fpga/ypcb/hexn_speech/run_speech.sh
# Logs and the build folder go to /mnt/hdd/hexn_builds/speech/ and speech.log. The expected result on the card: led[1] on (finished), led[2] on (PASS); the model says 262 of 300 right.
set -u
OUT=/mnt/hdd/hexn_builds; name=speech
: "${CHIPDB:=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin}"; export CHIPDB
[ -s "$CHIPDB" ] || { echo "CHIPDB file not found or empty: $CHIPDB (export CHIPDB=<path to xc7k480tffg1156.bin>)"; exit 1; }
[ -d designs/hexn_speech ] || { echo "run this from ~/ypcb-00338-1p1 after: ln -sfn ~/hexn-wt/fpga/ypcb/hexn_speech designs/hexn_speech"; exit 1; }
mountpoint -q /mnt/hdd || { echo "/mnt/hdd is not mounted: sudo mount /dev/sda1 /mnt/hdd"; exit 1; }
mkdir -p $OUT/$name && ln -sfn $OUT/$name designs/hexn_speech/build_$name
echo "=== $(date '+%F %T') start $name"
HEXN_REPO=$HOME/hexn-wt BUILD=build_$name THREADS=4 FPGA_HOST=$(hostname -s) ./fpga build designs/hexn_speech hexn_speech > $OUT/$name.log 2>&1
rc=$?; echo "=== $(date '+%F %T') end   $name (exit $rc)"
echo; echo "SUMMARY (lines copied from the logs; the clock is what nextpnr reports at a 50 MHz target, NOT a measurement on silicon)"
grep -E "Max frequency|rror" $OUT/$name.log | tail -6
grep -E "SLICE_LUTX|SLICE_FFX|DSP48|RAMB|CARRY4" $OUT/$name/hexn_speech.nextpnr.log 2>/dev/null | head -12
grep -E "^\s+[0-9]+\s+(LUT[1-6]|FDRE|FDCE|FDPE|FDSE|DSP48E1|CARRY4|RAMB)" $OUT/$name/hexn_speech.yosys.log 2>/dev/null | tail -20
ls $OUT/$name/*.bit >/dev/null 2>&1 && echo "bitstream: yes" || echo "bitstream: NO (build failed; see $OUT/$name.log)"
