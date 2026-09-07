// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// shift_fine_addon_v1.v — points.md #683, per Alan's own direct
// design: a genuine, general 2-bit shifter (amounts 0-3), meant to sit
// IMMEDIATELY BEFORE shift_lane_addon_v2 in the addon chain, not as a
// replacement for it. `shift_lane_addon_v1`'s own coarse shift only
// covers 9 sparse amounts -- {1,2,4,8,12,16,20,24,28} -- a deliberate
// "constant shift is free rewiring" tradeoff, not a gap to silently
// work around. Alan's own real insight: adding a small 2-bit (0-3)
// FINE stage in front of that coarse table gives full, gap-free 0-31
// coverage for free, confirmed directly by construction -- the union
// of {coarse_tap + 0,1,2,3} for every one of the 9 taps (plus the
// implicit 0 tap already covered by shift_en=0) is exactly {0..31}
// with no gaps, since no two adjacent taps are ever more than 4 apart.
//
// GENUINELY NOT a sparse/fixed-pattern shifter like its coarse
// sibling -- with only 4 real amounts (0-3), a full mux-based general
// shifter costs nothing worth optimizing away; there is no "unsupported
// amount" case here at all, unlike the coarse stage.
//
// Real, deliberate placement in the chain, not incidental: this
// addon's own `shift_amount` output feeds `shift_lane_addon_v2`
// directly (see that module's own header) -- `lane_cut`'s boundary-
// crossing math needs the TOTAL real shift (fine + coarse) to stay
// correct once a fine pre-shift is layered in front of it, or it
// computes the wrong window entirely. This module's own job is
// strictly the DATA shift; carrying the fine amount forward as a
// separate signal (not folding it silently into the data alone) is
// what makes that downstream math possible at all.
//
// Same real direction convention as shift_lane_addon_v1, unchanged:
//   direction  — 0=SHIFT_IN (left-shift, before the cell's own gate
//                work sees the data), 1=SHIFT_OUT (right-shift, after
//                the gate has already fired)
//   shift_en   — 1=apply this fine shift this cycle, 0=pass through
//                (shift_amount still forwarded downstream either way,
//                so shift_lane_addon_v2's own lane_cut math stays
//                correct even when this stage itself is a no-op)
//   shift_amount[1:0] — 0-3, every value real, no unsupported case
`default_nettype none
`timescale 1ns / 1ps

module shift_fine_addon_v1 (
    input  wire        direction,      // 0=SHIFT_IN(left), 1=SHIFT_OUT(right)
    input  wire        shift_en,
    input  wire [1:0]  shift_amount,
    input  wire [31:0] data_in,
    output wire [31:0] data_out,
    output wire [1:0]  shift_amount_out  // forwarded, unchanged, for
                                          // shift_lane_addon_v2's own
                                          // total-shift lane_cut math
);

    wire [31:0] shifted_left;
    assign shifted_left = !shift_en           ? data_in :
                          (shift_amount==2'd1) ? {data_in[30:0], 1'h0} :
                          (shift_amount==2'd2) ? {data_in[29:0], 2'h0} :
                          (shift_amount==2'd3) ? {data_in[28:0], 3'h0} :
                          data_in;   // shift_amount==0: identity, real, not special-cased above

    wire [31:0] shifted_right;
    assign shifted_right = !shift_en           ? data_in :
                           (shift_amount==2'd1) ? {1'h0, data_in[31:1]} :
                           (shift_amount==2'd2) ? {2'h0, data_in[31:2]} :
                           (shift_amount==2'd3) ? {3'h0, data_in[31:3]} :
                           data_in;

    assign data_out = direction ? shifted_right : shifted_left;
    // Real, deliberate: forwards the FINE shift that ACTUALLY happened,
    // not the raw config value -- when shift_en=0 this stage performed
    // no real shift at all, so the correct real contribution to
    // shift_lane_addon_v2's own total-shift lane_cut math is 0, not
    // whatever shift_amount happens to be configured to.
    assign shift_amount_out = shift_en ? shift_amount : 2'd0;

endmodule
