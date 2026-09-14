// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v4c.v — points.md #720: the "c" (carrier) variant
// of accumulator_cell_v4.v. Same real reasoning as the other _v4c
// files' own headers -- the carrier's whole design concept is to hold
// common functionality centrally, and this core's own internal
// 3-addon chain duplicates exactly what the carrier itself now
// provides once, shared. accumulator_cell_v4.v itself is UNCHANGED,
// still the real, proven, standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from out_buffer (the real offered
//      snapshot; the internal `accumulator` register itself was NEVER
//      touched by the addon chain even in v4, so this change is
//      purely about what feeds data_out, nothing about the real
//      running-total semantics).
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and PROG_ID_ADDON_CONFIG. cfg_data KEEPS
//      its original 64-bit width; PROG_ID_COMPLETE stays at 3'd7,
//      addon_config's own old slot (3'd6) is simply unused now.
//   3. Same real config-off-shell reasoning as every other _v4c file:
//      all real config fields STAY registers; the real fix lives at
//      the carrier's own shell level.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   inc_dir           — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  dec_dir           — one-hot(s), N/S/E/W real + 2 reserved
//   [17:12] downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [25:18] step_amount       — unsigned magnitude per matching arrival
//   [26]    pulse_mode        — 0=static/continuous, 1=reset-after-fire
//   [42:27] threshold         — pulse_mode only
//   [63:43] reserved          — 21 bits (addon_config's own old home,
//                               now genuinely free, plus the original
//                               1 bit of headroom)

