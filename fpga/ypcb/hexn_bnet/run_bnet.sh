#!/usr/bin/env bash
# run_bnet.sh: builds the merged bus network for the Kintex card, one shape after another (ONE build at a time; the machine has 8 GB), and prints size and estimated clock for each.
# Run from ~/ypcb-00338-1p1 inside the openXC7 nix shell, CHIPDB exported, NO sudo, /mnt/hdd mounted, swap on, after:
#   git -C ~/hexn-wt pull origin Hex-N
#   ln -sfn ~/hexn-wt/fpga/ypcb/hexn_bnet designs/hexn_bnet
# Usage:  bash ~/hexn-wt/fpga/ypcb/hexn_bnet/run_bnet.sh [SHAPE...]      a SHAPE is G:PER:NIN:SQL ; default: 2:8:16:2 4:16:48:3 8:8:48:3
#   2:8:16:2  = the small shape that also fits the Tang Nano 20K (compare with direction doc section 46)
#   4:16:48:3 = 4 buses of 16 cells per layer, 48 input lines, sub-queue 8 (the design point of section 44)
#   8:8:48:3  = 8 buses of 8 (section 44 says it costs about 2.6 times the logic: not understood)
# A failed shape does not stop the others. Logs and build folders go to /mnt/hdd/hexn_builds/bnet_<shape>/ and bnet_<shape>.log
set -u
SHAPES=${*:-2:8:16:2 4:16:48:3 8:8:48:3}
OUT=${HEXN_OUT:-/mnt/hdd/hexn_builds}      # set HEXN_OUT=<folder> if the big disk is mounted somewhere else (for example /media/alan/InternalHDD/hexn_builds)
: "${CHIPDB:=/home/alan/openFPGALoader/build/demo-projects/chipdb/xc7k480tffg1156.bin}"; export CHIPDB
[ -s "$CHIPDB" ] || { echo "CHIPDB file not found or empty: $CHIPDB (export CHIPDB=<path to xc7k480tffg1156.bin>)"; exit 1; }
echo "CHIPDB = $CHIPDB ($(du -h "$CHIPDB" | cut -f1))"
[ -d designs/hexn_bnet ] || { echo "run this from ~/ypcb-00338-1p1 after: ln -sfn ~/hexn-wt/fpga/ypcb/hexn_bnet designs/hexn_bnet"; exit 1; }
[ -n "${HEXN_OUT:-}" ] || mountpoint -q /mnt/hdd || { echo "/mnt/hdd is not mounted: sudo mount /dev/sda1 /mnt/hdd"; exit 1; }
for s in $SHAPES; do
  IFS=: read G PER NIN SQL <<< "$s"
  name=bnet_${G}x${PER}_n${NIN}_q${SQL}
  mkdir -p $OUT/$name && ln -sfn $OUT/$name designs/hexn_bnet/build_$name
  echo "=== $(date '+%F %T') start $name"
  HEXN_REPO=$HOME/hexn-wt HEXN_G=$G HEXN_PER=$PER HEXN_NIN=$NIN HEXN_SQL=$SQL BUILD=build_$name THREADS=4 FPGA_HOST=$(hostname -s) \
    ./fpga build designs/hexn_bnet hexn_bnet > $OUT/$name.log 2>&1
  rc=$?
  echo "=== $(date '+%F %T') end   $name (exit $rc)"
done
echo; echo "SUMMARY (lines copied from the logs; the clock is what nextpnr reports at a 50 MHz target, NOT a measurement on silicon)"
for s in $SHAPES; do
  IFS=: read G PER NIN SQL <<< "$s"; name=bnet_${G}x${PER}_n${NIN}_q${SQL}; f=$OUT/$name.log; echo "--- $name"
  grep -E "Max frequency|rror" $f | tail -6
  grep -E "SLICE_LUTX|SLICE_FFX|DSP48|RAMB|CARRY4" $OUT/$name/hexn_bnet.nextpnr.log 2>/dev/null | head -12      # use of the chip, from nextpnr
  grep -E "^\s+[0-9]+\s+(LUT[1-6]|FDRE|FDCE|FDPE|FDSE|DSP48E1|CARRY4|RAMB)" $OUT/$name/hexn_bnet.yosys.log 2>/dev/null | tail -20      # cell counts, from yosys
  ls $OUT/$name/*.bit >/dev/null 2>&1 && echo "bitstream: yes" || echo "bitstream: NO (build failed; see $f)"
done
