#!/bin/bash
# points.md #886 -- size every standalone UniCell cell for the Tang Nano 20K's architecture (Gowin GW2A)
# with the OPEN flow (yosys synth_gowin). SYNTHESIS ONLY: pre place-and-route, no timing, generic mapping.
#
#   tools/gowin_sizing/size_cells.sh full    # cells exactly as built (addon chain included)
#   tools/gowin_sizing/size_cells.sh lean    # addon chain replaced by pass-through stubs = the CORE alone
#
# Needs only `yosys` (apt install yosys). Nothing here touches the repo's RTL.
# REAL LIMITS: yosys 0.33's synth_gowin has no `-family` switch, so the mapping is generic; yosys+abc is
# usually less area-efficient than a vendor tool; LUT4 counts exclude routing and any utilisation ceiling;
# `lean` deliberately DELETES the shifter, so it is a lower bound for a core, not a working cell.
MODE=${1:-full}
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
V=$ROOT/fpga/verilog
STUBS=$ROOT/tools/gowin_sizing/addon_passthrough_stubs.v
ADD="invert_addon_v1.v nibble_mask_addon_v1.v shift_fine_addon_v1.v shift_lane_addon_v1.v shift_lane_addon_v2.v"
[ "$MODE" = lean ] && ADD="$STUBS"
run() {
  top=$1; shift
  out=$(cd "$V" && timeout 300 yosys -q -p "read_verilog -sv $* ; hierarchy -top $top ; synth_gowin -top $top -noiopads ; tee -o /tmp/size_$top.txt stat" 2>&1) || { echo "$top FAILED: $(echo "$out" | grep -i -m1 error)"; return; }
  lut=$(grep -E "^\s+LUT[1-4]\s" /tmp/size_$top.txt | awk '{s+=$2} END{print s+0}')
  ff=$(grep -E "^\s+DFF" /tmp/size_$top.txt | awk '{s+=$2} END{print s+0}')
  printf "%-22s %-4s LUT4=%-5s FF=%s\n" "$top" "$MODE" "$lut" "$ff"
}
run ram_cell_v4          ram_cell_v4.v $ADD
run latch_cell_v4        latch_cell_v4.v $ADD
run accumulator_cell_v4  accumulator_cell_v4.v $ADD
run compare_cell_v4      compare_cell_v4.v $ADD
run branch_cell_v4       branch_cell_v4.v $ADD
run sequencer_cell_v4    sequencer_cell_v4.v $ADD
run command_cell_v4      command_cell_v4.v
run adder_cell_v4        adder_cell_v4.v adder_v1.v $ADD
run nano_gate_v4         nano_gate_v4.v $ADD
run mul_cell_v4          mul_cell_v4.v bitwise_multiplier_32bit.v $ADD
run mul_cell_v5          mul_cell_v5.v bitwise_multiplier_32bit.v $ADD
run priority_cell_v4     priority_cell_v4.v $ADD
run corner_cell_v4       corner_cell_v4.v
run cross_cell_v4        cross_cell_v4.v corner_cell_v4.v
run merge_cell_v4        merge_cell_v4.v $ADD
