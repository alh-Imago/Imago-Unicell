// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// priority_cell_v4.v — points.md #730: the 11th unified-carrier core,
// the real priority arbiter (#707, resolved #727). Genuinely different
// in SHAPE from every other core so far: not a two-operand combine
// (add/mul) needing two-stage capture, and not a single-operand
// transform (compare) — this core's own real job is deciding WHICH of
// several simultaneously-arrived real inputs gets captured first,
// using a real, configurable per-direction priority rank rather than
// the OR-combine every other core's own upstream_val already uses.
//
// Real, resolved design (#727), used directly, not re-derived:
//   - Uses the SAME real upstream_mask/downstream_mask convention
//     every other core already has — no fixed, asymmetric port roles.
//   - Priority order is a real, per-direction CONFIGURABLE rank
//     (2 bits each), not a hardcoded value — a fixed priority would
//     force every design using this core into one specific physical
//     layout.
//   - The real output side has no priority semantics attached at all
//     — a normal downstream_mask, exactly like every other core.
//   - Real, documented (not hardware-enforced) expectation: at least
//     TWO real input directions should be enabled via upstream_mask,
//     or there's genuinely no point using this core over a plain
//     relay.
//
// Real, second refinement (2026-09-08): strict priority alone
// genuinely starves lower-ranked ports under sustained load from the
// top-ranked one — not a corner case, the expected behavior of any
// fixed-priority scheme. A real, second scheduling mode added, not a
// replacement: `scheduling_mode` selects strict priority (0, the
// original design, rank 0=highest/3=lowest) or weighted round-robin
// (1, the SAME rank fields reinterpreted as relative WEIGHTS, 0=
// lowest possible weight). Real, honest mechanism: a genuine credit
// accumulator per direction (the same real technique real network
// schedulers use) -- every real arbitration decision, every OTHER
// candidate's own credit gains its own configured weight, and the
// winner's own credit resets to 0. This produces a real, proportional
// interleaving (roughly A,A,A,B,A,A,A,B for a real 3:1 weight ratio),
// not an exact, pre-specified sequence -- a genuinely different,
// bigger core would be needed for that.
//
// Real, honest scope for the arbitration logic itself: both modes
// share ONE real comparator structure over a unified per-direction
// "score" (strict mode: `3 - rank`, so lower rank gives a higher
// score; RR mode: the real, live credit value) — ties broken by the
// same fixed, real N>S>E>W order in both modes. Single-stage capture
// (data_reg/data_valid only) — genuinely simpler than add/mul's own
// two-stage a_reg/a_arrived shape, since there is no second operand to
// wait for at all; the "other" operand here is a competing ARRIVAL,
// not a value to combine with.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   upstream_mask     — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [13:12] priority_rank_n   — strict mode: 0=highest,3=lowest.
//   [15:14] priority_rank_s     RR mode: relative weight, 0=lowest
//   [17:16] priority_rank_e     possible weight.
//   [19:18] priority_rank_w
//   [20]    scheduling_mode   — 0=strict priority, 1=weighted RR
//   [40:21] addon_config      — 20 bits, SAME real layout as every
//                               other _v4 core's own addon chain
//                               (shifted 1 bit for scheduling_mode)
//   [63:41] reserved
`default_nettype none
`timescale 1ns / 1ps

