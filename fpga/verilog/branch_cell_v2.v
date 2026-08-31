// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// branch_cell_v2.v — points.md #564: cloned from branch_cell_v1.v,
// zero behavioral change to the default path. Same optional external-
// storage mechanism, applied with extra care to this core's own real,
// richest field layout and most complex update logic (held-reference
// two-phase capture, rolling mode, the documented real `consumed`
// double-capture bugfix -- see v1's own header for the full real
// history of each).
//
// Real, precise bit layout for the 117-bit external state word:
//   [1:0]    upstream_dir
//   [2]      value_source_low
//   [3]      value_source_equal
//   [4]      value_source_high
//   [11:5]   fixed_value_low (7)
//   [18:12]  fixed_value_equal (7)
//   [25:19]  fixed_value_high (7)
//   [26]     emit_low
//   [27]     emit_equal
//   [28]     emit_high
//   [32:29]  route_low (4)
//   [36:33]  route_equal (4)
//   [40:37]  route_high (4)
//   [41]     rolling_mode
//   [73:42]  ref_value (32)
//   [74]     ref_valid
//   [106:75] out_buffer (32)
//   [107]    data_valid
//   [111:108] active_route (4)
//   [115:112] pending_ack (4)
//   [116]    consumed
`default_nettype none
`timescale 1ns / 1ps

