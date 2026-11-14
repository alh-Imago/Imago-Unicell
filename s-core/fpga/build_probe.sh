#!/bin/bash
# build_probe.sh - build the block-RAM probe (bram_probe_top) for the Tang Nano 20K.
# Same open flow as build_tang.sh.  Usage: ./build_probe.sh [outdir]      (default: fpga/build_probe)
# TOP=bram_char_top ./build_probe.sh builds the characterisation design instead (output fpga/build_char_top).
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
TOP=${TOP:-bram_probe_top}; OUT=${1:-$HERE/build_${TOP#bram_}}; DEVICE="GW2AR-LV18QN88C8/I7"; SEED=${SEED:-1}
mkdir -p "$OUT"; cd "$OUT"
YS=$(command -v yosys || command -v yowasp-yosys)
echo "== 1/3 yosys synth_gowin -nowidelut =="
$YS -q -l synth.log -p "read_verilog -sv -I$HERE $HERE/../uc_core_v2s.v $HERE/uart.v $HERE/$TOP.v ; hierarchy -top $TOP ; \
  synth_gowin -nowidelut -top $TOP -json $TOP.json"
echo "== 2/3 nextpnr-himbaechel-gowin place and route =="
cp "$HERE/sc_top_tang.cst" "$TOP.cst"
PNR=$(command -v nextpnr-himbaechel || command -v nextpnr-himbaechel-gowin || command -v yowasp-nextpnr-himbaechel-gowin || true)
[ -n "$PNR" ] || { echo "No nextpnr found. Install one:  pip install yowasp-nextpnr-himbaechel-gowin apycula"; exit 1; }
command -v gowin_pack >/dev/null || { echo "gowin_pack not found. Install:  pip install apycula"; exit 1; }
$PNR --device "$DEVICE" --vopt family=GW2A-18C --vopt cst="$TOP.cst" --seed $SEED \
  --json "$TOP.json" --write "${TOP}_routed.json" --report "${TOP}_report.json" --freq 27 2>&1 | tail -15
echo "== 3/3 gowin_pack =="
gowin_pack -d "$DEVICE" -o "$TOP.fs" -s "$TOP.cst" "${TOP}_routed.json"
python3 - "$TOP" << 'PYEOF'
import json, sys
r = json.load(open(sys.argv[1] + "_report.json")); u = r["utilization"]
for k in ("LUT4", "ALU", "DFF", "RAM16SDP4", "BSRAM", "IOB"):
    if k in u: print("%-10s %6d / %d" % (k, u[k]["used"], u[k]["available"]))
for c, f in r["fmax"].items(): print("Fmax %s: %.1f MHz (target %.0f)" % (c, f["achieved"], f["constraint"]))
PYEOF
echo "Bitstream: $OUT/$TOP.fs"
