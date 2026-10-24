#!/bin/bash
# ledger #1324 -- size ONE full carrier (VIXeN and v1d) in SKY130 standard cells with a native yosys (0.33). SYNTHESIS ONLY: cell area from the liberty file, nothing placed or routed,
# no clock tree, no timing, no utilisation. The liberty file is NOT in the repo (12.8 MB, public); fetch it once:
#   curl -L -o hd.lib https://raw.githubusercontent.com/efabless/skywater-pdk-libs-sky130_fd_sc_hd/master/timing/sky130_fd_sc_hd__tt_025C_1v80.lib
# Usage:  LIB=/path/hd.lib tools/sky130_sizing/size_carrier_sky130_v1.sh [OUTDIR]
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
LIB=${LIB:?set LIB to the sky130_fd_sc_hd liberty file}
OUT=${1:-/tmp/sky130_size}
mkdir -p "$OUT"
cd "$ROOT" || exit 1
for TOP in unicell_vixen_v1 unicell_vix_carrier_v1d; do
  FILES=$(python3 -c "import sys; sys.path.insert(0,'tools'); import verilog_deps_v1 as vd; print(' '.join(vd.deps('$TOP',['fpga/verilog'])))")
  yosys -p "read_verilog -sv $FILES ; hierarchy -top $TOP ; synth -top $TOP -flatten ; dfflibmap -liberty $LIB ; abc -liberty $LIB ; opt_clean ; tee -o $OUT/$TOP.stat stat -liberty $LIB" > $OUT/$TOP.log 2>&1 \
    || { echo "$TOP FAILED:"; grep -A3 "ERROR" $OUT/$TOP.log | head -5; continue; }
  echo "== $TOP"; grep -E "Number of cells|Chip area|sky130_fd_sc_hd__df" $OUT/$TOP.stat
done
echo "NAND2_1 area in this library: 3.7536 um2 (read from the liberty file); gate equivalents = chip area / 3.7536"
