// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v2.v — points.md #564: cloned from
// sequencer_cell_v1.v, zero behavioral change to the default path.
// Same optional external-storage mechanism, applied to this core's
// own real "advance on ack, offer the value at the NEW index" shape.
//
// Real, precise bit layout for the 53-bit external state word:
//   [7:0]   value_0
//   [15:8]  value_1
//   [23:16] value_2
//   [31:24] value_3
//   [33:32] sequence_len_m1
//   [37:34] downstream_mask
//   [39:38] seq_index
//   [47:40] out_buffer
//   [48]    data_valid
//   [52:49] pending_ack
`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v2 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        EXTERNAL_STORAGE = 0
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
    output wire [1:0]   status_seq_index,

    // ── real, optional external-storage interface (points.md #564) ──
    input  wire [52:0]  ext_state_in,
    output wire [52:0]  ext_state_out
);

    reg [7:0] int_value_0 = 8'h00, int_value_1 = 8'h00, int_value_2 = 8'h00, int_value_3 = 8'h00;
    reg [1:0] int_sequence_len_m1 = 2'd0;
    reg [3:0] int_downstream_mask = 4'h0;
    reg [1:0] int_seq_index  = 2'd0;
    reg [7:0] int_out_buffer = 8'h00;
    reg int_data_valid = 1'b0;
    reg [3:0] int_pending_ack = 4'h0;

    wire [7:0] value_0 = EXTERNAL_STORAGE ? ext_state_in[7:0]   : int_value_0;
    wire [7:0] value_1 = EXTERNAL_STORAGE ? ext_state_in[15:8]  : int_value_1;
    wire [7:0] value_2 = EXTERNAL_STORAGE ? ext_state_in[23:16] : int_value_2;
    wire [7:0] value_3 = EXTERNAL_STORAGE ? ext_state_in[31:24] : int_value_3;
    wire [1:0] sequence_len_m1 = EXTERNAL_STORAGE ? ext_state_in[33:32] : int_sequence_len_m1;
    wire [3:0] downstream_mask = EXTERNAL_STORAGE ? ext_state_in[37:34] : int_downstream_mask;
    wire [1:0] seq_index  = EXTERNAL_STORAGE ? ext_state_in[39:38] : int_seq_index;
    wire [7:0] out_buffer = EXTERNAL_STORAGE ? ext_state_in[47:40] : int_out_buffer;
    wire data_valid   = EXTERNAL_STORAGE ? ext_state_in[48] : int_data_valid;
    wire [3:0] pending_ack = EXTERNAL_STORAGE ? ext_state_in[52:49] : int_pending_ack;

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

    wire [7:0] next_value_0_reg = (rst) ? 8'h0 : (cfg_valid) ? cfg_data[7:0]   : value_0;
    wire [7:0] next_value_1_reg = (rst) ? 8'h0 : (cfg_valid) ? cfg_data[15:8]  : value_1;
    wire [7:0] next_value_2_reg = (rst) ? 8'h0 : (cfg_valid) ? cfg_data[23:16] : value_2;
    wire [7:0] next_value_3_reg = (rst) ? 8'h0 : (cfg_valid) ? cfg_data[31:24] : value_3;
    wire [1:0] next_sequence_len_m1_reg = (rst) ? 2'd0 : (cfg_valid) ? cfg_data[33:32] : sequence_len_m1;
    wire [3:0] next_downstream_mask_reg = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[37:34] : downstream_mask;
    wire [1:0] next_seq_index_reg = (rst) ? 2'd0 :
                                     (cfg_valid) ? 2'd0 :
                                     (offer_just_completed) ? next_seq_index : seq_index;
    wire [7:0] next_out_buffer_reg = (rst) ? 8'h0 :
                                      (cfg_valid) ? cfg_data[7:0] :
                                      (offer_just_completed) ? value_for_index(next_seq_index) : out_buffer;
    wire next_data_valid_reg = (rst) ? 1'b0 : (cfg_valid) ? 1'b1 : data_valid;
    wire [3:0] next_pending_ack_reg = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {next_pending_ack_reg, next_data_valid_reg, next_out_buffer_reg,
                             next_seq_index_reg, next_downstream_mask_reg, next_sequence_len_m1_reg,
                             next_value_3_reg, next_value_2_reg, next_value_1_reg, next_value_0_reg};

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_value_0         <= next_value_0_reg;
                int_value_1         <= next_value_1_reg;
                int_value_2         <= next_value_2_reg;
                int_value_3         <= next_value_3_reg;
                int_sequence_len_m1 <= next_sequence_len_m1_reg;
                int_downstream_mask <= next_downstream_mask_reg;
                int_seq_index       <= next_seq_index_reg;
                int_out_buffer      <= next_out_buffer_reg;
                int_data_valid      <= next_data_valid_reg;
                int_pending_ack     <= next_pending_ack_reg;
            end
        end
    endgenerate

endmodule
