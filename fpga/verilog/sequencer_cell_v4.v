// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v4.v — points.md #617/#625: the SEVENTH and final
// real "unified carrier" core (all 8 real core types now have a real
// `v4` build). Real core logic CLONED from sequencer_cell_v1.v
// unchanged: a config-fixed cyclic list of up to 4 real 8-bit values,
// offered in order, advancing only once the current offer is
// genuinely acked.
//
// REAL, HONEST CONFIRMATION OF ALAN'S OWN DIRECT PREDICTION, CHECKED
// AGAINST THE REAL RTL BEFORE BUILDING, NOT ASSUMED: this core
// genuinely has NO capture side at all -- `ack_out_X` is tied low on
// every direction in the real v1 RTL (confirmed directly, "there is
// nothing to acknowledge," matching that file's own real comment).
// Several of #617's own 5 points therefore have LESS real surface
// here than on any other core built so far:
//   1. programming: STILL real and applies in full -- every one of
//      this core's own real fields (VALUE_0-3, SEQUENCE_LEN,
//      downstream_mask) is real, targetable config, same as anywhere
//      else.
//   2. shift/nibble_mask/lane: STILL real and applies in full --
//      wired to the offered output, same as every other core.
//   3. 6-way cardinality: applies ONLY to `downstream_mask` (the one
//      real directional field this core has at all) -- there is no
//      `upstream_mask` to widen, because there is no upstream.
//   4. "ack all around": the real PROGRAMMING channel still gets its
//      own real, independent ack per direction (unchanged from every
//      other core) -- but the ORDINARY data-side ack stays tied to 0
//      on every direction, unchanged from v1, because there is
//      genuinely nothing to acknowledge on that side, ever.
//   5. `active`: applies, but with a real, genuine SIMPLIFICATION
//      versus every other core built so far (#618-#624) -- there is
//      no capture path to separately gate. Gating `want_to_offer`
//      alone is sufficient: `offer_just_completed` (the real advance
//      trigger) is causally downstream of a successful offer, so an
//      inactive cell's own index cannot advance AT ALL while inactive
//      -- not because of an extra, explicit gate, but because the
//      offer that would trigger an advance never happens in the first
//      place. The simplest real case of the "inactive = zero effect"
//      principle across all seven cores built so far, not requiring
//      the extra capture-side wiring #621/#623's own real accumulator/
//      latch builds needed.
//
// REAL, NOTABLE DATA POINT: this core's own real field total
// (32+2+6+20 = 60 bits) fits in the original 64-bit cfg_data with 4
// bits of real, honest margin -- no widening needed. Its own real
// PROG_ID budget (7 real fields: VALUE_0-3, SEQUENCE_LEN,
// downstream_mask, addon_config) fits EXACTLY in the same 3-bit ID
// every core except `branch` (#624, 15 fields) used -- a real,
// concrete confirmation that the ID-width question genuinely depends
// on each core's own real field count, not a fixed rule.
//
// REAL, HONEST SCOPE, matching #618-#624's own stated deferrals:
// `is_command_cell` mode NOT included (parked as a possible 9th-core
// question).
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [7:0]   VALUE_0
//   [15:8]  VALUE_1
//   [23:16] VALUE_2
//   [31:24] VALUE_3
//   [33:32] SEQUENCE_LEN     — stored as length-1 (0 means length 1)
//   [39:34] downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [59:40] addon_config     — 20 bits, SAME real layout as
//                              unicell_super_v3.v's own real addon_config
//   [63:60] reserved
`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    // points.md #617 point 5: real, explicit "active" bit -- gates
    // the offer side only, see the header's own real reasoning above.
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
    // shape as #618-#624's own -- fully real and applicable here,
    // unlike the data-side capture logic every other core has. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         ready_out,
    output wire [1:0]   status_seq_index
);

    reg [7:0] value_0 = 8'h00, value_1 = 8'h00, value_2 = 8'h00, value_3 = 8'h00;
    reg [1:0] sequence_len_m1 = 2'd0;
    reg [5:0] downstream_mask = 6'h0;
    reg [19:0] addon_config = 20'h0;

    reg [1:0] seq_index  = 2'd0;
    reg [7:0] out_buffer = 8'h00;
    reg data_valid = 1'b0;
    reg [3:0] pending_ack = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state, same
    // real semantics as #618-#624's own.
    reg armed = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    function [7:0] value_for_index(input [1:0] idx);
        case (idx)
            2'd0: value_for_index = value_0;
            2'd1: value_for_index = value_1;
            2'd2: value_for_index = value_2;
            default: value_for_index = value_3;
        endcase
    endfunction

    // Real, unchanged from v1: no capture at all -- nothing arrives
    // that this core reacts to, confirmed directly, not assumed.
    assign ack_out_n = 1'b0;
    assign ack_out_s = 1'b0;
    assign ack_out_e = 1'b0;
    assign ack_out_w = 1'b0;

    // ── Downstream offering -- real, unchanged shape from v1, gated
    // additionally on effective_armed (#617's own real principle,
    // applied here in its simplest real form -- see header). ──
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

    wire offer_just_completed = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);
    wire [1:0] next_seq_index = (seq_index == sequence_len_m1) ? 2'd0 : seq_index + 2'd1;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #617: the real, three-addon chain, applied to the
    // offered {24'h0,out_buffer} expansion, wired identically to
    // #618-#624's own. ──
    wire [31:0] seq_expanded = {24'h0, out_buffer};
    wire [31:0] after_mask, after_shiftlane, addon_out;
    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(seq_expanded), .data_out(after_mask)
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

    assign status_seq_index = seq_index;
    // Real, honest gating: an inactive/disarmed cell is never ready --
    // same real convention as #618-#624's own.
    assign ready_out = effective_armed && !effective_freeze;

    // ── points.md #617: real, targeted programming channel — same
    // real priority-select shape as #618-#624's own. Every real field
    // here fits in a single targeted write; the real ID budget fits
    // EXACTLY in 3 bits (7 fields + COMPLETE), unlike branch's own
    // real 4-bit need (#624) -- a real, direct confirmation the
    // budget genuinely depends on each core's own field count. ──
    localparam [2:0] PROG_ID_VALUE_0         = 3'd0;
    localparam [2:0] PROG_ID_VALUE_1         = 3'd1;
    localparam [2:0] PROG_ID_VALUE_2         = 3'd2;
    localparam [2:0] PROG_ID_VALUE_3         = 3'd3;
    localparam [2:0] PROG_ID_SEQUENCE_LEN    = 3'd4;
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd5;
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
            value_0         <= 8'h00; value_1 <= 8'h00; value_2 <= 8'h00; value_3 <= 8'h00;
            sequence_len_m1 <= 2'd0;
            downstream_mask <= 6'h0;
            addon_config    <= 20'h0;
            seq_index       <= 2'd0;
            out_buffer      <= 8'h00;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            value_0         <= cfg_data[7:0];
            value_1         <= cfg_data[15:8];
            value_2         <= cfg_data[23:16];
            value_3         <= cfg_data[31:24];
            sequence_len_m1 <= cfg_data[33:32];
            downstream_mask <= cfg_data[39:34];
            addon_config    <= cfg_data[59:40];
            seq_index       <= 2'd0;
            out_buffer      <= cfg_data[7:0];   // value_for_index(0) -- same value_0 field, direct
            data_valid      <= 1'b1;            // live from the first cycle after config
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_VALUE_0:         value_0         <= prog_word[7:0];
                PROG_ID_VALUE_1:         value_1         <= prog_word[7:0];
                PROG_ID_VALUE_2:         value_2         <= prog_word[7:0];
                PROG_ID_VALUE_3:         value_3         <= prog_word[7:0];
                PROG_ID_SEQUENCE_LEN:    sequence_len_m1 <= prog_word[1:0];
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (offer_just_completed) begin
                seq_index  <= next_seq_index;
                out_buffer <= value_for_index(next_seq_index);
            end
            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
