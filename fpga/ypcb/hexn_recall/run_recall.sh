#!/usr/bin/env bash
# run_recall.sh: ONE build of the hexn_recall design (settings loader). Run from ~/ypcb-00338-1p1 inside the openXC7 nix shell, CHIPDB exported, NO sudo, after:
#   git -C ~/hexn-wt pull origin Hex-N
#   ln -sfn ~/hexn-wt/fpga/ypcb/hexn_recall designs/hexn_recall
# Usage:  bash ~/hexn-wt/fpga/ypcb/hexn_recall/run_recall.sh [NCELL]      default 7 cells (the joint build's size)
# Logs and the build folder go to /mnt/hdd/hexn_builds/recall_<NCELL>/ and recall_<NCELL>.log
set -u
NC=${1:-7}; OUT=/mnt/hdd/hexn_builds
: "${CHIPDB:=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin}"; export CHIPDB
[ -s "$CHIPDB" ] || { echo "CHIPDB file not found or empty: $CHIPDB (export CHIPDB=<path to xc7k480tffg1156.bin>)"; exit 1; }
echo "CHIPDB = $CHIPDB ($(du -h "$CHIPDB" | cut -f1))"
[ -d designs/hexn_recall ] || { echo "run this from ~/ypcb-00338-1p1 after: ln -sfn ~/hexn-wt/fpga/ypcb/hexn_recall designs/hexn_recall"; exit 1; }
mountpoint -q /mnt/hdd || { echo "/mnt/hdd is not mounted: sudo mount /dev/sda1 /mnt/hdd"; exit 1; }
name=recall_${NC}
mkdir -p $OUT/$name && ln -sfn $OUT/$name designs/hexn_recall/build_$name
echo "=== $(date '+%F %T') start $name"
HEXN_REPO=$HOME/hexn-wt HEXN_SHAPE=hex7 HEXN_NCELL=$NC BUILD=build_$name THREADS=4 FPGA_HOST=$(hostname -s) ./fpga build designs/hexn_recall hexn_recall > $OUT/$name.log 2>&1
rc=$?
echo "=== $(date '+%F %T') end   $name (exit $rc)"
grep -E "Max frequency|Device utilisation|SLICE_LUTX|FDRE|critical path" $OUT/$name.log | tail -8
ls $OUT/$name/*.bit 2>/dev/null && echo "bitstream: yes" || echo "bitstream: NO (build failed; see $OUT/$name.log)"
