#!/bin/bash
# Build the SDRAM test bitstream for the Tang Nano 20K (stage 1 of the far-RAM work).  Usage: fpga/build_sdt.sh [--out DIR] [--seed N]
set -e
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/sdt"; SEED=1
while [ $# -gt 0 ]; do case "$1" in --out) OUT=$2; shift;; --seed) SEED=$2; shift;; *) echo "unknown option $1"; exit 1;; esac; shift; done
DEVICE="GW2AR-LV18QN88C8/I7"; TOP=sc_top_sdt
mkdir -p "$OUT"; cd "$OUT"
YS=$(command -v yosys || command -v yowasp-yosys)
echo "== 1/3 yosys synth_gowin =="
$YS -q -l synth.log -p "read_verilog -sv $HERE/uart.v $HERE/sdram_ctl.v $HERE/sdt_selftest.v $HERE/sdt_bridge.v $HERE/$TOP.v ; hierarchy -top $TOP ; synth_gowin -top $TOP -json $TOP.json"
echo "== 2/3 nextpnr-himbaechel-gowin place and route =="
cp "$HERE/$TOP.cst" "$TOP.cst"
PNR=$(command -v nextpnr-himbaechel || command -v nextpnr-himbaechel-gowin || command -v yowasp-nextpnr-himbaechel-gowin || true)
[ -n "$PNR" ] || { echo "No nextpnr found. Install one:  pip install yowasp-nextpnr-himbaechel-gowin apycula"; exit 1; }
command -v gowin_pack >/dev/null || { echo "gowin_pack not found. Install:  pip install apycula"; exit 1; }
$PNR --device "$DEVICE" --vopt family=GW2A-18C --vopt cst="$TOP.cst" --seed $SEED --json "$TOP.json" --write "${TOP}_routed.json" --report "${TOP}_report.json" --freq 27 2>&1 | tee pnr.log | tail -25
echo "== 3/3 gowin_pack =="
gowin_pack -d "$DEVICE" -o "$TOP.fs" -s "$TOP.cst" "${TOP}_routed.json"
python3 - "$TOP" << 'PYEOF'
import json, sys
r = json.load(open(sys.argv[1] + "_report.json")); u = r["utilization"]
for k in ("LUT4", "ALU", "DFF", "BSRAM", "IOB"):
    if k in u: print("%-8s %6d / %d" % (k, u[k]["used"], u[k]["available"]))
for c, v in r["fmax"].items(): print("Fmax %s: %.1f MHz (target %.0f)" % (c, v["achieved"], v["constraint"]))
PYEOF
echo "Bitstream: $OUT/$TOP.fs   Load (SRAM only): openFPGALoader -b tangnano20k $OUT/$TOP.fs"
