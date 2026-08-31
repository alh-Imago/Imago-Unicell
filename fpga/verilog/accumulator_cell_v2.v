// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v2.v — points.md #564: cloned from
// accumulator_cell_v1.v, zero behavioral change to the default path.
// Same optional external-storage mechanism, applied to this core's
// own real, richer dual (static/pulse) update logic with real care.
//
// Real, precise bit layout for the 107-bit external state word:
//   [3:0]    inc_dir
//   [7:4]    dec_dir
//   [11:8]   downstream_mask
//   [19:12]  step_amount
//   [20]     pulse_mode
//   [36:21]  threshold
//   [68:37]  accumulator (32 bits)
//   [100:69] out_buffer (32 bits)
//   [101]    data_valid
//   [102]    pulse_pending
//   [106:103] pending_ack
`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v2 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32,
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
    output wire         status_negative,

    // ── real, optional external-storage interface (points.md #564) ──
    input  wire [106:0] ext_state_in,
    output wire [106:0] ext_state_out
);

    reg [3:0]  int_inc_dir         = 4'h0;
    reg [3:0]  int_dec_dir         = 4'h0;
    reg [3:0]  int_downstream_mask = 4'h0;
    reg [7:0]  int_step_amount     = 8'h00;
    reg        int_pulse_mode      = 1'b0;
    reg [15:0] int_threshold       = 16'h0000;
    reg signed [WIDTH-1:0] int_accumulator = 0;
    reg signed [WIDTH-1:0] int_out_buffer  = 0;
    reg int_data_valid = 1'b0;
    reg int_pulse_pending = 1'b0;
    reg [3:0] int_pending_ack = 4'h0;

    wire [3:0]  inc_dir         = EXTERNAL_STORAGE ? ext_state_in[3:0]    : int_inc_dir;
    wire [3:0]  dec_dir         = EXTERNAL_STORAGE ? ext_state_in[7:4]    : int_dec_dir;
    wire [3:0]  downstream_mask = EXTERNAL_STORAGE ? ext_state_in[11:8]   : int_downstream_mask;
    wire [7:0]  step_amount     = EXTERNAL_STORAGE ? ext_state_in[19:12]  : int_step_amount;
    wire        pulse_mode      = EXTERNAL_STORAGE ? ext_state_in[20]     : int_pulse_mode;
    wire [15:0] threshold       = EXTERNAL_STORAGE ? ext_state_in[36:21]  : int_threshold;
    wire signed [WIDTH-1:0] accumulator = EXTERNAL_STORAGE ? ext_state_in[68:37]  : int_accumulator;
    wire signed [WIDTH-1:0] out_buffer  = EXTERNAL_STORAGE ? ext_state_in[100:69] : int_out_buffer;
    wire data_valid    = EXTERNAL_STORAGE ? ext_state_in[101] : int_data_valid;
    wire pulse_pending  = EXTERNAL_STORAGE ? ext_state_in[102] : int_pulse_pending;
    wire [3:0] pending_ack = EXTERNAL_STORAGE ? ext_state_in[106:103] : int_pending_ack;

    // ── Real computation logic, IDENTICAL to v1 ──
    wire effective_freeze = freeze_in;

    wire sel_inc_n = arrived_n && inc_dir[0];
    wire sel_inc_s = arrived_s && inc_dir[1];
    wire sel_inc_e = arrived_e && inc_dir[2];
    wire sel_inc_w = arrived_w && inc_dir[3];
    wire capture_inc = (sel_inc_n | sel_inc_s | sel_inc_e | sel_inc_w) && !effective_freeze;

    wire sel_dec_n = arrived_n && dec_dir[0];
    wire sel_dec_s = arrived_s && dec_dir[1];
    wire sel_dec_e = arrived_e && dec_dir[2];
    wire sel_dec_w = arrived_w && dec_dir[3];
    wire capture_dec = (sel_dec_n | sel_dec_s | sel_dec_e | sel_dec_w) && !effective_freeze;

    assign ack_out_n = (sel_inc_n || sel_dec_n) && !effective_freeze;
    assign ack_out_s = (sel_inc_s || sel_dec_s) && !effective_freeze;
    assign ack_out_e = (sel_inc_e || sel_dec_e) && !effective_freeze;
    assign ack_out_w = (sel_inc_w || sel_dec_w) && !effective_freeze;

    wire signed [WIDTH-1:0] step_ext = {{(WIDTH-8){1'b0}}, step_amount};
    wire signed [WIDTH-1:0] delta = (capture_inc && !capture_dec) ?  step_ext :
                                     (capture_dec && !capture_inc) ? -step_ext :
                                                                      {WIDTH{1'b0}};
    wire signed [WIDTH-1:0] next_accumulator = accumulator + delta;

    wire signed [WIDTH-1:0] threshold_ext  = {{(WIDTH-16){1'b0}}, threshold};
    wire signed [WIDTH-1:0] abs_next_acc   = next_accumulator[WIDTH-1] ? -next_accumulator : next_accumulator;
    wire threshold_hit = pulse_mode && (capture_inc || capture_dec) &&
                         (threshold != 16'h0000) && (abs_next_acc >= threshold_ext);

    wire want_to_offer = (pulse_mode ? pulse_pending : data_valid) && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer[31:0];
    assign data_out_s = out_buffer[31:0];
    assign data_out_e = out_buffer[31:0];
    assign data_out_w = out_buffer[31:0];

    assign status_negative = out_buffer[WIDTH-1];
    assign ready_out = !effective_freeze;

    // ── Real next-state computation, matching v1's own real, sequential
    // multi-condition update logic EXACTLY (see v1's own header for the
    // full real reasoning). ──
    wire signed [WIDTH-1:0] next_accumulator_reg =
        (rst) ? {WIDTH{1'b0}} :
        (cfg_valid) ? {WIDTH{1'b0}} :
        (capture_inc || capture_dec) ? ((pulse_mode && threshold_hit) ? {WIDTH{1'b0}} : next_accumulator) :
        accumulator;

    wire signed [WIDTH-1:0] next_out_buffer_reg =
        (rst) ? {WIDTH{1'b0}} :
        (cfg_valid) ? {WIDTH{1'b0}} :
        (pulse_mode) ? (threshold_hit ? next_accumulator : out_buffer) :
                       ((pending_ack == 4'h0) ? next_accumulator : out_buffer);

    wire next_data_valid_reg = (rst) ? 1'b0 : (cfg_valid) ? 1'b1 : data_valid;

    wire next_pulse_pending_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? 1'b0 :
        (pulse_mode) ? (threshold_hit ? 1'b1 :
                        ((pending_ack != 4'h0) && (next_pending_ack == 4'h0)) ? 1'b0 : pulse_pending) :
        pulse_pending;

    wire [3:0] next_inc_dir_reg         = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[3:0]   : inc_dir;
    wire [3:0] next_dec_dir_reg         = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[7:4]   : dec_dir;
    wire [3:0] next_downstream_mask_reg = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[11:8]  : downstream_mask;
    wire [7:0] next_step_amount_reg     = (rst) ? 8'h0 : (cfg_valid) ? cfg_data[19:12] : step_amount;
    wire       next_pulse_mode_reg      = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[20]    : pulse_mode;
    wire [15:0] next_threshold_reg      = (rst) ? 16'h0 : (cfg_valid) ? cfg_data[36:21] : threshold;
    wire [3:0] next_pending_ack_reg     = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {next_pending_ack_reg, next_pulse_pending_reg, next_data_valid_reg,
                             next_out_buffer_reg, next_accumulator_reg, next_threshold_reg,
                             next_pulse_mode_reg, next_step_amount_reg, next_downstream_mask_reg,
                             next_dec_dir_reg, next_inc_dir_reg};

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_inc_dir         <= next_inc_dir_reg;
                int_dec_dir         <= next_dec_dir_reg;
                int_downstream_mask <= next_downstream_mask_reg;
                int_step_amount     <= next_step_amount_reg;
                int_pulse_mode      <= next_pulse_mode_reg;
                int_threshold       <= next_threshold_reg;
                int_accumulator     <= next_accumulator_reg;
                int_out_buffer      <= next_out_buffer_reg;
                int_data_valid      <= next_data_valid_reg;
                int_pulse_pending   <= next_pulse_pending_reg;
                int_pending_ack     <= next_pending_ack_reg;
            end
        end
    endgenerate

endmodule
