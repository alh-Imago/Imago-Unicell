#!/usr/bin/env bash
# run_arr.sh: builds the hex pattern arrays for the Kintex ONE AT A TIME (8 GB machine) and prints size and clock for each.
# Run from ~/ypcb-00338-1p1 inside the openXC7 nix shell, NO sudo, after:
#   git -C ~/hexn-wt pull origin Hex-N
#   ln -sfn ~/hexn-wt/fpga/ypcb/hexn_arr designs/hexn_arr
# Usage: bash ~/hexn-wt/fpga/ypcb/hexn_arr/run_arr.sh [PATTERNS...]   (HEXN_FRAME=v5 in front: debug frame with the S status command; HEXN_NORAM=1: no RAM32M/SRL16E, plain flip-flops; =ram: only the memories; =srl: only the config chains)     default: hex7_off2_mix   (others: hex6 hex5)
# Builds go to $OUT (default /media/alan/InternalHDD/hexn_builds; override: OUT=/mnt/hdd/hexn_builds bash ...). Only builds; never touches a board.
set -u
PATS=${*:-hex7_off2_mix}
[ -n "${HEXN_BASE:-}" ] && PATS=base      # BASE design: HEXN_BASE=hex7_off2_mix,hex6 bash run_arr.sh   (judge + those arrays + program library; folder arr_base...)
SUF=${HEXN_FRAME:+_$HEXN_FRAME}$( case "${HEXN_NORAM:-}" in "") ;; 1) echo _noram;; *) echo _noram_$HEXN_NORAM;; esac )      # build folder suffix: arr_hex5_v5 for the debug frame, so the v4 builds are kept
: "${OUT:=/media/alan/InternalHDD/hexn_builds}"
: "${CHIPDB:=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin}"; export CHIPDB
[ -s "$CHIPDB" ] || { echo "CHIPDB file not found or empty: $CHIPDB"; exit 1; }
[ -d designs/hexn_arr ] || { echo "run this from ~/ypcb-00338-1p1 after: ln -sfn ~/hexn-wt/fpga/ypcb/hexn_arr designs/hexn_arr"; exit 1; }
[ -d "$OUT" ] || { echo "$OUT is not there (disk not mounted?). Set OUT=<big disk folder>"; exit 1; }
for p in $PATS; do
  name=arr_$p$SUF; ref=$HOME/hexn-wt/docs/hex-n/data/hexrefs/$p.json
  [ -n "${HEXN_BASE:-}" ] || [ -s "$ref" ] || { echo "no reference $ref"; continue; }
  mkdir -p $OUT/$name && ln -sfn $OUT/$name designs/hexn_arr/build_$name
  echo "=== $(date '+%F %T') start $name"
  HEXN_REPO=$HOME/hexn-wt HEXN_REF=$ref BUILD=build_$name THREADS=4 FPGA_HOST=$(hostname -s) \
    ./fpga build designs/hexn_arr hexn_arr > $OUT/$name.log 2>&1
  rc=$?
  echo "=== $(date '+%F %T') end   $name (exit $rc)"
  [ $rc -ne 0 ] && { echo "--- last lines of the log:"; tail -15 $OUT/$name.log; }
done
echo; echo "SUMMARY (from the logs; the clock is nextpnr's estimate, NOT a measurement on silicon)"
for p in $PATS; do
  f=$OUT/arr_$p$SUF.log; echo "--- $p"
  grep -E "Max frequency" $f | tail -4
  grep -E -A8 "Device utilisation" $OUT/arr_$p$SUF/hexn_arr.nextpnr.log | head -9
  ls $OUT/arr_$p$SUF/*.bit >/dev/null 2>&1 && echo "bitstream: yes" || echo "bitstream: NO (see $f)"
done
