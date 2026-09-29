// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// shift_cell_v4s.v -- a NEW v4s cell type (not a stripped version of an existing
// core): the shift function, extracted from shift_lane_addon_v2.v (unchanged,
// reused directly, not re-derived) and given its own standalone cell shell, per
// Alan's own direct scope: "the routing, the shift and the mask" as the genuinely
// new pieces the v4s family needs, with everything else being stripped versions
// of existing cores. See sub/README.md for the family's full design.
//
// Same shape as adder_cell_v4s.v: one data_in, one data_out, one forward timing
// line, fixed one-cycle latency, boot-load-only config (no live reprogramming, no
// ack, no freeze -- see adder_cell_v4s.v's own header for why, unchanged here).
//
// cfg_data field map (12 bits used, matching shift_lane_addon_v2's own real ports
// exactly -- nothing renumbered, nothing reinterpreted):
//   [0]     direction      -- 0=SHIFT_IN(left), 1=SHIFT_OUT(right)
//   [1]     shift_en       -- 0=pass through unchanged, 1=apply the shift
//   [6:2]   shift_amt[4:0] -- one of the 9 real supported amounts (1,2,4,8,12,16,
//                             20,24,28); any other value is a deliberate no-op,
//                             matching shift_lane_addon_v2's own sparse table
//   [9:7]   lane_cut[2:0]  -- SHIFT_OUT direction only, unchanged semantics
//   [11:10] shift_fine_in[1:0] -- carried-through fine-shift correction; since
//                             this v4s cell has no upstream shift_fine_addon wired
//                             to it (that would itself need to be a separate v4s
//                             cell feeding this one), this is loaded as a FIXED
//                             config value, not a live signal from another stage.
//                             Leave at 0 unless a real upstream fine-shift stage
//                             is later chained before this one.
`default_nettype none
`timescale 1ns / 1ps

module shift_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [31:0]  data_in,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        direction      = 1'b0;
    reg        shift_en       = 1'b0;
    reg  [4:0] shift_amt      = 5'h0;
    reg  [2:0] lane_cut       = 3'h0;
    reg  [1:0] shift_fine_in  = 2'h0;
    reg        armed          = 1'b0;
    reg [31:0] out_buffer     = 32'h0;
    reg        valid_out_r    = 1'b0;

    // ── The real shift logic -- unchanged from shift_lane_addon_v2 ──────
    wire [31:0] shift_result;
    shift_lane_addon_v2 SHIFT (
        .direction(direction), .shift_en(shift_en), .shift_amt(shift_amt),
        .lane_cut(lane_cut), .shift_fine_in(shift_fine_in),
        .data_in(data_in), .data_out(shift_result)
    );

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            direction     <= 1'b0;
            shift_en      <= 1'b0;
            shift_amt     <= 5'h0;
            lane_cut      <= 3'h0;
            shift_fine_in <= 2'h0;
            armed         <= 1'b0;
            out_buffer    <= 32'h0;
            valid_out_r   <= 1'b0;
        end else if (cfg_valid) begin
            direction     <= cfg_data[0];
            shift_en      <= cfg_data[1];
            shift_amt     <= cfg_data[6:2];
            lane_cut      <= cfg_data[9:7];
            shift_fine_in <= cfg_data[11:10];
            armed         <= 1'b1;
            valid_out_r   <= 1'b0;
        end else begin
            out_buffer  <= shift_result;
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
