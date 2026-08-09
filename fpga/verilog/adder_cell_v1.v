// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v1.v — first real RTL draft of the arithmetic cell
// (points.md #248 task 2, #251). DRAFT — same status ram_cell_v1.v
// carried before Alan's review: shape confirmed in discussion, not yet
// silicon-measured. Only iverilog sim so far.
//
// WHAT THIS IS (points.md #251): Alan's direct correction to Claude's
// earlier "addon alongside the gate tree" proposal — an arithmetic cell
// REMOVES the core function, it doesn't run beside it. Checked against
// unicell_stripped_v1.v directly: computed_output is ONE case(topology)
// statement, a single compute path per cell, not several running in
// parallel. This cell reuses that compute cell's two-arrival A/B capture
// SHAPE (first arrival held as A, second arrival triggers the fire) and
// its cardinal/ready/ack handshake conventions, but the gate tree
// (topology field, g0-g9) is gone entirely — computed_output becomes
// adder_v1.v's real carry-chain sum of A+B instead. Same "genuinely
// different, dedicated cell type" category ram_cell_v1.v already
// established, not a config variant of unicell_stripped_v1.v.
//
// cfg_data[63:0] field map (first proposal, same convention as
// ram_cell_v1.v — NOT frozen):
//   [3:0]   downstream_mask  — one-hot(s), N/S/E/W, routing_mask convention
//   [7:4]   upstream_mask    — one-hot(s), N/S/E/W, same convention
//   [63:8]  reserved
//
// TWO-STAGE CAPTURE, mirroring unicell_stripped_v1.v's own can_fire
// gating: the first arrival (any direction with upstream_mask set)
// becomes A (a_reg/a_arrived) — captured whenever a_arrived is clear,
// REGARDLESS of whether a previous sum is still being offered (a_reg and
// out_buffer are separate registers, so this genuinely pipelines: a new
// operand pair can start capturing while the previous sum drains
// downstream). The second arrival becomes B and fires ONLY once the
// output slot is free (!data_valid) — mirrors both ram_cell_v1.v's own
// capture gate and unicell_stripped_v1.v's own "doubly full" comment
// (a_arrived=1 AND ready_bit=0 blocks can_fire there; the equivalent
// block here is a_arrived=1 AND data_valid=1, exposed combinationally
// via ready_out).
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

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

    input  wire         freeze_in,

    output wire         status_data_valid,   // out_buffer holds an unconsumed sum
    output wire         status_a_arrived     // A captured, awaiting B — debug only
);

    // ── State ───────────────────────────────────────────────────────────
    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  downstream_mask = 4'h0;
    reg [3:0]  upstream_mask   = 4'h0;
    reg [3:0]  pending_ack     = 4'h0;

    wire effective_freeze = freeze_in;

    // ── Upstream arrival selection — same independent-per-direction
    // OR-combine style ram_cell_v1.v/unicell_stripped_v1.v both use
    // (points.md #153). ──
    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // First arrival -> A. Independent of data_valid (see header note).
    wire capture_now = any_upstream_arrived && !a_arrived && !effective_freeze;

    // Second arrival -> B, fires the real adder. Gated on !data_valid —
    // the "doubly full" block.
    wire can_fire = any_upstream_arrived && a_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = (capture_now || can_fire) && sel_n;
    assign ack_out_s = (capture_now || can_fire) && sel_s;
    assign ack_out_e = (capture_now || can_fire) && sel_e;
    assign ack_out_w = (capture_now || can_fire) && sel_w;

    // ── The real arithmetic — adder_v1.v's carry chain, not a fabric
    // gate tree (points.md #245/#246/#251). A = a_reg (held), B = the
    // live second arrival (upstream_val at the can_fire cycle). ──
    wire [31:0] adder_sum;
    wire        adder_cout;   // unused for now — no overflow/carry-out port yet, flagged
    adder_v1 #(.WIDTH(32)) ADD (
        .a(a_reg), .b(upstream_val), .cin(1'b0),
        .sum(adder_sum), .cout(adder_cout)
    );

    // ── Downstream offering — identical shape to ram_cell_v1.v ─────────
    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    // Ready whenever NOT doubly full (a_arrived && data_valid) — mirrors
    // unicell_stripped_v1.v's own can_fire gating comment exactly.
    assign ready_out = !effective_freeze && !(a_arrived && data_valid);
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    always @(posedge clk) begin
        if (rst) begin
            a_reg           <= 32'h0;
            a_arrived       <= 1'b0;
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 4'h0;
            upstream_mask   <= 4'h0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[3:0];
            upstream_mask   <= cfg_data[7:4];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;  // fresh config clears any stale offer,
                                       // same discipline as ram_cell_v1.v
        end else begin
            if (can_fire) begin
                out_buffer <= adder_sum;
                data_valid <= 1'b1;
                a_arrived  <= 1'b0;   // A slot freed for the next pair
            end else if (capture_now) begin
                a_reg     <= upstream_val;
                a_arrived <= 1'b1;
            end

            // Independent of the branch above — capture_now (touches
            // a_reg/a_arrived) and offer_draining (touches data_valid)
            // can genuinely coincide in the same cycle (a fresh A arriving
            // the exact cycle a previous sum's ack lands). An earlier
            // draft chained this as an `else if` after capture_now, which
            // silently skipped the drain whenever that coincidence
            // happened — and since pending_ack had already reached 0 by
            // then, offer_draining never re-asserted, permanently
            // stranding data_valid=1 (confirmed: iverilog hung on the
            // SECOND operand pair every time, `wait(status_a_arrived)`
            // never resolving because ready_out stayed low forever).
            // can_fire and offer_draining, by contrast, provably cannot
            // coincide — can_fire requires !data_valid, and data_valid
            // stays 1 for the entire time pending_ack is nonzero — so no
            // real conflict exists between this block and the one above.
            if (offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;
        end
    end

endmodule
