# (settings block: shift-chain version hexn_cfgbank_v2; the address-decoded hexn_cfgbank_v1 was measured at Gowin 473 / 1,516 / 3,064 / 5,061 LUT4 for the four cases below.)
# Hex-N training bank v2 (rtl/hexn_trainbank_v2.v + hexn_sdiv_v1.v) size, alone and together with the detector settings it fills (rtl/hexn_cfgbank_v2.v). Synthesis only, native yosys, defaults edited in a temporary copy.
# Usage: sh tools/hexn_size_train_v2.sh
Y=${YOSYS:-/usr/bin/yosys}; cd "$(dirname "$0")/.." || exit 1; D=${OUT:-/tmp/hexn_size}; mkdir -p $D
cnt() { awk -v t="$1" -v m="$2" '/^ +[A-Z_$][A-Za-z0-9_$]* +[0-9]+ *$/{ n=$1; x=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") c+=x; if(n ~ /^(DFF|FD)/) f+=x; if(n ~ /^(RAM|SPX|SDPB|DPB|RAMB)/) r+=x } END{printf "%-7s %-34s LUT %6d  FF %6d  carry/ALU %4d  ram %d\n", t, m, l, f, c, r}' $3; }
for tgt in gowin xc7; do
  if [ $tgt = gowin ]; then s="synth_gowin -top"; else s="synth_xilinx -family xc7 -flatten -noiopad -top"; fi
  for cfg in "4 12 6" "8 12 6" "16 12 6" "16 20 7"; do set -- $cfg
    sed "s/parameter K = 4/parameter K = $1/; s/parameter NB = 12/parameter NB = $2/; s/parameter AW = 6/parameter AW = $3/" rtl/hexn_trainbank_v2.v > $D/t2_$1_$2_$3.v
    sed "s/parameter K = 4/parameter K = $1/; s/parameter NB = 12/parameter NB = $2/; s/parameter AW = 6/parameter AW = $3/" rtl/hexn_cfgbank_v2.v > $D/c3_$1_$2_$3.v
    $Y -q -l $D/t2_${tgt}_$1_$2_$3.log -p "read_verilog $D/t2_$1_$2_$3.v rtl/hexn_sdiv_v1.v; $s hexn_trainbank_v2" >/dev/null 2>&1; cnt $tgt "trainer K $1 NB $2 AW $3" $D/t2_${tgt}_$1_$2_$3.log
    $Y -q -l $D/c3_${tgt}_$1_$2_$3.log -p "read_verilog $D/c3_$1_$2_$3.v; $s hexn_cfgbank_v2" >/dev/null 2>&1; cnt $tgt "  detector settings (K $1 NB $2)" $D/c3_${tgt}_$1_$2_$3.log
  done
done
