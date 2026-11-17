#!/bin/sh
# seedsweep.sh - build the DDR3 design with several placer seeds, side by side, so each layout can be tried on the card.
# Why: the placer's layout decides how long the wires to the DDR3 pins are.  Same seed + same tools = same layout every time, so a seed that works on the card
# can be kept ("golden seed").  Sirmick saw about 1 layout in 4 fail a lane on this card.
# Run inside the nix shell, from this folder (it sits in demo-projects/sc_k7_ddr3):
#   sh seedsweep.sh 1 2 3 4          (builds seeds 1..4, two at a time; each in demo-projects/sc_k7_ddr3_seedN)
# Then load one:  cd ../sc_k7_ddr3_seed2 && make program JTAG_LINK="-c ft232"      and test it (ddr3test.py normal and stride, several runs).
# GPL-3.0 build (see README.md).  Never write the card's flash.
[ $# -gt 0 ] || { echo "usage: sh seedsweep.sh SEED [SEED ...]"; exit 1; }
here=$(cd "$(dirname "$0")" && pwd)
# VER=v2 builds the design with the fixed host link (Makefile.v2, folders sc_k7_ddr3_fix_seedN); default v1 as before.
VER=${VER:-v1}
if [ "$VER" = v2 ]; then MK=Makefile.v2; PFX=sc_k7_ddr3_fix_seed; BIT=sc_k7_ddr3_v2.bit; else MK=Makefile; PFX=sc_k7_ddr3_seed; BIT=sc_k7_ddr3_v1.bit; fi
[ -f "$here/../openXC7.mk" ] || { echo "run from demo-projects/sc_k7_ddr3 (../openXC7.mk not found)"; exit 1; }
[ -f "$here/../chipdb/xc7k480tffg1156.bin" ] || { echo "chipdb missing: stop, it would regenerate"; exit 1; }
build() {
  s=$1; d="$here/../$PFX$s"
  mkdir -p "$d" && cp -r "$here"/Makefile "$here"/Makefile.v2 "$here"/*.v "$here"/*.xdc "$here"/mod "$here"/upstream "$here"/rtl "$d"/ || { echo "seed $s: copy failed"; return; }
  ( cd "$d" && make -f $MK PNR_ARGS="--freq 50 --seed $s --write placed.json" > build.log 2>&1 )
  if [ -f "$d/$BIT" ]; then echo "seed $s: bitstream built"; else echo "seed $s: NO bitstream (see $d/build.log)"; fi
}
n=0
for s in "$@"; do
  build "$s" &
  n=$((n+1)); [ $((n % 2)) -eq 0 ] && wait
done
wait
echo; echo "Max frequency per seed (need cclk >= 83.33, pool_clk >= 50, ref_clk >= 200):"
for s in "$@"; do echo "-- seed $s"; grep "Max frequency" "$here/../$PFX$s/build.log" 2>/dev/null | tail -3; done
