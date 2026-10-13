// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// cross_cell_v4sa.v -- ledger #1165: the CROSSING tile, native flex cell: straight through (N<->S, E<->W), one tick per tile, four independent slices. Same module as the corner tile with
// CROSS = 1 (as cross_cell_v4 is for corner_cell_v4); see corner_cell_v4sa.v for the handshake and the port naming.
`default_nettype none
`timescale 1ns / 1ps

module cross_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,
    input  wire        cfg_valid,
    input  wire [WIDTH-1:0] din_n, din_s, din_e, din_w,
    input  wire             valid_in_n, valid_in_s, valid_in_e, valid_in_w,
    output wire             ack_out_n, ack_out_s, ack_out_e, ack_out_w,
    output wire [WIDTH-1:0] data_out_n, data_out_s, data_out_e, data_out_w,
    output wire             valid_out_n, valid_out_s, valid_out_e, valid_out_w,
    input  wire             ack_in_n, ack_in_s, ack_in_e, ack_in_w
);
    corner_cell_v4sa #(.CELL_ID(CELL_ID), .WIDTH(WIDTH), .CROSS(1), .TURN(0)) core (
        .clk(clk), .rst(rst), .freeze_in(freeze_in), .cfg_valid(cfg_valid), .din_n(din_n), .valid_in_n(valid_in_n), .ack_out_n(ack_out_n), .data_out_n(data_out_n), .valid_out_n(valid_out_n), .ack_in_n(ack_in_n), .din_s(din_s), .valid_in_s(valid_in_s), .ack_out_s(ack_out_s), .data_out_s(data_out_s), .valid_out_s(valid_out_s), .ack_in_s(ack_in_s), .din_e(din_e), .valid_in_e(valid_in_e), .ack_out_e(ack_out_e), .data_out_e(data_out_e), .valid_out_e(valid_out_e), .ack_in_e(ack_in_e), .din_w(din_w), .valid_in_w(valid_in_w), .ack_out_w(ack_out_w), .data_out_w(data_out_w), .valid_out_w(valid_out_w), .ack_in_w(ack_in_w));
endmodule
