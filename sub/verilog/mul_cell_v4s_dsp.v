// mul_cell_v4s_dsp.v -- points.md #901 experiment: same real function as
// mul_cell_v4s.v, but the multiply itself is a plain, native `a * b` (per Alan's
// own real DSP-inference example), not the hand-built bitwise_multiplier_32bit
// array multiplier. Real question being tested: does yosys's synth_gowin
// actually map this onto the chip's real MULT18X18/MULT36X36 DSP blocks (48
// available, confirmed sitting at 0 used in every report so far this session),
// or does it still fall back to LUT fabric regardless of RTL style?
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4s_dsp #(
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
    reg [63:0] out_buffer  = 64'h0;   // full real product this time, not pre-truncated
    reg        valid_out_r = 1'b0;

    assign data_out  = out_buffer[31:0];
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            out_buffer  <= 64'h0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            valid_out_r <= 1'b0;
        end else begin
            // Plain multiply -- the pattern a DSP-inference pass actually looks
            // for, per Alan's own real example.
            out_buffer  <= in_a * in_b;
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
