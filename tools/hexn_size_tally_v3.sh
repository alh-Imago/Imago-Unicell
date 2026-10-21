# Hex-N counted detector (training side) size, parallel (rtl/hexn_tally_v1.v) against serial (rtl/hexn_tally_serial_v1.v), 12/18/24 input lanes. Synthesis only (native yosys).
# v3 (new file; supersedes hexn_size_tally_v1.sh and _v2.sh): parameters are set by editing the DEFAULTS in a temporary copy of the RTL, NOT with yosys chparam, because chparam -set gave a smaller, different circuit (probably unsigned parameter arithmetic) from the one the simulation checked.
# Usage: sh tools/hexn_size_tally_v3.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; D=${OUT:-/tmp/hexn_size}; mkdir -p $D
printf '%-7s %-9s %5s %6s %6s %6s\n' target version lanes LUTs FFs carry
for tgt in gowin xc7; do for ver in parallel serial; do for L in 12 18 24; do
  if [ $ver = parallel ]; then src=rtl/hexn_tally_v1.v; top=hexn_tally_v1; else src=rtl/hexn_tally_serial_v1.v; top=hexn_tally_serial_v1; fi
  iw=4; [ $L -gt 16 ] && iw=5
  sed -e "s/parameter LANES = 12/parameter LANES = $L/" -e "s/parameter IW = 4/parameter IW = $iw/" $src > $D/t3_${ver}_$L.v
  if [ $tgt = gowin ]; then s="synth_gowin -top $top"; else s="synth_xilinx -family xc7 -top $top -flatten -noiopad"; fi
  log=$D/tally3_${tgt}_${ver}_${L}.log
  $Y -q -l $log -p "read_verilog $D/t3_${ver}_$L.v; $s" >/dev/null 2>&1
  awk -v t=$tgt -v v=$ver -v l=$L '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) lu+=x; if(n=="ALU"||n=="CARRY4") ca+=x; if(n ~ /^(DFF|FD)/) f+=x } END{printf "%-7s %-9s %5d %6d %6d %6d\n", t, v, l, lu, f, ca}' $log
done; done; done
