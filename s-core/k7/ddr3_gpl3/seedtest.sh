#!/bin/sh
# seedtest.sh - load each built seed onto the card and run the DDR3 test on it, then print one line per seed.
# For each seed: up to 3 runs in normal order, then up to 3 in stride order; a seed stops at its first failing run (it is not a good layout, no need to wait longer).
# Seed 0 means the original build in demo-projects/sc_k7_ddr3.  Full output of every run goes to $HOME/seedtest_logs/.
# Run in the nix shell (needs make, openFPGALoader and openocd on the path), with nothing else heavy running on the PC:
#   sh seedtest.sh 2 1 3 4 0
# GPL-3.0 build folder (see README.md).  Never writes the card's flash (make program loads SRAM only).
DEMO=${DEMO:-/home/alan/openFPGALoader/build/demo-projects}
S_CORE=${S_CORE:-$HOME/Imago-Unicell-score/s-core}
VER=${VER:-v1}
if [ "$VER" = v2 ]; then MK=Makefile.v2; PFX=sc_k7_ddr3_fix_seed; BIT=sc_k7_ddr3_v2.bit; else MK=Makefile; PFX=sc_k7_ddr3_seed; BIT=sc_k7_ddr3_v1.bit; fi   # VER=v2: seeds built from the fixed-link design
LOGS=$HOME/seedtest_logs; mkdir -p "$LOGS"
[ $# -gt 0 ] || { echo "usage: sh seedtest.sh SEED [SEED ...]   (0 = the original build)"; exit 1; }
which openocd >/dev/null || { echo "openocd not on the path: run  nix shell nixpkgs#openocd  first"; exit 1; }
echo "uptime: $(uptime)"
summary=""
for s in "$@"; do
  if [ "$s" = 0 ]; then d="$DEMO/sc_k7_ddr3"; else d="$DEMO/${PFX}$s"; fi
  [ -f "$d/$BIT" ] || { echo "seed $s: no bitstream in $d"; summary="$summary\nseed $s: no bitstream"; continue; }
  pkill -9 openocd 2>/dev/null; sleep 1
  echo "=== seed $s: loading"; ( cd "$d" && make -f $MK program JTAG_LINK="-c ft232" ) > "$LOGS/seed${s}_load.log" 2>&1 || { echo "seed $s: load FAILED, see $LOGS/seed${s}_load.log"; summary="$summary\nseed $s: load failed"; continue; }
  sleep 3
  res=""; bad=0
  for mode in normal stride; do
    [ $bad -eq 1 ] && break
    for i in 1 2 3; do
      if [ $mode = stride ]; then arg=stride; else arg=; fi
      ( cd "$S_CORE" && python3 ddr3test.py jtag 2048 $arg ) > "$LOGS/seed${s}_${mode}_$i.log" 2>&1
      pkill -9 openocd 2>/dev/null
      if grep -q "ALL OK" "$LOGS/seed${s}_${mode}_$i.log"; then r="ok"; else r=$(grep -E "wrong words in all|Error|error" "$LOGS/seed${s}_${mode}_$i.log" | tail -1 | cut -c1-60); [ -n "$r" ] || r="FAIL"; bad=1; fi
      echo "   $mode $i: $r"; res="$res $mode$i=$r;"
      [ $bad -eq 1 ] && break
    done
  done
  summary="$summary\nseed $s:$res"
done
echo; echo "=== summary (nothing else heavy should have been running)"; printf "$summary\n"
