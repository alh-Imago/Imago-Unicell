#!/bin/bash
# run_fz_clk_v2.sh - run the fusion clock tests one after the other and collect the numbers (ledger #1364).  ONE build at a time.
# Run inside the nix shell (nix develop github:openxc7/toolchain-nix), in the build folder (demo-projects/sc_k7_sizes), after
#   cp the k7 files there and   S_CORE=$HOME/Imago-Unicell-score/s-core sh stage_fzp.sh
# Usage:  bash run_fz_clk_v2.sh                        (variants p4 p8 p16, targets 50 and 100 MHz, seed 1)
#         VARIANTS="p16" FREQS="100" SEEDS="1 2" bash run_fz_clk_v2.sh
# Writes build_fz_<variant>_f<freq>_s<seed>.log for each build and one summary file fzp_clk_result.txt (the numbers to paste back): the Max frequency lines of the
# placer and of the router, the LUT / FF / CARRY counts and whether it routed.  A build that fails timing at the higher target is NOT an error here: we want the number.
VARIANTS=${VARIANTS:-"p4 p8 p16"}
FREQS=${FREQS:-"50 100"}
SEEDS=${SEEDS:-"1"}
OUT=fzp_clk_result.txt
for t in nextpnr-xilinx yosys make; do command -v $t >/dev/null || { echo "STOP: $t not found: not inside the nix shell (nix develop github:openxc7/toolchain-nix)"; exit 1; }; done
[ -d rtl ] || { echo "STOP: no rtl/ folder: run stage_fzp.sh first"; exit 1; }
say() { echo "$(date '+%F %T') $*" | tee -a "$OUT"; }
say "run_fz_clk_v2: variants $VARIANTS, targets $FREQS MHz, seeds $SEEDS"
for v in $VARIANTS; do
  for f in $FREQS; do
    for s in $SEEDS; do
      [ -f Makefile.fz_$v ] || { say "STOP: Makefile.fz_$v missing"; exit 1; }
      proj=sc_k7_fz_$v; log=build_fz_${v}_f${f}_s${s}.log
      rm -f $proj.fasm $proj.frames $proj.bit
      say "=== $v target $f MHz seed $s: start ($log)"
      t0=$(date +%s)
      make -f Makefile.fz_$v PNR_ARGS="--freq $f --seed $s" > "$log" 2>&1; rc=$?
      min=$(( ($(date +%s) - t0) / 60 ))
      say "    make ended with code $rc after $min min"
      grep -E "Max frequency" "$log" | sed 's/^/    /' | tee -a "$OUT"
      grep -E "SLICE_LUTX|SLICE_FFX|CARRY4|iter=[0-9]+ overused=0|overused" "$log" | tail -4 | sed 's/^/    /' | tee -a "$OUT"
    done
  done
done
say "finished. Paste $OUT back."
