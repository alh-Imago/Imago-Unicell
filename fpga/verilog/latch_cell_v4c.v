// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v4c.v — points.md #720: the "c" (carrier) variant of
// latch_cell_v4.v. Same real reasoning as the other _v4c files' own
// headers -- the carrier's whole design concept is to hold common
// functionality centrally, and this core's own internal 3-addon chain
// duplicates exactly what the carrier itself now provides once,
// shared. latch_cell_v4.v itself is UNCHANGED, still the real,
// proven, standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from {31'h0, out_buffer}, the real
//      single-bit latch state, expanded exactly as v4 does before its
//      own addon chain, just without the transform after.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and PROG_ID_ADDON_CONFIG. cfg_data KEEPS
//      its original 64-bit width; PROG_ID_COMPLETE stays at 3'd7,
//      addon_config's own old slot (3'd4) is simply unused now.
//   3. Same real config-off-shell reasoning as every other _v4c file:
//      all real config fields STAY registers; the real fix lives at
//      the carrier's own shell level.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   set_dir           — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  clear_dir         — one-hot(s), N/S/E/W real + 2 reserved
//   [17:12] downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [23:18] toggle_dir        — one-hot(s), N/S/E/W real + 2 reserved
//   [63:24] reserved          — 40 bits (addon_config's own old home,
//                               now genuinely free, plus the original
//                               20 bits of headroom)

`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v4c #(
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

    // ── points.md #720: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active. ──
    wire [31:0] latch_expanded = {31'h0, out_buffer};
    assign data_out_n = latch_expanded;
    assign data_out_s = latch_expanded;
    assign data_out_e = latch_expanded;
    assign data_out_w = latch_expanded;

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
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            set_dir         <= cfg_data[5:0];
            clear_dir       <= cfg_data[11:6];
            downstream_mask <= cfg_data[17:12];
            toggle_dir      <= cfg_data[23:18];
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
