#!/bin/bash
# build_icebreaker.sh — Build and flash unicell-latch for iCEBreaker
# Claudette v2.1 / unicell-latch variant
#
# Requirements:
#   yosys, nextpnr-ice40, icepack, iceprog
#
# Usage:
#   ./build_icebreaker.sh          # build only
#   ./build_icebreaker.sh flash    # build and flash

set -e
cd "$(dirname "$0")"

VDIR="verilog"
PCF="constraints/icebreaker.pcf"
BUILD="build"

mkdir -p $BUILD

echo "=== Imago UniCell Latch — iCEBreaker build ==="
echo "Clock:  24MHz (SB_HFOSC internal, validated)"
echo "Cells:  8 (NUM_CELLS in top_icebreaker.v)"
echo ""

echo "--- Synthesising..."
yosys -p "
    read_verilog $VDIR/unicell_latch.v
    read_verilog $VDIR/unicell_array_latch.v
    read_verilog $VDIR/uart_bridge.v
    read_verilog $VDIR/top_icebreaker.v
    synth_ice40 -top top -json $BUILD/icebreaker.json
" 2>&1 | grep -E "=== |Number of |Warning:|Error:"

echo ""
echo "--- Place and route (24MHz target)..."
nextpnr-ice40 \
    --up5k \
    --package sg48 \
    --pcf $PCF \
    --json $BUILD/icebreaker.json \
    --asc $BUILD/icebreaker.asc \
    --freq 24 \
    2>&1 | grep -E "Info:|Warning:|Error:|critical|MHz"

echo ""
echo "--- Packing bitstream..."
icepack $BUILD/icebreaker.asc $BUILD/icebreaker.bin

echo ""
echo "=== Build complete: $BUILD/icebreaker.bin ==="
ls -lh $BUILD/icebreaker.bin

if [ "$1" == "flash" ]; then
    echo ""
    echo "--- Flashing to iCEBreaker..."
    iceprog $BUILD/icebreaker.bin
    echo "=== Flashed ==="
fi
