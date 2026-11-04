#!/usr/bin/env bash
# run_arr.sh: builds the hex pattern arrays for the Kintex ONE AT A TIME (8 GB machine) and prints size and clock for each.
# Run from ~/ypcb-00338-1p1 inside the openXC7 nix shell, NO sudo, after:
#   git -C ~/hexn-wt pull origin Hex-N
#   ln -sfn ~/hexn-wt/fpga/ypcb/hexn_arr designs/hexn_arr
# Usage: bash ~/hexn-wt/fpga/ypcb/hexn_arr/run_arr.sh [PATTERNS...]     default: hex7_off2_mix   (others: hex6 hex5)
# Builds go to $OUT (default /media/alan/InternalHDD/hexn_builds; override: OUT=/mnt/hdd/hexn_builds bash ...). Only builds; never touches a board.
set -u
PATS=${*:-hex7_off2_mix}
: "${OUT:=/media/alan/InternalHDD/hexn_builds}"
: "${CHIPDB:=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin}"; export CHIPDB
[ -s "$CHIPDB" ] || { echo "CHIPDB file not found or empty: $CHIPDB"; exit 1; }
[ -d designs/hexn_arr ] || { echo "run this from ~/ypcb-00338-1p1 after: ln -sfn ~/hexn-wt/fpga/ypcb/hexn_arr designs/hexn_arr"; exit 1; }
[ -d "$OUT" ] || { echo "$OUT is not there (disk not mounted?). Set OUT=<big disk folder>"; exit 1; }
for p in $PATS; do
  name=arr_$p; ref=$HOME/hexn-wt/docs/hex-n/data/hexrefs/$p.json
  [ -s "$ref" ] || { echo "no reference $ref"; continue; }
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
  f=$OUT/arr_$p.log; echo "--- $p"
  grep -E "Max frequency|Device utilisation|SLICE_LUTX|FDRE|critical path" $f | tail -8
  ls $OUT/arr_$p/*.bit >/dev/null 2>&1 && echo "bitstream: yes" || echo "bitstream: NO (see $f)"
done
