#!/bin/bash
# build_tang.sh - synthesise, place-and-route and pack the S-Core single-set design for the Tang Nano 20K,
# with the same open flow as tools/gowin_sizing/build_smoke_bitstream.sh (yosys synth_gowin -nowidelut ->
# nextpnr-himbaechel-gowin -> gowin_pack).  Needs: pip install yowasp-yosys yowasp-nextpnr-himbaechel-gowin apycula
# Env: POOL=1 builds the v5 pool of 1-bit cores; NOBRAM=1 keeps every memory in LUT-RAM (no block RAM), for isolating block-RAM problems.
# Usage: ./build_tang.sh [outdir] [S] [IMEM_WORDS] [DMW] [QD] [FINE]      defaults: build 1 128 16 16 0   (FINE=1: half-octave duration buckets)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
OUT=${1:-$HERE/build}; S=${2:-1}; IMW=${3:-128}; DMW=${4:-16}; QD=${5:-16}; FINE=${6:-0}
DEVICE="GW2AR-LV18QN88C8/I7"; TOP=sc_top_tang; SEED=${SEED:-1}
SRCS="$HERE/../uc_core_fp.v $HERE/../sc_sys_v4.v"
if [ "${POOL:-0}" = 1 ]; then TOP=sc_top_pool; SRCS="$HERE/../uc_core_v2s.v $HERE/../sc_sys_v5.v"; fi   # POOL=1: pool of fixed 1-bit cores (v5)
mkdir -p "$OUT"; cd "$OUT"
if [ -n "${NOBRAM:-}" ] && [ "${POOL:-0}" = 1 ]; then   # strip the block-RAM attribute so every memory stays in LUT-RAM
  sed 's/(\* ram_style = "block" \*) //g' "$HERE/../sc_sys_v5.v" > sc_sys_v5_nobram.v
  SRCS="$HERE/../uc_core_v2s.v $(pwd)/sc_sys_v5_nobram.v"
fi
YS=$(command -v yosys || command -v yowasp-yosys)   # native yosys first: the YoWASP build runs out of stack on this design
echo "== 1/3 yosys synth_gowin -nowidelut  (S=$S IMEM_WORDS=$IMW DMW=$DMW QD=$QD) =="
$YS -q -l synth.log -p "read_verilog -sv $SRCS $HERE/uart.v $HERE/host_bridge.v $HERE/$TOP.v ; \
  chparam -set S $S -set IMEM_WORDS $IMW -set DMW $DMW -set QD $QD -set FINE $FINE $TOP ; hierarchy -top $TOP ; \
  synth_gowin -nowidelut ${NOBRAM:+-nobram} -top $TOP -json $TOP.json" 
grep -A40 "Number of cells" synth.log | tail -45 | head -40 || true
echo "== 2/3 nextpnr-himbaechel-gowin place and route =="
cp "$HERE/sc_top_tang.cst" "$TOP.cst"
PNR=$(command -v nextpnr-himbaechel || command -v nextpnr-himbaechel-gowin || command -v yowasp-nextpnr-himbaechel-gowin || true)
[ -n "$PNR" ] || { echo "No nextpnr found. Install one:  pip install yowasp-nextpnr-himbaechel-gowin apycula   (or a native nextpnr-himbaechel)"; exit 1; }
command -v gowin_pack >/dev/null || { echo "gowin_pack not found. Install:  pip install apycula"; exit 1; }
echo "using $PNR"
$PNR --device "$DEVICE" --vopt family=GW2A-18C --vopt cst="$TOP.cst" \
  --seed $SEED --json "$TOP.json" --write "${TOP}_routed.json" --report "${TOP}_report.json" --freq 27 2>&1 | tail -25
echo "== 3/3 gowin_pack =="
gowin_pack -d "$DEVICE" -o "$TOP.fs" -s "$TOP.cst" "${TOP}_routed.json"
python3 - "$TOP" << 'PYEOF'
import json, sys
r = json.load(open(sys.argv[1] + "_report.json"))
u = r["utilization"]
for k in ("LUT4", "ALU", "DFF", "RAM16SDP4", "BSRAM", "IOB", "MULT18X18"):
    if k in u: print("%-10s %6d / %d" % (k, u[k]["used"], u[k]["available"]))
f = r["fmax"]
for c in f: print("Fmax %s: %.1f MHz (target %.0f)" % (c, f[c]["achieved"], f[c]["constraint"]))
PYEOF
echo "Bitstream: $OUT/$TOP.fs   Flash (SRAM only): openFPGALoader -b tangnano20k $OUT/$TOP.fs"
