// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// nano_cell_v4sa.v -- points.md #917: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to nano_cell_v4s.v, built to compare
// against it directly, per Alan's own request.
//
// Same real universal 2-input gate function as nano_cell_v4s.v -- see that
// file's own header for the full, hand-verified truth table and the real
// reasoning for the dedicated hold_in_data/flow_in_data two-port shape. No
// change to the function itself; only the family's standard ack+freeze+WIDTH
// treatment added on top.
//
// One real design choice worth stating: `load_hold` is treated as its own
// event, gated by the SAME pending/ack discipline as a normal flowing
// capture would be -- loading a new hold value and presenting a normal
// computed offer are mutually exclusive on any one cycle (matching the
// family's own established "exactly one real thing happens per cycle,
// never two" convention, e.g. router_cell_v4sa.v's clear-vs-capture
// priority). `load_hold` does not itself produce an offer -- it is a real,
// silent side effect that changes what future flowing captures compute
// against, consistent with the original cell's own real behaviour (loading
// the hold was never itself an "output" event there either).
//
// cfg_data field map, unchanged: [9:0] topology.
`default_nettype none
`timescale 1ns / 1ps

module nano_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire [WIDTH-1:0]  hold_in_data,
    input  wire               load_hold,

    input  wire [WIDTH-1:0]  flow_in_data,
    input  wire               valid_in,
    output wire                ack_out,     // backward, to whoever drives flow_in_data/valid_in

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in       // backward, from the one fixed downstream receiver
);

    reg [9:0]       topology    = 10'h0;
    reg             armed       = 1'b0;
    reg             pending     = 1'b0;
    reg [WIDTH-1:0] held_value  = {WIDTH{1'b0}};
    reg [WIDTH-1:0] out_buffer  = {WIDTH{1'b0}};

    // ── The real gate logic -- unchanged from nano_cell_v4s.v, hand-verified
    // against a full truth table before trusting it (see that file's header) ──
    wire [WIDTH-1:0] g0 = ~(held_value    | held_value);
    wire [WIDTH-1:0] g1 = ~(flow_in_data  | flow_in_data);
    wire [WIDTH-1:0] g2 = ~(g0 | g1);
    wire [WIDTH-1:0] g3 = ~(g2 | g2);
    wire [WIDTH-1:0] g4 = ~(held_value    | flow_in_data);
    wire [WIDTH-1:0] g5 = ~(g4 | g4);
    wire [WIDTH-1:0] g6 = ~(held_value | g4);
    wire [WIDTH-1:0] g7 = ~(flow_in_data | g4);
    wire [WIDTH-1:0] g8 = ~(g6 | g7);
    wire [WIDTH-1:0] g9 = ~(g8 | g8);

    reg [WIDTH-1:0] computed_output;
    always @(*) begin
        computed_output = held_value;
        case (topology)
            10'h000: computed_output = held_value;
            10'h02C: computed_output = flow_in_data;
            10'h001: computed_output = g0;
            10'h002: computed_output = g1;
            10'h004: computed_output = g4;
            10'h007: computed_output = g2;
            10'h024: computed_output = g5;
            10'h027: computed_output = g3;
            10'h0BC: computed_output = g9;
            10'h03C: computed_output = g8;
            10'h030: computed_output = {WIDTH{1'b0}};
            10'h0B0: computed_output = {WIDTH{1'b1}};
            default: computed_output = held_value;
        endcase
    end

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            topology    <= 10'h0;
            armed       <= 1'b0;
            pending     <= 1'b0;
            held_value  <= {WIDTH{1'b0}};
            out_buffer  <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            topology    <= cfg_data[9:0];
            armed       <= 1'b1;
            pending     <= 1'b0;
        end else if (!freeze_in) begin
            // load_hold is a real, silent side effect -- it changes what
            // future captures compute against, but is not itself an offer.
            if (load_hold) held_value <= hold_in_data;

            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (valid_in) begin
                out_buffer <= computed_output;
                pending    <= 1'b1;
            end
        end
    end

endmodule
