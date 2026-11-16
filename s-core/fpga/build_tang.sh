#!/bin/bash
# build_tang.sh - synthesise, place-and-route and pack the S-Core single-set design for the Tang Nano 20K,
# with the same open flow as tools/gowin_sizing/build_smoke_bitstream.sh (yosys synth_gowin -nowidelut ->
# nextpnr-himbaechel-gowin -> gowin_pack).  Needs: pip install yowasp-yosys yowasp-nextpnr-himbaechel-gowin apycula
# Env: POOL=1 builds the v5 pool of 1-bit cores; POOL=2 the v6 pool (32-bit-wide block-RAM memories, the one that works on the board); POOL=3 v7 = v6 plus hold/go (host commands H and G); POOL=4 v8 = v7 with one shared code store; POOL=5 v9 = v8 plus regions (base/limit checks); POOL=6 v10 = v9 plus the shared data RAM (--shared N words); POOL=7 v11 = v10 plus the code library window; NOBRAM=1 keeps every memory in LUT-RAM (no block RAM), for isolating block-RAM problems.
# Usage: ./build_tang.sh [outdir] [S] [IMEM_WORDS] [DMW] [QD] [FINE]      defaults: build 1 128 16 16 0   (FINE=1: half-octave duration buckets)
set -euo pipefail
HERE=$(cd "$(dirname "$0")" && pwd)
# Settings, either as named options in any order, or the old positional form (outdir S IMEM_WORDS DMW QD FINE).
#   --out DIR      output folder                      (default build)
#   --pool N       design: 1 v5, 2 v6, 3 v7 (hold/go), 4 v8 (shared code store), 5 v9 (regions), 6 v10 (shared data RAM), 7 v11 (+ code library window), 8 v12 (+ status / usage / trap cause)   (default: env POOL, else 7)
#   --slices N     number of 1-bit cores (slices)     (default 1)
#   --code N       shared code store, 32-bit words, power of 2   (default 128)
#   --data N       data words per slice               (default 16)
#   --shared N     shared data RAM, 32-bit words, power of 2, >= 32 (pools 6 and 7; one block RAM holds up to 512)   (default 256)
#   --queue N      task-table / queue depth           (default 16)
#   --fine 0|1     half-octave duration buckets       (default 0)
#   --seed N       place-and-route seed               (default 1)
# Every value is fixed when the bitstream is built; the board reports slices, code words and data words to the host (V command).
OUT=""; S=1; IMW=128; DMW=16; QD=16; FINE=0; DSH=256; POOLSET=${POOL:-}; POOL=${POOL:-0}   # (positional form keeps the old default: POOL unset = the v4 single-set design)
if [[ "${1:-}" == --* ]]; then
  while [ $# -gt 0 ]; do
    case "$1" in
      --out) OUT=$2;; --pool) POOL=$2; POOLSET=$2;; --slices) S=$2;; --code) IMW=$2;; --data) DMW=$2;; --shared) DSH=$2;; --queue) QD=$2;; --fine) FINE=$2;; --seed) SEED=$2;;
      -h|--help) sed -n '/^# Settings/,/^# Every value/p' "$0"; exit 0;;
      *) echo "unknown option $1 (try --help)"; exit 1;;
    esac
    [ $# -ge 2 ] || { echo "option $1 needs a value"; exit 1; }
    shift 2
  done
  OUT=${OUT:-$HERE/build}; [ -n "$POOLSET" ] || POOL=7
else
  OUT=${1:-$HERE/build}; S=${2:-1}; IMW=${3:-128}; DMW=${4:-16}; QD=${5:-16}; FINE=${6:-0}
fi
[ $((IMW & (IMW - 1))) -eq 0 ] || { echo "--code must be a power of 2 (got $IMW)"; exit 1; }
[ $((DMW & (DMW - 1))) -eq 0 ] || { echo "--data must be a power of 2 (got $DMW)"; exit 1; }
[ $((DSH & (DSH - 1))) -eq 0 ] && [ "$DSH" -ge 32 ] || { echo "--shared must be a power of 2, at least 32 (got $DSH)"; exit 1; }
export POOL
DEVICE="GW2AR-LV18QN88C8/I7"; TOP=sc_top_tang; SEED=${SEED:-1}
SRCS="$HERE/../uc_core_fp.v $HERE/../sc_sys_v4.v"; BRIDGE="$HERE/host_bridge.v"
if [ "${POOL:-0}" = 1 ]; then TOP=sc_top_pool; SRCS="$HERE/../uc_core_v2s.v $HERE/../sc_sys_v5.v"; fi   # POOL=1: pool of fixed 1-bit cores (v5)
if [ "${POOL:-0}" = 2 ]; then TOP=sc_top_pool6; SRCS="$HERE/../uc_core_v2s.v $HERE/../sc_sys_v6.v"; fi   # POOL=2: v6, memories in 32-bit-wide block RAM
if [ "${POOL:-0}" = 3 ]; then TOP=sc_top_pool7; SRCS="$HERE/../uc_core_v2s.v $HERE/../sc_sys_v7.v"; BRIDGE="$HERE/host_bridge_v2.v"; fi   # POOL=3: v7 = v6 plus hold/go
if [ "${POOL:-0}" = 4 ]; then TOP=sc_top_pool8; SRCS="$HERE/../uc_core_v2t.v $HERE/../sc_sys_v8.v"; BRIDGE="$HERE/host_bridge_v2.v"; fi   # POOL=4: v8 = v7 plus ONE shared code store for all slices
if [ "${POOL:-0}" = 5 ]; then TOP=sc_top_pool9; SRCS="$HERE/../uc_core_v2u.v $HERE/../sc_sys_v9.v"; BRIDGE="$HERE/host_bridge_v3.v"; fi   # POOL=5: v9 = v8 plus regions (code base/limit, data limit; host command B)
if [ "${POOL:-0}" = 6 ]; then TOP=sc_top_pool10; SRCS="$HERE/../uc_core_v2v.v $HERE/../sc_sys_v10.v"; BRIDGE="$HERE/host_bridge_v4.v"; fi   # POOL=6: v10 = v9 plus the shared data RAM (host commands M, L, X, Z)
if [ "${POOL:-0}" = 7 ]; then TOP=sc_top_pool11; SRCS="$HERE/../uc_core_v2v.v $HERE/../sc_sys_v11.v"; BRIDGE="$HERE/host_bridge_v5.v"; fi   # POOL=7: v11 = v10 plus the shared code library window (host command Y)
if [ "${POOL:-0}" = 8 ]; then TOP=sc_top_pool12; SRCS="$HERE/../uc_core_v2v.v $HERE/../sc_sys_v12.v"; BRIDGE="$HERE/host_bridge_v6.v"; fi   # POOL=8: v12 = v11 plus status (T), per-slice usage (U) and trap cause (E)
EXTRA=""; [ "${POOL:-0}" -ge 6 ] && EXTRA="-set DSH $DSH"
mkdir -p "$OUT"; cd "$OUT"
printf "pool=%s slices=%s code_words=%s data_words=%s shared_words=%s queue=%s fine=%s seed=%s built=%s\n" "$POOL" "$S" "$IMW" "$DMW" "$([ "$POOL" -ge 6 ] && echo $DSH || echo 0)" "$QD" "$FINE" "$SEED" "$(date -u +%FT%TZ)" | tee build_info.txt
if [ -n "${NOBRAM:-}" ] && [ "${POOL:-0}" = 1 ]; then   # force LUT-RAM (distributed) instead of block RAM: NOBRAM=1 all pool memories, =rf the register file only, =dm the data memory only
  case "$NOBRAM" in
    rf) PAT='/reg rf_a/' ;;
    dm) PAT='/reg dm/' ;;
    *)  PAT='/ram_style/' ;;
  esac
  sed "$PAT"' s/ram_style = "block"/ram_style = "distributed"/g' "$HERE/../sc_sys_v5.v" > sc_sys_v5_nobram.v
  SRCS="$HERE/../uc_core_v2s.v $(pwd)/sc_sys_v5_nobram.v"
