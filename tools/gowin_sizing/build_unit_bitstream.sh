#!/bin/bash
# build_unit_bitstream.sh -- build a flashable Tang Nano 20K bitstream for a generated small unit
# (output of tools/sd_unit_top_v1.py): yosys -> nextpnr-himbaechel-gowin -> gowin_pack.
# Needs: `pip install yowasp-yosys yowasp-nextpnr-himbaechel-gowin apycula`.
# Usage: tools/gowin_sizing/build_unit_bitstream.sh <unit_dir> [seed]
#   Writes <unit_dir>/build/unit_top.fs plus the nextpnr report. Prints LUT/FF/BSRAM use and real Fmax.
set -euo pipefail
UNIT=$(cd "$1" && pwd)
SEED=${2:-1}
DEVICE="GW2AR-LV18QN88C8/I7"
OUT=$UNIT/build
mkdir -p "$OUT"
cd "$UNIT"
FILES=$(grep -E '\.v$' FILES.txt | tr '\n' ' ')
echo "== 1/3: yosys synthesis (yowasp-yosys, -family gw2a so the memories become BSRAM) =="
# NOTE: the system yosys 0.33 disables block RAM whenever -json is used (its own help says so), which turns the
# playout/capture memories into 1,024 LUT-RAMs and fails to place. yowasp-yosys (0.69) supports block RAM for GW2A.
yowasp-yosys -q -p "read_verilog -sv $FILES ; hierarchy -top unit_top ; synth_gowin -family gw2a -top unit_top -json build/unit_top.json" > "$OUT/yosys.log" 2>&1 || { tail -20 "$OUT/yosys.log"; exit 1; }
echo "== 2/3: place and route ($DEVICE), seed $SEED =="
cp unit_top.cst "$OUT/unit_top.cst"
cd "$OUT"   # the yowasp wrapper only sees paths below the current directory
yowasp-nextpnr-himbaechel-gowin --device "$DEVICE" --vopt family=GW2A-18C --vopt cst=unit_top.cst \
  --seed "$SEED" --json unit_top.json --write unit_top_routed.json \
  --report unit_top_report.json --freq 27 > nextpnr.log 2>&1 || { tail -30 nextpnr.log; exit 1; }
echo "== 3/3: gowin_pack =="
gowin_pack -d "$DEVICE" -o unit_top.fs -s unit_top_placed.cst unit_top_routed.json
python3 - "$OUT/unit_top_report.json" << 'PY'
import json, sys
r = json.load(open(sys.argv[1]))
u = r["utilization"]
f = max(v["achieved"] for v in r["fmax"].values())
print("Fmax %.1f MHz (board clock 27 MHz)" % f)
for k in ("LUT4","DFF","BSRAM","MULT18X18","IOB"):
    if k in u: print("%-10s %d / %d" % (k, u[k]["used"], u[k]["available"]))
assert min(v["achieved"] for v in r["fmax"].values()) >= 27, "timing FAILED at 27 MHz - do not flash"
print("PASS: timing met at 27 MHz")
PY
echo "Bitstream: $OUT/unit_top.fs"
echo "Flash (SRAM, lost on power-off): openFPGALoader -b tangnano20k $OUT/unit_top.fs"
