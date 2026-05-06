#!/bin/bash
# compare_variants.sh — Build both latch variants and compare LUT usage
# Claudette v2.1 / variant explorer
#
# Builds:
#   1. unicell_latch      (standard 32-bit tree)
#   2. unicell_latch_split (16-bit tree, 2x internal clock)
#
# Compares synthesis LUT counts to validate the theory.
# The winner becomes the production cell.

set -e
cd "$(dirname "$0")"

VDIR="verilog"
PCF="constraints/icebreaker.pcf"
BUILD="build"
mkdir -p $BUILD

echo "================================================"
echo " Imago UniCell — Variant Comparison"
echo " latch (32-bit tree) vs split (16-bit 2x clock)"
echo "================================================"
echo ""

# ── Build standard latch variant ─────────────────────────────────────────────
echo "--- Building unicell_latch (standard 32-bit tree)..."
yosys -p "
    read_verilog $VDIR/unicell_latch.v
    read_verilog $VDIR/unicell_array_latch.v
    read_verilog $VDIR/uart_bridge.v
    read_verilog $VDIR/top_icebreaker.v
    synth_ice40 -top top -json $BUILD/latch.json
" 2>&1 | grep "Number of cells\|LUT\|DFF\|CARRY"

nextpnr-ice40 --up5k --package sg48 --pcf $PCF \
    --json $BUILD/latch.json --asc $BUILD/latch.asc --freq 24 \
    2>&1 | grep "Max frequency\|ICESTORM_LC\|Warning"

icepack $BUILD/latch.asc $BUILD/latch.bin

LATCH_LUTS=$(nextpnr-ice40 --up5k --package sg48 --pcf $PCF \
    --json $BUILD/latch.json --asc /dev/null --freq 24 2>&1 | \
    grep "ICESTORM_LC" | grep -o "[0-9]* /" | head -1 | tr -d ' /')

echo ""
echo "--- Building unicell_latch_split (16-bit tree, 2x clock)..."
yosys -p "
    read_verilog $VDIR/unicell_latch_split.v
    read_verilog $VDIR/unicell_array_split.v
    read_verilog $VDIR/uart_bridge.v
    read_verilog $VDIR/top_icebreaker_split.v
    synth_ice40 -top top -json $BUILD/split.json
" 2>&1 | grep "Number of cells\|LUT\|DFF\|CARRY"

nextpnr-ice40 --up5k --package sg48 --pcf $PCF \
    --json $BUILD/split.json --asc $BUILD/split.asc --freq 24 \
    2>&1 | grep "Max frequency\|ICESTORM_LC\|Warning"

icepack $BUILD/split.asc $BUILD/split.bin

echo ""
echo "================================================"
echo " Results"
echo "================================================"
echo ""
echo " latch.bin:  $(ls -lh $BUILD/latch.bin | awk '{print $5}')"
echo " split.bin:  $(ls -lh $BUILD/split.bin | awk '{print $5}')"
echo ""
echo " Flash latch:  iceprog $BUILD/latch.bin"
echo " Flash split:  iceprog $BUILD/split.bin"
echo ""
echo " Check nextpnr output above for ICESTORM_LC counts."
echo " Lower count = fewer LUTs = more cells fit on iCEBreaker."
echo "================================================"
