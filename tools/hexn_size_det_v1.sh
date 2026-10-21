# Hex-N minimal detector (rtl/hexn_det_v1.v) size vs input width NB and accumulator width AW, next to the full run-time cell (rtl/hexn_cell_v2.v, 24 lanes). Synthesis only (native yosys), parameters by editing the defaults of a temporary copy (as hexn_size_aw_v1.sh).
# Usage: sh tools/hexn_size_det_v1.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; D=${OUT:-/tmp/hexn_size}; mkdir -p $D
cnt() { awk -v t="$1" -v m="$2" '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") c+=x; if(n ~ /^(DFF|FD)/) f+=x } END{printf "%-7s %-22s %6d %6d %6d\n", t, m, l, f, c}' $3; }
printf '%-7s %-22s %6s %6s %6s\n' target unit LUTs FFs carry
for tgt in gowin xc7; do
  if [ $tgt = gowin ]; then s="synth_gowin -top"; else s="synth_xilinx -family xc7 -flatten -noiopad -top"; fi
  for cfg in "12 6" "18 7" "20 7"; do set -- $cfg
    sed "s/parameter NB = 12/parameter NB = $1/; s/parameter AW = 6/parameter AW = $2/" rtl/hexn_det_v1.v > $D/det_$1_$2.v
    $Y -q -l $D/det_${tgt}_$1_$2.log -p "read_verilog $D/det_$1_$2.v; $s hexn_det_v1" >/dev/null 2>&1; cnt $tgt "detector NB $1 AW $2" $D/det_${tgt}_$1_$2.log
  done
  for aw in 6 7; do
    sed "s/parameter AW = 6/parameter AW = $aw/" rtl/hexn_cell_v2.v > $D/cellb_$aw.v
    $Y -q -l $D/cellb_${tgt}_$aw.log -p "read_verilog $D/cellb_$aw.v; $s hexn_cell_v2" >/dev/null 2>&1; cnt $tgt "full cell AW $aw" $D/cellb_${tgt}_$aw.log
  done
done
