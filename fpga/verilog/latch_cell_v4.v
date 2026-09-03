// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v4.v — points.md #617/#623: the FIFTH real "unified
// carrier" core, following `adder`/`ram`/`compare`/`accumulator`
// (#618-#621). Shares `accumulator_cell_v4.v`'s own real
// continuously-live shape (state updates unconditionally, offered
// snapshot refreshes only when free) -- but SET/CLEAR/TOGGLE
// semantics on a single bit, not arithmetic increment/decrement on a
// running total. A genuinely different real STATE MODEL tested
// against the same shell template, not just a different set of
// triggers.
//
// Real core logic CLONED from latch_cell_v1.v unchanged, INCLUDING its
// own real, documented history, faithfully preserved, not silently
// dropped:
//   - the real `#295` bug fix: only an arrival that actually CARRIES a
//     1 on set_dir triggers a set (an earlier draft treated ANY
//     arrival as a trigger, misinterpreting a genuinely correct "0"
//     reading as a set).
//   - the real `#522` TOGGLE extension: a third real trigger, flipping
//     the current state rather than forcing one, with real priority
//     CLEAR > SET > TOGGLE when multiple land the same cycle
//     (extending #279/#284's own "explicit host action wins" rule).
//
// Same real shell additions as #618-#621, per Alan's own precise
// 5-point breakdown (#617):
//   1. programming: real, targeted program_in/PROG_ID channel.
//   2. shift/nibble_mask/lane: the same real, already-proven 3-addon
//      chain, applied to the offered {31'h0,out_buffer} expansion --
//      genuinely useful even for a single real bit (invert flips all
//      32 offered bits; shift can relocate which bit position carries
//      the real latch value).
//   3. 6-way cardinality: real field-width headroom only.
//   4. ack all around: the programming channel's own real ack.
//   5. `active`: the same real, explicit port -- REAL, NECESSARY
//      EXTENSION matching `#621`'s own real precedent for
//      accumulator: gates `capture_set`/`capture_clr`/`capture_tog`
//      too, so an inactive cell's own internal latch state genuinely
//      holds rather than silently flipping in the background.
//
// REAL, NOTABLE DATA POINT: this core's own real field total
// (6×4 + 20 = 44 bits) fits comfortably in the original 64-bit
// cfg_data with real, honest room to spare -- no widening needed, a
// fourth real, different answer on this same question (#619 needed
// 80 bits, #620/#621 fit exactly in 64, this one fits with margin).
//
// REAL, HONEST SCOPE, matching #618-#621's own stated deferrals:
// `is_command_cell` mode NOT included (parked as a possible 9th-core
// question).
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   set_dir           — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  clear_dir         — one-hot(s), N/S/E/W real + 2 reserved
//   [17:12] downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [23:18] toggle_dir        — one-hot(s), N/S/E/W real + 2 reserved
//   [43:24] addon_config      — 20 bits, SAME real layout as
//                               unicell_super_v3.v's own real addon_config
//   [63:44] reserved          — 20 bits, real, honest headroom
`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
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
    // shape as #618-#621's own. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         ready_out,
    output wire         status_latched
);

    reg [5:0] set_dir         = 6'h0;
    reg [5:0] clear_dir       = 6'h0;
    reg [5:0] downstream_mask = 6'h0;
    reg [5:0] toggle_dir      = 6'h0;
    reg [19:0] addon_config   = 20'h0;

    reg latched    = 1'b0;   // ALWAYS correct, unconditional update, never blocked
    reg out_buffer = 1'b0;   // the OFFERED snapshot — stable while a transfer is in flight
    reg data_valid = 1'b0;
    reg [3:0] pending_ack = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state, same
    // real semantics as #618-#621's own.
    reg armed = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ── Real, unchanged from v1: set/clear/toggle capture, only the
    // low 4 bits of each now-6-bit direction field are ever wired to a
    // real physical port here (bits [5:4] real, reserved headroom,
    // matching nano's own convention). Real, necessary extension:
    // also gated on effective_armed/!program_in — an inactive or
    // mid-reprogram cell must not silently keep flipping its own
    // internal state in the background (#621's own real precedent). ──
    wire sel_set_n = arrived_n && set_dir[0];
    wire sel_set_s = arrived_s && set_dir[1];
    wire sel_set_e = arrived_e && set_dir[2];
    wire sel_set_w = arrived_w && set_dir[3];
    // Real #295 bug fix, faithfully preserved: only an arrival that
    // actually CARRIES a 1 triggers a set — not just any arrival.
    wire set_arrived_value = (sel_set_n ? data_in_n[0] : 1'b0) |
                             (sel_set_s ? data_in_s[0] : 1'b0) |
                             (sel_set_e ? data_in_e[0] : 1'b0) |
                             (sel_set_w ? data_in_w[0] : 1'b0);
    wire capture_set = (sel_set_n | sel_set_s | sel_set_e | sel_set_w) && set_arrived_value &&
                       !effective_freeze && effective_armed && !program_in;

    wire sel_clr_n = arrived_n && clear_dir[0];
    wire sel_clr_s = arrived_s && clear_dir[1];
    wire sel_clr_e = arrived_e && clear_dir[2];
    wire sel_clr_w = arrived_w && clear_dir[3];
    wire capture_clr = (sel_clr_n | sel_clr_s | sel_clr_e | sel_clr_w) &&
                       !effective_freeze && effective_armed && !program_in;

    // Real #522 TOGGLE extension, faithfully preserved: any real
    // arrival on toggle_dir flips the state, value not checked.
    wire sel_tog_n = arrived_n && toggle_dir[0];
    wire sel_tog_s = arrived_s && toggle_dir[1];
    wire sel_tog_e = arrived_e && toggle_dir[2];
    wire sel_tog_w = arrived_w && toggle_dir[3];
    wire capture_tog = (sel_tog_n | sel_tog_s | sel_tog_e | sel_tog_w) &&
                       !effective_freeze && effective_armed && !program_in;

    assign ack_out_n = (sel_set_n || sel_clr_n || sel_tog_n) && !effective_freeze && effective_armed && !program_in;
    assign ack_out_s = (sel_set_s || sel_clr_s || sel_tog_s) && !effective_freeze && effective_armed && !program_in;
    assign ack_out_e = (sel_set_e || sel_clr_e || sel_tog_e) && !effective_freeze && effective_armed && !program_in;
    assign ack_out_w = (sel_set_w || sel_clr_w || sel_tog_w) && !effective_freeze && effective_armed && !program_in;

    // Real, unchanged priority from v1: CLEAR > SET > TOGGLE.
    wire next_latched = capture_clr ? 1'b0 : capture_set ? 1'b1 : capture_tog ? ~latched : latched;

    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
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
    // offered {31'h0,out_buffer} expansion -- genuinely useful even
    // for a single real bit (invert flips all 32 offered bits; shift
    // can relocate which bit position carries the real latch value). ──
    wire [31:0] latch_expanded = {31'h0, out_buffer};
    wire [31:0] after_mask, after_shiftlane, addon_out;
    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(latch_expanded), .data_out(after_mask)
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

    assign status_latched = latched;
    // Real, honest gating: an inactive/disarmed cell is never ready --
    // same real convention as #618-#621's own.
    assign ready_out = effective_armed && !effective_freeze;

    // ── points.md #617: real, targeted programming channel — same
    // real priority-select shape as #618-#621's own. Every real field
    // here fits in a single targeted write (no split needed, matching
    // #621's own step_amount case, not #619/#620's wider fields). ──
    localparam [2:0] PROG_ID_SET_DIR         = 3'd0;
    localparam [2:0] PROG_ID_CLEAR_DIR       = 3'd1;
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd2;
    localparam [2:0] PROG_ID_TOGGLE_DIR      = 3'd3;
    localparam [2:0] PROG_ID_ADDON_CONFIG    = 3'd4;
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
            latched         <= 1'b0;
            out_buffer      <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            set_dir         <= 6'h0;
            clear_dir       <= 6'h0;
            downstream_mask <= 6'h0;
            toggle_dir      <= 6'h0;
            addon_config    <= 20'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            set_dir         <= cfg_data[5:0];
            clear_dir       <= cfg_data[11:6];
            downstream_mask <= cfg_data[17:12];
            toggle_dir      <= cfg_data[23:18];
            addon_config    <= cfg_data[43:24];
            latched         <= 1'b0;
            out_buffer      <= 1'b0;
            data_valid      <= 1'b1;   // live from the first cycle after config
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_SET_DIR:         set_dir         <= prog_word[5:0];
                PROG_ID_CLEAR_DIR:       clear_dir       <= prog_word[5:0];
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_TOGGLE_DIR:      toggle_dir      <= prog_word[5:0];
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (capture_set || capture_clr || capture_tog) begin
                latched <= next_latched;
            end

            if (pending_ack == 4'h0) begin
                out_buffer <= next_latched;
            end

            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
