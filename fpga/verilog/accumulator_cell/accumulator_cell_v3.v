// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v3.v — points.md #592: the same real change as
// compare_cell_v3.v (#584) and latch_cell_v3.v (#587), applied to the
// widest real config budget touched by this thread so far -- 37 real
// bits (inc_dir/dec_dir/downstream_mask/step_amount/pulse_mode/
// threshold), versus compare's 40 and latch's 16 (a real, direct
// per-field comparison, not per-total-width, since compare's own 40
// bits happen to include a wide 32-bit threshold field too -- picked
// per Alan's own real request for "a more complex, wider" core next,
// specifically because a bigger real config budget should make any
// real saving from this mechanism easier to see above the real
// build-to-build noise floor `#591` found on the two smaller cores).
//
// Config fields (inc_dir/dec_dir/downstream_mask/step_amount/
// pulse_mode/threshold) no longer re-latched into a private local
// copy on cfg_valid -- read straight off a continuously-valid cfg_data
// input instead (the shell's own core_config, stable for as long as
// this core stays selected). Genuine runtime state (accumulator/
// out_buffer/data_valid/pulse_pending/pending_ack) UNCHANGED from v1
// -- still real per-core registers, same real semantics, including
// v1's own real quirk that data_valid goes live immediately on
// cfg_valid (matching latch_cell_v3's own real precedent, #587).
//
// Same real safety reasoning as compare_cell_v3.v/latch_cell_v3.v's
// own headers: arrived_n/s/e/w are gated by the shell's own sel_
// active_acc at the instantiation site (unchanged), so a misread
// config value from another core's own bit pattern (shared budget,
// reused positions) can never trigger a genuine inc/dec/pulse while
// this core is deselected.
//
// cfg_data[63:0] field map — UNCHANGED from v1:
//   [3:0]   inc_dir           — one-hot direction, arrivals here = +step_amount
//   [7:4]   dec_dir           — one-hot direction, arrivals here = -step_amount
//   [11:8]  downstream_mask   — where the current total/pulse is offered
//   [19:12] step_amount       — unsigned magnitude applied per matching arrival
//   [20]    pulse_mode        — 0=static/continuous, 1=reset-after-fire pulse
//   [36:21] threshold         — pulse_mode only
//   [63:37] reserved
`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v3 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,   // points.md #592: must be CONTINUOUSLY
                                    // valid (wired to the shell's own
                                    // core_config), same real precondition
                                    // as compare_cell_v3.v/latch_cell_v3.v.

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         ready_out,
    output wire         status_negative
);

    // ── points.md #592: THE real change -- config fields read straight
    // off the continuously-valid cfg_data input, no local register, no
    // load-vs-hold mux. ──
    wire [3:0]  inc_dir         = cfg_data[3:0];
    wire [3:0]  dec_dir         = cfg_data[7:4];
    wire [3:0]  downstream_mask = cfg_data[11:8];
    wire [7:0]  step_amount     = cfg_data[19:12];
    wire        pulse_mode      = cfg_data[20];
    wire [15:0] threshold       = cfg_data[36:21];

    // ── UNCHANGED from v1: genuine runtime state ──
    reg signed [WIDTH-1:0] accumulator = 0;
    reg signed [WIDTH-1:0] out_buffer  = 0;
    reg data_valid = 1'b0;
    reg pulse_pending = 1'b0;
    reg [3:0] pending_ack = 4'h0;

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

    // ── points.md #592: the reset/reload block is now ONLY about
    // genuine runtime state -- no config fields left to latch here. ──
    always @(posedge clk) begin
        if (rst) begin
            accumulator     <= 0;
            out_buffer      <= 0;
            data_valid      <= 1'b0;
            pulse_pending   <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            accumulator     <= 0;
            out_buffer      <= 0;
            data_valid      <= 1'b1;   // UNCHANGED from v1 — live from the
                                        // first cycle after config.
            pulse_pending   <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            if (capture_inc || capture_dec) begin
                accumulator <= (pulse_mode && threshold_hit) ? {WIDTH{1'b0}} : next_accumulator;
            end

            if (pulse_mode) begin
                if (threshold_hit) begin
                    out_buffer <= next_accumulator;
                end
                if (threshold_hit) begin
                    pulse_pending <= 1'b1;
                end else if ((pending_ack != 4'h0) && (next_pending_ack == 4'h0)) begin
                    pulse_pending <= 1'b0;
                end
            end else begin
                if (pending_ack == 4'h0) begin
                    out_buffer <= next_accumulator;
                end
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
