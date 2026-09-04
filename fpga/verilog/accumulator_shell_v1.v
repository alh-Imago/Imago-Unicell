// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_shell_v1.v — same real pattern as `branch_shell_v1.v`
// (see its own header for the full real rationale, points.md #646).
`default_nettype none
`timescale 1ns / 1ps

module accumulator_shell_v1 #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire         rst,

    input  wire         active_in_n, active_in_s, active_in_e, active_in_w,
    input  wire         freeze_in_n, freeze_in_s, freeze_in_e, freeze_in_w,

    input  wire         cfg_valid,
    input  wire [63:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    output wire         ready_out,
    output wire         status_negative
);

    wire active_comb = active_in_n | active_in_s | active_in_e | active_in_w;
    wire freeze_comb = freeze_in_n | freeze_in_s | freeze_in_e | freeze_in_w;

    accumulator_cell_v4 #(.CELL_ID(CELL_ID), .WIDTH(WIDTH)) CORE (
        .clk(clk), .rst(rst), .active(active_comb),
        .cfg_valid(cfg_valid), .cfg_data(cfg_data),
        .data_in_n(data_in_n), .data_in_s(data_in_s), .data_in_e(data_in_e), .data_in_w(data_in_w),
        .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(arrived_e), .arrived_w(arrived_w),
        .data_out_n(data_out_n), .data_out_s(data_out_s), .data_out_e(data_out_e), .data_out_w(data_out_w),
        .fire_n(fire_n), .fire_s(fire_s), .fire_e(fire_e), .fire_w(fire_w),
        .ready_in_n(ready_in_n), .ready_in_s(ready_in_s), .ready_in_e(ready_in_e), .ready_in_w(ready_in_w),
        .ack_out_n(ack_out_n), .ack_out_s(ack_out_s), .ack_out_e(ack_out_e), .ack_out_w(ack_out_w),
        .ack_in_n(ack_in_n), .ack_in_s(ack_in_s), .ack_in_e(ack_in_e), .ack_in_w(ack_in_w),
        .program_in(program_in), .program_done(program_done),
        .prog_data_in_n(prog_data_in_n), .prog_data_in_s(prog_data_in_s),
        .prog_data_in_e(prog_data_in_e), .prog_data_in_w(prog_data_in_w),
        .prog_arrived_in_n(prog_arrived_in_n), .prog_arrived_in_s(prog_arrived_in_s),
        .prog_arrived_in_e(prog_arrived_in_e), .prog_arrived_in_w(prog_arrived_in_w),
        .prog_ack_out_n(prog_ack_out_n), .prog_ack_out_s(prog_ack_out_s),
        .prog_ack_out_e(prog_ack_out_e), .prog_ack_out_w(prog_ack_out_w),
        .freeze_in(freeze_comb),
        .ready_out(ready_out), .status_negative(status_negative)
    );

endmodule
