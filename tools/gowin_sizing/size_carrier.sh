#!/bin/bash
# points.md #887 -- size the VIX CARRIER positions for the Tang Nano 20K's architecture (Gowin GW2A) with yosys.
# SYNTHESIS ONLY: pre place-and-route, no routing/timing, generic mapping (yosys 0.33 has no synth_gowin -family).
#   tools/gowin_sizing/size_carrier.sh          # both carrier variants
# One carrier POSITION contains all 11 core shells sharing ONE addon chain (unlike the standalone cells, which each
# carry their own), so it is far larger than any single cell. Needs only `yosys`.
ROOT=$(cd "$(dirname "$0")/../.." && pwd)
V=$ROOT/fpga/verilog
cd "$V" || exit 1
SHELLS=$(ls *_shell_v1c.v | tr '\n' ' ')
CELLS=$(ls *_cell_v4c.v | grep -v '^tb_' | tr '\n' ' ')
HELP="invert_addon_v1.v nibble_mask_addon_v1.v shift_fine_addon_v1.v shift_lane_addon_v2.v adder_v1.v bitwise_multiplier_32bit.v nano_gate_v4.v nano_gate_v4c.v"
for TOP in unicell_vix_carrier_v1d unicell_vix_carrier_v1; do
  out=$(timeout 900 yosys -p "read_verilog -sv $TOP.v $SHELLS $CELLS $HELP ; hierarchy -top $TOP ; synth_gowin -top $TOP -noiopads ; tee -o /tmp/size_$TOP.txt stat" 2>&1) \
    || { echo "$TOP FAILED:"; echo "$out" | grep -A3 "^ERROR" | head -5; continue; }
  lut=$(grep -E "^\s+LUT[1-4]\s" /tmp/size_$TOP.txt | awk '{s+=$2} END{print s+0}')
  ff=$(grep -E "^\s+DFF" /tmp/size_$TOP.txt | awk '{s+=$2} END{print s+0}')
  printf "%-26s LUT4=%-6s FF=%-5s  (%.1f%% of 20,736 LUT4; %.1f%% of 15,552 FF)\n" "$TOP" "$lut" "$ff" \
         "$(echo "scale=1; 100*$lut/20736" | bc)" "$(echo "scale=1; 100*$ff/15552" | bc)"
done
