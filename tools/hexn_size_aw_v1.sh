# Hex-N run-time cell v2 size against ACCUMULATOR WIDTH (AW 5..9), 24 lanes (PAIRS 4). Synthesis only (native yosys). Parameters are set by editing the DEFAULTS of a temporary copy of rtl/hexn_cell_v2.v (as hexn_size_tally_v3.sh), and, for comparison, AW 6 also with yosys chparam as tools/hexn_size_v2.sh does.
# Usage: sh tools/hexn_size_aw_v1.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; D=${OUT:-/tmp/hexn_size}; mkdir -p $D
cnt() { awk -v t="$1" -v a="$2" -v m="$3" '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") c+=x; if(n ~ /^(DFF|FD)/) f+=x } END{printf "%-7s AW %-2s %-18s %6d %6d %6d\n", t, a, m, l, f, c}' $4; }
printf '%-7s %-5s %-18s %6s %6s %6s\n' target width method LUTs FFs carry
for tgt in gowin xc7; do
  if [ $tgt = gowin ]; then s="synth_gowin -top hexn_cell_v2"; else s="synth_xilinx -family xc7 -top hexn_cell_v2 -flatten -noiopad"; fi
  for aw in 5 6 7 8 9; do
    sed "s/parameter AW = 6/parameter AW = $aw/" rtl/hexn_cell_v2.v > $D/cell_aw$aw.v
    $Y -q -l $D/aw_${tgt}_$aw.log -p "read_verilog $D/cell_aw$aw.v; $s" >/dev/null 2>&1; cnt $tgt $aw "edited defaults" $D/aw_${tgt}_$aw.log
  done
  $Y -q -l $D/aw_${tgt}_chp6.log -p "read_verilog rtl/hexn_cell_v2.v; chparam -set PAIRS 4 -set AW 6 hexn_cell_v2; $s" >/dev/null 2>&1; cnt $tgt 6 "chparam" $D/aw_${tgt}_chp6.log
done
