// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v4.v — points.md #617/#621: the FOURTH real
// "unified carrier" core, following `adder_cell_v4.v` (#618, two-stage
// A/B), `ram_cell_v4.v` (#619, single-arrival, no computation), and
// `compare_cell_v4.v` (#620, single-arrival WITH computation). This
// core is structurally the most different of all four: a real,
// CONTINUOUSLY-LIVE running total (never one-shot capture-then-empty),
// with TWO INDEPENDENT capture triggers (inc_dir/dec_dir, not a
// matched pair) — confirming the shell template keeps generalizing
// even against a genuinely different real state model.
//
// Real core logic CLONED from accumulator_cell_v1.v unchanged (the
// unconditional, never-blocked internal accumulator; step_amount;
// pulse_mode's own real reset-after-fire threshold semantics). Same
// real shell additions as `#618`-`#620`, per Alan's own precise
// 5-point breakdown (`#617`):
//   1. programming: real, targeted program_in/PROG_ID channel.
//   2. shift/nibble_mask/lane: the same real, already-proven 3-addon
//      chain, wired identically, applied to the OFFERED snapshot
//      (`out_buffer`), never the internal running total itself.
//   3. 6-way cardinality: real field-width headroom only.
//   4. ack all around: the programming channel's own real ack.
//   5. `active`: the same real, explicit port -- REAL, NECESSARY
//      EXTENSION of the "inactive = zero real effect" principle
//      #618-#620 already established: gates `capture_inc`/
//      `capture_dec` too, so an inactive cell's own INTERNAL running
//      total genuinely holds rather than silently drifting in the
//      background -- not just its offered output.
//
// REAL, NOTABLE DATA POINT: this core's own real field total
// (6+6+6+8+1+16+20 = 63 bits, 1 bit real spare) fits in the ORIGINAL
// 64-bit cfg_data, same as `compare_cell_v4.v` (#620) -- no widening
// needed. `threshold` here is 16 bits (not comparator's 32), so it
// fits in ONE real targeted PROG_ID write directly -- no split
// LOW/HIGH write needed, unlike both `ram`'s `init_data` and
// `compare`'s `threshold` (#619/#620). A third real, different answer
// to the same real question, not a coincidence -- confirms the
// carrier's own real protocol genuinely adapts to what each core's
// own real fields actually need.
//
// REAL, HONEST SCOPE, matching `#618`-`#620`'s own stated deferrals:
// `is_command_cell` mode NOT included (parked as a possible 9th-core
// question).
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   inc_dir           — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  dec_dir           — one-hot(s), N/S/E/W real + 2 reserved
//   [17:12] downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [25:18] step_amount       — unsigned magnitude per matching arrival
//   [26]    pulse_mode        — 0=static/continuous, 1=reset-after-fire
//   [42:27] threshold         — pulse_mode only
//   [62:43] addon_config      — 20 bits, SAME real layout as
//                               unicell_super_v3.v's own real addon_config
//   [63]    reserved
`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v4 #(
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
    reg [19:0] addon_config    = 20'h0;

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

    // ── points.md #617: the real, three-addon chain, applied to the
    // OFFERED snapshot only -- the internal accumulator itself is
    // never touched, matching this core's own real "the internal
    // total is always correct, unconditionally" invariant exactly. ──
    wire [31:0] after_mask, after_shiftlane, addon_out;
    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(out_buffer[31:0]), .data_out(after_mask)
    );
    shift_lane_addon_v1 ADDON_SL (
        .direction(addon_config[15]), .shift_en(addon_config[14]),
        .shift_amt(addon_config[13:9]), .lane_cut(addon_config[18:16]),
        .data_in(after_mask), .data_out(after_shiftlane)
    );
    invert_addon_v1 ADDON_INV (
        .invert_en(addon_config[19]),
        .data_in(after_shiftlane), .data_out(addon_out)
    );

    assign data_out_n = addon_out;
    assign data_out_s = addon_out;
    assign data_out_e = addon_out;
    assign data_out_w = addon_out;

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
    localparam [2:0] PROG_ID_ADDON_CONFIG    = 3'd6;
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
            addon_config    <= 20'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            inc_dir         <= cfg_data[5:0];
            dec_dir         <= cfg_data[11:6];
            downstream_mask <= cfg_data[17:12];
            step_amount     <= cfg_data[25:18];
            pulse_mode      <= cfg_data[26];
            threshold       <= cfg_data[42:27];
            addon_config    <= cfg_data[62:43];
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
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
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