module priority_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

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

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,

    output wire         status_data_valid,
    output wire  [1:0]  status_winning_dir   // 2'b00=N 01=S 10=E 11=W, real diagnostic only
);

    reg [31:0] data_reg        = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [1:0]  priority_rank_n = 2'h0;
    reg [1:0]  priority_rank_s = 2'h0;
    reg [1:0]  priority_rank_e = 2'h0;
    reg [1:0]  priority_rank_w = 2'h0;
    reg        scheduling_mode = 1'b0;
    reg [19:0] addon_config    = 20'h0;
    reg [3:0]  pending_ack     = 4'h0;
    reg        armed           = 1'b0;
    reg [1:0]  winning_dir_reg = 2'h0;

    // ── points.md #730 (2nd refinement): real, live credit state for
    // weighted round-robin mode -- internal scheduler state only, NOT
    // part of cfg_data, not directly user-visible. Unused (stays at 0)
    // in strict-priority mode. ──
    reg [7:0]  credit_n = 8'h0;
    reg [7:0]  credit_s = 8'h0;
    reg [7:0]  credit_e = 8'h0;
    reg [7:0]  credit_w = 8'h0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ── Real, genuine priority encoder — the one thing that's new
    // here. A direction is a real candidate only if it's BOTH enabled
    // (upstream_mask) AND has real, arrived data waiting right now.
    // Both scheduling modes share ONE comparator structure over a
    // unified per-direction "score" (points.md #730's own 2nd
    // refinement): strict mode uses `3 - rank` (so a lower configured
    // rank gives a HIGHER score, preserving "0 = highest priority"
    // exactly); RR mode uses the real, live credit value directly.
    // Ties (equal score) broken by a fixed N>S>E>W order in both
    // modes, unchanged from the original design. ──
    wire cand_n = arrived_n && upstream_mask[0];
    wire cand_s = arrived_s && upstream_mask[1];
    wire cand_e = arrived_e && upstream_mask[2];
    wire cand_w = arrived_w && upstream_mask[3];

    // ── points.md #730 (2nd refinement, corrected): the real, proven
    // "Surplus Round Robin" shape -- EVERY real candidate's credit
    // gains its own weight EVERY cycle it competes (win or lose), and
    // ONLY the winner's own credit is then reduced, by the TOTAL
    // weight of every candidate that round (clamped at 0, never
    // negative). An earlier draft incremented only the LOSER's own
    // credit and reset the winner to 0 -- confirmed by direct
      // simulation to produce strict alternation regardless of the
    // configured weight ratio (a real, wrong result, caught before
    // committing to it), since a big winning margin always fully
    // reset rather than carrying its own real surplus forward. ──
    wire [7:0] credit_n_inc = cand_n ? (credit_n + {6'h0, priority_rank_n}) : credit_n;
    wire [7:0] credit_s_inc = cand_s ? (credit_s + {6'h0, priority_rank_s}) : credit_s;
    wire [7:0] credit_e_inc = cand_e ? (credit_e + {6'h0, priority_rank_e}) : credit_e;
    wire [7:0] credit_w_inc = cand_w ? (credit_w + {6'h0, priority_rank_w}) : credit_w;
    wire [7:0] total_weight = (cand_n ? {6'h0, priority_rank_n} : 8'h0) +
                              (cand_s ? {6'h0, priority_rank_s} : 8'h0) +
                              (cand_e ? {6'h0, priority_rank_e} : 8'h0) +
                              (cand_w ? {6'h0, priority_rank_w} : 8'h0);

    wire [7:0] score_n = scheduling_mode ? credit_n_inc : {6'h0, (2'd3 - priority_rank_n)};
    wire [7:0] score_s = scheduling_mode ? credit_s_inc : {6'h0, (2'd3 - priority_rank_s)};
    wire [7:0] score_e = scheduling_mode ? credit_e_inc : {6'h0, (2'd3 - priority_rank_e)};
    wire [7:0] score_w = scheduling_mode ? credit_w_inc : {6'h0, (2'd3 - priority_rank_w)};

    wire n_beats_s = !cand_s || (score_n >= score_s);
    wire n_beats_e = !cand_e || (score_n >= score_e);
    wire n_beats_w = !cand_w || (score_n >= score_w);
    wire win_n = cand_n && n_beats_s && n_beats_e && n_beats_w;

    wire s_beats_e = !cand_e || (score_s >= score_e);
    wire s_beats_w = !cand_w || (score_s >= score_w);
    wire win_s = cand_s && !win_n && s_beats_e && s_beats_w;

    wire e_beats_w = !cand_w || (score_e >= score_w);
    wire win_e = cand_e && !win_n && !win_s && e_beats_w;

    wire win_w = cand_w && !win_n && !win_s && !win_e;

    wire any_win = win_n | win_s | win_e | win_w;
    wire [31:0] winning_val = (win_n ? data_in_n : 32'h0) |
                              (win_s ? data_in_s : 32'h0) |
                              (win_e ? data_in_e : 32'h0) |
                              (win_w ? data_in_w : 32'h0);

    // ── Real, single-stage capture — no second operand to wait for. ──
    wire capture_now = any_win && !data_valid && !effective_freeze &&
                       effective_armed && !program_in;

    assign ack_out_n = capture_now && win_n;
    assign ack_out_s = capture_now && win_s;
    assign ack_out_e = capture_now && win_e;
    assign ack_out_w = capture_now && win_w;

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

    // ── points.md #617's own real, three-addon chain, wired exactly
    // as every other _v4 core's own -- same order, same 20-bit
    // addon_config layout, reused verbatim. ──
    wire [31:0] after_mask, after_shiftlane, addon_out;
    nibble_mask_addon_v1 ADDON_NM (
        .mask_en(addon_config[8]), .nibble_mask(addon_config[7:0]),
        .data_in(data_reg), .data_out(after_mask)
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
    assign status_data_valid   = data_valid;
    assign status_winning_dir  = winning_dir_reg;

    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd0;
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd1;
    localparam [2:0] PROG_ID_PRIORITY_RANKS  = 3'd2;   // {sched_mode,rank_w,rank_e,rank_s,rank_n}, 9 bits
    localparam [2:0] PROG_ID_ADDON_CONFIG    = 3'd3;
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
            data_reg        <= 32'h0;
            data_valid      <= 1'b0;
            upstream_mask   <= 6'h0;
            downstream_mask <= 6'h0;
            priority_rank_n <= 2'h0;
            priority_rank_s <= 2'h0;
            priority_rank_e <= 2'h0;
            priority_rank_w <= 2'h0;
            scheduling_mode <= 1'b0;
            addon_config    <= 20'h0;
            credit_n        <= 8'h0;
            credit_s        <= 8'h0;
            credit_e        <= 8'h0;
            credit_w        <= 8'h0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            program_done_r  <= 1'b0;
            winning_dir_reg <= 2'h0;
        end else if (cfg_valid) begin
            upstream_mask   <= cfg_data[5:0];
            downstream_mask <= cfg_data[11:6];
            priority_rank_n <= cfg_data[13:12];
            priority_rank_s <= cfg_data[15:14];
            priority_rank_e <= cfg_data[17:16];
            priority_rank_w <= cfg_data[19:18];
            scheduling_mode <= cfg_data[20];
            addon_config    <= cfg_data[40:21];
            credit_n        <= 8'h0;
            credit_s        <= 8'h0;
            credit_e        <= 8'h0;
            credit_w        <= 8'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_PRIORITY_RANKS: begin
                    priority_rank_n <= prog_word[1:0];
                    priority_rank_s <= prog_word[3:2];
                    priority_rank_e <= prog_word[5:4];
                    priority_rank_w <= prog_word[7:6];
                    scheduling_mode <= prog_word[8];
                    credit_n <= 8'h0;
                    credit_s <= 8'h0;
                    credit_e <= 8'h0;
                    credit_w <= 8'h0;
                end
                PROG_ID_ADDON_CONFIG:    addon_config    <= prog_word[19:0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (capture_now) begin
                data_reg        <= winning_val;
                data_valid      <= 1'b1;
                winning_dir_reg <= win_n ? 2'b00 : win_s ? 2'b01 : win_e ? 2'b10 : 2'b11;

                // ── points.md #730 (2nd refinement): real credit
                // update, RR mode only -- every OTHER real candidate
                // that lost this round gains its own configured
                // weight; the winner's own credit resets to 0. Stays
                // at 0 (never accumulates) in strict mode, matching
                // the original design exactly when scheduling_mode=0.
                // ── points.md #730 (2nd refinement, corrected): real
                // Surplus Round Robin update -- every candidate's
                // credit already gained its own weight this cycle
                // (credit_*_inc, computed combinationally above); only
                // the real winner's own credit is now reduced by the
                // real total weight, clamped at 0 rather than
                // underflowing. Non-winning candidates simply keep
                // their own incremented value.
                if (scheduling_mode) begin
                    credit_n <= win_n ? ((credit_n_inc > total_weight) ? (credit_n_inc - total_weight) : 8'h0) : credit_n_inc;
                    credit_s <= win_s ? ((credit_s_inc > total_weight) ? (credit_s_inc - total_weight) : 8'h0) : credit_s_inc;
                    credit_e <= win_e ? ((credit_e_inc > total_weight) ? (credit_e_inc - total_weight) : 8'h0) : credit_e_inc;
                    credit_w <= win_w ? ((credit_w_inc > total_weight) ? (credit_w_inc - total_weight) : 8'h0) : credit_w_inc;
                end
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