`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v4c #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,

    // points.md #617 point 5: real, explicit "active" bit.
    input  wire         active,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    // ── points.md #617: real, targeted programming channel, same real
    // shape as #618-#620's own. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         ready_out,
    output wire         status_negative
);

    reg [5:0]  inc_dir         = 6'h0;
    reg [5:0]  dec_dir         = 6'h0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [7:0]  step_amount     = 8'h00;
    reg        pulse_mode      = 1'b0;
    reg [15:0] threshold       = 16'h0000;

    reg signed [WIDTH-1:0] accumulator = 0;
    reg signed [WIDTH-1:0] out_buffer  = 0;
    reg data_valid = 1'b0;
    reg pulse_pending = 1'b0;
    reg [3:0] pending_ack = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state, same
    // real semantics as #618-#620's own.
    reg armed = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ── Real, unchanged from v1: independent inc/dec capture, only
    // the low 4 bits of the now-6-bit inc_dir/dec_dir are ever wired
    // to a real physical port here (bits [5:4] real, reserved
    // headroom, matching nano's own convention). Real, necessary
    // extension: also gated on effective_armed/!program_in — an
    // inactive or mid-reprogram cell must not silently keep
    // incrementing its own internal total in the background. ──
    wire sel_inc_n = arrived_n && inc_dir[0];
    wire sel_inc_s = arrived_s && inc_dir[1];
    wire sel_inc_e = arrived_e && inc_dir[2];
    wire sel_inc_w = arrived_w && inc_dir[3];
    wire capture_inc = (sel_inc_n | sel_inc_s | sel_inc_e | sel_inc_w) &&
                       !effective_freeze && effective_armed && !program_in;

    wire sel_dec_n = arrived_n && dec_dir[0];
    wire sel_dec_s = arrived_s && dec_dir[1];
    wire sel_dec_e = arrived_e && dec_dir[2];
    wire sel_dec_w = arrived_w && dec_dir[3];
    wire capture_dec = (sel_dec_n | sel_dec_s | sel_dec_e | sel_dec_w) &&
                       !effective_freeze && effective_armed && !program_in;

    assign ack_out_n = (sel_inc_n || sel_dec_n) && !effective_freeze && effective_armed && !program_in;
    assign ack_out_s = (sel_inc_s || sel_dec_s) && !effective_freeze && effective_armed && !program_in;
    assign ack_out_e = (sel_inc_e || sel_dec_e) && !effective_freeze && effective_armed && !program_in;
    assign ack_out_w = (sel_inc_w || sel_dec_w) && !effective_freeze && effective_armed && !program_in;

    wire signed [WIDTH-1:0] step_ext = {{(WIDTH-8){1'b0}}, step_amount};
    wire signed [WIDTH-1:0] delta = (capture_inc && !capture_dec) ?  step_ext :
                                     (capture_dec && !capture_inc) ? -step_ext :
                                                                      {WIDTH{1'b0}};
    wire signed [WIDTH-1:0] next_accumulator = accumulator + delta;

    wire signed [WIDTH-1:0] threshold_ext  = {{(WIDTH-16){1'b0}}, threshold};
    wire signed [WIDTH-1:0] abs_next_acc   = next_accumulator[WIDTH-1] ? -next_accumulator : next_accumulator;
    wire threshold_hit = pulse_mode && (capture_inc || capture_dec) &&
                         (threshold != 16'h0000) && (abs_next_acc >= threshold_ext);

    wire want_to_offer = (pulse_mode ? pulse_pending : data_valid) && !effective_freeze && effective_armed;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #720: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active.
    // data_out_n/s/e/w are the real offered snapshot, directly (the
    // internal accumulator itself is still never touched here, same
    // as v4). ──
    assign data_out_n = out_buffer[31:0];
    assign data_out_s = out_buffer[31:0];
    assign data_out_e = out_buffer[31:0];
    assign data_out_w = out_buffer[31:0];

    assign status_negative = out_buffer[WIDTH-1];
    // Real, honest gating: an inactive/disarmed cell is never ready --
    // same real convention as #618-#620's own.
    assign ready_out = effective_armed && !effective_freeze;

    // ── points.md #617: real, targeted programming channel — same
    // real priority-select shape as #618-#620's own. Real, notable:
    // threshold (16 bits) fits in ONE real targeted write here, no
    // split needed (a third, different real answer to the same
    // question #619/#620 each answered differently). ──
    localparam [2:0] PROG_ID_INC_DIR         = 3'd0;
    localparam [2:0] PROG_ID_DEC_DIR         = 3'd1;
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd2;
    localparam [2:0] PROG_ID_STEP_AMOUNT     = 3'd3;
    localparam [2:0] PROG_ID_PULSE_MODE      = 3'd4;
    localparam [2:0] PROG_ID_THRESHOLD       = 3'd5;
    localparam [2:0] PROG_ID_COMPLETE        = 3'd7;

    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n :
                                prog_sel_s ? prog_data_in_s :
                                prog_sel_e ? prog_data_in_e :
                                             prog_data_in_w;
    wire [2:0]  prog_id   = prog_data_val[22:20];
    wire [19:0] prog_word = prog_data_val[19:0];

    wire programming_active = program_in && active && prog_any_arrived;
    assign program_done = program_done_r;
    reg   program_done_r = 1'b0;

    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    always @(posedge clk) begin
        if (rst) begin
            accumulator     <= 0;
            out_buffer      <= 0;
            data_valid      <= 1'b0;
            pulse_pending   <= 1'b0;
            pending_ack     <= 4'h0;
            inc_dir         <= 6'h0;
            dec_dir         <= 6'h0;
            downstream_mask <= 6'h0;
            step_amount     <= 8'h00;
            pulse_mode      <= 1'b0;
            threshold       <= 16'h0000;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            inc_dir         <= cfg_data[5:0];
            dec_dir         <= cfg_data[11:6];
            downstream_mask <= cfg_data[17:12];
            step_amount     <= cfg_data[25:18];
            pulse_mode      <= cfg_data[26];
            threshold       <= cfg_data[42:27];
            accumulator     <= 0;
            out_buffer      <= 0;
            data_valid      <= 1'b1;
            pulse_pending   <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_INC_DIR:         inc_dir         <= prog_word[5:0];
                PROG_ID_DEC_DIR:         dec_dir         <= prog_word[5:0];
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_STEP_AMOUNT:     step_amount     <= prog_word[7:0];
                PROG_ID_PULSE_MODE:      pulse_mode      <= prog_word[0];
                PROG_ID_THRESHOLD:       threshold       <= prog_word[15:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (capture_inc || capture_dec) begin
                accumulator <= (pulse_mode && threshold_hit) ? {WIDTH{1'b0}} : next_accumulator;
            end

            if (pulse_mode) begin
                if (threshold_hit) begin
                    out_buffer    <= next_accumulator;
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

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
