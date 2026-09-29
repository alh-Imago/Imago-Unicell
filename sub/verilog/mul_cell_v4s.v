// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4s.v -- stripped version of mul_cell_v4c.v's real function. Exactly
// adder_cell_v4s.v's own shape: this is the textbook case of Alan's own stated
// v4s rule -- however many genuinely distinct roles a function needs, that's how
// many dedicated ports it gets, never a runtime decision about which port means
// what. Multiply needs two real operands, same as add; two dedicated ports
// (in_a, in_b), same as adder_cell_v4s, no cardinality, no mask.
//
// The real arithmetic -- unchanged, same bitwise_multiplier_32bit primitive
// mul_cell_v4/v4c already use, purely combinational, zero clock cycles of its
// own latency (confirmed directly in that primitive's own header). Only the low
// 32 bits of the real 64-bit product are offered, matching mul_cell_v4c's own
// real LLVM-mul-truncation convention.
//
// No config fields at all -- unlike adder (which keeps one bit for
// subtract_mode), multiply has no equivalent mode to select. cfg_valid still
// exists purely to arm the cell, matching every other v4s cell's convention.
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,   // unused; kept for a uniform port shape

    input  wire [31:0]  in_a,
    input  wire [31:0]  in_b,
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        armed       = 1'b0;
    reg [31:0] out_buffer  = 32'h0;
    reg        valid_out_r = 1'b0;

    // ── The real arithmetic -- unchanged from mul_cell_v4/v4c ────────────
    wire [63:0] mul_product;
    bitwise_multiplier_32bit MUL (
        .A(in_a), .B(in_b), .Product(mul_product)
    );

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            out_buffer  <= 32'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else begin
            // Fixed one-cycle latency, unconditional once armed -- same
            // convention as every other v4s cell.
            out_buffer  <= mul_product[31:0];
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
