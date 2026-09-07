// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// shift_lane_addon_v2.v — points.md #683. Cloned from
// shift_lane_addon_v1.v (kept, unchanged, matching this project's own
// "clone, don't modify a proven file" rule) -- the ONLY real change is
// a new `shift_fine_in[1:0]` input, used SOLELY to correct `lane_cut`'s
// own boundary-crossing math once `shift_fine_addon_v1` (a new, 2-bit,
// general fine-shift stage) is wired immediately upstream of this
// module in the addon chain, per Alan's own direct design.
//
// THE REAL PROBLEM THIS SOLVES, stated precisely: `lane_cut` zeros the
// bit window that CROSSED a byte boundary DURING THE SHIFT. That
// window depends on the TOTAL real shift, not just this module's own
// coarse portion. If a fine pre-shift already moved the data by 0-3
// bits before this module ever sees it, computing the window from
// `shift_amt` ALONE is wrong by up to 3 bits -- either missing a real
// crossing or drawing the window in the wrong place entirely. Per
// Alan's own direct framing: the fine amount has to be "carried
// through" to this stage, not just baked into the data, "or it will
// fail." `shift_fine_in` is that carried-through value.
//
// Genuinely NOT a re-derivation of the fine shift itself -- this
// module's own coarse sparse-table logic (the 9 discrete amounts,
// silent no-op otherwise) is IDENTICAL to v1, completely unchanged,
// and still operates only on whatever `data_in` it's given (already
// fine-shifted upstream by the time it arrives here). `shift_fine_in`
// feeds ONLY the lane_cut window math below, nowhere else.
//
// Matches v1's own existing pattern exactly: lane_cut's window math
// uses `shift_amt` unconditionally, regardless of this module's own
// `shift_en` state (an existing v1 property, not introduced here) --
// `shift_fine_in` is added into that same unconditional computation,
// not made conditional on anything v1 itself didn't already condition
// on.
//
// cfg bits, additive on top of v1's own, deliberately drawn from the
// 13 genuinely-reserved SUPER_LATCH[79:67] bits (not a re-encoding of
// any existing field):
//   shift_fine_in[1:0] — the real fine shift already applied upstream
//                 by shift_fine_addon_v1 (0 if that stage was disabled
//                 or configured to 0) -- used only to correct this
//                 module's own lane_cut window computation
`default_nettype none
`timescale 1ns / 1ps

module shift_lane_addon_v2 (
    input  wire        direction,     // 0=SHIFT_IN(left), 1=SHIFT_OUT(right)
    input  wire         shift_en,
    input  wire  [4:0]  shift_amt,
    input  wire  [2:0]  lane_cut,      // SHIFT_OUT direction only
    input  wire  [1:0]  shift_fine_in, // real, already-applied upstream fine shift
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

    // ── Lane-cut, SHIFT_OUT direction only, faithfully ported, plus
    // the real fine-shift correction (points.md #683): `lane_s` now
    // reflects the TOTAL real shift (coarse + fine), not coarse alone,
    // since the window a byte-boundary crossing occupies depends on
    // the FULL shift distance, and the fine stage has already moved
    // the data by `shift_fine_in` bits before this module ever sees
    // it. Max total is 28+3=31, still exactly 5 bits -- no overflow.
    wire [6:0]  lane_s     = {2'b0, shift_amt} + {5'b0, shift_fine_in};
    wire [63:0] lane_ones  = (64'd1 << lane_s) - 64'd1;
    wire [31:0] lane_win8  = lane_cut[0] ? ((lane_ones << 8 ) >> lane_s) : 32'd0;
    wire [31:0] lane_win16 = lane_cut[1] ? ((lane_ones << 16) >> lane_s) : 32'd0;
    wire [31:0] lane_win24 = lane_cut[2] ? ((lane_ones << 24) >> lane_s) : 32'd0;
    wire [31:0] lane_kill  = ~(lane_win8 | lane_win16 | lane_win24);

    wire [31:0] shift_out_result = shifted_right & lane_kill;

    assign data_out = direction ? shift_out_result : shifted_left;

endmodule
