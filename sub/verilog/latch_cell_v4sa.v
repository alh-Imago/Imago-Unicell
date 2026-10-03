// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v4sa.v -- points.md #915: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to latch. Unlike adder/accumulator/
// compare, latch's real payload is always exactly 1 bit -- WIDTH here only
// changes how many zero-padding bits surround that bit in data_out, kept for
// uniformity with the rest of the family's bus convention, not for any real
// resource saving (flagged honestly, not oversold).
//
// Same real wrinkle as latch_cell_v4s.v: SET/CLEAR/TOGGLE as three dedicated
// one-bit event pulses (not cardinal-direction masks); priority CLEAR > SET >
// TOGGLE unchanged. See latch_cell_v4s.v's own header for the real SET-only-
// fires-on-a-1 equivalence reasoning -- unchanged here.
//
// ack/freeze: identical shape to adder_cell_v4sa.v/accumulator_cell_v4sa.v/
// compare_cell_v4sa.v -- standard ready/valid, freeze_in global and gating
// the whole update including cfg_valid's own effect.
//
// Lessons from #906/#911/#912 applied from the start: the testbench settles
// (a real delay) BEFORE clearing any event pulse the DUT also samples on the
// same edge.
`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,   // unused by this cell's function; kept for a
                                     // uniform port shape across the family

    input  wire         set_in,
    input  wire         clear_in,
    input  wire         toggle_in,
    output wire          ack_out,     // backward, to whoever drives set/clear/toggle

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in
);

    reg armed       = 1'b0;
    reg latched     = 1'b0;
    reg pending     = 1'b0;
    reg out_buffer  = 1'b0;

    // ── The real priority logic -- unchanged: CLEAR > SET > TOGGLE ───────
    wire next_latched = clear_in ? 1'b0 : set_in ? 1'b1 : toggle_in ? ~latched : latched;
    wire any_event = set_in || clear_in || toggle_in;

    assign data_out  = {{(WIDTH-1){1'b0}}, out_buffer};
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            latched     <= 1'b0;
            pending     <= 1'b0;
            out_buffer  <= 1'b0;
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            latched     <= 1'b0;
            pending     <= 1'b0;
            out_buffer  <= 1'b0;
        end else if (!freeze_in) begin
            // The latch's own stored state updates on every real event
            // regardless of pending/ack, same reasoning as accumulator's
            // running total -- only the OFFER is ack-gated.
            if (any_event) latched <= next_latched;

            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (any_event) begin
                out_buffer <= next_latched;
                pending    <= 1'b1;
            end
        end
    end

endmodule
