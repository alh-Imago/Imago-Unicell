// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// router_cell_v4sa.v -- points.md #915: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to router. A genuinely new design
// question this cell raises, not faced by any single-output cell so far: it
// has TWO independent outputs, each potentially feeding a different
// downstream receiver on its own schedule. Resolved here, stated precisely:
// the router only accepts a NEW input once every ENABLED output's own
// previous offer has been acked -- a disabled output never blocks anything,
// since it never offered anything in the first place (matching
// router_cell_v4s.v's own existing rule that a disabled output's valid_out
// is always low). This is still "physics, not control": which outputs exist
// and whether they are enabled is fixed at configuration time, same as
// before -- what's new is each enabled output now has its own real
// handshake, not a shared, undifferentiated one.
//
// cfg_data field map, unchanged: [0] enable_a, [1] enable_b.
`default_nettype none
`timescale 1ns / 1ps

module router_cell_v4sa #(
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

    output wire [WIDTH-1:0]  data_out_a,
    output wire               valid_out_a,
    input  wire                ack_in_a,    // backward, from output A's own receiver

    output wire [WIDTH-1:0]  data_out_b,
    output wire               valid_out_b,
    input  wire                ack_in_b     // backward, from output B's own receiver
);

    reg             enable_a    = 1'b0;
    reg             enable_b    = 1'b0;
    reg             armed       = 1'b0;
    reg             pending_a   = 1'b0;
    reg             pending_b   = 1'b0;
    reg [WIDTH-1:0] out_buffer  = {WIDTH{1'b0}};

    // An output only "blocks" readiness for new input while it is BOTH
    // enabled AND still holding an unacked offer -- a disabled output is
    // never busy, since it never offers anything (matching v4s's own rule).
    wire busy_a = enable_a && pending_a;
    wire busy_b = enable_b && pending_b;

    assign data_out_a  = out_buffer;
    assign data_out_b  = out_buffer;
    assign valid_out_a = pending_a;
    assign valid_out_b = pending_b;
    assign ack_out     = armed && !busy_a && !busy_b && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            enable_a   <= 1'b0;
            enable_b   <= 1'b0;
            armed      <= 1'b0;
            pending_a  <= 1'b0;
            pending_b  <= 1'b0;
            out_buffer <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            enable_a   <= cfg_data[0];
            enable_b   <= cfg_data[1];
            armed      <= 1'b1;
            pending_a  <= 1'b0;
            pending_b  <= 1'b0;
        end else if (!freeze_in) begin
            // Each output clears independently on its own ack -- real,
            // separate handshakes, not a shared one.
            if (pending_a && ack_in_a) pending_a <= 1'b0;
            if (pending_b && ack_in_b) pending_b <= 1'b0;

            // New input only accepted once neither ENABLED output is still
            // busy (using this cycle's pre-edge busy state, same priority
            // discipline every other v4sa cell uses, so a clear and a fresh
            // capture never both happen to the same output in one cycle).
            if (!busy_a && !busy_b && valid_in) begin
                out_buffer <= data_in;
                if (enable_a) pending_a <= 1'b1;
                if (enable_b) pending_b <= 1'b1;
            end
        end
    end

endmodule
