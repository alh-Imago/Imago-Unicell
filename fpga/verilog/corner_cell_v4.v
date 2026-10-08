// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// corner_cell_v4.v — ledger #1035: the CORNER wiring core (core 11 in the ICM numbering, SEL_CORNER = 12 in the carrier).
// A pure-wiring tile that lets two lanes cross at one cell by TURNING:
//     turn = cfg_data[0] = 0 : E <-> N  and  W <-> S
//     turn = cfg_data[0] = 1 : E <-> S  and  W <-> N
// Each pairing is bidirectional, so a cell holds FOUR independent one-word slices, one per face a word can enter by.  A word that arrives on face X is held in slice X and offered
// on partner(X); when the partner acknowledges, the slice empties.  One tick per tile, no arithmetic, no addon chain (a wiring tile transforms nothing: the v4 addon field is ignored,
// which is why the v4 and v4c corner are the same module).  The cell has a single ready_out, so it reads "at least one slice is empty"; a word that arrives at a full slice is simply not
// acknowledged and the sender keeps offering it (fire is a held level), exactly as for any other cell.  program_in / PROG_ID: ID 2 (FIXED_MODE word) is reused as the TURN word;
// ID 7 COMPLETE re-arms; every other ID is ignored.
`default_nettype none
`timescale 1ns / 1ps

module corner_cell_v4 #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        active,

    input  wire         cfg_valid,
    input  wire [79:0]  cfg_data,

    input  wire [31:0]  data_in_n,   data_in_s,   data_in_e,   data_in_w,
    input  wire         arrived_n,   arrived_s,   arrived_e,   arrived_w,

    output wire [31:0]  data_out_n,  data_out_s,  data_out_e,  data_out_w,
    output wire         fire_n,      fire_s,      fire_e,      fire_w,

    output wire         ready_out,
    input  wire         ready_in_n,  ready_in_s,  ready_in_e,  ready_in_w,

    output wire         ack_out_n,   ack_out_s,   ack_out_e,   ack_out_w,
    input  wire         ack_in_n,    ack_in_s,    ack_in_e,    ack_in_w,

    input  wire         program_in,
    output wire         program_done,
    input  wire [31:0]  prog_data_in_n,  prog_data_in_s,  prog_data_in_e,  prog_data_in_w,
    input  wire          prog_arrived_in_n, prog_arrived_in_s, prog_arrived_in_e, prog_arrived_in_w,
    output wire          prog_ack_out_n,    prog_ack_out_s,    prog_ack_out_e,    prog_ack_out_w,

    input  wire         freeze_in,
    output wire         status_data_valid
);
    // face index: 0=N 1=S 2=E 3=W
    reg turn = 1'b0;
    reg armed = 1'b0;
    wire eff_armed = armed && active;

    // partner face of each face, as a 2-bit index (turn 0: N-E, S-W;  turn 1: N-W, S-E)
    function [1:0] partner(input [1:0] f, input t);
        begin
            case (f)
                2'd0: partner = t ? 2'd3 : 2'd2;   // N
                2'd1: partner = t ? 2'd2 : 2'd3;   // S
                2'd2: partner = t ? 2'd1 : 2'd0;   // E
                default: partner = t ? 2'd0 : 2'd1; // W
            endcase
        end
    endfunction

    wire [3:0]  arrived = {arrived_w, arrived_e, arrived_s, arrived_n};
    wire [3:0]  ready_i = {ready_in_w, ready_in_e, ready_in_s, ready_in_n};
    wire [3:0]  ack_i   = {ack_in_w, ack_in_e, ack_in_s, ack_in_n};
    wire [31:0] din [0:3];
    assign din[0] = data_in_n; assign din[1] = data_in_s; assign din[2] = data_in_e; assign din[3] = data_in_w;

    reg [31:0] sdata [0:3];
    reg [3:0]  svalid = 4'h0;
    reg [3:0]  spend  = 4'h0;       // slice i has fired on partner(i) and awaits its ack
    integer k;
    initial for (k = 0; k < 4; k = k + 1) sdata[k] = 32'h0;

    wire [3:0] cap;                 // slice i captures this tick
    genvar g;
    generate for (g = 0; g < 4; g = g + 1) begin : S
        assign cap[g] = arrived[g] && !svalid[g] && !freeze_in && eff_armed && !program_in;
        wire [1:0] p = partner(g[1:0], turn);
        wire fire_ok = svalid[g] && !spend[g] && ready_i[p] && !freeze_in && eff_armed;
        wire acked   = spend[g] && ack_i[p];
        always @(posedge clk) begin
            if (rst || cfg_valid) begin
                svalid[g] <= 1'b0; spend[g] <= 1'b0; sdata[g] <= 32'h0;
            end else begin
                if (cap[g]) begin sdata[g] <= din[g]; svalid[g] <= 1'b1; end
                if (fire_ok) spend[g] <= 1'b1;
                if (acked) begin spend[g] <= 1'b0; svalid[g] <= 1'b0; end
            end
        end
    end endgenerate

    // outputs: face o is driven by the slice of its partner (partner is an involution)
    wire [1:0] pn = partner(2'd0, turn), ps = partner(2'd1, turn), pe = partner(2'd2, turn), pw = partner(2'd3, turn);
    assign data_out_n = sdata[pn]; assign data_out_s = sdata[ps]; assign data_out_e = sdata[pe]; assign data_out_w = sdata[pw];
    assign fire_n = spend[pn];     assign fire_s = spend[ps];     assign fire_e = spend[pe];     assign fire_w = spend[pw];
    assign ack_out_n = cap[0]; assign ack_out_s = cap[1]; assign ack_out_e = cap[2]; assign ack_out_w = cap[3];

    assign ready_out = eff_armed && !freeze_in && (svalid != 4'hF);
    assign status_data_valid = |svalid;

    // targeted programming: only the TURN word (ID 2) and COMPLETE (ID 7)
    wire prog_any = prog_arrived_in_n | prog_arrived_in_s | prog_arrived_in_e | prog_arrived_in_w;
    wire pn_ = prog_arrived_in_n;
    wire ps_ = prog_arrived_in_s && !prog_arrived_in_n;
    wire pe_ = prog_arrived_in_e && !prog_arrived_in_n && !prog_arrived_in_s;
    wire pw_ = prog_arrived_in_w && !prog_arrived_in_n && !prog_arrived_in_s && !prog_arrived_in_e;
    wire [31:0] pdata = pn_ ? prog_data_in_n : ps_ ? prog_data_in_s : pe_ ? prog_data_in_e : prog_data_in_w;
    wire [2:0]  pid   = pdata[22:20];
    wire        pact  = program_in && active && prog_any;
    assign prog_ack_out_n = pact && pn_; assign prog_ack_out_s = pact && ps_;
    assign prog_ack_out_e = pact && pe_; assign prog_ack_out_w = pact && pw_;
    reg pdone = 1'b0;
    assign program_done = pdone;

    always @(posedge clk) begin
        if (rst) begin turn <= 1'b0; armed <= 1'b0; pdone <= 1'b0; end
        else if (cfg_valid) begin turn <= cfg_data[0]; armed <= 1'b1; end
        else if (pact) begin
            if (pid == 3'd2) turn <= pdata[0];
            if (pid == 3'd7) begin pdone <= 1'b1; armed <= pdata[0]; end
        end else if (!program_in) pdone <= 1'b0;
    end
endmodule
