// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v1.v — a genuine new CORE (points.md #418's own
// promotion assessment: the sequencer's underlying idea, cycling
// through a short, fixed, host-configured list of values, is real,
// distinct territory none of the 6 existing cores cover). Unlike
// `cell_command_sequencer_v1.v` (which drives OTHER cells' own
// programming channel with cardinal_edge values -- a genuinely
// different, specialized mechanism, deliberately NOT reused here),
// this core offers its own sequence of values through the ORDINARY
// cardinal `data_out_X`/`fire_X` ports, exactly like any other core --
// the real, distinguishing feature of a promoted core per `#418`'s own
// assessment.
//
// THE MECHANISM, mirrored directly from `accumulator_cell_v1.v`'s own
// real "continuously live" shape (the closest existing precedent):
// this cell holds a small, config-time-fixed list of up to 4 values
// and offers them in order, one at a time, advancing to the next value
// only once the CURRENT offer is genuinely acked (matching every other
// core's own "offered data stays stable until acked" protocol) --
// wrapping back to the first value after `SEQUENCE_LEN` values have
// been offered. Unlike the accumulator, capture (`arrived_X`) plays NO
// role at all here -- this core's own output is driven purely by its
// own prior ack completion, not by anything arriving. `ack_out_X` is
// tied low on every direction for that same reason -- there is nothing
// to acknowledge.
//
// A REAL, DELIBERATE BUDGET CHOICE, worth stating precisely: 4 values
// at 8 bits each (32 bits) + 2-bit SEQUENCE_LEN + 4-bit
// downstream_mask = 38 bits, fitting comfortably inside the 42-bit
// `core_config` union with 4 bits spare -- not 32-bit values (4x32=128
// bits would blow the budget by nearly 3x). A short list of SMALL
// values, matching the real use case this idea originated from
// (cycling small control/tag values), not a general data-streaming
// mechanism.
//
// cfg_data field map:
//   [7:0]   VALUE_0
//   [15:8]  VALUE_1
//   [23:16] VALUE_2
//   [31:24] VALUE_3
//   [33:32] SEQUENCE_LEN     — how many of the 4 values are real (1-4,
//                              stored as 0-3 meaning length-1)
//   [37:34] downstream_mask  — where the sequence is offered
//   [63:38] reserved
`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         ready_out,       // matching accumulator's own real fix (#295) --
                                          // this core never blocks on capture either (it
                                          // captures nothing at all), so it is always
                                          // genuinely ready when not frozen.
    output wire [1:0]   status_seq_index // free debug tap -- which value is currently offered
);

    reg [7:0] value_0 = 8'h00, value_1 = 8'h00, value_2 = 8'h00, value_3 = 8'h00;
    reg [1:0] sequence_len_m1 = 2'd0;   // stored as length-1 (0 means length 1)
    reg [3:0] downstream_mask = 4'h0;

    reg [1:0] seq_index  = 2'd0;
    reg [7:0] out_buffer = 8'h00;   // the OFFERED snapshot -- stable while a transfer is in flight
    reg data_valid = 1'b0;          // continuously live from config onward, same as accumulator
    reg [3:0] pending_ack = 4'h0;

    wire effective_freeze = freeze_in;

    function [7:0] value_for_index(input [1:0] idx);
        case (idx)
            2'd0: value_for_index = value_0;
            2'd1: value_for_index = value_1;
            2'd2: value_for_index = value_2;
            default: value_for_index = value_3;
        endcase
    endfunction

    // No capture at all -- nothing arrives that this core reacts to.
    assign ack_out_n = 1'b0;
    assign ack_out_s = 1'b0;
    assign ack_out_e = 1'b0;
    assign ack_out_w = 1'b0;

    // ── Downstream offering -- same shell shape as every other core. ──
    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;

    // The real advance condition: the CURRENT offer was pending and has
    // now fully drained (every required ack has landed) -- matching
    // "advance only once genuinely acked," not "advance the instant a
    // new offer is attempted."
    wire offer_just_completed = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);
    wire [1:0] next_seq_index = (seq_index == sequence_len_m1) ? 2'd0 : seq_index + 2'd1;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = {24'h0, out_buffer};
    assign data_out_s = {24'h0, out_buffer};
    assign data_out_e = {24'h0, out_buffer};
    assign data_out_w = {24'h0, out_buffer};

    assign status_seq_index = seq_index;
    assign ready_out = !effective_freeze;   // always genuinely ready -- there is no capture to block

    always @(posedge clk) begin
        if (rst) begin
            value_0         <= 8'h00; value_1 <= 8'h00; value_2 <= 8'h00; value_3 <= 8'h00;
            sequence_len_m1 <= 2'd0;
            downstream_mask <= 4'h0;
            seq_index       <= 2'd0;
            out_buffer      <= 8'h00;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            value_0         <= cfg_data[7:0];
            value_1         <= cfg_data[15:8];
            value_2         <= cfg_data[23:16];
            value_3         <= cfg_data[31:24];
            sequence_len_m1 <= cfg_data[33:32];
            downstream_mask <= cfg_data[37:34];
            seq_index       <= 2'd0;
            out_buffer      <= cfg_data[7:0];   // value_for_index(0) -- same value_0 field, direct
            data_valid      <= 1'b1;            // live from the first cycle after config
            pending_ack     <= 4'h0;
        end else begin
            if (offer_just_completed) begin
                seq_index  <= next_seq_index;
                out_buffer <= value_for_index(next_seq_index);
            end
            pending_ack <= next_pending_ack;
        end
    end

endmodule
