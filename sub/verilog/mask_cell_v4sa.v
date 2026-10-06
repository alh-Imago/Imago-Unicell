// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mask_cell_v4sa.v -- points.md #915: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to mask.
//
// A real complication thought through deliberately, not papered over:
// mask_cell_v4s.v reuses nibble_mask_addon_v1, which is hardcoded for exactly
// 8 nibbles (32 bits). The real native width for this card is 18 bits, and
// 18 is NOT a multiple of 4 -- there is no way to reuse that fixed-width
// primitive correctly at WIDTH=18. Resolved here with a genuinely generic,
// inline nibble-mask built from a generate loop: NIBBLES = ceil(WIDTH/4),
// and the TOP nibble is allowed to be genuinely partial (fewer than 4 real
// bits) when WIDTH is not a multiple of 4 -- e.g. at WIDTH=18, nibble 4
// covers only bits [17:16], a real 2-bit nibble, not a padded or truncated
// 4-bit one. Blocking that partial nibble zeros exactly those 2 real bits,
// same meaning as blocking any other nibble -- "zero these bits if their
// nibble's mask bit is set," generalised honestly rather than assumed.
//
// cfg_data field map: [0] mask_en; [8:1] nibble_mask[7:0] -- up to 8 nibble
// mask bits are available regardless of WIDTH (matching the original's own
// field layout); at WIDTH=18 only the low 5 of those 8 bits correspond to a
// real nibble, the rest are simply unused.
`default_nettype none
`timescale 1ns / 1ps

module mask_cell_v4sa #(
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

    // #968 (Alan, 2026-10-06): the mask word stays 8 bits at every width, so each mask bit covers GROUP = ceil(WIDTH/8) data bits:
    // 1 bit up to WIDTH 8, 2 up to 16, 3 up to 24, 4 up to 32 (= the original nibble), 5 up to 40. The top group may be partial.
    // Every data bit is therefore covered at every width (the old fixed 4-bit nibble left bits 32+ with no mask bit at WIDTH > 32).
    localparam integer GROUP   = (WIDTH + 7) / 8;
    localparam integer NIBBLES = (WIDTH + GROUP - 1) / GROUP;   // group count, always <= 8 (name kept: the nibble_mask field)

    reg             mask_en     = 1'b0;
    reg  [7:0]      nibble_mask = 8'h0;
    reg             armed       = 1'b0;
    reg             pending     = 1'b0;
    reg [WIDTH-1:0] out_buffer  = {WIDTH{1'b0}};

    // ── The real, genuinely generic mask logic -- a real nibble count
    // derived from WIDTH, the top nibble honestly partial when WIDTH is not
    // a multiple of 4, not assumed or padded. ──────────────────────────
    wire [WIDTH-1:0] mask_result;
    genvar gi;
    generate
        for (gi = 0; gi < NIBBLES; gi = gi + 1) begin : NIB
            localparam integer LO = gi * GROUP;
            localparam integer HI = (LO + GROUP - 1 < WIDTH) ? (LO + GROUP - 1) : (WIDTH - 1);
            assign mask_result[HI:LO] = (mask_en && nibble_mask[gi]) ? {(HI-LO+1){1'b0}} : data_in[HI:LO];
        end
    endgenerate

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            mask_en     <= 1'b0;
            nibble_mask <= 8'h0;
            armed       <= 1'b0;
            pending     <= 1'b0;
            out_buffer  <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            mask_en     <= cfg_data[0];
            nibble_mask <= cfg_data[8:1];
            armed       <= 1'b1;
            pending     <= 1'b0;
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (valid_in) begin
                out_buffer <= mask_result;
                pending    <= 1'b1;
            end
        end
    end

endmodule
