// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// ram_cell_v2.v — points.md #563: cloned from ram_cell_v1.v, zero
// behavioral change to the default path. Same genuinely optional
// external-storage mechanism proven on latch_cell_v2.v, applied to a
// deliberately different real width (46 bits here vs. latch's 23) --
// proving the pattern generalizes, not just working for one size.
//
// Real, precise bit layout for the 46-bit external state word:
//   [3:0]   downstream_mask
//   [7:4]   upstream_mask
//   [8]     fixed_mode
//   [9]     data_valid
//   [41:10] data_reg (32 bits)
//   [45:42] pending_ack
`default_nettype none
`timescale 1ns / 1ps

module ram_cell_v2 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        EXTERNAL_STORAGE = 0
) (
    input  wire        clk,
    input  wire         rst,

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

    // ── real, optional external-storage interface (points.md #563) ──
    input  wire [45:0]  ext_state_in,
    output wire [45:0]  ext_state_out
);

    reg [3:0]  int_downstream_mask = 4'h0;
    reg [3:0]  int_upstream_mask   = 4'h0;
    reg        int_fixed_mode      = 1'b0;
    reg        int_data_valid      = 1'b0;
    reg [31:0] int_data_reg        = 32'h0;
    reg [3:0]  int_pending_ack     = 4'h0;

    wire [3:0]  downstream_mask = EXTERNAL_STORAGE ? ext_state_in[3:0]   : int_downstream_mask;
    wire [3:0]  upstream_mask   = EXTERNAL_STORAGE ? ext_state_in[7:4]   : int_upstream_mask;
    wire        fixed_mode      = EXTERNAL_STORAGE ? ext_state_in[8]     : int_fixed_mode;
    wire        data_valid      = EXTERNAL_STORAGE ? ext_state_in[9]     : int_data_valid;
    wire [31:0] data_reg        = EXTERNAL_STORAGE ? ext_state_in[41:10] : int_data_reg;
    wire [3:0]  pending_ack     = EXTERNAL_STORAGE ? ext_state_in[45:42] : int_pending_ack;

    // ── Real computation logic, IDENTICAL to v1 ──
    wire effective_freeze = freeze_in;

    wire ram_sel_n = arrived_n && upstream_mask[0];
    wire ram_sel_s = arrived_s && upstream_mask[1];
    wire ram_sel_e = arrived_e && upstream_mask[2];
    wire ram_sel_w = arrived_w && upstream_mask[3];
    wire ram_any_upstream_arrived = ram_sel_n | ram_sel_s | ram_sel_e | ram_sel_w;
    wire [31:0] upstream_val = (ram_sel_n ? data_in_n : 32'h0) |
                               (ram_sel_s ? data_in_s : 32'h0) |
                               (ram_sel_e ? data_in_e : 32'h0) |
                               (ram_sel_w ? data_in_w : 32'h0);

    wire capture_now = ram_any_upstream_arrived && !data_valid && !fixed_mode && !effective_freeze;

    assign ack_out_n = capture_now && ram_sel_n;
    assign ack_out_s = capture_now && ram_sel_s;
    assign ack_out_e = capture_now && ram_sel_e;
    assign ack_out_w = capture_now && ram_sel_w;

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

    assign data_out_n = data_reg;
    assign data_out_s = data_reg;
    assign data_out_e = data_reg;
    assign data_out_w = data_reg;

    assign ready_out = !data_valid && !fixed_mode && !effective_freeze;
    assign status_data_valid = data_valid;

    // ── Real next-state computation, identical regardless of mode ──
    wire [3:0]  next_downstream_mask = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[3:0]   : downstream_mask;
    wire [3:0]  next_upstream_mask   = (rst) ? 4'h0 : (cfg_valid) ? cfg_data[7:4]   : upstream_mask;
    wire        next_fixed_mode      = (rst) ? 1'b0 : (cfg_valid) ? cfg_data[8]     : fixed_mode;
    wire        next_data_valid_reg  = (rst) ? 1'b0 :
                                        (cfg_valid) ? cfg_data[9] :
                                        (capture_now) ? 1'b1 :
                                        (!fixed_mode && offer_draining) ? 1'b0 : data_valid;
    wire [31:0] next_data_reg        = (rst) ? 32'h0 :
                                        (cfg_valid) ? cfg_data[41:10] :
                                        (capture_now) ? upstream_val : data_reg;
    wire [3:0]  next_pending_ack_reg = (rst) ? 4'h0 : (cfg_valid) ? 4'h0 : next_pending_ack;

    assign ext_state_out = {next_pending_ack_reg, next_data_reg, next_data_valid_reg,
                             next_fixed_mode, next_upstream_mask, next_downstream_mask};

    generate
        if (!EXTERNAL_STORAGE) begin : internal_storage
            always @(posedge clk) begin
                int_downstream_mask <= next_downstream_mask;
                int_upstream_mask   <= next_upstream_mask;
                int_fixed_mode      <= next_fixed_mode;
                int_data_valid      <= next_data_valid_reg;
                int_data_reg        <= next_data_reg;
                int_pending_ack     <= next_pending_ack_reg;
            end
        end
    endgenerate

endmodule