fi
YS=$(command -v yosys || command -v yowasp-yosys)   # native yosys first: the YoWASP build runs out of stack on this design
echo "== 1/3 yosys synth_gowin -nowidelut  (S=$S IMEM_WORDS=$IMW DMW=$DMW QD=$QD) =="
$YS -q -l synth.log -p "read_verilog -sv $SRCS $HERE/uart.v $BRIDGE $HERE/$TOP.v ; \
  chparam -set S $S -set IMEM_WORDS $IMW -set DMW $DMW -set QD $QD -set FINE $FINE $EXTRA $TOP ; hierarchy -top $TOP ; \
  synth_gowin -nowidelut -top $TOP -json $TOP.json" 
grep -A40 "Number of cells" synth.log | tail -45 | head -40 || true
echo "== 2/3 nextpnr-himbaechel-gowin place and route =="
cp "$HERE/sc_top_tang.cst" "$TOP.cst"
PNR=$(command -v nextpnr-himbaechel || command -v nextpnr-himbaechel-gowin || command -v yowasp-nextpnr-himbaechel-gowin || true)
[ -n "$PNR" ] || { echo "No nextpnr found. Install one:  pip install yowasp-nextpnr-himbaechel-gowin apycula   (or a native nextpnr-himbaechel)"; exit 1; }
command -v gowin_pack >/dev/null || { echo "gowin_pack not found. Install:  pip install apycula"; exit 1; }
echo "using $PNR"
$PNR --device "$DEVICE" --vopt family=GW2A-18C --vopt cst="$TOP.cst" \
  --seed $SEED --json "$TOP.json" --write "${TOP}_routed.json" --report "${TOP}_report.json" --freq 27 2>&1 | tee pnr.log | tail -25
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
