# Hex-N counted detector (training side, rtl/hexn_tally_v1.v) size, synthesis only (native yosys), 12 input lanes. Usage: sh tools/hexn_size_tally_v1.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; mkdir -p "${OUT:-/tmp/hexn_size}"
printf '%-7s %-28s %6s %6s %6s\n' target config LUTs FFs carry
for tgt in gowin xc7; do for cfg in "12 6 3 8" "12 6 7 8" "12 6 15 8" "12 5 3 4" "24 6 3 8"; do set -- $cfg; L=$1; CW=$2; PU=$3; T=$4
  if [ $tgt = gowin ]; then s="synth_gowin -top hexn_tally_v1"; else s="synth_xilinx -family xc7 -top hexn_tally_v1 -flatten -noiopad"; fi
  log=${OUT:-/tmp/hexn_size}/tally_${tgt}_${L}_${CW}_${PU}_${T}.log
  $Y -q -l $log -p "read_verilog rtl/hexn_tally_v1.v; chparam -set LANES $L -set CW $CW -set PUSH_OWN $PU -set T $T hexn_tally_v1; $s" >/dev/null 2>&1
  awk -v t=$tgt -v c="lanes=$L cw=$CW push=$PU T=$T" '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") ca+=x; if(n ~ /^(DFF|FD)/) f+=x } END{printf "%-7s %-28s %6d %6d %6d\n", t, c, l, f, ca}' $log
done; done
