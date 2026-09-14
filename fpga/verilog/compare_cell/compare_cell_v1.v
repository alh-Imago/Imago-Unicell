// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// compare_cell_v1.v — the comparator core for the sentinel's discrete-
// cell decomposition (points.md #291/#293/#294). A genuine new CORE,
// per `#253`'s SHELL/CORE model — same shell every other cell has, a
// comparison core instead of a pass-through latch (`ram_cell_v1.v`)
// or an addition (`adder_cell_v1.v`).
//
// SIMPLER than `accumulator_cell_v1.v`, deliberately, for a real
// reason: the accumulator's internal total must NEVER drop an event —
// losing a real +1/-1 is an unrecoverable correctness bug. This cell
// only ever cares about the CURRENT diff value — if a newer reading
// overwrites one that hasn't been read downstream yet, nothing is
// genuinely lost, since the next accumulator update produces another
// one anyway. So this uses the plain, already-proven single-capture
// shell pattern (`ram_cell_v1.v`'s own shape, doubly-full guard
// included), not the accumulator's own special "never block capture"
// adaptation.
//
// CORE: `signed_input >= threshold`, a genuine two's-complement
// comparison (matching the same signed arithmetic the accumulator
// already produces). The threshold is a CONFIGURED value (set at
// config time, like `chain_length` itself in the compiler-supplied
// sense) — not a second cardinal-port operand — so this is a
// single-arrival cell, not a two-arrival one like `adder_cell_v1.v`.
//
// The boolean result is offered downstream as `data_out_x[0]`
// (1 = input >= threshold, 0 = not) — same "LSB of the 32-bit data
// bus carries a flag" convention already usable anywhere else in this
// project a boolean needs to travel over an ordinary cardinal link.
//
// cfg_data[63:0] field map:
//   [3:0]   downstream_mask   — where the boolean result is offered
//   [7:4]   upstream_mask     — where the value to compare arrives from
//   [39:8]  threshold         — the configured reference (32-bit signed)
//   [63:40] reserved
`default_nettype none
`timescale 1ns / 1ps

module compare_cell_v1 #(
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

    output wire         status_data_valid
);

    reg [3:0]  downstream_mask = 4'h0;
    reg [3:0]  upstream_mask   = 4'h0;
    reg signed [31:0] threshold = 32'sh0;

    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;
    reg [3:0]  pending_ack = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire signed [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                                      (sel_s ? data_in_s : 32'h0) |
                                      (sel_e ? data_in_e : 32'h0) |
                                      (sel_w ? data_in_w : 32'h0);

    // Same doubly-full guard as ram_cell_v1.v/adder_cell_v1.v — don't
    // capture a new value while the previous comparison result is
    // still undrained.
    wire capture_now = any_upstream_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    // ── THE CORE — a genuine two's-complement comparison ────────────────
    wire result_bit = (upstream_val >= threshold);

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

    assign ready_out = !effective_freeze && !data_valid;
    assign status_data_valid = data_valid;

    always @(posedge clk) begin
        if (rst) begin
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
            downstream_mask <= 4'h0;
            upstream_mask   <= 4'h0;
            threshold       <= 32'sh0;
        end else if (cfg_valid) begin
            downstream_mask <= cfg_data[3:0];
            upstream_mask   <= cfg_data[7:4];
            threshold       <= cfg_data[39:8];
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            if (capture_now) begin
                out_buffer <= {31'h0, result_bit};
                data_valid <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
