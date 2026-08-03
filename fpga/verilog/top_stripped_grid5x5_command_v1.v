// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_grid5x5_command_v1.v — STEP 3 of the points.md #103
// measurement campaign, REBUILT (points.md #137) around the CORRECTED
// single-hop command-cell design (#123/#126), replacing the deprecated
// multi-hop relay-chain mechanism (#110, set aside per #122's scope
// correction).
//
// Same 25-cell grid, same snake data topology as step 1 (#104/#129),
// configured via the same cheap one-shot cfg_valid walk (#105's fix) --
// this is genuinely separate from what's being measured here. What's NEW:
// every cell gets its own cell_command_v1 companion (#126), each one
// targeting THAT SAME cell via the dedicated, genuinely cardinal
// programming channel (#133) — NOT the ordinary data grid at all, so
// there's no interference between the snake's real data flow and this
// mechanism, confirmed by construction (separate wires, per #133).
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_grid5x5_command_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

localparam [9:0] TOPO_NOR = 10'h004;

function [5:0] snake_mask(input [2:0] r, input [2:0] c);
    begin
        if (r == 3'd4 && c == 3'd4)
            snake_mask = 6'b000000;
        else if (r[0] == 1'b0) begin
            if (c < 3'd4) snake_mask = 6'b000100;
            else          snake_mask = 6'b000010;
        end else begin
            if (c > 3'd0) snake_mask = 6'b001000;
            else          snake_mask = 6'b000010;
        end
    end
endfunction

// ── Free-running stimulus into cell (0,0)'s north port — same as step 1 ──
reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = (stim_cnt[7:0] == 8'h00);
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};

// ── One-hot walking config sequencer — same fix as #105 (avoids the
// comparator artifact that dominated #104's first attempt). Sets up the
// SAME snake topology as step 1, via ordinary cfg_valid — genuinely
// separate from the command mechanism being measured here. ──
reg [24:0] cfg_walk = 25'h1;
reg        cfg_active = 1'b1;
always @(posedge clk) begin
    if (rst) begin
        cfg_walk   <= 25'h1;
        cfg_active <= 1'b1;
    end else if (cfg_active) begin
        if (cfg_walk[24]) cfg_active <= 1'b0;
        else              cfg_walk   <= {cfg_walk[23:0], 1'b0};
    end
end

// ── Command mechanism stimulus: a simple, shared trigger + 3-word data
// driver, fed identically to every cell's dedicated West programming
// channel. Purely for real, non-optimizable switching activity — the
// mechanism's functional correctness was already confirmed in #125/#126;
// this measures cost at scale, matching this project's own precedent
// (step 1/2 never needed "meaningful" data either, just genuine
// activity). ──
reg [1:0]  cmd_word = 2'h0;
reg        cmd_trigger = 1'b0;
reg        cmd_arrived = 1'b0;
localparam [2:0] PID_TOPOLOGY = 3'd0, PID_ROUTING_MASK = 3'd1, PID_COMPLETE = 3'd7;
wire [31:0] cmd_data = (cmd_word == 2'd0) ? {13'h0, PID_TOPOLOGY, 6'h0, TOPO_NOR} :
                       (cmd_word == 2'd1) ? {13'h0, PID_ROUTING_MASK, 16'h0} :
                                            {13'h0, PID_COMPLETE, 16'h0};
always @(posedge clk) begin
    if (rst) begin
        cmd_word    <= 2'h0;
        cmd_trigger <= 1'b0;
        cmd_arrived <= 1'b0;
    end else begin
        cmd_trigger <= stim_cnt[13];       // slow, free-running trigger
        cmd_arrived <= stim_cnt[13] && (stim_cnt[6:0] != 7'h7F); // pulses while triggered
        if (cmd_arrived) cmd_word <= (cmd_word == 2'd2) ? 2'd0 : (cmd_word + 2'd1);
    end
end

// ── Per-cell signal arrays: data grid (identical to step 1) ──
wire [31:0] c_dout_n[0:4][0:4], c_dout_s[0:4][0:4], c_dout_e[0:4][0:4], c_dout_w[0:4][0:4];
wire        c_fire_n[0:4][0:4], c_fire_s[0:4][0:4], c_fire_e[0:4][0:4], c_fire_w[0:4][0:4];
wire        c_ready [0:4][0:4];
wire        c_ackn  [0:4][0:4], c_acks [0:4][0:4], c_acke [0:4][0:4], c_ackw [0:4][0:4];

wire        c_program_done[0:4][0:4];
wire        cmd_program_out[0:4][0:4];

genvar r, c;
generate
for (r = 0; r < 5; r = r + 1) begin : ROW
    for (c = 0; c < 5; c = c + 1) begin : COL

        localparam integer FLAT = r*5 + c;
        localparam [5:0] MY_SNAKE_MASK = snake_mask(r[2:0], c[2:0]);

        // ── Every cell gets its own command companion, targeting itself
        // via the dedicated West programming channel. ──
        cell_command_v1 CMD (
            .clk(clk), .rst(rst),
            .trigger_in(cmd_trigger),
            .program_done_in(c_program_done[r][c]),
            .program_out(cmd_program_out[r][c])
        );

        unicell_stripped_v1 #(.CELL_ID({8'h0, r[3:0], c[3:0]})) CELL (
            .clk(clk), .rst(rst),
            .cfg_valid(cfg_walk[FLAT]), .cfg_data({58'h0, MY_SNAKE_MASK, 54'h0, TOPO_NOR}),

            .data_in_n((r==0) ? ((c==0) ? seed_data : 32'h0) : c_dout_s[r-1][c]),
            .arrived_n((r==0) ? ((c==0) ? seed_pulse : 1'b0) : c_fire_s[r-1][c]),
            .data_in_s((r==4) ? 32'h0 : c_dout_n[r+1][c]),
            .arrived_s((r==4) ? 1'b0  : c_fire_n[r+1][c]),
            .data_in_e((c==4) ? 32'h0 : c_dout_w[r][c+1]),
            .arrived_e((c==4) ? 1'b0  : c_fire_w[r][c+1]),
            .data_in_w((c==0) ? 32'h0 : c_dout_e[r][c-1]),
            .arrived_w((c==0) ? 1'b0  : c_fire_e[r][c-1]),

            .data_out_n(c_dout_n[r][c]), .fire_n(c_fire_n[r][c]),
            .data_out_s(c_dout_s[r][c]), .fire_s(c_fire_s[r][c]),
            .data_out_e(c_dout_e[r][c]), .fire_e(c_fire_e[r][c]),
            .data_out_w(c_dout_w[r][c]), .fire_w(c_fire_w[r][c]),

            .ready_out(c_ready[r][c]),
            .ready_in_n((r==0) ? 1'b1 : c_ready[r-1][c]),
            .ready_in_s((r==4) ? 1'b1 : c_ready[r+1][c]),
            .ready_in_e((c==4) ? 1'b1 : c_ready[r][c+1]),
            .ready_in_w((c==0) ? 1'b1 : c_ready[r][c-1]),

            .ack_out_n(c_ackn[r][c]), .ack_out_s(c_acks[r][c]),
            .ack_out_e(c_acke[r][c]), .ack_out_w(c_ackw[r][c]),
            .ack_in_n((r==0) ? 1'b0 : c_acks[r-1][c]),
            .ack_in_s((r==4) ? 1'b0 : c_ackn[r+1][c]),
            .ack_in_e((c==4) ? 1'b0 : c_ackw[r][c+1]),
            .ack_in_w((c==0) ? 1'b0 : c_acke[r][c-1]),

            .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
            .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),

            .freeze_in(1'b0),
            .hold_in(1'b0),
            .fb_internal_in(1'b0),
            .a_reemit_in(1'b0),
            .a_update_in(1'b0),
            .a_self_update_in(1'b0),

            .program_in(cmd_program_out[r][c]),
            .program_done(c_program_done[r][c]),
            .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(cmd_data),
            .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(cmd_arrived),
            .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
        );

    end
end
endgenerate

wire cmd_activity = c_program_done[0][0] | c_program_done[1][1] | c_program_done[2][2]
                  | c_program_done[3][3] | c_program_done[4][4]
                  | cmd_program_out[0][0] | cmd_program_out[2][3] | cmd_program_out[4][1];

wire all_ready = c_ready[0][0] & c_ready[0][1] & c_ready[0][2] & c_ready[0][3] & c_ready[0][4]
                & c_ready[1][0] & c_ready[1][1] & c_ready[1][2] & c_ready[1][3] & c_ready[1][4]
                & c_ready[2][0] & c_ready[2][1] & c_ready[2][2] & c_ready[2][3] & c_ready[2][4]
                & c_ready[3][0] & c_ready[3][1] & c_ready[3][2] & c_ready[3][3] & c_ready[3][4]
                & c_ready[4][0] & c_ready[4][1] & c_ready[4][2] & c_ready[4][3] & c_ready[4][4];

assign LED0_N = all_ready;
assign LED1_N = ~(stim_cnt[23] ^ cmd_activity);

endmodule
