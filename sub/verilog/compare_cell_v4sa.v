// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v4sa.v -- points.md #912: the Flex-Sub shape (ack+freeze per
// #906, real WIDTH parameter per #909/#910) applied to compare -- a third
// cell with genuine per-cycle arithmetic (a signed comparison is typically
// implemented as a subtraction under the hood, the same ALU primitive
// adder/accumulator use), continuing the ALU-ratio story #908-#911 built.
//
// The real function, unchanged from compare_cell_v4c/v4s: result = (data_in
// >= threshold), a genuine two's-complement signed comparison, output
// zero-extended to the full bus width (matching the original's own
// `{31'h0, result_bit}` convention, now `{WIDTH-1{1'b0}, result_bit}`).
//
// WIDTH note: the threshold is stored in the LOW WIDTH bits of cfg_data, not
// the full 32-bit word -- with WIDTH<32, upper cfg_data bits are simply
// unused/reserved, not reinterpreted as anything else.
//
// ack/freeze: identical shape and reasoning to adder_cell_v4sa.v/
// accumulator_cell_v4sa.v -- standard ready/valid (valid_out stays high until
// ack_in, not a one-shot pulse), freeze_in global and gating the entire
// update including cfg_valid's own effect. See adder_cell_v4sa.v's header for
// the full "why this is not a retreat from physics, not control" reasoning.
//
// Lessons from #906/#911 applied DELIBERATELY from the start here, not
// discovered again through debugging: the testbench for this file settles
// (a real delay) BEFORE clearing any pulse-like input the DUT also samples on
// the same edge -- the exact race class both those entries hit.
`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [WIDTH-1:0]  data_in,
    input  wire               valid_in,
    output wire                ack_out,     // backward, to whoever feeds data_in

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in       // backward, from the one fixed downstream receiver
);

    reg signed [WIDTH-1:0] threshold   = 0;
    reg                     armed       = 1'b0;
    reg                     pending     = 1'b0;
    reg [WIDTH-1:0]         out_buffer  = {WIDTH{1'b0}};

    // ── The real comparison -- unchanged from compare_cell_v4c/v4s ──────
    wire result_bit = ($signed(data_in) >= threshold);
    wire [WIDTH-1:0] result_ext = {{(WIDTH-1){1'b0}}, result_bit};

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            threshold   <= 0;
            armed       <= 1'b0;
            pending     <= 1'b0;
            out_buffer  <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            threshold   <= cfg_data[WIDTH-1:0];
            armed       <= 1'b1;
            pending     <= 1'b0;
            out_buffer  <= {WIDTH{1'b0}};
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (valid_in) begin
                out_buffer <= result_ext;
                pending    <= 1'b1;
            end
        end
    end

endmodule
