#!/bin/bash
# build_kintex7.sh — Build Imago UniCell bitstream for Kintex-7
# Run inside the openXC7 nix environment: nix develop ~/toolchain-nix
#
# Usage: bash build_kintex7.sh [NUM_CELLS]
# Default: NUM_CELLS=10 for initial size measurement

set -e

NUM_CELLS=${1:-10}
DEVICE="xc7k480tffg1156-2"
TOP="top_kintex7"
SCRIPT_DIR="$(cd "$(dirname $0)" && pwd)"
VERILOG_DIR="$SCRIPT_DIR/verilog"
BUILD_DIR="$(dirname $0)/build_kintex7"

mkdir -p $BUILD_DIR
cd $BUILD_DIR

echo "=== Imago UniCell Kintex-7 Build ==="
echo "Device:    $DEVICE"
echo "NUM_CELLS: $NUM_CELLS"
echo "Top:       $TOP"
echo ""

# Step 1: Synthesis
echo "--- Step 1: Synthesis (yosys) ---"
yosys -p "
    read_verilog -sv $VERILOG_DIR/unicell.v
    read_verilog -sv $VERILOG_DIR/unicell_array.v
    read_verilog -sv $VERILOG_DIR/uart_bridge.v
    read_verilog -sv $VERILOG_DIR/top_kintex7.v
    chparam -set NUM_CELLS $NUM_CELLS top
    synth_xilinx -flatten -abc9 -top top -json ${TOP}_${NUM_CELLS}.json
" 2>&1 | tee yosys_${NUM_CELLS}.log

echo ""
echo "--- Synthesis complete ---"
grep "Number of cells:" yosys_${NUM_CELLS}.log | tail -5

# Step 2: Place and route
echo ""
echo "--- Step 2: Place and route (nextpnr-xilinx) ---"
CHIPDB=$(ls /nix/store/*nextpnr*xilinx*/share/nextpnr/xilinx/*.bin 2>/dev/null | grep -i "k480t\|480t" | head -1)
echo "Using chipdb: $CHIPDB"
nextpnr-xilinx \
    --chipdb $CHIPDB \
    --xdc $VERILOG_DIR/top_kintex7.xdc \
    --json ${TOP}_${NUM_CELLS}.json \
    --write ${TOP}_${NUM_CELLS}_routed.json \
    --fasm ${TOP}_${NUM_CELLS}.fasm \
    2>&1 | tee nextpnr_${NUM_CELLS}.log

echo ""
echo "--- Place and route complete ---"
grep "Max frequency\|PASS\|FAIL" nextpnr_${NUM_CELLS}.log | tail -5

# Step 3: Bitstream
echo ""
echo "--- Step 3: Bitstream generation ---"
fasm2frames \
    --part ${DEVICE} \
    --db-root $(ls -d /nix/store/*nextpnr*xilinx*/share/nextpnr/external/prjxray-db/kintex7 2>/dev/null | head -1) \
    ${TOP}_${NUM_CELLS}.fasm > ${TOP}_${NUM_CELLS}.frames

xc7frames2bit \
    --part_file $(ls /nix/store/*nextpnr*xilinx*/share/nextpnr/external/prjxray-db/kintex7/${DEVICE}/part.yaml 2>/dev/null | head -1) \
    --part_name ${DEVICE} \
    --frm_file ${TOP}_${NUM_CELLS}.frames \
    --output_file ${TOP}_${NUM_CELLS}.bit

echo ""
echo "=== BUILD COMPLETE ==="
echo "Bitstream: $BUILD_DIR/${TOP}_${NUM_CELLS}.bit"
ls -lh ${TOP}_${NUM_CELLS}.bit

# Resource summary
echo ""
echo "--- Resource usage ---"
grep -E "LUT|FF|BRAM|DSP|CARRY" yosys_${NUM_CELLS}.log | grep "Number of" | tail -10
