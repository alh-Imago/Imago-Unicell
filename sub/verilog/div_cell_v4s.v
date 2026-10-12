// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// div_cell_v4s.v -- ledger #1072: the division core for the SUB (stripped) family. The same arithmetic as
// div_cell_v4sa.v (unsigned restoring long division, STEPS quotient bits per clock), with what the v4s family
// removes removed, exactly as adder_cell_v4s.v does:
//   - no ack, no freeze: the cell never waits and never asks anyone to wait; its latency is a FIXED number of
//     clocks that the design must know and pad for (see below);
//   - no width control: the word is 32 bits, a localparam, not a parameter;
//   - one output only (no second port: the sub family has none). cfg_data[1] = rem_primary picks, at boot,
//     which of the two results that one output carries: 0 = the quotient (x / y), 1 = the remainder (x mod y).
// Dividend = in_a, divisor = in_b (roles by port). Division by zero needs no special case: the quotient comes
// out all ones and the remainder equals the dividend.
//
// FIXED LATENCY: valid_in sampled at an edge E0 -> valid_out high (one cycle, a forward pulse, never a stall)
// after the edge that finishes the last quotient bit, i.e. LATENCY = ceil(32 / STEPS) clocks, counting E0 as
// the first (the first STEPS bits are done at E0 straight from in_a / in_b, no separate capture clock).
//   STEPS = 32 (the default): the whole division in ONE clock, LATENCY = 1 -- the same fixed latency as
//     adder_cell_v4s / mul_cell_v4s, so a design needs no padding change; fully pipelined (a new pair every
//     clock); the largest form (a 32-deep chain).
//   STEPS < 32: a loop, LATENCY = ceil(32/STEPS), the cell is BUSY meanwhile. THROUGHPUT CONSTRAINT, stated
//     plainly (the same one mul_cell_v4s_dsp3.v has): a new operation can only start every LATENCY clocks; a
//     valid_in presented while the cell is busy is silently NOT taken (not an error, not corruption, simply not
//     sampled), so upstream must space its pairs by at least LATENCY clocks. Tested explicitly below.
//
// cfg_data: [0] reserved, [1] rem_primary, [31:2] reserved. cfg_valid arms the cell (output gated until then)
// and discards any operation in flight.
`default_nettype none
`timescale 1ns / 1ps

module div_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        STEPS   = 32       // quotient bits per clock, 1..32
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [31:0]  in_a,      // dividend
    input  wire [31:0]  in_b,      // divisor
    input  wire         valid_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    localparam W = 32;

    reg        rem_primary = 1'b0;
    reg        armed       = 1'b0;
    reg        busy        = 1'b0;
    reg        valid_out_r = 1'b0;
    reg [31:0] d_reg       = 32'h0;
    reg [31:0] r_reg       = 32'h0;
    reg [31:0] q_reg       = 32'h0;     // starts as the dividend; its bits shift out at the top as quotient bits shift in
    reg [5:0]  remaining   = 6'd0;
    reg [31:0] out_buffer  = 32'h0;

    // the first clock of an operation works straight from the inputs; later clocks from the registers
    wire        start = armed && !busy && valid_in;
    wire [31:0] sD    = busy ? d_reg     : in_b;
    wire [31:0] sR    = busy ? r_reg     : 32'h0;
    wire [31:0] sQ    = busy ? q_reg     : in_a;
    wire [5:0]  sRem  = busy ? remaining : 6'd32;

    // ── STEPS restoring-division steps in one clock; a step is skipped once the bits are used up ──
    reg [31:0] nR, nQ;
    reg [32:0] diff;
    integer    i;
    always @* begin
        nR = sR;
        nQ = sQ;
        diff = 33'h0;
        for (i = 0; i < STEPS; i = i + 1) begin
            if (i < sRem) begin
                nR   = {nR[30:0], nQ[31]};
                nQ   = {nQ[30:0], 1'b0};
                diff = {1'b0, nR} - {1'b0, sD};
                if (!diff[32]) begin
                    nR    = diff[31:0];
                    nQ[0] = 1'b1;
                end
            end
        end
    end
    wire last_clock = (sRem <= STEPS);

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            rem_primary <= 1'b0;
            armed       <= 1'b0;
            busy        <= 1'b0;
            valid_out_r <= 1'b0;
            remaining   <= 6'd0;
            out_buffer  <= 32'h0;
        end else if (cfg_valid) begin
            rem_primary <= cfg_data[1];
            armed       <= 1'b1;
            busy        <= 1'b0;
            valid_out_r <= 1'b0;
        end else begin
            valid_out_r <= 1'b0;                       // a forward pulse, one cycle
            if (busy || start) begin
                d_reg <= sD;
                r_reg <= nR;
                q_reg <= nQ;
                if (last_clock) begin
                    busy        <= 1'b0;
                    out_buffer  <= rem_primary ? nR : nQ;
                    valid_out_r <= 1'b1;
                end else begin
                    busy        <= 1'b1;
                    remaining   <= sRem - STEPS;
                end
            end
        end
    end

endmodule
