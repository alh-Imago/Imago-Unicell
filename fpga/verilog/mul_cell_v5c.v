// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// mul_cell_v5c.v — points.md #853: real, SEQUENTIAL two-phase
// delivery of the internal 64-bit product's high half, correcting a
// first, discarded design (a parallel second routing group) that Alan
// caught as violating this project's own real discipline: a value
// leaving a cell has to obey the same rules as everywhere else, not
// get a second, special-cased path. Here there is only ONE result
// path, reused twice -- exactly like every other core's own single
// downstream_mask/pending_ack mechanism, run through its normal cycle
// twice instead of once. mul_cell_v4c.v itself is UNCHANGED.
//
// Real, honest design, per Alan's own direct correction:
//   - A new `wide_mode` config bit selects between v4c's own existing
//     behaviour (0: low half only, high half silently discarded,
//     single delivery cycle -- byte-for-byte v4c) and the new
//     two-phase behaviour (1: low half delivered and fully acked
//     first, THEN the high half loaded into the SAME out_buffer and
//     delivered through the SAME downstream_mask/pending_ack
//     mechanism a second time).
//   - Real, necessary consequence, stated directly by Alan: this cell
//     cannot accept a new pair of operands until BOTH deliveries are
//     complete in wide_mode -- `ready_out` (and the early-capture
//     overlap v4c's own single-value design allows) are both
//     genuinely blocked for the WHOLE two-phase window, not just the
//     first delivery. When wide_mode=0, v4c's own existing overlap-
//     friendly behaviour is completely unchanged.
//   - Real, deliberate reuse: keeping ONE shared downstream_mask means
//     full routing flexibility is preserved -- a real, stated reason
//     to prefer this over the discarded parallel-path design, which
//     would have split routing_mask bits between two destinations and
//     genuinely reduced where the result could go.
//
// cfg_data[63:0] field map (atomic boot-load path):
//   [5:0]   downstream_mask  — one-hot(s), N/S/E/W real + 2 reserved
//   [11:6]  upstream_mask    — one-hot(s), N/S/E/W real + 2 reserved
//   [12]    wide_mode        — NEW: 0=v4c behaviour (low only), 1=two-phase (low then high)
//   [63:13] reserved         — 51 bits

`default_nettype none
`timescale 1ns / 1ps

