// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v3.v — points.md #699: the same real config-off-shell
// change already applied to compare/latch/accumulator (`#584`/`#587`/
// `#592`) and RAM (this same entry), now applied to adder. Simpler
// than RAM's own real case: all three of adder's own config fields
// (downstream_mask/upstream_mask/subtract_mode) are read EVERY cycle
// for live behavior (subtract_mode feeds `adder_b_in` combinationally,
// every relevant cycle) -- there is no genuine one-time SEED field
// here the way RAM's own `load_data_valid`/`init_data` were. This
// file changes NOTHING about real runtime state (`a_reg`/`a_arrived`/
// `out_buffer`/`data_valid`/`pending_ack`) -- kept exactly where v1
// already keeps them.
//
// The shell wiring this file needs (matching `unicell_super_v6.v`'s
// own real precedent): `cfg_data` must be wired to the shell's own
// continuously-valid `core_config`, NOT the transient `incoming_
// config` pulse v1 uses.
//
// WHY THIS IS SAFE, same real reasoning `compare_cell_v3.v`'s own
// header already established: arrived_n/s/e/w are already AND-gated
// with sel_active_adder at the shell level (unchanged) -- any_
// upstream_arrived is force-zero whenever this core isn't genuinely
// selected, regardless of what core_config happens to hold.
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v3 #(
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

    output wire         status_data_valid,
    output wire         status_a_arrived
);

    // ── Real config fields, read CONTINUOUSLY off cfg_data (#699) --
    // no local latch at all for these three. ──────────────────────
    wire [3:0] downstream_mask = cfg_data[3:0];
    wire [3:0] upstream_mask   = cfg_data[7:4];
    wire       subtract_mode   = cfg_data[8];

    // ── Real, genuine runtime state -- unchanged from v1. ──────────
    reg [31:0] a_reg           = 32'h0;
    reg        a_arrived       = 1'b0;
    reg [31:0] out_buffer      = 32'h0;
    reg        data_valid      = 1'b0;
    reg [3:0]  pending_ack     = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_n = arrived_n && upstream_mask[0];
    wire sel_s = arrived_s && upstream_mask[1];
    wire sel_e = arrived_e && upstream_mask[2];
    wire sel_w = arrived_w && upstream_mask[3];
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    wire capture_now = any_upstream_arrived && !a_arrived && !effective_freeze;
    wire can_fire = any_upstream_arrived && a_arrived && !data_valid && !effective_freeze;

    assign ack_out_n = (capture_now || can_fire) && sel_n;
    assign ack_out_s = (capture_now || can_fire) && sel_s;
    assign ack_out_e = (capture_now || can_fire) && sel_e;
    assign ack_out_w = (capture_now || can_fire) && sel_w;

    wire [31:0] adder_b_in = subtract_mode ? ~upstream_val : upstream_val;
    wire [31:0] adder_sum;
    wire        adder_cout;
    adder_v1 #(.WIDTH(32)) ADD (
        .a(a_reg), .b(adder_b_in), .cin(subtract_mode),
        .sum(adder_sum), .cout(adder_cout)
    );

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

    assign ready_out = !effective_freeze && !(a_arrived && data_valid);
    assign status_data_valid = data_valid;
    assign status_a_arrived  = a_arrived;

    always @(posedge clk) begin
        if (rst) begin
            a_reg           <= 32'h0;
            a_arrived       <= 1'b0;
            out_buffer      <= 32'h0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else if (cfg_valid) begin
            // downstream_mask/upstream_mask/subtract_mode are no
            // longer latched here at all (#699) -- fresh config still
            // clears any real, in-flight runtime state, same
            // discipline as v1.
            a_arrived       <= 1'b0;
            data_valid      <= 1'b0;
            pending_ack     <= 4'h0;
        end else begin
            if (can_fire) begin
                out_buffer <= adder_sum;
                data_valid <= 1'b1;
                a_arrived  <= 1'b0;
            end else if (capture_now) begin
                a_reg     <= upstream_val;
                a_arrived <= 1'b1;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end
            pending_ack <= next_pending_ack;
        end
    end

endmodule
