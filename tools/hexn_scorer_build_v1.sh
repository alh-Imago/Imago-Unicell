#!/bin/sh
# hexn_scorer_build_v1.sh -- open-flow build of the batch-scorer small unit for the Tang Nano 20K (new file 1 Nov 2026): generator -> yosys synth_gowin -> YoWASP nextpnr-himbaechel -> gowin_pack.
# Usage: sh tools/hexn_scorer_build_v1.sh   Output: fpga/build/hexn_scorer_unit_v1/ (unit_top.v, rtl/, unit_top.cst, unit_top.fs, unit_top_report.json). NOT run on a board.
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); O=$R/fpga/build/hexn_scorer_unit_v1; rm -rf $O; python3 tools/hexn_scorer_unit_v1.py --output $O > /dev/null || exit 1; cd $O || exit 1
yosys -q -l synth.log -p "read_verilog -sv $(tr '\n' ' ' < FILES.txt); synth_gowin -top unit_top -json t.json" > synth.out 2>&1 || { echo "synthesis failed"; tail -8 synth.out; exit 1; }
yowasp-nextpnr-himbaechel-gowin --device GW2AR-LV18QN88C8/I7 --vopt family=GW2A-18C --vopt cst=unit_top.cst --json t.json --freq 27 --seed ${SEED:-1} --report unit_top_report.json --write routed.json > pnr.log 2>&1 || { echo "place and route failed"; tail -15 pnr.log; exit 1; }
gowin_pack -d GW2A-18C -o unit_top.fs routed.json > pack.log 2>&1 || { echo "pack failed"; tail -5 pack.log; exit 1; }
python3 - <<'PY'
import json; r = json.load(open("unit_top_report.json")); u = r.get("utilization", {})
print({k: "%s/%s" % (v["used"], v["available"]) for k, v in u.items() if v.get("used")}); print("clock:", {k: (v["achieved"], v["constraint"]) for k, v in r.get("fmax", {}).items()}, "MHz achieved (target)")
PY
rm -f t.json routed.json synth.out pack.log; ls -l unit_top.fs
