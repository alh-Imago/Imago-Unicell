// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// router_cell_v4s.v -- a NEW v4s cell type: a FIXED physical fan-out junction, per
// Alan's own direct scope ("if we need a split, then that's its function"). This
// is deliberately NOT an arbitrated or masked router -- see sub/README.md's own
// warning: if a router evaluates anything at runtime, it is just the old cardinal
// decode logic (upstream_mask/downstream_mask) wearing a new cell's name, and the
// whole "physics, not control" point is lost.
//
// What it does: the SAME data value is presented, unconditionally, to BOTH
// outputs, every single cycle -- there is no per-item decision about which output
// gets the data; both always do. The only configurable thing is a per-output
// ENABLE, set once at boot-load and never touched again -- a build-time choice
// about which physical output paths are actually wired into use downstream, not a
// runtime routing decision. A disabled output simply never asserts its own
// valid_out; it still receives the same data value on data_out, harmlessly.
//
// One-to-two split (the common real case). A wider fan-out is a straightforward,
// mechanical extension of the exact same pattern if a real use ever needs it --
// not built speculatively here.
//
// Same fixed one-cycle latency as every other v4s cell, for a uniform, simple
// latency budget across the whole family (every v4s cell = exactly one cycle).
//
// cfg_data field map:
//   [0] enable_a -- 1 = output A's valid_out is live
//   [1] enable_b -- 1 = output B's valid_out is live
`default_nettype none
`timescale 1ns / 1ps

module router_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [31:0]  data_in,
    input  wire         valid_in,

    output wire [31:0]  data_out_a,
    output wire          valid_out_a,
    output wire [31:0]  data_out_b,
    output wire          valid_out_b
);

    reg        enable_a     = 1'b0;
    reg        enable_b     = 1'b0;
    reg        armed        = 1'b0;
    reg [31:0] out_buffer   = 32'h0;
    reg        valid_a_r    = 1'b0;
    reg        valid_b_r    = 1'b0;

    assign data_out_a  = out_buffer;
    assign data_out_b  = out_buffer;
    assign valid_out_a = valid_a_r;
    assign valid_out_b = valid_b_r;

    always @(posedge clk) begin
        if (rst) begin
            enable_a   <= 1'b0;
            enable_b   <= 1'b0;
            armed      <= 1'b0;
            out_buffer <= 32'h0;
            valid_a_r  <= 1'b0;
            valid_b_r  <= 1'b0;
        end else if (cfg_valid) begin
            enable_a   <= cfg_data[0];
            enable_b   <= cfg_data[1];
            armed      <= 1'b1;
            valid_a_r  <= 1'b0;
            valid_b_r  <= 1'b0;
        end else begin
            // Unconditional copy -- no decision, both outputs always get it.
            out_buffer <= data_in;
            valid_a_r  <= armed && valid_in && enable_a;
            valid_b_r  <= armed && valid_in && enable_b;
        end
    end

endmodule
