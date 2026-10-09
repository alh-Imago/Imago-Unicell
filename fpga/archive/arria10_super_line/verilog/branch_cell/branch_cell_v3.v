// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v3.v — points.md #699: the same real config-off-shell
// change already applied to compare/latch/accumulator/ram/adder/
// sequencer, now applied to branch -- the most config-heavy core in
// this whole family (14 real fields, matching `#497`'s own fully-used
// 42-bit budget). Real, careful check made before writing this, not
// assumed: ALL 14 fields (upstream_dir, value_source_low/equal/high,
// fixed_value_low/equal/high, emit_low/equal/high, route_low/equal/
// high, rolling_mode) are read COMBINATIONALLY on every real
// `capture_compare` event, not just once at config time -- there is
// no genuine one-time-seed field here at all (unlike RAM's own real
// `load_data_valid`/`init_data`). All 14 move to the continuous
// group. This file changes NOTHING about branch's own real, genuine
// runtime state -- `ref_value`/`ref_valid` (the held reference,
// `#497`'s own real optimization), `out_buffer`/`data_valid`/
// `active_route`/`pending_ack`/`consumed` -- kept exactly where v1
// already keeps them, including the real release-on-reprogram
// behavior and the real `consumed` double-capture guard.
//
// The shell wiring this file needs (matching `unicell_super_v6.v`'s
// own real precedent): `cfg_data` must be wired to the shell's own
// continuously-valid `core_config`, NOT the transient `incoming_
// config` pulse v1 uses.
//
// WHY THIS IS SAFE, same real reasoning `compare_cell_v3.v`'s own
// header already established: arrived_n/s/e/w are already AND-gated
// with sel_active_branch at the shell level (unchanged) -- any_
// upstream_arrived is force-zero whenever this core isn't genuinely
// selected, regardless of what core_config happens to hold.
`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v3 #(
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

    // ── Real config fields, read CONTINUOUSLY off cfg_data (#699) --
    // no local latch at all for any of the 14. ──────────────────────
    wire [1:0] upstream_dir = cfg_data[1:0];
    wire value_source_low = cfg_data[2], value_source_equal = cfg_data[3], value_source_high = cfg_data[4];
    wire [6:0] fixed_value_low = cfg_data[11:5], fixed_value_equal = cfg_data[18:12], fixed_value_high = cfg_data[25:19];
    wire emit_low = cfg_data[26], emit_equal = cfg_data[27], emit_high = cfg_data[28];
    wire [3:0] route_low = cfg_data[32:29], route_equal = cfg_data[36:33], route_high = cfg_data[40:37];
    wire rolling_mode = cfg_data[41];

    // ── The held reference, per #497's own real optimization --
    // real, genuine runtime state, unchanged from v1. ───────────────
    reg [31:0] ref_value = 32'h0;
    reg        ref_valid = 1'b0;

    reg [31:0] out_buffer  = 32'h0;
    reg        data_valid  = 1'b0;
    reg [3:0]  active_route = 4'h0;
    reg [3:0]  pending_ack  = 4'h0;

    wire effective_freeze = freeze_in;

    wire sel_n = arrived_n && (upstream_dir == 2'd0);
    wire sel_s = arrived_s && (upstream_dir == 2'd1);
    wire sel_e = arrived_e && (upstream_dir == 2'd2);
    wire sel_w = arrived_w && (upstream_dir == 2'd3);
    wire any_upstream_arrived = sel_n | sel_s | sel_e | sel_w;
    wire [31:0] upstream_val = (sel_n ? data_in_n : 32'h0) |
                               (sel_s ? data_in_s : 32'h0) |
                               (sel_e ? data_in_e : 32'h0) |
                               (sel_w ? data_in_w : 32'h0);

    // Real, genuine runtime state -- the same real double-capture
    // guard v1 already found and fixed, unchanged.
    reg consumed = 1'b0;

    wire capture_reference = any_upstream_arrived && !consumed && !ref_valid && !effective_freeze;
    wire capture_compare   = any_upstream_arrived && !consumed && ref_valid && !data_valid && !effective_freeze;
    wire capture_now       = capture_reference || capture_compare;

    assign ack_out_n = capture_now && sel_n;
    assign ack_out_s = capture_now && sel_s;
    assign ack_out_e = capture_now && sel_e;
    assign ack_out_w = capture_now && sel_w;

    wire signed [31:0] signed_val = upstream_val;
    wire signed [31:0] signed_ref = ref_value;
    wire is_low   = (signed_val <  signed_ref);
    wire is_equal = (signed_val == signed_ref);
    wire is_high  = (signed_val >  signed_ref);

    wire outcome_value_source = (is_low  ? value_source_low  :
                                  is_equal ? value_source_equal :
                                             value_source_high);
    wire [6:0] outcome_fixed_value = (is_low  ? fixed_value_low  :
                                       is_equal ? fixed_value_equal :
                                                  fixed_value_high);
    wire outcome_emit = (is_low  ? emit_low  :
                          is_equal ? emit_equal :
                                     emit_high);
    wire [3:0] outcome_route = (is_low  ? route_low  :
                                 is_equal ? route_equal :
                                            route_high);

    wire [31:0] outcome_out_value = outcome_value_source ? {25'h0, outcome_fixed_value}
                                                           : upstream_val;

    wire want_to_offer = data_valid && !effective_freeze;
    wire targets_all_ready = (!active_route[0] || ready_in_n) &&
                             (!active_route[1] || ready_in_s) &&
                             (!active_route[2] || ready_in_e) &&
                             (!active_route[3] || ready_in_w);

    wire [3:0] ack_in_vec = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire any_fire = want_to_offer && (pending_ack == 4'h0) && targets_all_ready;
    wire [3:0] next_pending_ack = any_fire              ? (active_route & ~ack_in_vec) :
                                  (pending_ack != 4'h0)  ? (pending_ack  & ~ack_in_vec) :
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

    assign ready_out = !effective_freeze && !data_valid && ref_valid;
    assign status_data_valid = data_valid;

    always @(posedge clk) begin
        if (rst) begin
            ref_value            <= 32'h0;
            ref_valid            <= 1'b0;
            out_buffer           <= 32'h0;
            data_valid           <= 1'b0;
            active_route         <= 4'h0;
            pending_ack          <= 4'h0;
            consumed             <= 1'b0;
        end else if (cfg_valid) begin
            // All 14 real config fields are no longer latched here at
            // all (#699). Real release: reprogramming still discards
            // the held reference and any in-flight offer, matching
            // v1's own real, explicitly-flagged judgment call exactly.
            ref_value             <= 32'h0;
            ref_valid             <= 1'b0;
            data_valid            <= 1'b0;
            pending_ack           <= 4'h0;
            consumed              <= 1'b0;
        end else begin
            if (capture_reference) begin
                ref_value <= upstream_val;
                ref_valid <= 1'b1;
            end else if (capture_compare) begin
                if (outcome_emit) begin
                    out_buffer   <= outcome_out_value;
                    active_route <= outcome_route;
                    data_valid   <= 1'b1;
                end
                if (rolling_mode) begin
                    ref_value <= upstream_val;
                end
            end

            if (capture_now) begin
                consumed <= 1'b1;
            end else if (!any_upstream_arrived) begin
                consumed <= 1'b0;
            end

            if (offer_draining) begin
                data_valid <= 1'b0;
            end

            pending_ack <= next_pending_ack;
        end
    end

endmodule
