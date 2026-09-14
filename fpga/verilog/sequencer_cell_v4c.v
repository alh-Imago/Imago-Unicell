// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sequencer_cell_v4c.v — points.md #720: the "c" (carrier) variant of
// sequencer_cell_v4.v. Same real reasoning as the other _v4c files'
// own headers -- the carrier's whole design concept is to hold common
// functionality centrally, and this core's own internal 3-addon chain
// duplicates exactly what the carrier itself now provides once,
// shared. sequencer_cell_v4.v itself is UNCHANGED, still the real,
// proven, standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from {24'h0, out_buffer}, the real
//      expanded current sequence value, expanded exactly as v4 does
//      before its own addon chain, just without the transform after.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and PROG_ID_ADDON_CONFIG. cfg_data KEEPS
//      its original 64-bit width; PROG_ID_COMPLETE stays at 3'd7,
//      addon_config's own old slot (3'd6) is simply unused now.
//   3. Same real config-off-shell reasoning as every other _v4c file:
//      all real config fields STAY registers; the real fix lives at
//      the carrier's own shell level.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [7:0]   VALUE_0
//   [15:8]  VALUE_1
//   [23:16] VALUE_2
//   [31:24] VALUE_3
//   [33:32] SEQUENCE_LEN     — stored as length-1 (0 means length 1)
//   [39:34] downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [63:40] reserved         — 24 bits (addon_config's own old home,
//                              now genuinely free, plus the original
//                              4 bits of headroom)

`default_nettype none
`timescale 1ns / 1ps

module sequencer_cell_v4c #(
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

    // ── points.md #720: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active. ──
    wire [31:0] seq_expanded = {24'h0, out_buffer};
    assign data_out_n = seq_expanded;
    assign data_out_s = seq_expanded;
    assign data_out_e = seq_expanded;
    assign data_out_w = seq_expanded;

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
