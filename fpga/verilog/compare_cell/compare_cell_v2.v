// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v2.v — points.md #564: cloned from compare_cell_v1.v,
// zero behavioral change to the default path. Same optional external-
// storage mechanism proven on latch/ram/adder.
//
// Real, precise bit layout for the 77-bit external state word:
//   [3:0]   downstream_mask
//   [7:4]   upstream_mask
//   [39:8]  threshold (32 bits, signed)
//   [71:40] out_buffer (32 bits)
//   [72]    data_valid
//   [76:73] pending_ack
`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v2 #(
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

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         status_data_valid,

    // ── real, optional external-storage interface (points.md #564) ──
    input  wire [76:0]  ext_state_in,
    output wire [76:0]  ext_state_out
);

    reg [3:0]  int_downstream_mask = 4'h0;
    reg [3:0]  int_upstream_mask   = 4'h0;
    reg signed [31:0] int_threshold = 32'sh0;
    reg [31:0] int_out_buffer  = 32'h0;
    reg        int_data_valid  = 1'b0;
    reg [3:0]  int_pending_ack = 4'h0;

    wire [3:0]  downstream_mask = EXTERNAL_STORAGE ? ext_state_in[3:0]   : int_downstream_mask;
    wire [3:0]  upstream_mask   = EXTERNAL_STORAGE ? ext_state_in[7:4]   : int_upstream_mask;
    wire signed [31:0] threshold = EXTERNAL_STORAGE ? ext_state_in[39:8]  : int_threshold;
    wire [31:0] out_buffer      = EXTERNAL_STORAGE ? ext_state_in[71:40] : int_out_buffer;
    wire        data_valid      = EXTERNAL_STORAGE ? ext_state_in[72]    : int_data_valid;
    wire [3:0]  pending_ack     = EXTERNAL_STORAGE ? ext_state_in[76:73] : int_pending_ack;

    // ── Real computation logic, IDENTICAL to v1 ──
    wire effective_freeze = freeze_in;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire signed [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                                      (sel_s ? data_in_s : 32'h0) |
                                      (sel_e ? data_in_e : 32'h0) |
                                      (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    wire result_bit = (upstream_val >= threshold);

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
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = !effective_freeze && !data_valid;
    assign status_data_valid = data_valid;

    wire [3:0]  next_downstream_mask = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[3:0]  : downstream_mask;
    wire [3:0]  next_upstream_mask   = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[7:4]  : upstream_mask;
    wire signed [31:0] next_threshold = (rst) ? 32'sh0 : (cfg_valid) ? cfg_data[39:8] : threshold;
    wire [31:0] next_out_buffer = (rst) ? 32'h0 : (cfg_valid) ? out_buffer : (capture_now) ? {31'h0, result_bit} : out_buffer;
    wire        next_data_valid = (rst) ? 1'b0 :
                                   (cfg_valid) ? 1'b0 :
                                   (offer_draining) ? 1'b0 :
                                   (capture_now) ? 1'b1 : data_valid;
    wire [3:0]  next_pending_ack_reg = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {next_pending_ack_reg, next_data_valid, next_out_buffer,
                             next_threshold, next_upstream_mask, next_downstream_mask};

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_downstream_mask <= next_downstream_mask;
                int_upstream_mask   <= next_upstream_mask;
                int_threshold       <= next_threshold;
                int_out_buffer      <= next_out_buffer;
                int_data_valid      <= next_data_valid;
                int_pending_ack     <= next_pending_ack_reg;
            end
        end
    endgenerate

endmodule
