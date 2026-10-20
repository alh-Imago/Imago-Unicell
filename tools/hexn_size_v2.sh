# Hex-N cell size, v1 against v2, at 1/2/4/8 lanes per face, AW 6. Synthesis only (native yosys). Usage: sh tools/hexn_size_v2.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; mkdir -p "${OUT:-/tmp/hexn_size}"
printf '%-7s %-3s %5s %3s %6s %6s %6s\n' target ver lanes AW LUTs FFs carry
for v in 1 2; do for tgt in gowin xc7; do for p in 1 2 4 8; do aw=6
  if [ $tgt = gowin ]; then s="synth_gowin -top hexn_cell_v$v"; else s="synth_xilinx -family xc7 -top hexn_cell_v$v -flatten -noiopad"; fi
  log=${OUT:-/tmp/hexn_size}/v${v}_${tgt}_p${p}.log
  $Y -q -l $log -p "read_verilog rtl/hexn_cell_v$v.v; chparam -set PAIRS $p -set AW $aw hexn_cell_v$v; $s" >/dev/null 2>&1
  awk -v t=$tgt -v v=$v -v p=$p -v aw=$aw '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") c+=x; if(n ~ /^(DFF|FD)/) f+=x } END{printf "%-7s v%-2s %5d %3d %6d %6d %6d\n",t,v,p,aw,l,f,c}' $log
done; done; done
