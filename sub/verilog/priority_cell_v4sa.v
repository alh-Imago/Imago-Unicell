// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// priority_cell_v4sa.v -- ledger #1017: the PRIORITY core on the flex family (valid/ready ack, global freeze, WIDTH), the last of the cores to be ported across.
// The behaviour is priority_cell_v4c.v's (fpga/verilog), unchanged, in the family's handshake protocol:
//
//   FOUR inputs, one per face (n, s, e, w), each with its own data / valid / ready. ONE output (data_out / valid_out / ack_in); the generator's eager fork delivers it to every consumer.
//   A face is a CANDIDATE when its valid is high AND its bit in `upstream_mask` is set (a connected face that the configuration masks off never wins, exactly as in the VM).
//   Exactly ONE candidate is granted per item and ONLY that source is acknowledged; the losers' items stay where they are, waiting, and nobody is blocked by them.
//
//   scheduling_mode 0  STRICT    the candidate with the lowest rank wins ("0 = highest priority"); score = 3 - rank.
//   scheduling_mode 1  WEIGHTED  SURPLUS ROUND ROBIN: every candidate's credit gains its own weight (= its rank field, 0 = lowest weight, 3 = highest) on every round it competes, win or lose;
//                                the highest credit wins; ONLY the winner's credit is then reduced, by the total weight of all candidates that round (clamped at 0).
//   scheduling_mode 2  SEQUENCED CHANNEL (ledger #1018, Alan's #772)  a fixed, cyclic TURN ORDER (up to four turns, each a face; a face may appear more than once). ONLY the face whose turn it is
//                                is ever a candidate; every other arrival waits, however early, however long the due face takes (head-of-line blocking, by design). The turn advances when the due face's
//                                word is taken, and wraps. An empty order never captures. The cell, not the wiring, guarantees the order.
//   Ties (equal score) are broken by the fixed order N > S > E > W in modes 0 and 1.
//
// cfg_data (32 bits):  [3:0] upstream_mask (n = bit 0, s = 1, e = 2, w = 3)   [5:4] rank_n  [7:6] rank_s  [9:8] rank_e  [11:10] rank_w   [12] weighted (mode 1)
//                      [13] sequenced (mode 2, wins over [12])   [16:14] sequence_len (0..4)   [18:17] turn 0  [20:19] turn 1  [22:21] turn 2  [24:23] turn 3  (face codes 0 n, 1 s, 2 e, 3 w)
//   (the downstream mask of the v4c cell is not here: a consumer is wiring, the generator forks the one output.)
//
// PROTOCOL (the family's, read from merge_cell_v4sa.v): the cell captures at an edge where it is not `pending`; the winner's word is registered (out_buffer) and `valid_out = pending` is held until
// `ack_in` is high at an edge. An input's `ack_out_*` is the cell's READY for THAT input, high only for the granted face, so a transfer is an edge where `valid_in_*` and `ack_out_*` are both high.
// One item per two cycles, `freeze_in` gates everything, configuration arms the cell and clears its state (credits included). One cycle of added latency and storage, like a relay.
`default_nettype none
`timescale 1ns / 1ps

