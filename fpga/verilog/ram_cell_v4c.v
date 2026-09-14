// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// ram_cell_v4c.v — points.md #720: the "c" (carrier) variant of
// ram_cell_v4.v. Same real reasoning as adder_cell_v4c.v's own header
// -- the VIX carrier's whole design concept is to hold common
// functionality centrally, and ram_cell_v4's own internal 3-addon
// chain (nibble_mask/shift_lane/invert) duplicates exactly what the
// carrier itself now provides once, shared across whichever core is
// active. ram_cell_v4.v itself is UNCHANGED, still the real, proven,
// standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from data_reg, the real held value.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and the PROG_ID_ADDON_CONFIG case -- cfg_
//      data KEEPS its original 80-bit width (simpler, no risk to any
//      wiring elsewhere that assumes it); the bits addon_config used
//      to occupy are now genuinely reserved.
//   3. downstream_mask/upstream_mask/fixed_mode/init_data STAY real
//      registers (same reasoning as adder_cell_v4c.v's own header:
//      this cell's live-programming channel genuinely needs a
//      register it can independently write to). The real config-off-
//      shell fix lives at the carrier's own shell level -- feed this
//      cell's own cfg_data from the carrier's stable core_config, not
//      a transient incoming/about-to-commit value.
//
// cfg_data[79:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask    — one-hot(s), N/S/E/W real + 2 reserved
//   [12]    fixed_mode       — 1=permanent ROM-style, 0=flowing
//   [13]    load_data_valid  — mark data_reg valid immediately on load
//   [45:14] init_data[31:0]  — preset value
//   [79:46] reserved         — 34 bits (addon_config's own old home,
//                              now genuinely free, plus the original
//                              14 bits of headroom)

`default_nettype none
`timescale 1ns / 1ps

module ram_cell_v4c #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    // points.md #617 point 5: real, explicit "active" bit — tie high
    // for standalone use.
    input  wire         active,

    input  wire         cfg_valid,
    input  wire [79:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    // ── points.md #617: the real, targeted programming channel, same
    // real shape as adder_cell_v4.v's own (#618) — faithfully ported
    // from nano's real program_in/PROG_ID protocol. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid
);

    // ── State — real core state, matching v1's own shape (6-bit
    // masks instead of 4-bit is the only real width change here;
    // #720 removed addon_config entirely rather than adding it) ──
    reg [31:0] data_reg        = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg        fixed_mode      = 1'b0;
    reg [3:0]  pending_ack     = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state, same
    // real semantics as adder_cell_v4.v's own (#618) and
    // unicell_stripped_v1.v's own real `armed` register.
    reg        armed           = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ── Upstream capture — real, unchanged shape from v1: single-
    // arrival, no A/B two-stage. Only the low 4 bits of the now-6-bit
    // upstream_mask are ever wired to a real physical port here
    // (bits [5:4] are real, reserved headroom, matching nano's own
    // convention — #604's own 3D prerequisite, not implemented). ──
    wire ram_sel_n = arrived_n && upstream_mask[0];
    wire ram_sel_s = arrived_s && upstream_mask[1];
    wire ram_sel_e = arrived_e && upstream_mask[2];
    wire ram_sel_w = arrived_w && upstream_mask[3];
    wire ram_any_upstream_arrived = ram_sel_n | ram_sel_s | ram_sel_e | ram_sel_w;
    wire [31:0] upstream_val = (ram_sel_n ? data_in_n : 32'h0) |
                               (ram_sel_s ? data_in_s : 32'h0) |
                               (ram_sel_e ? data_in_e : 32'h0) |
                               (ram_sel_w ? data_in_w : 32'h0);

    wire capture_now = ram_any_upstream_arrived && !data_valid && !fixed_mode &&
                       !effective_freeze && effective_armed && !program_in;

    assign ack_out_n = capture_now && ram_sel_n;
    assign ack_out_s = capture_now && ram_sel_s;
    assign ack_out_e = capture_now && ram_sel_e;
    assign ack_out_w = capture_now && ram_sel_w;

    // ── Downstream offering — real, unchanged shape from v1, gated
    // additionally on `effective_armed`. ──
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
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #720: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active.
    // data_out_n/s/e/w are the real held value, directly. ──
    assign data_out_n = data_reg;
    assign data_out_s = data_reg;
    assign data_out_e = data_reg;
    assign data_out_w = data_reg;

    // Real, honest gating: an inactive or disarmed cell never signals
    // ready, same real convention as adder_cell_v4.v's own (#618) and
    // nano's own real `ready_bit && armed` (#615).
    assign ready_out = effective_armed && !data_valid && !fixed_mode && !effective_freeze;
    assign status_data_valid = data_valid;

    // ── points.md #617: real, targeted programming channel — same
    // real priority-select shape as adder_cell_v4.v's own (#618).
    // Real, necessary protocol adaptation: init_data (32 bits) is
    // split across two real half-writes (LOW/HIGH), since it can't
    // fit in one real 20-bit word alongside its own 3-bit ID. ──
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_FIXED_MODE      = 3'd2;
    localparam [2:0] PROG_ID_INIT_DATA_LOW   = 3'd3;
    localparam [2:0] PROG_ID_INIT_DATA_HIGH  = 3'd4;
    localparam [2:0] PROG_ID_LOAD_DATA_VALID = 3'd6;
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

    // Split into a separate real reg so the two half-writes can land
    // independently without disturbing each other — same real
    // "targeted, not a hammer" property every other field already has.
    reg [31:0] init_data = 32'h0;

    always @(posedge clk) begin
        if (rst) begin
            data_reg        <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 6'h0;
            upstream_mask   <= 6'h0;
            fixed_mode      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
            init_data       <= 32'h0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            fixed_mode      <= cfg_data[12];
            data_valid      <= cfg_data[13];
            init_data       <= cfg_data[45:14];
            data_reg        <= cfg_data[45:14];
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_FIXED_MODE:      fixed_mode      <= prog_word[0];
                PROG_ID_INIT_DATA_LOW:   init_data[15:0]  <= prog_word[15:0];
                PROG_ID_INIT_DATA_HIGH:  init_data[31:16] <= prog_word[15:0];
                // points.md #617/#619: a real, necessary correction,
                // caught by simulation, not assumed correct -- a first
                // draft had COMPLETE unconditionally recommit
                // data_reg/data_valid from init_data on EVERY targeted
                // reprogram, even ones that never touched init_data at
                // all, silently corrupting a flowing cell's own
                // current held value. Real fix: committing init_data
                // into data_reg is its own real, explicit, separate
                // action (PROG_ID_LOAD_DATA_VALID), matching
                // cfg_data's own real `load_data_valid` bit -- COMPLETE
                // itself now does ONLY what nano's own real COMPLETE
                // does (#615): commit the arm state, nothing else.
                PROG_ID_LOAD_DATA_VALID: begin
                    if (prog_word[0]) begin
                        data_reg   <= init_data;
                        data_valid <= 1'b1;
                    end
                end
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (capture_now) begin
                data_reg   <= upstream_val;
                data_valid <= 1'b1;
            end else if (!fixed_mode && offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
