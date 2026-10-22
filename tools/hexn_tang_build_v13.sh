# (v13: clone of build_v12, left untouched; CELL MODE: bank v12 + glue buffer + hexn_cell_v2 + lattice v11 (tools/hexn_lattice_gen_v11.py <shape> <NBW> <AWB> -> rtl/gen/hexn_lattice_<shape>_w<NBW>_v11.v) + board top v9 (commands 0x0E LOADCELL, 0x0F RUNCELL).)
# (v12: clone of build_v11, left untouched; NO FEEDBACK PHASE: bank v11 + detector v3 + lattice v10 (tools/hexn_lattice_gen_v10.py <shape> <NBW> <AWB> -> rtl/gen/hexn_lattice_<shape>_w<NBW>_v10.v). The board top (v8), the trainer and the host tools are unchanged: only the run takes 2*PL clocks instead of 4*PL.)
# (v11: clone of build_v10 for the WIDE INPUT design: NBW (input wires, default 18) and AWB (accumulator bits, default 7) as environment variables; needs rtl/gen/hexn_lattice_<shape>_w<NBW>_v9.v from tools/hexn_lattice_gen_v9.py <shape> <NBW> <AWB>; board top v8, bank v10, trainbank v9. Use NOALU=1 (no carry-chain cells).)
# (v10: clone of build_v9; NOALU=1 env passes -noalu to synth_gowin so adders and comparators are built from plain logic, not the chip's carry-chain (ALU) cells. Same design files as v9.)
# (v9: clone of build_v8; trainer v8 with the SETW capture, bank v9, lattice v8, board top v7 with CAP 0x0D.)
# (v8: clone of build_v7; trainer v7 with the weight comparisons as plain logic, bank v8, lattice v7; board top stays v6.)
# (v7: clone of build_v6; board top v6 with ECHO 0x0C.)
# (v6: clone of build_v5; trainer v6 with one-clock ACCUM from the detectors' settings, bank v7, lattice v6; board top stays v5.)
# (v5: clone of build_v5 for board top v5 with PEEK; reads all trainer counters back.)
# (v4: board top v4 with DUMP, DUMPSUMS, DIVTEST, PROBE; ACCMODE=0|1 chooses the threshold-pass accumulation (signed sum / unsigned counters); NORAM=1 forces the trainer's counter memory into plain flip-flops, as a test of the distributed-RAM blocks.)
# Hex-N: build the Tang Nano 20K bitstream of the lattice bank with the serial command link. Native yosys -> YoWASP nextpnr-himbaechel-gowin -> gowin_pack (Apycula). Usage: sh tools/hexn_tang_build_v1.sh [shape cells]   (default hex7 7)
# Output: $OUT/hexn_tang_<shape>.fs (load with:  openFPGALoader -b tangnano20k hexn_tang_<shape>.fs   or  ... -f  to write it to flash).  Pins: rtl/hexn_tang_v1.cst.
SH=${1:-hex7}; K=${2:-7}; Y=${YOSYS:-/usr/bin/yosys}
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_tang}/$SH; mkdir -p $D; cd $D || exit 1; cp $R/rtl/hexn_tang_v1.cst top.cst
TAG="_acc${ACCMODE:-0}${NOALU:+_noalu}"; TR=$R/rtl/hexn_trainbank_v9.v
if [ -n "$NORAM" ]; then TAG="${TAG}_noram"; sed 's/reg signed \[CB-1:0\] mem /(* ram_style = "registers" *) reg signed [CB-1:0] mem /' $TR > trainbank11_noram.v; TR=$D/trainbank11_noram.v; fi
SRC="$R/rtl/hexn_tang_top_v9.v $R/rtl/hexn_uart_v1.v $R/rtl/gen/hexn_lattice_${SH}_w${NBW:-18}_v11.v $R/rtl/hexn_bank_v12.v $R/rtl/hexn_det_v3.v $R/rtl/hexn_glue_v1.v $R/rtl/hexn_cell_v2.v $TR $R/rtl/hexn_cfgbank_v2.v $R/rtl/hexn_sdiv_v1.v"
$Y -q -l synth.log -p "read_verilog -DLATMOD=hexn_lattice_${SH}_v11 -DNBW=${NBW:-18} -DAWB=${AWB:-7} -DNCLS=$K -DACCMODE=${ACCMODE:-0} $SRC; synth_gowin ${NOALU:+-noalu} -top hexn_tang_top_v9 -json bank.json" >/dev/null 2>&1 || { echo "synthesis failed"; tail -5 synth.log; exit 1; }
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88PC8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json bank.json --freq 27 --seed ${SEED:-1} --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed"; tail -8 pnr.log; exit 1; }
gowin_pack -d GW2A-18C -o hexn_tang13_w${NBW:-18}_${SH}${TAG}.fs routed.json > pack.log 2>&1 || { echo "pack failed"; tail -5 pack.log; exit 1; }
python3 - $SH $K <<'PY'
import json, sys
r = json.load(open('report.json')); u = r['utilization']
lut, alu, dff = u['LUT4']['used'], u['ALU']['used'], u['DFF']['used']
print("== %s (%s detectors): LUT4 %d + ALU %d = %d of 20736 slots (%.1f%%), %d flip-flops, %d IO, clock %.1f MHz (board clock 27)" % (sys.argv[1], sys.argv[2], lut, alu, lut + alu, 100 * (lut + alu) / 20736, dff, u['IOB']['used'], list(r['fmax'].values())[0]['achieved']))
PY
ls -l hexn_tang13_w${NBW:-18}_${SH}${TAG}.fs
