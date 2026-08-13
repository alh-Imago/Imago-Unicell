// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v1.v — first real RTL of the sentinel's discrete-
// cell decomposition (points.md #291/#293). A genuine new CORE, per
// `#253`'s SHELL/CORE model — same shell every other cell has, a
// different capture-and-compute pattern (same lineage as ram_cell_v1's
// "capture once" and adder_cell_v1's "capture a matched pair").
//
// THE MECHANISM: Alan's own recollection of the old fat cell's
// `one_shot` design (`unicell64_v3.v`'s `one_shot`/`one_shot_fired`,
// `new_data = !(one_shot && one_shot_fired) && (bus_hit && a_arrived)`)
// — hold an operand permanently rather than clearing it after one fire,
// so every new matching arrival fires again immediately. Translated
// from the old BUS-based architecture (deliberately not ported as-is —
// this project moved away from shared-bus contention, `#153`'s own
// history) into the current cardinal/point-to-point model: this cell
// holds its OWN running total permanently, and DIRECTION (not arrival
// order) determines the operation — arrivals on `inc_dir` always mean
// +1, arrivals on `dec_dir` always mean -1. No "first vs second
// arrival" pairing at all, unlike `adder_cell_v1.v`'s own two-arrival
// shape, which this deliberately does NOT reuse (a real structural
// mismatch, confirmed in discussion before building: the sentinel
// needs a continuously-live running total, not one-shot matched pairs).
//
// A REAL, DELIBERATE PROTOCOL ADAPTATION, worth being explicit about:
// unlike every prior core (which offers a discrete value that gets
// consumed and the cell goes empty), this cell represents a
// CONTINUOUSLY-LIVE status — there is always a "current total," never
// an empty state. The internal `accumulator` register updates
// IMMEDIATELY on every capture, unconditionally — a slow downstream
// reader must NEVER cause a lost or corrupted count, that would be a
// genuine correctness bug, not a pipelining nicety. The OFFERED
// snapshot (`out_buffer`) only refreshes when the shell is free to
// accept a new one (matching every other core's own "offered data
// stays stable until acked" protocol) — meaning a slow reader sees the
// LATEST value, not every intermediate step, which is correct for a
// status register, not a data stream.
//
// THE SIGN BIT IS FREE: the accumulator is genuine two's-complement
// arithmetic (a real add of +1 or -1 each cycle), so its own MSB
// directly indicates negative — no separate comparator needed for the
// sentinel's `diff<0` check, confirmed correct, not assumed (see
// `status_negative` below).
//
// cfg_data[63:0] field map:
//   [3:0]   inc_dir           — one-hot direction, arrivals here = +1
//   [7:4]   dec_dir           — one-hot direction, arrivals here = -1
//   [11:8]  downstream_mask   — where the current total is offered
//   [63:12] reserved
`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         freeze_in,

    output wire         ready_out,   // real fix (found via #295's own 3-cell chain test): this port
                                      // was missing entirely, unlike every other cell here. Since
                                      // this cell's own capture is UNCONDITIONAL by design (never
                                      // blocked, see header), ready_out is simply "not frozen" —
                                      // always genuinely ready, matching the real truth of this cell's
                                      // own behavior, not a placeholder.
    output wire         status_negative   // free sign-bit tap — diff<0, no separate comparator needed
);

    reg [3:0]  inc_dir         = 4'h0;
    reg [3:0]  dec_dir         = 4'h0;
    reg [3:0]  downstream_mask = 4'h0;

    reg signed [WIDTH-1:0] accumulator = 0;   // ALWAYS correct, unconditional update, never blocked
    reg signed [WIDTH-1:0] out_buffer  = 0;   // the OFFERED snapshot — stable while a transfer is in flight
    reg data_valid = 1'b0;   // set once at config, stays 1 forever — a continuously-live status,
                              // never goes back to "empty" the way a one-shot cell's own data_valid does
    reg [3:0] pending_ack = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_inc_n = arrived_n && inc_dir[0];
    wire sel_inc_s = arrived_s && inc_dir[1];
    wire sel_inc_e = arrived_e && inc_dir[2];
    wire sel_inc_w = arrived_w && inc_dir[3];
    wire capture_inc = (sel_inc_n | sel_inc_s | sel_inc_e | sel_inc_w) && !effective_freeze;

    wire sel_dec_n = arrived_n && dec_dir[0];
    wire sel_dec_s = arrived_s && dec_dir[1];
    wire sel_dec_e = arrived_e && dec_dir[2];
    wire sel_dec_w = arrived_w && dec_dir[3];
    wire capture_dec = (sel_dec_n | sel_dec_s | sel_dec_e | sel_dec_w) && !effective_freeze;

    // Ack fires immediately on capture, same convention as every other
    // core here — UNCONDITIONAL, never gated by the offer side (the
    // whole point: a slow downstream reader must never block or drop a
    // real increment/decrement event).
    assign ack_out_n = (sel_inc_n || sel_dec_n) && !effective_freeze;
    assign ack_out_s = (sel_inc_s || sel_dec_s) && !effective_freeze;
    assign ack_out_e = (sel_inc_e || sel_dec_e) && !effective_freeze;
    assign ack_out_w = (sel_inc_w || sel_dec_w) && !effective_freeze;

    // Both directions arriving the SAME cycle nets to zero change — a
    // genuine, correctly-handled case (a feed and a collect landing
    // together), not an error.
    wire signed [WIDTH-1:0] delta = (capture_inc && !capture_dec) ?  {{(WIDTH-1){1'b0}}, 1'b1} :
                                     (capture_dec && !capture_inc) ? -{{(WIDTH-1){1'b0}}, 1'b1} :
                                                                      {WIDTH{1'b0}};
    wire signed [WIDTH-1:0] next_accumulator = accumulator + delta;

    // ── Downstream offering — same shell shape as every other core,
    // but out_buffer only refreshes when free (pending_ack==0), per
    // this cell's own deliberate protocol adaptation (see header). ──
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

    assign fire_n = pending_ack[0];
    assign fire_s = pending_ack[1];
    assign fire_e = pending_ack[2];
    assign fire_w = pending_ack[3];

    assign data_out_n = out_buffer[31:0];
    assign data_out_s = out_buffer[31:0];
    assign data_out_e = out_buffer[31:0];
    assign data_out_w = out_buffer[31:0];

    assign status_negative = out_buffer[WIDTH-1];   // the free sign-bit tap
    assign ready_out = !effective_freeze;   // always genuinely ready — capture is never blocked

    always @(posedge clk) begin
        if (rst) begin
            accumulator     <= 0;
            out_buffer      <= 0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            inc_dir         <= 4'h0;
            dec_dir         <= 4'h0;
            downstream_mask <= 4'h0;
        end else if (cfg_valid) begin
            inc_dir         <= cfg_data[3:0];
            dec_dir         <= cfg_data[7:4];
            downstream_mask <= cfg_data[11:8];
            accumulator     <= 0;
            out_buffer      <= 0;
            data_valid      <= 1'b1;   // live from the first cycle after config — always a "current" value
            pending_ack     <= 4'h0;
        end else begin
            // The internal total — ALWAYS updates, unconditionally,
            // regardless of the offer side's own state.
            if (capture_inc || capture_dec) begin
                accumulator <= next_accumulator;
            end

            // The OFFERED snapshot — only refreshes when free to accept
            // a new one (pending_ack==0), matching every other core's
            // "offered data stays stable until acked" protocol. Uses
            // `next_accumulator` directly so a capture on THIS same
            // cycle is correctly reflected immediately, not one cycle
            // late.
            if (pending_ack == 4'h0) begin
                out_buffer <= next_accumulator;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
