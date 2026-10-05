// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v4sa.v -- points.md #915: the Flex-Sub shape (ack+freeze per
// #906, WIDTH per #909/#910) applied to sequencer. Same honest note as
// latch_cell_v4sa.v: the real stored values are fixed 8-bit fields packed
// into cfg_data (a native constraint, not a WIDTH choice), so WIDTH here only
// changes data_out's zero-padding, kept for bus-convention uniformity, not a
// real resource saving.
//
// Same real structural point as sequencer_cell_v4s.v: the original never
// captures incoming data -- advance_in is a genuine forward control pulse
// (the external tick pattern #892's real smoke test already used), not a
// backward ack.
//
// What's new here, and worth stating precisely: advance_in is now gated by
// the SAME pending/ack discipline every other v4sa cell uses, not accepted
// unconditionally every time it fires. A new advance_in while a previous
// offer is still unacked is ignored -- exactly like any other v4sa cell's
// sender being expected to check ack_out before firing again. This is a
// real, deliberate behavioural narrowing from sequencer_cell_v4s.v's own
// "advance_in always moves the index, every single assertion," needed to fit
// the family's now-standard backpressure discipline.
//
// cfg_data field map, unchanged: [7:0]/[15:8]/[23:16]/[31:24] = VALUE_0..3;
// cfg_seq_len_m1[1:0] on its own small port, same reason as v4s.
`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,
    input  wire [1:0]   cfg_seq_len_m1,

    input  wire         advance_in,
    output wire          ack_out,     // backward, to whoever drives advance_in

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in
);

    reg [7:0] value_0 = 8'h00, value_1 = 8'h00, value_2 = 8'h00, value_3 = 8'h00;
    reg [1:0] sequence_len_m1 = 2'd0;
    reg       armed = 1'b0;
    reg       pending = 1'b0;

    reg [1:0] seq_index   = 2'd0;
    reg [7:0] out_buffer  = 8'h00;

    // ── Real, unchanged from v4c/v4s ──────────────────────────────────────
    function [7:0] value_for_index(input [1:0] idx);
        case (idx)
            2'd0: value_for_index = value_0;
            2'd1: value_for_index = value_1;
            2'd2: value_for_index = value_2;
            default: value_for_index = value_3;
        endcase
    endfunction

    wire [1:0] next_seq_index = (seq_index == sequence_len_m1) ? 2'd0 : seq_index + 2'd1;

    assign data_out  = {{(WIDTH-8){1'b0}}, out_buffer};
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            value_0 <= 8'h00; value_1 <= 8'h00; value_2 <= 8'h00; value_3 <= 8'h00;
            sequence_len_m1 <= 2'd0;
            armed           <= 1'b0;
            pending         <= 1'b0;
            seq_index       <= 2'd0;
            out_buffer      <= 8'h00;
        end else if (cfg_valid) begin
            value_0         <= cfg_data[7:0];
            value_1         <= cfg_data[15:8];
            value_2         <= cfg_data[23:16];
            value_3         <= cfg_data[31:24];
            sequence_len_m1 <= cfg_seq_len_m1;
            armed           <= 1'b1;
            pending         <= 1'b0;
            seq_index       <= 2'd0;
            out_buffer      <= cfg_data[7:0];   // value_for_index(0)
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (advance_in && armed) begin   // gated by `armed` like every other v4sa cell (ledger #956: an UNCONFIGURED cell used to offer a value)
                seq_index  <= next_seq_index;
                out_buffer <= value_for_index(next_seq_index);
                pending    <= 1'b1;
            end
        end
    end

endmodule
