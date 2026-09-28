#!/bin/bash
# build_smoke_bitstream.sh -- points.md #892: build the real, flashable Tang Nano 20K smoke-test bitstream
# from source, end to end: yosys synthesis -> nextpnr-himbaechel-gowin place-and-route (real GW2A-18C chip
# database) -> gowin_pack (real Gowin bitstream packer).
#
# Needs: yosys, `pip install yowasp-nextpnr-himbaechel-gowin apycula`.
# Usage: tools/gowin_sizing/build_smoke_bitstream.sh [output_dir]   (default: fpga/build)
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-$ROOT/fpga/build}
V=$ROOT/fpga/verilog
DEVICE="GW2AR-LV18QN88C8/I7"
TOP=unicell_tang_nano_20k_smoke_v1
SEED=1   # pinned for a reproducible build -- nextpnr's placer is otherwise seed-dependent

mkdir -p "$OUT"
cd "$OUT"

echo "== 1/3: yosys synthesis =="
yosys -p "read_verilog -sv $V/$TOP.v $V/sequencer_shell_v1c.v $V/sequencer_cell_v4c.v ; \
          hierarchy -top $TOP ; synth_gowin -top $TOP -json $TOP.json"

echo "== 2/3: real place-and-route against $DEVICE (GW2A-18C) =="
cat > "$TOP.cst" << CST
IO_LOC "BOARD_CLK" 4;
IO_PORT "BOARD_CLK" IO_TYPE=LVCMOS33 DRIVE=8;
IO_LOC "BTN_RST_N" 88;
IO_PORT "BTN_RST_N" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "LED0_N" 15;
IO_PORT "LED0_N" IO_TYPE=LVCMOS33 DRIVE=8;
IO_LOC "LED1_N" 16;
IO_PORT "LED1_N" IO_TYPE=LVCMOS33 DRIVE=8;
IO_LOC "LED2_N" 17;
IO_PORT "LED2_N" IO_TYPE=LVCMOS33 DRIVE=8;
IO_LOC "LED3_N" 18;
IO_PORT "LED3_N" IO_TYPE=LVCMOS33 DRIVE=8;
CST
yowasp-nextpnr-himbaechel-gowin --device "$DEVICE" --vopt family=GW2A-18C --vopt cst="$TOP.cst" \
  --seed $SEED --json "$TOP.json" --write "${TOP}_routed.json" --report "${TOP}_report.json" --freq 27

echo "== 3/3: gowin_pack (real bitstream) =="
gowin_pack -d "$DEVICE" -o "$TOP.fs" -s "$TOP.cst" "${TOP}_routed.json"

python3 - "$TOP" << 'PYEOF'
import json, sys
top = sys.argv[1]
r = json.load(open(f"{top}_report.json"))
fmax = r["fmax"]["clk"]["achieved"]
print(f"\nReal Fmax: {fmax:.2f} MHz (board clock: 27 MHz, margin: {fmax/27:.1f}x)")
u = r["utilization"]
print(f"LUT4 {u['LUT4']['used']}/{u['LUT4']['available']}   "
      f"DFF {u['DFF']['used']}/{u['DFF']['available']}   "
      f"IOB {u['IOB']['used']}/{u['IOB']['available']}")
assert fmax >= 27, "FAILED real timing at the board clock -- do not flash this build"
print("PASS: real timing closure at 27 MHz confirmed.")
PYEOF

echo
echo "Bitstream: $OUT/$TOP.fs"
echo "Flash with: openFPGALoader -b tangnano20k $OUT/$TOP.fs"
