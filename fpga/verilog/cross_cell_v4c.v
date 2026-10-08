// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// cross_cell_v4c.v -- ledger #1036: the CROSS wiring core (ICM core 10): N<->S and E<->W pass straight through, four independent one-word slices, one tick per tile, no addon chain.
// It is corner_cell_v4 with CROSS=1 (the `turn` bit is ignored), so the v4 and v4c cross are the same module.
`default_nettype none
`timescale 1ns / 1ps
module cross_cell_v4c #(parameter [15:0] CELL_ID = 16'h0000) (
    input wire clk, input wire rst, input wire active,
    input wire cfg_valid, input wire [79:0] cfg_data,
    input wire [31:0] data_in_n, data_in_s, data_in_e, data_in_w,
    input wire arrived_n, arrived_s, arrived_e, arrived_w,
    output wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w,
    output wire fire_n, fire_s, fire_e, fire_w,
    output wire ready_out,
    input wire ready_in_n, ready_in_s, ready_in_e, ready_in_w,
    output wire ack_out_n, ack_out_s, ack_out_e, ack_out_w,
    input wire ack_in_n, ack_in_s, ack_in_e, ack_in_w,
    input wire program_in, output wire program_done,
    input wire [31:0] prog_data_in_n, prog_data_in_s, prog_data_in_e, prog_data_in_w,
    input wire prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire prog_ack_out_n, prog_ack_out_s, prog_ack_out_e, prog_ack_out_w,
    input wire freeze_in, output wire status_data_valid
);
    corner_cell_v4 #(.CELL_ID(CELL_ID), .CROSS(1)) U (.*);
endmodule
