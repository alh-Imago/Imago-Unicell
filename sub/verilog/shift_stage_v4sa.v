// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// shift_stage_v4sa.v -- points.md #916: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to shift_stage. Per Alan's own real
// point: the meaningful SHIFT_AMT range is directly tied to WIDTH, not a
// fixed 0-31 regardless of it -- the real range is 0 to WIDTH-1. An amount
// >= WIDTH is still well-defined Verilog behaviour (everything shifts out,
// the result is all zero), but it is not a USEFUL shift for that width, and
// the assembler-side work that will eventually choose SHIFT_AMT per target
// should respect WIDTH-1 as the real ceiling, not an arbitrary wider one.
//
// The shift logic itself needs no change beyond WIDTH being threaded through
// correctly: `data_in << SHIFT_AMT` / `>> SHIFT_AMT` on a WIDTH-bit value
// already shifts correctly WITHIN that width (bits shifted past either edge
// are genuinely lost, zeros fill in) -- the same real Verilog mechanism
// #909 already proved correct for width-generic arithmetic, applied here to
// a logical shift instead.
//
// Build-time-fixed SHIFT_AMT/DIRECTION, unchanged in spirit from
// shift_stage_v4s.v -- the whole reason this variant is cheap (#899: 26 LUT4
// vs the runtime-configurable shift_cell_v4s's 3,261) is that there is
// nothing left to select at runtime. Chain several of these to compose a
// larger total shift.
`default_nettype none
`timescale 1ns / 1ps

module shift_stage_v4sa #(
    parameter [15:0] CELL_ID   = 16'h0000,
    parameter        WIDTH     = 32,
    parameter        SHIFT_AMT = 0,       // real range: 0 to WIDTH-1 for a useful shift
    parameter        DIRECTION = 1'b0     // FIXED at build time: 0=left, 1=right
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,   // arms the cell; no function config left to load
    input  wire [31:0]  cfg_data,    // unused; kept for a uniform port shape

    input  wire [WIDTH-1:0]  data_in,
    input  wire               valid_in,
    output wire                ack_out,     // backward, to whoever feeds data_in

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in       // backward, from the one fixed downstream receiver
);

    reg             armed       = 1'b0;
    reg             pending     = 1'b0;
    reg [WIDTH-1:0] out_buffer  = {WIDTH{1'b0}};

    // Build-time-fixed shift -- a real Verilog parameter case, not a runtime
    // mux, now genuinely WIDTH-generic: the shift happens within exactly
    // WIDTH bits, same mechanism #909 proved correct for arithmetic.
    wire [WIDTH-1:0] shifted = (SHIFT_AMT == 0) ? data_in :
                               (DIRECTION == 1'b0) ? (data_in << SHIFT_AMT) :
                                                     (data_in >> SHIFT_AMT);

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            pending     <= 1'b0;
            out_buffer  <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            pending     <= 1'b0;
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (valid_in) begin
                out_buffer <= shifted;
                pending    <= 1'b1;
            end
        end
    end

endmodule
