// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v4c.v — points.md #720: the "c" (carrier) variant of
// compare_cell_v4.v. Same real reasoning as adder_cell_v4c.v's/ram_
// cell_v4c.v's own headers -- the carrier's whole design concept is
// to hold common functionality centrally, and this core's own
// internal 3-addon chain duplicates exactly what the carrier itself
// now provides once, shared. compare_cell_v4.v itself is UNCHANGED,
// still the real, proven, standalone core.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from out_buffer, the real comparison
//      result.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and the PROG_ID_ADDON_CONFIG case -- cfg_
//      data KEEPS its original 64-bit width; those bits are now
//      genuinely reserved.
//   3. Same real config-off-shell reasoning as the other _v4c files:
//      downstream_mask/upstream_mask/threshold STAY real registers
//      (this cell's live-programming channel genuinely needs them
//      independently writable); the real fix lives at the carrier's
//      own shell level -- feed cfg_data from stable core_config, not
//      transient incoming_config.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask     — one-hot(s), N/S/E/W real + 2 reserved
//   [43:12] threshold         — the configured reference (32-bit signed)
//   [63:44] reserved          — 20 bits (addon_config's own old home,
//                               now genuinely free)

`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v4c #(
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

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    // ── points.md #617: the real, targeted programming channel, same
    // real shape as #618/#619's own. ──
    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid
);

    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg signed [31:0] threshold = 32'sh0;

    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;
    reg [3:0]  pending_ack = 4'h0;
    // points.md #617: real, staged-reconfiguration arm state, same
    // real semantics as #618/#619's own.
    reg        armed       = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire signed [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                                      (sel_s ? data_in_s : 32'h0) |
                                      (sel_e ? data_in_e : 32'h0) |
                                      (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !data_valid && !effective_freeze &&
                       effective_armed && !program_in;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── THE CORE — real, unchanged from v1: a genuine two's-complement
    // comparison against the configured threshold. ──
    wire result_bit = (upstream_val >= threshold);

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
    // data_out_n/s/e/w are the real comparison result, directly. ──
    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = effective_armed && !effective_freeze && !data_valid;
    assign status_data_valid = data_valid;

    // ── points.md #617: real, targeted programming channel — same
    // real priority-select shape as #618/#619's own. threshold split
    // across two real half-writes, same real reason as ram's own
    // init_data (#619) -- but real, deliberately simpler here: no
    // separate commit trigger needed, since threshold is pure config,
    // not a currently-held, offer-bound value. ──
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_THRESHOLD_LOW   = 3'd2;
    localparam [2:0] PROG_ID_THRESHOLD_HIGH  = 3'd3;
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
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            downstream_mask <= 6'h0;
            upstream_mask   <= 6'h0;
            threshold       <= 32'sh0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            threshold       <= cfg_data[43:12];
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask   <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask     <= prog_word[5:0];
                PROG_ID_THRESHOLD_LOW:   threshold[15:0]   <= prog_word[15:0];
                PROG_ID_THRESHOLD_HIGH:  threshold[31:16]  <= prog_word[15:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (capture_now) begin
                out_buffer <= {31'h0, result_bit};
                data_valid <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
