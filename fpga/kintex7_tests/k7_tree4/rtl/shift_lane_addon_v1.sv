// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// shift_lane_addon_v1.v — the FIRST real ADDON in the nano/stripped
// line (points.md #253 named the ADDON category conceptually; #303
// found the FULL cell's real shift/lane mechanisms; #309/#310 sorted
// the FULL cell's audit into addon-shaped vs shell-shaped candidates
// and this is the first of the addon-shaped four to actually get
// built). Genuinely a data-path wrapper, NOT a core — never touches
// gate computation or the cell's own capture/firing state, only the
// data flowing in before it reaches the gate, or the data flowing out
// after the gate has already fired. Placement-flexible (before or
// after the cell's own data work) per Alan's own framing, 2026-08-14.
//
// FAITHFULLY PORTED, not reimplemented from the concept alone —
// verified directly against `archeology/full-cell/verilog/
// unicell64_v3.v`'s real, in-use logic (not just its own header
// comment, which describes a wider "0..31 bits" range than what's
// actually wired):
//
//   THIS IS A SPARSE, FIXED-PATTERN SHIFTER, NOT A GENERAL BARREL
//   SHIFTER. The FULL cell supports exactly 9 discrete shift amounts
//   -- {1,2,4,8,12,16,20,24,28} -- purpose-built for a packed
//   Kogge-Stone adder's own specific needs (the nibble multiples plus
//   two sub-nibble spans). Any OTHER requested amount silently passes
//   through completely unshifted -- confirmed directly in the RTL
//   ("unsupported amount: no shift"), not an oversight, a deliberate
//   "constant shift is pure rewiring (zero logic)" cost tradeoff.
//   Faithfully preserved here rather than "upgraded" to a general
//   shifter -- building something more capable than what was proven
//   would be a DIFFERENT mechanism wearing the same name, not a port.
//
//   Lane-cut is coupled to the OUT-shift direction ONLY, confirmed
//   directly at the point of use (`computed_lane = computed_shifted &
//   lane_kill` -- operates on the shift-OUT result specifically, never
//   on the shift-in path). NOT an independent third mechanism, despite
//   how it read from the header summary alone -- a real correction
//   made before building, not after (points.md #311).
//
// cfg bits, deliberately NOT cmd_latch bits (per #174's own resolved
// addon-delivery decision: dedicated addon config space, zero core
// cmd_latch bits spent on addon control):
//   direction   — 0=SHIFT_IN (left-shift before the cell's own gate
//                 work sees the data), 1=SHIFT_OUT (right-shift after
//                 the gate has already fired; lane-cut only active
//                 in this direction, matching the FULL cell exactly)
//   shift_en    — 1=apply the shift this cycle, 0=pass through
//   shift_amt   — 5-bit, only {1,2,4,8,12,16,20,24,28} do anything;
//                 any other value is a silent, deliberate no-op
//   lane_cut[2:0] — inter-byte boundary cuts (bit8/16/24), SHIFT_OUT
//                 direction only; ignored entirely in SHIFT_IN
`default_nettype none
`timescale 1ns / 1ps

module shift_lane_addon_v1 (
    input  wire        direction,     // 0=SHIFT_IN(left), 1=SHIFT_OUT(right)
    input  wire         shift_en,
    input  wire  [4:0]  shift_amt,
    input  wire  [2:0]  lane_cut,      // SHIFT_OUT direction only
    input  wire  [31:0] data_in,
    output wire  [31:0] data_out
);

    // ── Sparse fixed-pattern shift, faithfully ported ───────────────
    // Pure rewiring per proven amount, zero logic per unsupported one
    // -- exactly the FULL cell's own cost tradeoff, unchanged.
    wire [31:0] shifted_left;
    assign shifted_left = !shift_en          ? data_in :
                          (shift_amt==5'd1)  ? {data_in[30:0],  1'h0} :
                          (shift_amt==5'd2)  ? {data_in[29:0],  2'h0} :
                          (shift_amt==5'd4)  ? {data_in[27:0],  4'h0} :
                          (shift_amt==5'd8)  ? {data_in[23:0],  8'h0} :
                          (shift_amt==5'd12) ? {data_in[19:0], 12'h0} :
                          (shift_amt==5'd16) ? {data_in[15:0], 16'h0} :
                          (shift_amt==5'd20) ? {data_in[11:0], 20'h0} :
                          (shift_amt==5'd24) ? {data_in[7:0],  24'h0} :
                          (shift_amt==5'd28) ? {data_in[3:0],  28'h0} :
                          data_in;   // unsupported amount: deliberate no-op

    wire [31:0] shifted_right;
    assign shifted_right = !shift_en          ? data_in :
                           (shift_amt==5'd1)  ? { 1'h0, data_in[31: 1]} :
                           (shift_amt==5'd2)  ? { 2'h0, data_in[31: 2]} :
                           (shift_amt==5'd4)  ? { 4'h0, data_in[31: 4]} :
                           (shift_amt==5'd8)  ? { 8'h0, data_in[31: 8]} :
                           (shift_amt==5'd12) ? {12'h0, data_in[31:12]} :
                           (shift_amt==5'd16) ? {16'h0, data_in[31:16]} :
                           (shift_amt==5'd20) ? {20'h0, data_in[31:20]} :
                           (shift_amt==5'd24) ? {24'h0, data_in[31:24]} :
                           (shift_amt==5'd28) ? {28'h0, data_in[31:28]} :
                           data_in;   // unsupported amount: deliberate no-op

    // ── Lane-cut, SHIFT_OUT direction only, faithfully ported ───────
    // Zeros the bit window that crossed each active-cut byte boundary
    // during the right-shift. All-zero lane_cut (default/reserved) ->
    // lane_kill = all-ones -> computed_lane == shifted_right exactly,
    // bit-identical to the plain shift -- regression-safe default,
    // same as the FULL cell's own documented invariant.
    wire [6:0]  lane_s     = {2'b0, shift_amt};
    wire [63:0] lane_ones  = (64'd1 << lane_s) - 64'd1;
    wire [31:0] lane_win8  = lane_cut[0] ? ((lane_ones << 8 ) >> lane_s) : 32'd0;
    wire [31:0] lane_win16 = lane_cut[1] ? ((lane_ones << 16) >> lane_s) : 32'd0;
    wire [31:0] lane_win24 = lane_cut[2] ? ((lane_ones << 24) >> lane_s) : 32'd0;
    wire [31:0] lane_kill  = ~(lane_win8 | lane_win16 | lane_win24);

    wire [31:0] shift_out_result = shifted_right & lane_kill;

    assign data_out = direction ? shift_out_result : shifted_left;

endmodule
