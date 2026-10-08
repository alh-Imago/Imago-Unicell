#!/bin/bash
# build_adder_v4sa_scaling.sh -- points.md #908: real place-and-route for
# adder_cell_v4sa, single-unit and a real 100-stage chain, per Alan's own
# request (single unit first, then a "10x10 matrix" for real timing figures
# at scale). Both top-levels use the full-width XOR observability discipline
# #902 established -- a single-bit tap would let the synthesiser legitimately
# discard the real arithmetic as unobserved, exactly as it did on this file's
# own first draft before the mistake was caught and fixed.
#
# Needs: yosys, `pip install yowasp-nextpnr-himbaechel-gowin apycula`.
# Usage: tools/gowin_sizing/build_adder_v4sa_scaling.sh [output_dir]
#
# Honest note from building this: the 100-stage chain's place-and-route alone
# takes several minutes (real routing congestion at this scale, #908) -- in a
# sandboxed environment with a hard per-command time limit, running this whole
# script as one background job was unreliable (the job did not survive to
# completion). The single-unit stage finishes quickly; the 100-stage stage may
# need to be run as its own foreground step with a generous timeout rather than
# backgrounded, depending on the environment.
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
OUT=${1:-/tmp/adder_v4sa_scaling_build}
V=$ROOT/sub/verilog
DEVICE="GW2AR-LV18QN88C8/I7"

mkdir -p "$OUT"
cd "$OUT"

run_one () {
    TOP=$1; shift
    FILES="$@"
    echo "== $TOP: yosys synthesis =="
    yosys -p "read_verilog -sv $FILES ; hierarchy -top $TOP ; synth_gowin -top $TOP -json $TOP.json"
    cat > "$TOP.cst" << CST
IO_LOC "BOARD_CLK" 4;
IO_PORT "BOARD_CLK" IO_TYPE=LVCMOS33;
IO_LOC "BTN_RST_N" 88;
IO_PORT "BTN_RST_N" IO_TYPE=LVCMOS33 PULL_MODE=UP;
IO_LOC "BTN_ENTRY" 87;
IO_PORT "BTN_ENTRY" IO_TYPE=LVCMOS33;
IO_LOC "LED0_N" 15;
IO_PORT "LED0_N" IO_TYPE=LVCMOS33 DRIVE=8;
IO_LOC "LED1_N" 16;
IO_PORT "LED1_N" IO_TYPE=LVCMOS33 DRIVE=8;
IO_LOC "LED2_N" 17;
IO_PORT "LED2_N" IO_TYPE=LVCMOS33 DRIVE=8;
CST
    echo "== $TOP: real place-and-route against $DEVICE =="
    yowasp-nextpnr-himbaechel-gowin --device "$DEVICE" --vopt family=GW2A-18C --vopt cst="$TOP.cst" \
        --json "$TOP.json" --write "${TOP}_routed.json" --report "${TOP}_report.json" \
        --freq 27 --timing-allow-fail
    python3 - "$TOP" << 'PYEOF'
import json, sys
top = sys.argv[1]
r = json.load(open(f"{top}_report.json"))
fmax = list(r["fmax"].values())[0]["achieved"]
u = r["utilization"]
print(f"\n{top}: real Fmax {fmax:.1f} MHz (27 MHz target)")
for k in ("LUT4", "ALU", "DFF", "IOB"):
    v = u[k]
    print(f"  {k}: {v['used']}/{v['available']} ({100*v['used']/v['available']:.1f}%)")
PYEOF
    echo
}

run_one adder_v4sa_top_single "$V/adder_v4sa_top_single.v $V/adder_cell_v4sa.v $ROOT/fpga/verilog/adder_v1.v"
run_one adder_chain_v4sa_top100 "$V/adder_chain_v4sa_top100.v $V/adder_chain_v4sa.v $V/adder_cell_v4sa.v $ROOT/fpga/verilog/adder_v1.v"
