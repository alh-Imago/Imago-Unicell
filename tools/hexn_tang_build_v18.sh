# (v18: clone of v17 for board top v13 = core v9 with the layer 2 store v5 (address index + dense heap, 4-bit events); v17 left untouched as the core v8 fallback.) # (v18: new build for board top v12 = core v8 (layer 1 bank + hold + layer 2 store with reward values) behind the serial port. Clone of the v16 flow: yosys synth_gowin, YoWASP nextpnr-himbaechel, gowin_pack. Environment: SEED (default 1), FREQ (target MHz, default 27), OUT (default /tmp/hexn_tang), KCAP/CCAP are not set here (store defaults).)
# Usage: sh tools/hexn_tang_build_v18.sh   Output: $OUT/v18/hexn_tang18_core_v8.fs, report.json, pnr.log
SH=hex7; K=7; Y=${YOSYS:-yosys}
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_tang}/v18; mkdir -p $D; cd $D || exit 1; cp $R/rtl/hexn_tang_v1.cst top.cst
SRC="$R/rtl/hexn_tang_top_v13.v $R/rtl/hexn_core_v9.v $R/rtl/hexn_uart_v1.v $R/rtl/hexn_mem_v1.v $R/rtl/gen/hexn_lattice_${SH}_w18_v18.v $R/rtl/hexn_bank_v19.v $R/rtl/hexn_det_v3.v $R/rtl/hexn_glue_v1.v $R/rtl/hexn_cell_v5.v $R/rtl/hexn_trainbank_v9.v $R/rtl/hexn_cfgbank_v2.v $R/rtl/hexn_sdiv_v1.v $R/rtl/hexn_loader_v1.v $R/rtl/hexn_hold_v1.v $R/rtl/hexn_hold_v2.v $R/rtl/hexn_store_v5.v"
$Y -q -l synth.log -p "read_verilog -DLATMOD=hexn_lattice_${SH}_v18 -DNBW=18 -DAWB=7 -DNCLS=$K -DNCELL=${NCELL:-1} -DACCMODE=0 $SRC; synth_gowin -noalu -top hexn_tang_top_v13 -json bank.json" > synth.out 2>&1 || { echo "synthesis failed"; tail -8 synth.out; exit 1; }
grep -E "has no driver|is implicitly declared" synth.log | head -5 | sed "s/^/SYNTH WARNING: /"; if grep -q "has no driver" synth.log; then echo "wire with no driver; stopping"; exit 1; fi
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88PC8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json bank.json --freq ${FREQ:-27} --seed ${SEED:-1} --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed"; tail -12 pnr.log; exit 1; }
gowin_pack -d GW2A-18C -o hexn_tang18_core_v8.fs routed.json > pack.log 2>&1 || { echo "pack failed"; tail -5 pack.log; exit 1; }
python3 - <<'PY'
import json
r = json.load(open('report.json')); u = r['utilization']
print({k: "%d/%d" % (v['used'], v['available']) for k, v in u.items() if v['used']})
print("clock: %s MHz achieved (target %s)" % ({k: (v['achieved'], v['constraint']) for k, v in r['fmax'].items()}, 27))
PY
ls -l hexn_tang18_core_v8.fs
