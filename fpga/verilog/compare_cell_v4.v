// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v4.v — points.md #617/#620: the THIRD real "unified
// carrier" core, following `adder_cell_v4.v` (#618, two-stage A/B
// capture) and `ram_cell_v4.v` (#619, single-arrival, no real
// computation). This core is a third genuinely distinct combination:
// single-arrival capture (like ram) WITH a real computation against a
// configured value (like adder has real computation, but two-stage)
// -- confirming the shell template keeps generalizing across real,
// different core shapes, not just the two already tried.
//
// Real core logic CLONED from compare_cell_v1.v unchanged (the
// signed `>=` comparison against a configured threshold, the doubly-
// full single-capture guard). Same real shell additions as `#618`/
// `#619`, per Alan's own precise 5-point breakdown (`#617`):
//   1. programming: real, targeted program_in/PROG_ID channel.
//   2. shift/nibble_mask/lane: the same real, already-proven 3-addon
//      chain, wired identically.
//   3. 6-way cardinality: real field-width headroom only.
//   4. ack all around: the programming channel's own real,
//      independent per-direction ack.
//   5. `active`: the same real, explicit port.
//
// REAL, NOTEWORTHY DIFFERENCE FROM THE PRIOR TWO CORES: this one's
// real field total (6+6+32+20 = 64 bits) fits EXACTLY in v1's own
// original 64-bit cfg_data -- no widening needed, unlike ram_cell_v4.v
// (#619, needed 80 bits). A real, useful data point: the unified
// carrier's own real cost in bits genuinely varies per core, not a
// fixed tax every core pays identically.
//
// REAL, NECESSARY PROTOCOL ADAPTATION, same real reason as ram's own
// init_data (#619): `threshold` is 32 bits, too wide for one real
// targeted PROG_ID write alongside its own 3-bit ID -- split into two
// real half-writes (`PROG_ID_THRESHOLD_LOW`/`_HIGH`). REAL, DELIBERATE
// SIMPLIFICATION versus ram's own real "explicit commit" pattern:
// `threshold` is pure CONFIGURATION, never itself offered downstream
// the way ram's `data_reg` is -- each half-write takes effect
// immediately, no separate commit trigger needed, since there's no
// real "currently held, must not be silently corrupted" state at risk
// here the way there was for ram (#619's own real bug).
//
// REAL, HONEST SCOPE, matching `#618`/`#619`'s own stated deferrals:
// `is_command_cell` mode NOT included (parked as a possible 9th-core
// question, per this session's own later discussion).
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask     — one-hot(s), N/S/E/W real + 2 reserved
//   [43:12] threshold         — the configured reference (32-bit signed)
//   [63:44] addon_config      — 20 bits, SAME real layout as
//                               unicell_super_v3.v's own real addon_config
`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v4 #(
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
    reg [19:0] addon_config    = 20'h0;

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

    // ── points.md #617: the real, three-addon chain, wired identically
    // to #618/#619's own. ──
    wire [31:0] after_mask, after_shiftlane, addon_out;
    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(out_buffer), .data_out(after_mask)
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
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            downstream_mask <= 6'h0;
            upstream_mask   <= 6'h0;
            threshold       <= 32'sh0;
            addon_config    <= 20'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            threshold       <= cfg_data[43:12];
            addon_config    <= cfg_data[63:44];
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask   <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask     <= prog_word[5:0];
                PROG_ID_THRESHOLD_LOW:   threshold[15:0]   <= prog_word[15:0];
                PROG_ID_THRESHOLD_HIGH:  threshold[31:16]  <= prog_word[15:0];
                PROG_ID_ADDON_CONFIG:    addon_config      <= prog_word[19:0];
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
