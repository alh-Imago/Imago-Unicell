#!/bin/bash
# build_hexn_kintex_v1.sh - Hex-N bank + memory block on the Kintex-7 card, openXC7 flow: SIZE AND TIMING MEASUREMENT (no host link yet; top = rtl/hexn_kintex_top_v1.v).
# Run inside the openXC7 nix environment (same as fpga/build_kintex7.sh):   nix develop ~/toolchain-nix
# Usage: bash fpga/build_hexn_kintex_v1.sh SHAPE NCLS NCELL [BAUDDIV]      e.g.  hex7 7 7   |   hex19 19 1
# Prints ONE summary line at the end (yosys LUT/FF/DSP/BRAM, nextpnr max frequency at the 50 MHz clock, PASS/FAIL), also appended to $OUT/summary.txt.
# Same chipdb search and flow as fpga/build_kintex7.sh. No bitstream is made unless MAKEBIT=1 (the card has no way to talk to it yet).
set -o pipefail
SH=${1:-hex7}; K=${2:-7}; NC=${3:-1}; DIV=${4:-434}
DEVICE="xc7k480tffg1156-2"; DEVICE_BASE="xc7k480tffg1156"
cd "$(dirname "$0")/.." || exit 1; R=$(pwd); OUT=${OUT:-$R/build_hexn_kintex}; D=$OUT/${SH}_k${K}_nc$NC; mkdir -p $D; cd $D || exit 1
SRC="$R/rtl/hexn_kintex_top_v1.v $R/rtl/hexn_tang_top_v11.v $R/rtl/hexn_uart_v1.v $R/rtl/hexn_mem_v1.v $R/rtl/gen/hexn_lattice_${SH}_w18_v14.v $R/rtl/hexn_bank_v15.v $R/rtl/hexn_det_v3.v $R/rtl/hexn_glue_v1.v $R/rtl/hexn_cell_v4.v $R/rtl/hexn_trainbank_v9.v $R/rtl/hexn_cfgbank_v2.v $R/rtl/hexn_sdiv_v1.v"
echo "=== Hex-N on Kintex-7: $SH, K=$K detectors, NCELL=$NC ==="
yosys -q -l synth.log -p "read_verilog -sv -DLATMOD=hexn_lattice_${SH}_v14 -DNBW=18 -DAWB=7 -DNCLS=$K -DNCELL=$NC -DACCMODE=0 -DCLKDIV=$DIV $SRC; hierarchy -check -top top; synth_xilinx -flatten -top top -nolutram -nodsp; tee -o stat.txt stat; write_json hexn.json" >/dev/null 2>&1 || { echo "SYNTH FAILED, see $D/synth.log"; exit 1; }
CHIPDB=$(find ~ -name "${DEVICE_BASE}.bin" 2>/dev/null | head -1); [ -z "$CHIPDB" ] && CHIPDB=$(find ~ -name "xc7k480t*.bin" 2>/dev/null | head -1)
[ -z "$CHIPDB" ] && { echo "ERROR: chipdb not found (run the blinky build once to generate it, see build_kintex7.sh)"; exit 1; }
nextpnr-xilinx --chipdb $CHIPDB --xdc $R/archeology/full-cell/verilog/top_kintex7.xdc --json hexn.json --write hexn_routed.json --fasm hexn.fasm --router router2 --placer heap > pnr.log 2>&1
python3 - "$SH" "$K" "$NC" <<'P' | tee -a $OUT/summary.txt
import re,sys
t=open("stat.txt").read(); g=lambda n:int(m.group(1)) if (m:=re.search(r"^\s*(\d+)\s+"+n+r"\s*$",t,re.M)) else 0
lut=sum(g("LUT%d"%i) for i in range(1,7)); ff=sum(g(n) for n in ("FDRE","FDSE","FDCE","FDPE")); b=g("RAMB36E1")+g("RAMB18E1")+g("RAMB36E1")*0
p=open("pnr.log").read(); f=re.findall(r"Max frequency for clock '[^']*': ([\d.]+) MHz \((PASS|FAIL) at ([\d.]+) MHz\)",p)
fm=("%s MHz (%s at %s MHz)"%f[-1]) if f else "no timing line (place and route failed? see pnr.log)"
ok="routed" if "Routing complete" in p or f else "NOT ROUTED"
print("RESULT %s K=%s NCELL=%s | yosys LUT %d, FF %d, BRAM %d | nextpnr: %s | %s"%(sys.argv[1],sys.argv[2],sys.argv[3],lut,ff,b,fm,ok))
P
if [ -n "$MAKEBIT" ]; then
  fasm2frames --part ${DEVICE} --db-root $(ls -d /nix/store/*nextpnr*xilinx*/share/nextpnr/external/prjxray-db/kintex7 2>/dev/null | head -1) hexn.fasm > hexn.frames
  xc7frames2bit --part_file $(ls /nix/store/*nextpnr*xilinx*/share/nextpnr/external/prjxray-db/kintex7/${DEVICE}/part.yaml 2>/dev/null | head -1) --part_name ${DEVICE} --frm_file hexn.frames --output_file hexn.bit
fi
