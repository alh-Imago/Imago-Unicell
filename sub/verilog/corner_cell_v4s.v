// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// corner_cell_v4s.v -- ledger #1165: the CORNER wiring tile as a NATIVE sub (v4s) cell: no ack, fixed time, ONE CLOCK per tile. FOUR independent one-word slices, one per face a word can
// ENTER by; a word offered on face f (valid_in_f) is registered and appears on partner(f) one clock later, with valid_out for that one clock, exactly as the flowing ram_cell_v4s relay does
// (data follows valid_in; valid_out_r <= armed & valid_in). A word that arrives while the next is still being offered is simply replaced, as in any v4s relay (the planner aligns arrivals).
//   CROSS = 1 : straight through (N<->S, E<->W)      CROSS = 0, TURN = 0 : E<->N and W<->S      CROSS = 0, TURN = 1 : E<->S and W<->N
// Ports: INPUT lanes are named by the face the word ENTERS by; OUTPUT ports by the face it LEAVES by (data_out_o is fed by lane partner(o)).
`default_nettype none
`timescale 1ns / 1ps

module corner_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        CROSS   = 0,
    parameter        TURN    = 0
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        cfg_valid,
    input  wire [31:0] din_n, din_s, din_e, din_w,
    input  wire        valid_in_n, valid_in_s, valid_in_e, valid_in_w,
    output wire [31:0] data_out_n, data_out_s, data_out_e, data_out_w,
    output wire        valid_out_n, valid_out_s, valid_out_e, valid_out_w
);
    function [1:0] partner(input [1:0] f);   // 0 = N, 1 = S, 2 = E, 3 = W
        begin
            if (CROSS != 0) begin
                case (f) 2'd0: partner = 2'd1; 2'd1: partner = 2'd0; 2'd2: partner = 2'd3; default: partner = 2'd2; endcase
            end else if (TURN != 0) begin
                case (f) 2'd0: partner = 2'd3; 2'd1: partner = 2'd2; 2'd2: partner = 2'd1; default: partner = 2'd0; endcase
            end else begin
                case (f) 2'd0: partner = 2'd2; 2'd1: partner = 2'd3; 2'd2: partner = 2'd0; default: partner = 2'd1; endcase
            end
        end
    endfunction

    reg armed = 1'b0;
    reg [31:0] sdata [0:3];
    reg [3:0]  svalid = 4'h0;
    integer k;
    initial for (k = 0; k < 4; k = k + 1) sdata[k] = 32'h0;
    wire [31:0] din [0:3];
    assign din[0] = din_n; assign din[1] = din_s; assign din[2] = din_e; assign din[3] = din_w;
    wire [3:0] vin = {valid_in_w, valid_in_e, valid_in_s, valid_in_n};

    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : L
        always @(posedge clk) begin
            if (rst) begin
                sdata[g] <= 32'h0; svalid[g] <= 1'b0;
            end else if (cfg_valid) begin
                sdata[g] <= 32'h0; svalid[g] <= 1'b0;       // as the relay's config load
            end else begin
                if (vin[g]) sdata[g] <= din[g];
                svalid[g] <= armed && vin[g];
            end
        end
    end endgenerate
    always @(posedge clk) begin
        if (rst) armed <= 1'b0;
        else if (cfg_valid) armed <= 1'b1;
    end

    localparam [1:0] PN = partner(2'd0), PS = partner(2'd1), PE = partner(2'd2), PW = partner(2'd3);
    assign data_out_n = sdata[PN]; assign data_out_s = sdata[PS]; assign data_out_e = sdata[PE]; assign data_out_w = sdata[PW];
    assign valid_out_n = svalid[PN]; assign valid_out_s = svalid[PS]; assign valid_out_e = svalid[PE]; assign valid_out_w = svalid[PW];
endmodule
