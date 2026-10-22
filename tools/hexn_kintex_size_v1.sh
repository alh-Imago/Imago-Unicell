# Hex-N: size of the bank + memory block when mapped to Kintex-7 (7-series LUT6 / FF / BRAM) by yosys synth_xilinx. SYNTHESIS ONLY: no place and route, no timing; counts are what yosys maps, the real placed figures come from the openXC7 flow on the OptiPlex.
# Usage: sh tools/hexn_kintex_size_v1.sh SHAPE NCLS NCELL   (e.g. hex7 7 7 ; hex19 19 1)   -> prints one line and leaves the log in $OUT (default /tmp/hexn_kintex)
SH=${1:-hex7}; K=${2:-7}; NC=${3:-1}; Y=${YOSYS:-yosys}
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_kintex}/${SH}_nc$NC; mkdir -p $D; cd $D || exit 1
SRC="$R/rtl/hexn_tang_top_v11.v $R/rtl/hexn_uart_v1.v $R/rtl/hexn_mem_v1.v $R/rtl/gen/hexn_lattice_${SH}_w18_v14.v $R/rtl/hexn_bank_v15.v $R/rtl/hexn_det_v3.v $R/rtl/hexn_glue_v1.v $R/rtl/hexn_cell_v4.v $R/rtl/hexn_trainbank_v9.v $R/rtl/hexn_cfgbank_v2.v $R/rtl/hexn_sdiv_v1.v"
$Y -q -l synth.log -p "read_verilog -DLATMOD=hexn_lattice_${SH}_v14 -DNBW=18 -DAWB=7 -DNCLS=$K -DNCELL=$NC -DACCMODE=0 $SRC; synth_xilinx -flatten -top hexn_tang_top_v11; tee -o stat.txt stat" >/dev/null 2>&1 || { echo "SYNTH FAILED ($SH nc$NC), see $D/synth.log"; exit 1; }
python3 - "$SH" "$K" "$NC" <<'P'
import re,sys
t=open("stat.txt").read(); g=lambda n:int(m.group(1)) if (m:=re.search(r"^\s*(\d+)\s+"+n+r"\s*$",t,re.M)) else 0
lut=sum(g("LUT%d"%i) for i in range(1,7)); ff=sum(g(n) for n in ("FDRE","FDSE","FDCE","FDPE")); b36=g("RAMB36E1"); b18=g("RAMB18E1"); dsp=g("DSP48E1"); mux=g("MUXF7")+g("MUXF8"); carry=g("CARRY4"); lram=g("RAM32M")+g("RAM64M")+g("RAM32X1D")+g("RAM64X1D")+g("RAM128X1D")
print("%s %s detectors NCELL=%s: LUT %d (of 298600), FF %d (of 597200), RAMB36 %d RAMB18 %d (of 955 RAMB36), DSP %d, carry4 %d, muxF7/8 %d, distributed RAM primitives %d"%(sys.argv[1],sys.argv[2],sys.argv[3],lut,ff,b36,b18,dsp,carry,mux,lram))
P
