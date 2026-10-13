// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// cross_cell_v4s.v -- ledger #1165: the CROSSING tile, native sub cell: straight through (N<->S, E<->W), one clock per tile, four independent slices. corner_cell_v4s with CROSS = 1.
`default_nettype none
`timescale 1ns / 1ps

module cross_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        cfg_valid,
    input  wire [31:0] din_n, din_s, din_e, din_w,
    input  wire        valid_in_n, valid_in_s, valid_in_e, valid_in_w,
    output wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w,
    output wire        valid_out_n, valid_out_s, valid_out_e, valid_out_w
);
    corner_cell_v4s #(.CELL_ID(CELL_ID), .CROSS(1), .TURN(0)) core (.clk(clk), .rst(rst), .cfg_valid(cfg_valid), .din_n(din_n), .valid_in_n(valid_in_n), .din_s(din_s), .valid_in_s(valid_in_s), .din_e(din_e), .valid_in_e(valid_in_e), .din_w(din_w), .valid_in_w(valid_in_w), .data_out_n(data_out_n), .valid_out_n(valid_out_n), .data_out_s(data_out_s), .valid_out_s(valid_out_s), .data_out_e(data_out_e), .valid_out_e(valid_out_e), .data_out_w(data_out_w), .valid_out_w(valid_out_w));
endmodule
