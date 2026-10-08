// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v4s.v -- stripped version of compare_cell_v4c.v's real function
// (value vs a configured, static threshold), same mechanical strip as
// adder_cell_v4s.v: no addon chain (compare never had one used at this level
// anyway), no cardinal routing/masks, no ack, fixed one-cycle latency, boot-load
// config only. See sub/README.md and adder_cell_v4s.v for the family's shared
// rationale, unchanged here.
//
// The real function, unchanged from compare_cell_v4c: result = (data_in >=
// threshold), a genuine two's-complement signed comparison, output zero-extended
// to 32 bits (matching the original's own `{31'h0, result_bit}` convention).
//
// cfg_data field map:
//   [31:0] threshold -- the configured signed reference value, full 32 bits
//                        (compare_cell_v4c packed this alongside masks in a
//                        64-bit word; with no masks left here, it gets the
//                        whole cfg_data word to itself)
`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v4s #(
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

    reg signed [31:0] threshold   = 32'sh0;
    reg               armed       = 1'b0;
    reg        [31:0] out_buffer  = 32'h0;
    reg               valid_out_r = 1'b0;

    // ── The real comparison -- unchanged from compare_cell_v4c ──────────
    wire result_bit = ($signed(data_in) >= threshold);

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            threshold   <= 32'sh0;
            armed       <= 1'b0;
            out_buffer  <= 32'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            threshold   <= cfg_data;
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else begin
            out_buffer  <= {31'h0, result_bit};
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
