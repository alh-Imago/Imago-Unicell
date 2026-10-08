// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// merge_cell_v4c.v — ledger #1036: the MERGE core in the main (carrier) theme. The flex family's merge_cell_v4sa (A only / B only / arbitrate / join-OR) brought across: a cell with
// TWO input faces and one result, whose MODE says how the two meet.
//
//   cfg_data[5:0]   downstream_mask
//   cfg_data[11:6]  upstream_mask  — the two input faces (only [3:0] are wired). A = the first set bit in N,S,E,W order, B = the second.
//   cfg_data[13:12] mode           — 0 A only: B is never accepted.   1 B only: A is never accepted.
//                                    2 ARBITRATE: one word at a time; a same-cycle tie goes to the face the round-robin flag favours, and the flag rotates after every grant (neither can starve).
//                                    3 JOIN-OR: each face's word is held as it arrives (acknowledged at once); once BOTH are held, A|B is offered as ONE word.
//
// Why it is a core: a plain OR of simultaneous arrivals (what a ram with two upstream faces does) fuses two separate items into one corrupt value when both stay valid; the modes make the choice explicit.
// Protocol: the carrier's (fire / arrived / ack / ready). One word is held at a time; no new word is taken while a result is on offer. Targeted programming: PROG_ID 0 downstream, 1 upstream,
// 2 mode (word[1:0]), 7 COMPLETE (re-arm). Differences from merge_cell_v4sa: join-OR acknowledges each half as it arrives (the flex cell acknowledges both together), and a result is offered with fire/ack.
`default_nettype none
`timescale 1ns / 1ps

module merge_cell_v4c #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        active,

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

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,
    output wire         status_data_valid
);
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg [1:0]  mode            = 2'd2;
    reg        rr              = 1'b0;      // arbitrate: 1 = B wins a same-cycle tie
    reg [31:0] a_hold = 32'h0, b_hold = 32'h0;
    reg        a_have = 1'b0, b_have = 1'b0;
    reg [3:0]  pending_ack     = 4'h0;
    reg        armed           = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    // ---- the two faces: A = lowest set upstream bit (N,S,E,W order), B = the next ----
    wire [3:0] um   = upstream_mask[3:0];
    wire [3:0] a_oh = um & (~um + 4'd1);
    wire [3:0] um2  = um & ~a_oh;
    wire [3:0] b_oh = um2 & (~um2 + 4'd1);
    wire [3:0] arr  = {arrived_w, arrived_e, arrived_s, arrived_n};
    wire arr_a = |(arr & a_oh);
    wire arr_b = |(arr & b_oh);
    wire [31:0] val_a = (a_oh[0] ? data_in_n : 32'h0) | (a_oh[1] ? data_in_s : 32'h0) | (a_oh[2] ? data_in_e : 32'h0) | (a_oh[3] ? data_in_w : 32'h0);
    wire [31:0] val_b = (b_oh[0] ? data_in_n : 32'h0) | (b_oh[1] ? data_in_s : 32'h0) | (b_oh[2] ? data_in_e : 32'h0) | (b_oh[3] ? data_in_w : 32'h0);

    wire free = !data_valid && !effective_freeze && effective_armed && !program_in;
    wire m_a = (mode == 2'd0), m_b = (mode == 2'd1), m_arb = (mode == 2'd2), m_or = (mode == 2'd3);

    wire grant_a = free && (m_a ? arr_a : (m_arb ? (arr_a && (!arr_b || !rr)) : 1'b0));
    wire grant_b = free && (m_b ? arr_b : (m_arb ? (arr_b && !grant_a)        : 1'b0));
    wire take_a  = free && m_or && arr_a && !a_have;
    wire take_b  = free && m_or && arr_b && !b_have;
    wire join_done = m_or && (a_have || take_a) && (b_have || take_b);
    wire [31:0] join_a = a_have ? a_hold : val_a;
    wire [31:0] join_b = b_have ? b_hold : val_b;

    wire acc_a = grant_a || take_a;
    wire acc_b = grant_b || take_b;
    assign ack_out_n = (acc_a && a_oh[0]) || (acc_b && b_oh[0]);
    assign ack_out_s = (acc_a && a_oh[1]) || (acc_b && b_oh[1]);
    assign ack_out_e = (acc_a && a_oh[2]) || (acc_b && b_oh[2]);
    assign ack_out_w = (acc_a && a_oh[3]) || (acc_b && b_oh[3]);

    // ---- offering the result: the carrier's fire / ack handshake, as every single-shot core ----
    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) && (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) && (!downstream_mask[3] || ready_in_w);
    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire             ? (downstream_mask[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0) ? (pending_ack & ~ack_in_vec) : pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);
    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];
    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;
    assign ready_out = effective_armed && !effective_freeze && !data_valid;
    assign status_data_valid = data_valid;

    // ---- targeted programming ----
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_MODE            = 3'd2;
    localparam [2:0] PROG_ID_COMPLETE        = 3'd7;
    wire prog_any_arrived = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire prog_sel_n = prog_arrived_in_n;
    wire prog_sel_s = prog_arrived_in_s && !prog_arrived_in_n;
    wire prog_sel_e = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire prog_sel_w = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] prog_data_val = prog_sel_n ? prog_data_in_n : prog_sel_s ? prog_data_in_s : prog_sel_e ? prog_data_in_e : prog_data_in_w;
    wire [2:0]  prog_id   = prog_data_val[22:20];
    wire [19:0] prog_word = prog_data_val[19:0];
    wire programming_active = program_in && active && prog_any_arrived;
    reg  program_done_r = 1'b0;
    assign program_done = program_done_r;
    assign prog_ack_out_n = programming_active && prog_sel_n;
    assign prog_ack_out_s = programming_active && prog_sel_s;
    assign prog_ack_out_e = programming_active && prog_sel_e;
    assign prog_ack_out_w = programming_active && prog_sel_w;

    always @(posedge clk) begin
        if (rst) begin
            out_buffer <= 32'h0; data_valid <= 1'b0; downstream_mask <= 6'h0; upstream_mask <= 6'h0; mode <= 2'd2; rr <= 1'b0;
            a_hold <= 32'h0; b_hold <= 32'h0; a_have <= 1'b0; b_have <= 1'b0; pending_ack <= 4'h0; armed <= 1'b0; program_done_r <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            mode            <= cfg_data[13:12];
            rr <= 1'b0; a_have <= 1'b0; b_have <= 1'b0; data_valid <= 1'b0; pending_ack <= 4'h0; armed <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_MODE:            mode            <= prog_word[1:0];
                PROG_ID_COMPLETE: begin program_done_r <= 1'b1; armed <= prog_word[0]; end
                default: ;
            endcase
        end else begin
            if (m_or) begin
                if (take_a) begin a_hold <= val_a; a_have <= 1'b1; end
                if (take_b) begin b_hold <= val_b; b_have <= 1'b1; end
                if (join_done) begin
                    out_buffer <= join_a | join_b;
                    data_valid <= 1'b1;
                    a_have <= 1'b0; b_have <= 1'b0;
                end
            end else if (grant_a || grant_b) begin
                out_buffer <= grant_a ? val_a : val_b;
                data_valid <= 1'b1;
                if (m_arb) rr <= grant_a;
            end
            if (offer_draining) data_valid <= 1'b0;
            pending_ack <= next_pending_ack;
            if (!program_in) program_done_r <= 1'b0;
        end
    end
endmodule
