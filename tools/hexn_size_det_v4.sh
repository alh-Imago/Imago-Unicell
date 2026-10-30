# Hex-N detector v3 (unsigned, burst) against v4 (signed total and margin): logic size, same method as tools/hexn_size_det_v2.sh (parameters set by editing the defaults of a temporary copy).
# Also sizes the controller answer stage hexn_argmax_v1 (largest signed margin) for K = 4 / 8 / 16.  Usage: OUT=<writable dir> sh tools/hexn_size_det_v4.sh
# NOTE: the installed yosys may be a sandboxed (WASI) build that only sees files in its own working directory, so each run is made from inside $D with relative names.
Y=${YOSYS:-yosys}; R=$(cd "$(dirname "$0")/.." && pwd); D=${OUT:-/tmp/hexn_size_v4}; mkdir -p $D; cp $R/rtl/hexn_det_v3.v $R/rtl/hexn_det_v4.v $R/rtl/hexn_argmax_v1.v $D/; cd $D || exit 1
cnt() { awk -v t="$1" -v m="$2" '/^ +[0-9]+ +[A-Z_$][A-Za-z0-9_$]* *$/{ x=$1; n=$2; if(n ~ /^LUT[1-6]$/) l+=x; if(n=="ALU"||n=="CARRY4") c+=x; if(n ~ /^(DFF|FD)/) f+=x } END{printf "%-7s %-36s LUT %5d  FF %4d  ALU/carry %4d  (LUT+ALU %5d)\n", t, m, l, f, c, l+c}' $3; }
for tgt in gowin xc7; do
  if [ $tgt = gowin ]; then s="synth_gowin -top"; else s="synth_xilinx -family xc7 -flatten -noiopad -top"; fi
  for cfg in "12 6" "18 7" "20 7"; do set -- $cfg
    sed "s/parameter NB = 12/parameter NB = $1/; s/parameter AW = 6/parameter AW = $2/" hexn_det_v3.v > d3_$1_$2.v
    $Y -q -p "read_verilog d3_$1_$2.v; $s hexn_det_v3; tee -o d3_${tgt}_$1_$2.log stat" >/dev/null 2>&1; cnt $tgt "det v3 (unsigned, burst) NB $1 AW $2" d3_${tgt}_$1_$2.log
  done
  for cfg in "12 7" "18 7" "20 7"; do set -- $cfg
    sed "s/parameter NB = 12/parameter NB = $1/; s/parameter AW = 8/parameter AW = $2/" hexn_det_v4.v > d4_$1_$2.v
    $Y -q -p "read_verilog d4_$1_$2.v; $s hexn_det_v4; tee -o d4_${tgt}_$1_$2.log stat" >/dev/null 2>&1; cnt $tgt "det v4 (signed margin) NB $1 AW $2" d4_${tgt}_$1_$2.log
  done
  for cfg in "4 10" "8 10" "16 10"; do set -- $cfg
    $Y -q -p "read_verilog hexn_argmax_v1.v; chparam -set K $1 -set MW $2 hexn_argmax_v1; $s hexn_argmax_v1; tee -o am_${tgt}_$1.log stat" >/dev/null 2>&1; cnt $tgt "argmax K $1 (10-bit margins)" am_${tgt}_$1.log
  done
done