module mul_cell_v5c #(
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
    output wire         status_a_arrived
);

    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    // Real, necessary fix, found by testbench: mul_result_hi is purely
    // combinational, valid only at the instant operands are live on
    // upstream_val. By the time the phase-2 transition happens (long
    // after the operand pulses dropped), it silently reads zero.
    // Latched here at the SAME real moment out_buffer captures the low
    // half, exactly the same discipline already applied to that value.
    reg [31:0] captured_hi     = 32'h0;
    reg        data_valid      = 1'b0;
    reg [5:0]  downstream_mask = 6'h0;
    reg [5:0]  upstream_mask   = 6'h0;
    reg [3:0]  pending_ack     = 4'h0;
    reg        armed           = 1'b0;
    reg        wide_mode       = 1'b0;
    reg        delivering_hi   = 1'b0;
    // Real, necessary fix, found by testbench: without this, the
    // ORIGINAL any_fire mechanism (unchanged from v4c) independently
    // re-arms pending_ack on its own the moment it reads 0 while
    // data_valid is still high -- racing ahead of, and winning
    // against, the explicit phase-transition logic below, without
    // ever setting delivering_hi or reloading out_buffer. This makes
    // any_fire a genuine one-shot per round; phase 2's own re-arm goes
    // EXCLUSIVELY through start_hi_phase's explicit override.
    reg        phase1_offered  = 1'b0;

    wire effective_freeze = freeze_in;
    wire effective_armed  = armed && active;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // Real, necessary block, per Alan's own direct correction: in
    // wide_mode, NO new operand may be captured -- not even the
    // early-capture overlap v4c's own single-value design otherwise
    // allows -- until BOTH deliveries of the current result are done.
    // When wide_mode=0, this is always false, and v4c's own existing
    // overlap-friendly behaviour is completely unchanged.
    wire block_for_wide = wide_mode && data_valid;

    wire capture_now = any_upstream_arrived && !a_arrived && !effective_freeze &&
                       effective_armed && !program_in && !block_for_wide;
    wire can_fire = any_upstream_arrived && a_arrived && !data_valid && !effective_freeze &&
                    effective_armed && !program_in;

    assign ack_out_n = (capture_now || can_fire) && sel_n;
    assign ack_out_s = (capture_now || can_fire) && sel_s;
    assign ack_out_e = (capture_now || can_fire) && sel_e;
    assign ack_out_w = (capture_now || can_fire) && sel_w;

    // ── The real arithmetic — the one real, substantive difference
    // from adder_cell_v4.v. Purely combinational, zero clock cycles
    // of latency (confirmed directly before this promotion). Only the
    // low 32 bits are offered here, matching LLVM's own real `mul`
    // truncation semantics. ──
    wire [63:0] mul_product;
    bitwise_multiplier_32bit MUL (
        .A(a_reg), .B(upstream_val), .Product(mul_product)
    );
    wire [31:0] mul_result    = mul_product[31:0];
    wire [31:0] mul_result_hi = mul_product[63:32];

    wire want_to_offer = data_valid && !effective_freeze && effective_armed;
    wire targets_all_ready = (!downstream_mask[0] || ready_in_n) &&
                             (!downstream_mask[1] || ready_in_s) &&
                             (!downstream_mask[2] || ready_in_e) &&
                             (!downstream_mask[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && !phase1_offered && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (downstream_mask[3:0] & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack     & ~ack_in_vec) :
                                                           pending_ack;
    wire offer_draining = (pending_ack != 4'h0) && (next_pending_ack == 4'h0);
    // Real, necessary phase logic: when the current delivery just
    // fully drained, wide_mode is on, and we haven't yet delivered the
    // high half this round, that's a real phase transition, not a
    // genuine finish -- computed here (not left to the always block
    // alone) so both the re-armed pending_ack AND the reloaded
    // out_buffer land on the exact same real cycle, with no one-cycle
    // window where pending_ack reads 0 while data_valid is still high
    // (the real bug an earlier, discarded parallel-path design hit).
    wire start_hi_phase = offer_draining && wide_mode && !delivering_hi;
    wire genuinely_done = offer_draining && !start_hi_phase;

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    // ── points.md #724: NO addon chain here at all — the carrier
    // already provides one, shared across whichever core is active. ──
    assign data_out_n = out_buffer;
    assign data_out_s = out_buffer;
    assign data_out_e = out_buffer;
    assign data_out_w = out_buffer;

    assign ready_out = effective_armed && !effective_freeze && !(a_arrived && data_valid) && !block_for_wide;
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    // points.md #724: subtract_mode's own old PROG_ID slot (3'd2)
    // removed entirely (no real equivalent for multiply); addon_
    // config keeps its own old ID (3'd3) rather than renumbering.
    localparam [2:0] PROG_ID_DOWNSTREAM_MASK = 3'd0;
    localparam [2:0] PROG_ID_UPSTREAM_MASK   = 3'd1;
    localparam [2:0] PROG_ID_WIDE_MODE       = 3'd2;
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
            a_reg           <= 32'h0;
            a_arrived       <= 1'b0;
            out_buffer      <= 32'h0;
            captured_hi     <= 32'h0;
            data_valid      <= 1'b0;
            downstream_mask <= 6'h0;
            upstream_mask   <= 6'h0;
            pending_ack     <= 4'h0;
            armed           <= 1'b0;
            wide_mode       <= 1'b0;
            delivering_hi   <= 1'b0;
            phase1_offered  <= 1'b0;
            program_done_r  <= 1'b0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[5:0];
            upstream_mask   <= cfg_data[11:6];
            wide_mode       <= cfg_data[12];
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            delivering_hi   <= 1'b0;
            phase1_offered  <= 1'b0;
            armed           <= 1'b1;
        end else if (programming_active) begin
            case (prog_id)
                PROG_ID_DOWNSTREAM_MASK: downstream_mask <= prog_word[5:0];
                PROG_ID_UPSTREAM_MASK:   upstream_mask   <= prog_word[5:0];
                PROG_ID_WIDE_MODE:       wide_mode       <= prog_word[0];
                PROG_ID_COMPLETE: begin
                    program_done_r <= 1'b1;
                    armed          <= prog_word[0];
                end
                default: ;
            endcase
        end else begin
            if (can_fire) begin
                out_buffer     <= mul_result;
                captured_hi    <= mul_result_hi;
                data_valid     <= 1'b1;
                delivering_hi  <= 1'b0;
                phase1_offered <= 1'b0;
                a_arrived      <= 1'b0;
            end else begin
                if (capture_now) begin
                    a_reg     <= upstream_val;
                    a_arrived <= 1'b1;
                end
                // Real, necessary two-outcome branch, kept in its own
                // `else` alongside can_fire (not chained with
                // capture_now) so the legitimate same-cycle overlap
                // v4c already allows (a new operand arriving while the
                // current result drains) is preserved when wide_mode
                // is off, and cleanly blocked by `block_for_wide` when
                // it's on -- this branch only decides what happens to
                // THIS round's own delivery, not whether a new one may
                // start.
                if (start_hi_phase) begin
                    out_buffer    <= captured_hi;
                    delivering_hi <= 1'b1;
                    // pending_ack itself is re-armed below, in the
                    // shared assignment -- see start_hi_phase's own
                    // use there. data_valid deliberately stays 1.
                end else if (genuinely_done) begin
                    data_valid <= 1'b0;
                end
            end

            // Real, necessary re-arm: on a phase transition, pending_ack
            // gets downstream_mask fresh THIS cycle (not next_pending_ack,
            // which would read 0) -- the exact fix for the one-cycle
            // "reads 0 while still valid" window that broke the
            // discarded parallel-path design.
            pending_ack <= start_hi_phase ? downstream_mask[3:0] : next_pending_ack;
            if (any_fire) phase1_offered <= 1'b1;

            if (!program_in) program_done_r <= 1'b0;
        end
    end

endmodule