module priority_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire              clk,
    input  wire              rst,
    input  wire              freeze_in,
    input  wire              cfg_valid,
    input  wire [31:0]       cfg_data,
    input  wire [WIDTH-1:0]  in_n,
    input  wire              valid_in_n,
    output wire              ack_out_n,
    input  wire [WIDTH-1:0]  in_s,
    input  wire              valid_in_s,
    output wire              ack_out_s,
    input  wire [WIDTH-1:0]  in_e,
    input  wire              valid_in_e,
    output wire              ack_out_e,
    input  wire [WIDTH-1:0]  in_w,
    input  wire              valid_in_w,
    output wire              ack_out_w,
    output wire [WIDTH-1:0]  data_out,
    output wire              valid_out,
    input  wire              ack_in
);
    reg [3:0]       upstream_mask   = 4'h0;
    reg [1:0]       rank_n = 2'h0, rank_s = 2'h0, rank_e = 2'h0, rank_w = 2'h0;
    reg             scheduling_mode = 1'b0;
    reg             sequenced       = 1'b0;
    reg [2:0]       seq_len         = 3'h0;
    reg [7:0]       seq_order       = 8'h00;
    reg [2:0]       seq_idx         = 3'h0;
    reg [7:0]       credit_n = 8'h0, credit_s = 8'h0, credit_e = 8'h0, credit_w = 8'h0;
    reg             armed      = 1'b0;
    reg             pending    = 1'b0;
    reg [WIDTH-1:0] out_buffer = {WIDTH{1'b0}};

    wire ready = armed && !pending && !freeze_in && !seq_cap;

    // sequenced channel: the face whose turn it is (a turn index past the end, or an empty order, selects nothing)
    wire [1:0] due_face = seq_order[{seq_idx[1:0], 1'b0} +: 2];
    wire       due_ok   = sequenced && (seq_len != 3'h0);
    wire due_n = due_ok && due_face == 2'd0;
    wire due_s = due_ok && due_face == 2'd1;
    wire due_e = due_ok && due_face == 2'd2;
    wire due_w = due_ok && due_face == 2'd3;
    wire seq_cap = sequenced && !due_ok;                 // an empty order never captures

    // candidates: offered AND enabled (AND, in the sequenced mode, due)
    wire cand_n = valid_in_n && upstream_mask[0] && (!sequenced || due_n);
    wire cand_s = valid_in_s && upstream_mask[1] && (!sequenced || due_s);
    wire cand_e = valid_in_e && upstream_mask[2] && (!sequenced || due_e);
    wire cand_w = valid_in_w && upstream_mask[3] && (!sequenced || due_w);

    // surplus round robin: every candidate's credit gains its weight this round
    wire [7:0] inc_n = cand_n ? (credit_n + {6'h0, rank_n}) : credit_n;
    wire [7:0] inc_s = cand_s ? (credit_s + {6'h0, rank_s}) : credit_s;
    wire [7:0] inc_e = cand_e ? (credit_e + {6'h0, rank_e}) : credit_e;
    wire [7:0] inc_w = cand_w ? (credit_w + {6'h0, rank_w}) : credit_w;
    wire [7:0] total_weight = (cand_n ? {6'h0, rank_n} : 8'h0) + (cand_s ? {6'h0, rank_s} : 8'h0) +
                              (cand_e ? {6'h0, rank_e} : 8'h0) + (cand_w ? {6'h0, rank_w} : 8'h0);

    // one comparator structure for both modes: strict scores by (3 - rank), weighted by the credit
    wire [7:0] score_n = scheduling_mode ? inc_n : {6'h0, (2'd3 - rank_n)};
    wire [7:0] score_s = scheduling_mode ? inc_s : {6'h0, (2'd3 - rank_s)};
    wire [7:0] score_e = scheduling_mode ? inc_e : {6'h0, (2'd3 - rank_e)};
    wire [7:0] score_w = scheduling_mode ? inc_w : {6'h0, (2'd3 - rank_w)};

    // winner: highest score, ties N > S > E > W
    wire win_n = cand_n && (!cand_s || score_n >= score_s) && (!cand_e || score_n >= score_e) && (!cand_w || score_n >= score_w);
    wire win_s = cand_s && !win_n && (!cand_e || score_s >= score_e) && (!cand_w || score_s >= score_w);
    wire win_e = cand_e && !win_n && !win_s && (!cand_w || score_e >= score_w);
    wire win_w = cand_w && !win_n && !win_s && !win_e;
    wire any_win = win_n | win_s | win_e | win_w;

    wire [WIDTH-1:0] winning_val = (win_n ? in_n : {WIDTH{1'b0}}) | (win_s ? in_s : {WIDTH{1'b0}}) |
                                   (win_e ? in_e : {WIDTH{1'b0}}) | (win_w ? in_w : {WIDTH{1'b0}});

    // ready is raised ONLY for the granted face
    assign ack_out_n = ready && win_n;
    assign ack_out_s = ready && win_s;
    assign ack_out_e = ready && win_e;
    assign ack_out_w = ready && win_w;

    assign data_out  = out_buffer;
    assign valid_out = pending;

    always @(posedge clk) begin
        if (rst) begin
            upstream_mask <= 4'h0; scheduling_mode <= 1'b0; sequenced <= 1'b0; seq_len <= 3'h0; seq_order <= 8'h00; seq_idx <= 3'h0;
            rank_n <= 2'h0; rank_s <= 2'h0; rank_e <= 2'h0; rank_w <= 2'h0;
            credit_n <= 8'h0; credit_s <= 8'h0; credit_e <= 8'h0; credit_w <= 8'h0;
            armed <= 1'b0; pending <= 1'b0; out_buffer <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            upstream_mask   <= cfg_data[3:0];
            rank_n          <= cfg_data[5:4];
            rank_s          <= cfg_data[7:6];
            rank_e          <= cfg_data[9:8];
            rank_w          <= cfg_data[11:10];
            scheduling_mode <= cfg_data[12];
            sequenced       <= cfg_data[13];
            seq_len         <= cfg_data[16:14];
            seq_order       <= cfg_data[24:17];
            seq_idx         <= 3'h0;
            credit_n <= 8'h0; credit_s <= 8'h0; credit_e <= 8'h0; credit_w <= 8'h0;
            armed <= 1'b1; pending <= 1'b0; out_buffer <= {WIDTH{1'b0}};
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (ready && any_win) begin
                out_buffer <= winning_val;
                pending    <= 1'b1;
                if (sequenced) seq_idx <= (seq_idx + 3'h1 >= seq_len) ? 3'h0 : seq_idx + 3'h1;
                if (scheduling_mode && !sequenced) begin
                    credit_n <= win_n ? ((inc_n > total_weight) ? (inc_n - total_weight) : 8'h0) : inc_n;
                    credit_s <= win_s ? ((inc_s > total_weight) ? (inc_s - total_weight) : 8'h0) : inc_s;
                    credit_e <= win_e ? ((inc_e > total_weight) ? (inc_e - total_weight) : 8'h0) : inc_e;
                    credit_w <= win_w ? ((inc_w > total_weight) ? (inc_w - total_weight) : 8'h0) : inc_w;
                end
            end
        end
    end
endmodule
