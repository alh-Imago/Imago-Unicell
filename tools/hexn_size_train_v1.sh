# Hex-N training bank (rtl/hexn_trainbank_v1.v + hexn_sdiv_v1.v) size for K detectors of NB lanes. Synthesis only, native yosys, parameters by editing the defaults of a temporary copy. Usage: sh tools/hexn_size_train_v1.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; D=${OUT:-/tmp/hexn_size}; mkdir -p $D
cnt() { awk -v t="$1" -v m="$2" '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") c+=x; if(n ~ /^(DFF|FD)/) f+=x; if(n ~ /RAM|BSRAM|SDP|DPB|SP$/) r+=x } END{printf "%-7s %-26s LUT %6d  FF %6d  carry/ALU %5d  ram-blocks %d\n", t, m, l, f, c, r}' $3; }
for tgt in gowin xc7; do
  if [ $tgt = gowin ]; then s="synth_gowin -top"; else s="synth_xilinx -family xc7 -flatten -noiopad -top"; fi
  for cfg in "4 12 6" "8 12 6" "16 12 6" "16 20 7"; do set -- $cfg
    sed "s/parameter K = 4/parameter K = $1/; s/parameter NB = 12/parameter NB = $2/; s/parameter AW = 6/parameter AW = $3/" rtl/hexn_trainbank_v1.v > $D/tr_$1_$2_$3.v
    $Y -q -l $D/tr_${tgt}_$1_$2_$3.log -p "read_verilog $D/tr_$1_$2_$3.v rtl/hexn_sdiv_v1.v; $s hexn_trainbank_v1" >/dev/null 2>&1; cnt $tgt "bank K $1 NB $2 AW $3" $D/tr_${tgt}_$1_$2_$3.log
  done
done
