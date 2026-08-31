// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_cell_v2.v — points.md #564: cloned from adder_cell_v1.v, zero
// behavioral change to the default path. Same optional external-
// storage mechanism proven on latch_cell_v2.v/ram_cell_v2.v, applied
// here with real, deliberate care around v1's own documented subtlety:
// `can_fire`/`capture_now` (if/else-if, mutually exclusive) and
// `offer_draining` (independent, applied after) -- v1's own header
// proves these provably cannot coincide, but the next-state formulas
// below are written to match v1's own real non-blocking "last
// statement wins" semantics regardless, not relying on that proof
// alone.
//
// Real, precise bit layout for the 79-bit external state word:
//   [3:0]   downstream_mask
//   [7:4]   upstream_mask
//   [8]     subtract_mode
//   [40:9]  a_reg (32 bits)
//   [41]    a_arrived
//   [73:42] out_buffer (32 bits)
//   [74]    data_valid
//   [78:75] pending_ack
`default_nettype none
`timescale 1ns / 1ps

module adder_cell_v2 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        EXTERNAL_STORAGE = 0
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
    output wire         status_a_arrived,

    // ── real, optional external-storage interface (points.md #564) ──
    input  wire [78:0]  ext_state_in,
    output wire [78:0]  ext_state_out
);

    reg [31:0] int_a_reg           = 32'h0;
    reg        int_a_arrived       = 1'b0;
    reg [31:0] int_out_buffer      = 32'h0;
    reg        int_data_valid      = 1'b0;
    reg [3:0]  int_downstream_mask = 4'h0;
    reg [3:0]  int_upstream_mask   = 4'h0;
    reg        int_subtract_mode   = 1'b0;
    reg [3:0]  int_pending_ack     = 4'h0;

    wire [3:0]  downstream_mask = EXTERNAL_STORAGE ? ext_state_in[3:0]   : int_downstream_mask;
    wire [3:0]  upstream_mask   = EXTERNAL_STORAGE ? ext_state_in[7:4]   : int_upstream_mask;
    wire        subtract_mode   = EXTERNAL_STORAGE ? ext_state_in[8]     : int_subtract_mode;
    wire [31:0] a_reg           = EXTERNAL_STORAGE ? ext_state_in[40:9]  : int_a_reg;
    wire        a_arrived       = EXTERNAL_STORAGE ? ext_state_in[41]    : int_a_arrived;
    wire [31:0] out_buffer      = EXTERNAL_STORAGE ? ext_state_in[73:42] : int_out_buffer;
    wire        data_valid      = EXTERNAL_STORAGE ? ext_state_in[74]    : int_data_valid;
    wire [3:0]  pending_ack     = EXTERNAL_STORAGE ? ext_state_in[78:75] : int_pending_ack;

    // ── Real computation logic, IDENTICAL to v1 ──
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

    // ── Real next-state computation, matching v1's own real non-
    // blocking "last statement wins" semantics EXACTLY: the if/else-if
    // (can_fire/capture_now) sets a TENTATIVE value for a_arrived/
    // out_buffer/data_valid, then the independent `if (offer_draining)`
    // can OVERRIDE data_valid specifically -- v1's own header proves
    // these provably cannot coincide, but this formula matches the
    // real non-blocking priority regardless, not relying on that proof
    // alone to be correct. ──
    wire [31:0] next_a_reg      = (rst) ? 32'h0 : (cfg_valid) ? a_reg : (capture_now) ? upstream_val : a_reg;
    wire        next_a_arrived  = (rst) ? 1'b0  : (cfg_valid) ? 1'b0  : (can_fire) ? 1'b0 : (capture_now) ? 1'b1 : a_arrived;
    wire [31:0] next_out_buffer = (rst) ? 32'h0 : (cfg_valid) ? out_buffer : (can_fire) ? adder_sum : out_buffer;
    wire        next_data_valid = (rst) ? 1'b0  :
                                   (cfg_valid) ? 1'b0 :
                                   (offer_draining) ? 1'b0 :
                                   (can_fire) ? 1'b1 : data_valid;
    wire [3:0]  next_downstream_mask = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[3:0] : downstream_mask;
    wire [3:0]  next_upstream_mask   = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[7:4] : upstream_mask;
    wire        next_subtract_mode   = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[8]  : subtract_mode;
    wire [3:0]  next_pending_ack_reg = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {next_pending_ack_reg, next_data_valid, next_out_buffer,
                             next_a_arrived, next_a_reg, next_subtract_mode,
                             next_upstream_mask, next_downstream_mask};

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_a_reg           <= next_a_reg;
                int_a_arrived       <= next_a_arrived;
                int_out_buffer      <= next_out_buffer;
                int_data_valid      <= next_data_valid;
                int_downstream_mask <= next_downstream_mask;
                int_upstream_mask   <= next_upstream_mask;
                int_subtract_mode   <= next_subtract_mode;
                int_pending_ack     <= next_pending_ack_reg;
            end
        end
    endgenerate

endmodule
