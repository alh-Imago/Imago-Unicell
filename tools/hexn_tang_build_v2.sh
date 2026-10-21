# (v2: board top v2 with the DUMP command; NORAM=1 forces the trainer's counter memory into plain flip-flops, as a test of the distributed-RAM blocks.)
# Hex-N: build the Tang Nano 20K bitstream of the lattice bank with the serial command link. Native yosys -> YoWASP nextpnr-himbaechel-gowin -> gowin_pack (Apycula). Usage: sh tools/hexn_tang_build_v1.sh [shape cells]   (default hex7 7)
# Output: $OUT/hexn_tang_<shape>.fs (load with:  openFPGALoader -b tangnano20k hexn_tang_<shape>.fs   or  ... -f  to write it to flash).  Pins: rtl/hexn_tang_v1.cst.
SH=${1:-hex7}; K=${2:-7}; Y=${YOSYS:-/usr/bin/yosys}
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_tang}/$SH; mkdir -p $D; cd $D || exit 1; cp $R/rtl/hexn_tang_v1.cst top.cst
TAG=""; TR=$R/rtl/hexn_trainbank_v2.v
if [ -n "$NORAM" ]; then TAG="_noram"; sed 's/reg signed \[CB-1:0\] mem /(* ram_style = "registers" *) reg signed [CB-1:0] mem /' $TR > trainbank_noram.v; TR=$D/trainbank_noram.v; fi
SRC="$R/rtl/hexn_tang_top_v2.v $R/rtl/hexn_uart_v1.v $R/rtl/gen/hexn_lattice_${SH}_v2.v $R/rtl/hexn_bank_v3.v $R/rtl/hexn_det_v2.v $TR $R/rtl/hexn_cfgbank_v2.v $R/rtl/hexn_sdiv_v1.v"
$Y -q -l synth.log -p "read_verilog -DLATMOD=hexn_lattice_${SH}_v2 -DNCLS=$K $SRC; synth_gowin -top hexn_tang_top_v2 -json bank.json" >/dev/null 2>&1 || { echo "synthesis failed"; tail -5 synth.log; exit 1; }
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88PC8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json bank.json --freq 27 --seed ${SEED:-1} --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed"; tail -8 pnr.log; exit 1; }
gowin_pack -d GW2A-18C -o hexn_tang2_${SH}${TAG}.fs routed.json > pack.log 2>&1 || { echo "pack failed"; tail -5 pack.log; exit 1; }
python3 - $SH $K <<'PY'
import json, sys
r = json.load(open('report.json')); u = r['utilization']
lut, alu, dff = u['LUT4']['used'], u['ALU']['used'], u['DFF']['used']
print("== %s (%s detectors): LUT4 %d + ALU %d = %d of 20736 slots (%.1f%%), %d flip-flops, %d IO, clock %.1f MHz (board clock 27)" % (sys.argv[1], sys.argv[2], lut, alu, lut + alu, 100 * (lut + alu) / 20736, dff, u['IOB']['used'], list(r['fmax'].values())[0]['achieved']))
PY
ls -l hexn_tang2_${SH}${TAG}.fs
