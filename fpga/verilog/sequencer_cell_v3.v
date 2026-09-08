// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v3.v — points.md #699: the same real config-off-shell
// change already applied to compare/latch/accumulator/ram/adder, now
// applied to sequencer. Real, careful check made before writing this,
// not assumed: `value_0`-`value_3`/`sequence_len_m1`/`downstream_mask`
// are ALL read repeatedly, every time the sequence advances
// (`value_for_index(next_seq_index)` on every real `offer_just_
// completed` event, not just once at config time) -- unlike RAM's own
// real one-time seed fields, there is no genuine "used once, then pure
// runtime state" field here at all. All six real config fields move
// to the continuous group. The only real runtime state
// (`seq_index`/`out_buffer`/`data_valid`/`pending_ack`) is unchanged
// from v1.
//
// The shell wiring this file needs (matching `unicell_super_v6.v`'s
// own real precedent): `cfg_data` must be wired to the shell's own
// continuously-valid `core_config`, NOT the transient `incoming_
// config` pulse v1 uses.
`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v3 #(
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

    output wire         ready_out,
    output wire [1:0]   status_seq_index
);

    // ── Real config fields, read CONTINUOUSLY off cfg_data (#699) --
    // no local latch at all for any of the six. ────────────────────
    wire [7:0] value_0 = cfg_data[7:0];
    wire [7:0] value_1 = cfg_data[15:8];
    wire [7:0] value_2 = cfg_data[23:16];
    wire [7:0] value_3 = cfg_data[31:24];
    wire [1:0] sequence_len_m1 = cfg_data[33:32];
    wire [3:0] downstream_mask = cfg_data[37:34];

    // ── Real, genuine runtime state -- unchanged from v1. ──────────
    reg [1:0] seq_index  = 2'd0;
    reg [7:0] out_buffer = 8'h00;
    reg data_valid = 1'b0;
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

    assign ack_out_n = 1'b0;
    assign ack_out_s = 1'b0;
    assign ack_out_e = 1'b0;
    assign ack_out_w = 1'b0;

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
    assign ready_out = !effective_freeze;

    always @(posedge clk) begin
        if (rst) begin
            seq_index       <= 2'd0;
            out_buffer      <= 8'h00;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            // value_0-3/sequence_len_m1/downstream_mask are no longer
            // latched here at all (#699).
            seq_index       <= 2'd0;
            out_buffer      <= cfg_data[7:0];   // value_for_index(0), same real value_0 field
            data_valid      <= 1'b1;
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
