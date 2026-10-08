// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4s_dsp2.v -- points.md #901: real DSP-block multiply, per Alan's own
// example and correction. #901's first attempt (a plain `a * b`) confirmed a real
// toolchain gap: yosys's `synth_gowin` pass does NOT automatically infer the
// chip's real DSP blocks for a plain multiply (measured: identical LUT4 count,
// zero DSP primitives used) -- unlike Gowin's own proprietary compiler, which
// does exactly this per Alan's own real example. There is no `dsp_map.v`-style
// inference pass in this yosys's Gowin techlibs at all.
//
// The real primitives DO exist and ARE usable, though -- `MULT36X36` is declared
// as a real blackbox in yosys's own `cells_xtra.v` (confirmed by inspection, not
// assumed), covering our 32x32 need with 4 bits of unused headroom on each
// operand. This file instantiates it directly rather than relying on inference.
//
// ASIGN/BSIGN tied low (unsigned multiply, matching bitwise_multiplier_32bit's
// own existing unsigned behaviour, and mul_cell_v4s.v's for a fair comparison).
// AREG/BREG/OUT0_REG all left at their default 0 (no internal DSP pipeline
// registers) so this primitive's own real behaviour matches the family's
// existing fixed-one-cycle-latency convention exactly: the SAME external
// out_buffer register this cell already used still provides that one cycle,
// nothing added or hidden inside the DSP block itself.
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4s_dsp2 #(
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

    // ── The real DSP block, instantiated directly ────────────────────────
    wire [71:0] dsp_product;
    MULT36X36 #(
        .AREG(1'b0), .BREG(1'b0), .OUT0_REG(1'b0), .OUT1_REG(1'b0),
        .PIPE_REG(1'b0), .ASIGN_REG(1'b0), .BSIGN_REG(1'b0)
    ) MUL (
        .A({4'h0, in_a}), .B({4'h0, in_b}),
        .ASIGN(1'b0), .BSIGN(1'b0),
        .CE(1'b1), .CLK(clk), .RESET(rst),
        .DOUT(dsp_product)
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
            out_buffer  <= dsp_product[31:0];
            valid_out_r <= armed && valid_in;
        end
    end

endmodule
