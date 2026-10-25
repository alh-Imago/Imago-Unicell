#!/usr/bin/env bash
# run_sweep.sh: builds the four hexn_sweep variants one after another (ONE at a time; the machine has 8 GB) and prints a summary of size and clock for each.
# Run from ~/ypcb-00338-1p1 inside the openXC7 nix shell, CHIPDB exported, NO sudo, after:
#   git -C ~/hexn-wt pull origin Hex-N
#   ln -sfn ~/hexn-wt/fpga/ypcb/hexn_sweep designs/hexn_sweep
# Usage:  bash ~/hexn-wt/fpga/ypcb/hexn_sweep/run_sweep.sh [NCELL] [VARIANTS...]      default: 64 cells, base A B AB   e.g.  ... 64 base B
# A failed variant does not stop the others. Logs and build folders go to /mnt/hdd/hexn_builds/sweep_<variant>_<NCELL>/ and sweep_<variant>_<NCELL>.log
set -u
NC=${1:-64}; shift 2>/dev/null || true
VARS=${*:-base A B AB}
OUT=/mnt/hdd/hexn_builds
# The chip database must be the ready-made file, or the flow tries to generate it (hours, and it exhausts 8 GB: this happened on 25 Oct). Use the known path if CHIPDB is not set.
: "${CHIPDB:=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin}"; export CHIPDB
[ -s "$CHIPDB" ] || { echo "CHIPDB file not found or empty: $CHIPDB (export CHIPDB=<path to xc7k480tffg1156.bin>)"; exit 1; }
echo "CHIPDB = $CHIPDB ($(du -h "$CHIPDB" | cut -f1))"
[ -d designs/hexn_sweep ] || { echo "run this from ~/ypcb-00338-1p1 after: ln -sfn ~/hexn-wt/fpga/ypcb/hexn_sweep designs/hexn_sweep"; exit 1; }
mountpoint -q /mnt/hdd || { echo "/mnt/hdd is not mounted: sudo mount /dev/sda1 /mnt/hdd"; exit 1; }
for v in $VARS; do
  name=sweep_${v}_${NC}
  mkdir -p $OUT/$name && ln -sfn $OUT/$name designs/hexn_sweep/build_$name
  echo "=== $(date '+%F %T') start $name"
  HEXN_REPO=$HOME/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=$NC HEXN_VARIANT=$v BUILD=build_$name THREADS=4 FPGA_HOST=$(hostname -s) \
    ./fpga build designs/hexn_sweep hexn_sweep > $OUT/$name.log 2>&1
  rc=$?
  echo "=== $(date '+%F %T') end   $name (exit $rc)"
done
echo; echo "SUMMARY (lines copied from the logs; the clock is what nextpnr reports, NOT a measurement on silicon)"
for v in $VARS; do
  f=$OUT/sweep_${v}_${NC}.log; echo "--- $v"
  grep -E "Max frequency|Device utilisation|SLICE_LUTX|FDRE|critical path" $f | tail -8
  ls $OUT/sweep_${v}_${NC}/*.bit >/dev/null 2>&1 && echo "bitstream: yes" || echo "bitstream: NO (build failed; see $f)"
done
