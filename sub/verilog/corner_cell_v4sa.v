// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// corner_cell_v4sa.v -- ledger #1165: the CORNER wiring tile as a NATIVE flex (v4sa) cell (ledger #999 / #1035 left it open: until now the netlist stood a ram relay in for every used
// direction of travel). FOUR independent one-word slices, one per face a word can ENTER by; the slice of face f offers its word on partner(f) one clock after it was taken, and is freed when
// that face's receiver acks. ONE TICK PER TILE, no arithmetic, no control, no shared state between the slices (so two streams crossing in one tile never interact).
//   CROSS = 1 : straight through: N<->S, E<->W (TURN is ignored)            CROSS = 0, TURN = 0 : E<->N and W<->S          CROSS = 0, TURN = 1 : E<->S and W<->N
// Each slice follows EXACTLY the flowing ram's handshake (ram_cell_v4sa.v): ack_out = armed & !pending & !freeze; a word is taken when valid_in & ack_out; pending clears on ack_in. What it
// does NOT carry is everything a ram has for being a memory (init word, fixed / hold / one-shot modes, the config mux): the tile is cheaper than the relays it replaces (measured in #1165).
// Port naming: INPUT lanes are named by the face the word ENTERS by (din_n, valid_in_n, ack_out_n = the backward ack to whoever feeds that face); OUTPUT ports are named by the face the word
// LEAVES by (data_out_e, valid_out_e, ack_in_e = the ack from whoever is attached to that face). partner() is its own inverse, so lane partner(o) feeds output face o.
`default_nettype none
`timescale 1ns / 1ps

module corner_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32,
    parameter        CROSS   = 0,
    parameter        TURN    = 0
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
    // face index: 0 = N, 1 = S, 2 = E, 3 = W
    function [1:0] partner(input [1:0] f);
        begin
            if (CROSS != 0) begin
                case (f) 2'd0: partner = 2'd1; 2'd1: partner = 2'd0; 2'd2: partner = 2'd3; default: partner = 2'd2; endcase
            end else if (TURN != 0) begin
                case (f) 2'd0: partner = 2'd3; 2'd1: partner = 2'd2; 2'd2: partner = 2'd1; default: partner = 2'd0; endcase   // N-W, S-E
            end else begin
                case (f) 2'd0: partner = 2'd2; 2'd1: partner = 2'd3; 2'd2: partner = 2'd0; default: partner = 2'd1; endcase   // N-E, S-W
            end
        end
    endfunction

    reg armed = 1'b0;
    reg [3:0] pending = 4'h0;
    reg [WIDTH-1:0] sdata [0:3];
    integer k;
    initial for (k = 0; k < 4; k = k + 1) sdata[k] = {WIDTH{1'b0}};

    wire [WIDTH-1:0] din [0:3];
    assign din[0] = din_n; assign din[1] = din_s; assign din[2] = din_e; assign din[3] = din_w;
    wire [3:0] vin  = {valid_in_w, valid_in_e, valid_in_s, valid_in_n};
    wire [3:0] ackx = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};          // indexed by EXIT face
    wire [3:0] ackl;                                                       // per lane: the ack of the face this lane's word leaves by
    wire [3:0] rdy;

    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : L
        localparam [1:0] P = partner(g[1:0]);
        assign ackl[g] = ackx[P];
        assign rdy[g]  = armed && !pending[g] && !freeze_in;
        always @(posedge clk) begin
            if (rst) begin
                pending[g] <= 1'b0; sdata[g] <= {WIDTH{1'b0}};
            end else if (cfg_valid) begin
                pending[g] <= 1'b0; sdata[g] <= {WIDTH{1'b0}};     // as the relay's config load (init word 0), so even the idle data pins agree clock for clock
            end else if (!freeze_in) begin
                if (pending[g]) begin
                    if (ackl[g]) pending[g] <= 1'b0;
                end else if (vin[g]) begin
                    sdata[g] <= din[g]; pending[g] <= 1'b1;
                end
            end
        end
    end endgenerate

    always @(posedge clk) begin
        if (rst) armed <= 1'b0;
        else if (cfg_valid) armed <= 1'b1;
    end

    assign ack_out_n = rdy[0]; assign ack_out_s = rdy[1]; assign ack_out_e = rdy[2]; assign ack_out_w = rdy[3];

    // output face o is fed by lane partner(o)
    localparam [1:0] PN = partner(2'd0), PS = partner(2'd1), PE = partner(2'd2), PW = partner(2'd3);
    assign data_out_n = sdata[PN]; assign data_out_s = sdata[PS]; assign data_out_e = sdata[PE]; assign data_out_w = sdata[PW];
    assign valid_out_n = pending[PN]; assign valid_out_s = pending[PS]; assign valid_out_e = pending[PE]; assign valid_out_w = pending[PW];
endmodule
