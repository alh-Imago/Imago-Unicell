#!/bin/sh
# hexn_tang_cardtest_build_v5.sh -- open-flow build (yosys synth_gowin, YoWASP nextpnr-himbaechel, gowin_pack) of the v5 card-log test hexn_tang_cardtest_v5 (read-only probe first) for the Tang Nano 20K. New file; same flow as hexn_tang_build_v18.sh.
# Options (environment): ERASE=1 builds the opt-in variant that wipes its own region first (see the header of the top); SD_BASE=<block> moves the region.
# Usage: sh tools/hexn_tang_cardtest_build_v5.sh   Output: $OUT/cardtest5/hexn_tang_cardtest_v5.fs, report.json, pnr.log
Y=${YOSYS:-yosys}; cd "$(dirname "$0")/.." || exit 1; R=$(pwd); D=${OUT:-/tmp/hexn_tang}/cardtest5; mkdir -p $D; cd $D || exit 1
CHPARAM="log build_options"; [ -n "$ERASE" ] && CHPARAM="$CHPARAM; chparam -set ERASE $ERASE hexn_tang_cardtest_v5"; [ -n "$SD_BASE" ] && CHPARAM="$CHPARAM; chparam -set SD_BASE $SD_BASE hexn_tang_cardtest_v5"
cp $R/rtl/hexn_tang_cardtest_v5.cst top.cst
$Y -q -l synth.log -p "read_verilog $R/rtl/hexn_tang_cardtest_v5.v $R/rtl/hexn_tier_v5.v $R/fpga/verilog/sd_spi_v1.v $R/rtl/hexn_sdram_v1.v $R/rtl/hexn_uart_v1.v; ${CHPARAM}; synth_gowin -top hexn_tang_cardtest_v5 -json t.json" > synth.out 2>&1 || { echo "synthesis failed"; tail -8 synth.out; exit 1; }
grep -E "has no driver|is implicitly declared" synth.log | head -5 | sed "s/^/SYNTH WARNING: /"
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst=top.cst --json t.json --freq 27 --seed ${SEED:-1} --report report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed"; tail -15 pnr.log; exit 1; }
gowin_pack -d GW2A-18C -o hexn_tang_cardtest_v5.fs routed.json > pack.log 2>&1 || { echo "pack failed"; tail -5 pack.log; exit 1; }
python3 - <<'PY'
import json; r = json.load(open("report.json")); u = r.get("utilization", {})
print({k: "%s/%s" % (v["used"], v["available"]) for k, v in u.items() if v.get("used")}); print("clock:", {k: (v["achieved"], v["constraint"]) for k, v in r.get("fmax", {}).items()}, "MHz achieved (target)")
PY
ls -l hexn_tang_cardtest_v5.fs
