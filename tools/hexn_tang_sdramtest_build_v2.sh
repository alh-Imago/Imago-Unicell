#!/bin/sh
# hexn_tang_sdramtest_build_v2.sh -- open-flow build (yosys synth_gowin, YoWASP nextpnr-himbaechel, gowin_pack) of the SDRAM self-test hexn_tang_sdramtest_v2 for the Tang Nano 20K. New file; same flow as hexn_tang_build_v18.sh.
# Usage: sh tools/hexn_tang_sdramtest_build_v2.sh   Output: $OUT/sdramtest2/hexn_tang_sdramtest_v2.fs, report.json, pnr.log
Y=${YOSYS:-yosys}; cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_tang}/sdramtest2; mkdir -p $D; cd $D || exit 1
cp $R/rtl/hexn_tang_sdramtest_v2.cst top.cst
$Y -q -l synth.log -p "read_verilog $R/rtl/hexn_tang_sdramtest_v2.v $R/rtl/hexn_sdram_v1.v $R/rtl/hexn_uart_v1.v; synth_gowin -top hexn_tang_sdramtest_v2 -json t.json" > synth.out 2>&1 || { echo "synthesis failed"; tail -8 synth.out; exit 1; }
grep -E "has no driver|is implicitly declared" synth.log | head -5 | sed "s/^/SYNTH WARNING: /"
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json t.json --freq 27 --seed ${SEED:-1} --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed"; tail -15 pnr.log; exit 1; }
gowin_pack -d GW2A-18C -o hexn_tang_sdramtest_v2.fs routed.json > pack.log 2>&1 || { echo "pack failed"; tail -5 pack.log; exit 1; }
python3 - <<'PY'
import json; r = json.load(open("report.json")); u = r.get("utilization", {})
print({k: "%s/%s" % (v["used"], v["available"]) for k, v in u.items() if v.get("used")}); print("clock:", {k: (v["achieved"], v["constraint"]) for k, v in r.get("fmax", {}).items()}, "MHz achieved (target)")
PY
ls -l hexn_tang_sdramtest_v2.fs
