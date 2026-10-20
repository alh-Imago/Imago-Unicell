#!/bin/sh
# Hex-N cell size at different lanes per face, on the two cards Alan has. Native yosys (0.33 here). Synthesis only, no place and route.
# Usage: sh tools/hexn_size_v1.sh [OUTDIR]       Prints one row per (target, lanes per face, accumulator width).
# NOTE: the cell's settings (cfg_* ports) are INPUTS in this RTL, so the figures exclude the storage for them; see the printed per-size bit counts.
Y=${YOSYS:-/usr/bin/yosys}; OUT=${1:-/tmp/hexn_size}; mkdir -p "$OUT"; cd "$(dirname "$0")/.." || exit 1
printf '%-7s %5s %3s %6s %6s %6s %8s\n' target lanes AW LUTs FFs carry cfgbits
for tgt in gowin xc7; do for p in 1 2 3 4 8; do for aw in 6 4; do
  if [ $tgt = gowin ]; then s="synth_gowin -top hexn_cell_v1"; else s="synth_xilinx -family xc7 -top hexn_cell_v1 -flatten -noiopad"; fi
  log="$OUT/${tgt}_p${p}_aw${aw}.log"
  "$Y" -q -l "$log" -p "read_verilog rtl/hexn_cell_v1.v; chparam -set PAIRS $p -set AW $aw hexn_cell_v1; $s" >/dev/null 2>&1
  awk -v t=$tgt -v p=$p -v aw=$aw 'BEGIN{l=f=c=0} /^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; v=$2; if(n ~ /^LUT[1-6]$/) l+=v; if(n=="ALU"||n=="CARRY4") c+=v; if(n ~ /^(DFF|FD)/) f+=v } END{printf "%-7s %5d %3d %6d %6d %6d %8d\n",t,p,aw,l,f,c,5*6*p+aw*6+16}' "$log"
done; done; done
