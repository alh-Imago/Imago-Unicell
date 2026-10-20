#!/bin/bash
# ledger #1304 -- size the VIX CARRIER position for the Kintex-7 XC7K480T with yosys synth_xilinx. Clone in spirit of tools/gowin_sizing/size_carrier.sh (which is for the Tang).
# SYNTHESIS ONLY: pre place-and-route, no routing, no timing. It gives how many LUT6 / FF / DSP48 / BRAM one carrier position costs and the arithmetic capacity ceiling of the device; it is NOT a
# measure of how many positions place and route. Use a NATIVE yosys (apt install yosys, 0.33): the YoWASP yosys 0.69 on this machine ends its process in the ABC step on any design, so it cannot size anything. Set YOSYS=... to choose. Usage:  tools/kintex_sizing/size_carrier_k7_v1.sh [OUTDIR]
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
V=$ROOT/fpga/verilog
OUT=${1:-/tmp/k7_size}
mkdir -p "$OUT"
cd "$V" || exit 1
SHELLS=$(ls *_shell_v1c.v | tr '\n' ' ')
CELLS="corner_cell_v4.v "$(ls *_cell_v4c.v mul_cell_v5c.v | grep -v '^tb_' | tr "\n" " ")
HELP="invert_addon_v1.v nibble_mask_addon_v1.v shift_fine_addon_v1.v shift_lane_addon_v2.v adder_v1.v bitwise_multiplier_32bit.v nano_gate_v4.v nano_gate_v4c.v"
YOSYS=${YOSYS:-$( [ -x /usr/bin/yosys ] && echo /usr/bin/yosys || echo yosys )}
for TOP in unicell_vix_carrier_v1d unicell_vix_carrier_v1; do
  timeout 1500 $YOSYS -p "read_verilog -sv $TOP.v $SHELLS $CELLS $HELP ; hierarchy -top $TOP ; synth_xilinx -family xc7 -top $TOP -flatten -noiopad ; tee -o $OUT/$TOP.stat stat" > $OUT/$TOP.log 2>&1 \
    || { echo "$TOP FAILED:"; grep -A3 "ERROR" $OUT/$TOP.log | head -5; continue; }
  echo "== $TOP"; grep -E "^\s+(\$_?LUT|LUT[1-6]|CARRY4|FDRE|FDSE|FDCE|FDPE|DSP48E1|RAMB(18|36)E1|RAMB(18|36)|MUXF[789]|RAM[0-9A-Z]+)\s" $OUT/$TOP.stat
done
