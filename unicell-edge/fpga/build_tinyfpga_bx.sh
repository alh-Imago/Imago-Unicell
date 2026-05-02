#!/bin/bash
# build_tinyfpga_bx.sh -- Build Imago UniCell for TinyFPGA BX
#
# Requirements:
#   yosys        (synthesis)
#   nextpnr-ice40 (place and route)
#   icepack      (bitstream packing)
#   tinyprog     (programming via USB bootloader)
#
# Install on Ubuntu/Debian:
#   sudo apt install yosys nextpnr-ice40 icestorm
#   pip install tinyprog
#
# Usage:
#   ./build_tinyfpga_bx.sh          # build only
#   ./build_tinyfpga_bx.sh program  # build and program

set -e
cd "$(dirname "$0")"

DEVICE="lp8k"
PACKAGE="cm81"
PCF="tinyfpga_bx.pcf"
TOP="top_tinyfpga_bx"

echo "=== Imago UniCell -- TinyFPGA BX build ==="
echo "Device: iCE40LP8K-CM81"
echo "Clock:  16MHz internal oscillator"
echo ""

# Synthesis
echo "--- Synthesising..."
yosys -p "
    read_verilog verilog/unicell_v2.v
    read_verilog verilog/uart_bridge.v
    read_verilog verilog/top_tinyfpga_bx.v
    synth_ice40 -top $TOP -json build/tinyfpga_bx.json
" 2>&1 | tail -5

# Place and route
echo "--- Place and route..."
mkdir -p build
nextpnr-ice40 \
    --$DEVICE \
    --package $PACKAGE \
    --pcf $PCF \
    --json build/tinyfpga_bx.json \
    --asc build/tinyfpga_bx.asc \
    --freq 16 \
    2>&1 | grep -E "Info:|Warning:|Error:|critical"

# Pack bitstream
echo "--- Packing bitstream..."
icepack build/tinyfpga_bx.asc build/tinyfpga_bx.bin

echo ""
echo "=== Build complete: build/tinyfpga_bx.bin ==="
echo ""

# Program if requested
if [ "$1" == "program" ]; then
    echo "--- Programming TinyFPGA BX..."
    echo "    Hold RESET button while plugging USB, release when LED blinks"
    tinyprog -p build/tinyfpga_bx.bin
    echo "=== Programmed ==="
fi
