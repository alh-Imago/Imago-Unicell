#!/bin/bash
# build_k7_blink_v1.sh - build the first Kintex-7 bring-up bitstream (DRAFT, never run).
# Derived from fpga/build_kintex7.sh with the UniCell sources removed.
# Needs the openXC7 toolchain (yosys, nextpnr-xilinx, fasm2frames, xc7frames2bit)
# and the xc7k480tffg1156 chipdb; run it inside the openXC7 nix environment.
# Usage: bash build_k7_blink_v1.sh
set -eo pipefail
DEVICE="xc7k480tffg1156-2"
DEVICE_BASE="xc7k480tffg1156"
HERE="$(cd "$(dirname "$0")" && pwd)"
OUT="$HERE/build"
mkdir -p "$OUT"; cd "$OUT"

yosys -l yosys.log -p "read_verilog -sv $HERE/blink_k7_v1.v; synth_xilinx -flatten -top top -nolutram; write_json blink_k7.json"

CHIPDB=$(find ~ -name "${DEVICE_BASE}.bin" 2>/dev/null | head -1)
[ -n "$CHIPDB" ] || { echo "ERROR: chipdb ${DEVICE_BASE}.bin not found (build it first, see fpga/build_kintex7.sh)"; exit 1; }

nextpnr-xilinx --chipdb "$CHIPDB" --xdc "$HERE/blink_k7_v1.xdc" --json blink_k7.json \
    --write blink_k7_routed.json --fasm blink_k7.fasm --router router2 --placer heap 2>&1 | tee nextpnr.log

DB=$(ls -d /nix/store/*nextpnr*xilinx*/share/nextpnr/external/prjxray-db/kintex7 2>/dev/null | head -1)
fasm2frames --part ${DEVICE} --db-root "$DB" blink_k7.fasm > blink_k7.frames
xc7frames2bit --part_file "$DB/${DEVICE}/part.yaml" --part_name ${DEVICE} \
    --frm_file blink_k7.frames --output_file blink_k7.bit
ls -l blink_k7.bit
echo
echo "Load into the card's volatile memory only (a power cycle undoes it):"
echo "  sudo openFPGALoader -c ft232 $OUT/blink_k7.bit"
echo "Never use the -f / flash options on this card."