module branch_cell_v2 #(
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

    // ── real, optional external-storage interface (points.md #564) ──
    input  wire [116:0] ext_state_in,
    output wire [116:0] ext_state_out
);

    reg [1:0] int_upstream_dir = 2'h0;
    reg int_value_source_low = 1'b0, int_value_source_equal = 1'b0, int_value_source_high = 1'b0;
    reg [6:0] int_fixed_value_low = 7'h0, int_fixed_value_equal = 7'h0, int_fixed_value_high = 7'h0;
    reg int_emit_low = 1'b0, int_emit_equal = 1'b0, int_emit_high = 1'b0;
    reg [3:0] int_route_low = 4'h0, int_route_equal = 4'h0, int_route_high = 4'h0;
    reg int_rolling_mode = 1'b0;
    reg [31:0] int_ref_value = 32'h0;
    reg        int_ref_valid = 1'b0;
    reg [31:0] int_out_buffer  = 32'h0;
    reg        int_data_valid  = 1'b0;
    reg [3:0]  int_active_route = 4'h0;
    reg [3:0]  int_pending_ack  = 4'h0;
    reg int_consumed = 1'b0;

    wire [1:0] upstream_dir = EXTERNAL_STORAGE ? ext_state_in[1:0] : int_upstream_dir;
    wire value_source_low   = EXTERNAL_STORAGE ? ext_state_in[2]   : int_value_source_low;
    wire value_source_equal = EXTERNAL_STORAGE ? ext_state_in[3]   : int_value_source_equal;
    wire value_source_high  = EXTERNAL_STORAGE ? ext_state_in[4]   : int_value_source_high;
    wire [6:0] fixed_value_low   = EXTERNAL_STORAGE ? ext_state_in[11:5]  : int_fixed_value_low;
    wire [6:0] fixed_value_equal = EXTERNAL_STORAGE ? ext_state_in[18:12] : int_fixed_value_equal;
    wire [6:0] fixed_value_high  = EXTERNAL_STORAGE ? ext_state_in[25:19] : int_fixed_value_high;
    wire emit_low   = EXTERNAL_STORAGE ? ext_state_in[26] : int_emit_low;
    wire emit_equal = EXTERNAL_STORAGE ? ext_state_in[27] : int_emit_equal;
    wire emit_high  = EXTERNAL_STORAGE ? ext_state_in[28] : int_emit_high;
    wire [3:0] route_low   = EXTERNAL_STORAGE ? ext_state_in[32:29] : int_route_low;
    wire [3:0] route_equal = EXTERNAL_STORAGE ? ext_state_in[36:33] : int_route_equal;
    wire [3:0] route_high  = EXTERNAL_STORAGE ? ext_state_in[40:37] : int_route_high;
    wire rolling_mode = EXTERNAL_STORAGE ? ext_state_in[41] : int_rolling_mode;
    wire [31:0] ref_value = EXTERNAL_STORAGE ? ext_state_in[73:42] : int_ref_value;
    wire ref_valid = EXTERNAL_STORAGE ? ext_state_in[74] : int_ref_valid;
    wire [31:0] out_buffer = EXTERNAL_STORAGE ? ext_state_in[106:75] : int_out_buffer;
    wire data_valid = EXTERNAL_STORAGE ? ext_state_in[107] : int_data_valid;
    wire [3:0] active_route = EXTERNAL_STORAGE ? ext_state_in[111:108] : int_active_route;
    wire [3:0] pending_ack  = EXTERNAL_STORAGE ? ext_state_in[115:112] : int_pending_ack;
    wire consumed = EXTERNAL_STORAGE ? ext_state_in[116] : int_consumed;

    // ── Real computation logic, IDENTICAL to v1 ──
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

    // ── Real next-state computation, matching v1's own real, sequential
    // multi-condition update logic EXACTLY -- including the real,
    // independent (not mutually exclusive) outcome_emit/rolling_mode
    // updates within the capture_compare branch, and offer_draining's
    // own independent override of data_valid (provably non-conflicting
    // with capture_compare's own data_valid set, per v1's own real
    // capture-gating logic -- but the formula below matches real non-
    // blocking priority regardless, not relying on that proof alone). ──
    wire [31:0] next_ref_value_reg =
        (rst) ? 32'h0 :
        (cfg_valid) ? 32'h0 :
        (capture_reference) ? upstream_val :
        (capture_compare && rolling_mode) ? upstream_val :
        ref_value;

    wire next_ref_valid_reg = (rst) ? 1'b0 : (cfg_valid) ? 1'b0 : (capture_reference) ? 1'b1 : ref_valid;

    wire [31:0] next_out_buffer_reg =
        (rst) ? 32'h0 : (cfg_valid) ? 32'h0 :
        (capture_compare && outcome_emit) ? outcome_out_value : out_buffer;

    wire [3:0] next_active_route_reg =
        (rst) ? 4'h0 : (cfg_valid) ? 4'h0 :
        (capture_compare && outcome_emit) ? outcome_route : active_route;

    wire next_data_valid_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? 1'b0 :
        (offer_draining) ? 1'b0 :
        (capture_compare && outcome_emit) ? 1'b1 : data_valid;

    wire next_consumed_reg =
        (rst) ? 1'b0 :
        (cfg_valid) ? 1'b0 :
        (capture_now) ? 1'b1 :
        (!any_upstream_arrived) ? 1'b0 : consumed;

    wire [1:0] next_upstream_dir_reg       = (rst) ? 2'h0 : (cfg_valid) ? cfg_data[1:0]   : upstream_dir;
    wire next_value_source_low_reg         = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[2]     : value_source_low;
    wire next_value_source_equal_reg       = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[3]     : value_source_equal;
    wire next_value_source_high_reg        = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[4]     : value_source_high;
    wire [6:0] next_fixed_value_low_reg    = (rst) ? 7'h0 : (cfg_valid) ? cfg_data[11:5]  : fixed_value_low;
    wire [6:0] next_fixed_value_equal_reg  = (rst) ? 7'h0 : (cfg_valid) ? cfg_data[18:12] : fixed_value_equal;
    wire [6:0] next_fixed_value_high_reg   = (rst) ? 7'h0 : (cfg_valid) ? cfg_data[25:19] : fixed_value_high;
    wire next_emit_low_reg                 = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[26]    : emit_low;
    wire next_emit_equal_reg               = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[27]    : emit_equal;
    wire next_emit_high_reg                = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[28]    : emit_high;
    wire [3:0] next_route_low_reg          = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[32:29] : route_low;
    wire [3:0] next_route_equal_reg        = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[36:33] : route_equal;
    wire [3:0] next_route_high_reg         = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[40:37] : route_high;
    wire next_rolling_mode_reg             = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[41]    : rolling_mode;
    wire [3:0] next_pending_ack_reg        = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {
        next_consumed_reg, next_pending_ack_reg, next_active_route_reg,
        next_data_valid_reg, next_out_buffer_reg, next_ref_valid_reg, next_ref_value_reg,
        next_rolling_mode_reg, next_route_high_reg, next_route_equal_reg, next_route_low_reg,
        next_emit_high_reg, next_emit_equal_reg, next_emit_low_reg,
        next_fixed_value_high_reg, next_fixed_value_equal_reg, next_fixed_value_low_reg,
        next_value_source_high_reg, next_value_source_equal_reg, next_value_source_low_reg,
        next_upstream_dir_reg
    };

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_upstream_dir       <= next_upstream_dir_reg;
                int_value_source_low   <= next_value_source_low_reg;
                int_value_source_equal <= next_value_source_equal_reg;
                int_value_source_high  <= next_value_source_high_reg;
                int_fixed_value_low    <= next_fixed_value_low_reg;
                int_fixed_value_equal  <= next_fixed_value_equal_reg;
                int_fixed_value_high   <= next_fixed_value_high_reg;
                int_emit_low            <= next_emit_low_reg;
                int_emit_equal          <= next_emit_equal_reg;
                int_emit_high           <= next_emit_high_reg;
                int_route_low            <= next_route_low_reg;
                int_route_equal          <= next_route_equal_reg;
                int_route_high           <= next_route_high_reg;
                int_rolling_mode         <= next_rolling_mode_reg;
                int_ref_value             <= next_ref_value_reg;
                int_ref_valid             <= next_ref_valid_reg;
                int_out_buffer            <= next_out_buffer_reg;
                int_data_valid            <= next_data_valid_reg;
                int_active_route          <= next_active_route_reg;
                int_pending_ack           <= next_pending_ack_reg;
                int_consumed              <= next_consumed_reg;
            end
        end
    endgenerate

endmodule
