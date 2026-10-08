// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v4sa_dsp.v -- points.md #916: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to the real DSP-based multiply from
// #901. Per Alan's own direction: mul should let a deployment specify EITHER
// the on-board DSP logic (this file) OR the actual LUT-built mul core itself
// (mul_cell_v4s.v's own bitwise_multiplier_32bit, not yet Flex-Sub'd) -- both
// stay available, this is not a replacement for the other.
//
// A real constraint specific to this DSP-based variant, worth stating
// plainly: WIDTH must be <= 36 here, a genuine hardware ceiling -- MULT36X36
// is a FIXED-size primitive, not something that gets cheaper or more
// expensive as WIDTH narrows the way LUT-built logic does. Operands below 36
// bits are zero-extended into the DSP block; the block itself costs the same
// either way. At this card's own real native width (18), the fit is
// genuinely exact -- MULT18X18 would need no padding at all -- but this file
// keeps using MULT36X36 generically (the same real primitive #901 proved
// working end to end) so one file covers every width up to 36 without
// needing per-width primitive selection logic.
`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v4sa_dsp #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        SECOND_PORT = 0,   // 1 = build the data_out_hi port's logic (#976); 0 = port exists but is silent and costs nothing
    parameter        WIDTH   = 32   // real ceiling for this variant: WIDTH <= 36
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,   // bit 0 = hi_enable (also produce the HIGH word on data_out_hi)

    input  wire [WIDTH-1:0]  in_a,
    input  wire [WIDTH-1:0]  in_b,
    input  wire               valid_in,
    output wire                ack_out,     // backward, to whoever feeds in_a/in_b

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in,      // backward, from the one fixed downstream receiver

    // SECOND OUTPUT PORT (Alan's ruling, 2026-10-06: two results = two ports, as branch does):
    // the HIGH word of the 2*WIDTH product, own valid/ack, independent of data_out's. Only
    // produced when cfg_data[0] (hi_enable) is set; clear, the port is silent and the cell is
    // exactly as before, so leaving these three ports unconnected is safe.
    output wire [WIDTH-1:0]  data_out_hi,
    output wire               valid_out_hi,
    input  wire               ack_in_hi
);

    reg             armed       = 1'b0;
    reg             pending     = 1'b0;
    reg             hi_enable   = 1'b0;
    reg             pending_hi  = 1'b0;
    reg [WIDTH-1:0] hi_buffer   = {WIDTH{1'b0}};
    reg [WIDTH-1:0] out_buffer  = {WIDTH{1'b0}};

    // ── The real DSP block, instantiated directly, unchanged from #901 ───
    wire [71:0] dsp_product;
    MULT36X36 #(
        .AREG(1'b0), .BREG(1'b0), .OUT0_REG(1'b0), .OUT1_REG(1'b0),
        .PIPE_REG(1'b0), .ASIGN_REG(1'b0), .BSIGN_REG(1'b0)
    ) MUL (
        .A({{(36-WIDTH){1'b0}}, in_a}), .B({{(36-WIDTH){1'b0}}, in_b}),
        .ASIGN(1'b0), .BSIGN(1'b0),
        .CE(1'b1), .CLK(clk), .RESET(rst),
        .DOUT(dsp_product)
    );

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign data_out_hi  = hi_buffer;
    assign valid_out_hi = pending_hi;
    // a new round needs BOTH outputs consumed (same rule as branch_cell_v4sa)
    assign ack_out   = armed && !pending && !pending_hi && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            pending     <= 1'b0;
            hi_enable   <= 1'b0;
            pending_hi  <= 1'b0;
            hi_buffer   <= {WIDTH{1'b0}};
            out_buffer  <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            hi_enable   <= (SECOND_PORT != 0) && cfg_data[0];
            pending     <= 1'b0;
            pending_hi  <= 1'b0;
        end else if (!freeze_in) begin
            if (pending || pending_hi) begin
                if (pending    && ack_in)    pending    <= 1'b0;
                if (pending_hi && ack_in_hi) pending_hi <= 1'b0;
            end else if (valid_in) begin
                hi_buffer  <= (SECOND_PORT != 0) ? dsp_product[2*WIDTH-1:WIDTH] : {WIDTH{1'b0}};
                pending_hi <= hi_enable;
                out_buffer <= dsp_product[WIDTH-1:0];
                pending    <= 1'b1;
            end
        end
    end

endmodule
