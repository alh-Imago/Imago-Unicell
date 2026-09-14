// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// priority_cell_v4c.v — points.md #730: the "c" (carrier) variant of
// priority_cell_v4.v, built alongside it (matching mul's own #724
// precedent -- when both variants are built in the same pass, no
// retrofit is needed). Same real reasoning as every other _v4c file's
// own header: the carrier's whole design concept is to hold common
// functionality centrally, and this core's own internal 3-addon chain
// duplicates exactly what the carrier itself now provides once,
// shared. priority_cell_v4.v itself is UNCHANGED, still the real,
// proven, standalone core -- including its own real strict-priority
// AND weighted-round-robin scheduling modes, both fully preserved
// here unchanged; only the addon chain and config-off-shell source
// differ between the two files.
//
// Real, honest scope of this file's own changes from v4:
//   1. The internal addon chain is REMOVED entirely -- data_out_n/s/
//      e/w now come directly from data_reg, the real captured value.
//   2. addon_config (20 bits) is removed from cfg_data's own field
//      map, the register, and PROG_ID_ADDON_CONFIG. cfg_data KEEPS
//      its original 64-bit width; PROG_ID_COMPLETE stays at 3'd7,
//      addon_config's own old slot (3'd3) is simply unused now.
//   3. Same real config-off-shell reasoning as every other _v4c file
//      (confirmed correct the hard way in #723): this core's own real
//      config fields STAY registers, fed from the carrier's own
//      combinational incoming_config (the value about to be
//      committed), NOT the registered core_config.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   upstream_mask     — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  downstream_mask   — one-hot(s), N/S/E/W real + 2 reserved
//   [13:12] priority_rank_n   — strict mode: 0=highest,3=lowest. RR
//   [15:14] priority_rank_s     mode: relative weight, 0=lowest
//   [17:16] priority_rank_e     possible weight.
//   [19:18] priority_rank_w
//   [20]    scheduling_mode   — 0=strict priority, 1=weighted RR
//   [63:21] reserved          — 43 bits (addon_config's own old home,
//                               now genuinely free, plus the original
//                               23 bits of headroom)

`default_nettype none
`timescale 1ns / 1ps

module priority_cell_v4c #(
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

    // ── points.md #730: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active. ──
    assign data_out_n = data_reg;
    assign data_out_s = data_reg;
    assign data_out_e = data_reg;
    assign data_out_w = data_reg;

    assign ready_out = effective_armed && !effective_freeze && !data_valid;
    assign status_data_valid   = data_valid;
    assign status_winning_dir  = winning_dir_reg;

    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd0;
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd1;
    localparam [2:0] PROG_ID_PRIORITY_RANKS  = 3'd2;   // {sched_mode,rank_w,rank_e,rank_s,rank_n}, 9 bits
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
