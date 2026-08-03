// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_zone750_v1.v — points.md #148: a 50-cell (5x10) zone,
// combining the wrapper (#127/#146) and command-cell (#126/#146)
// mechanisms, scaling up from the 25-cell campaign for a "good base
// figure" ahead of eventual 16-zone/full-card extrapolation. Same design
// as top_stripped_grid5x5_both_v2.v, generalized from 5x5 to 5x10.
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_zone750_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

localparam ROWS = 25;
localparam COLS = 30;
localparam CELLS = ROWS*COLS;   // 50

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

localparam [9:0] TOPO_NOR = 10'h004;
localparam [2:0] OP_PROGRAM  = 3'b000;
localparam [2:0] OP_COLLECT  = 3'b001;
localparam [2:0] OP_SET_CTRL = 3'b010;
localparam [2:0] OP_CLR_CTRL = 3'b011;
localparam [2:0] OP_DIAG     = 3'b100;
localparam [2:0] PID_TOPOLOGY = 3'd0, PID_ROUTING_MASK = 3'd1, PID_COMPLETE = 3'd7;

// ── Snake routing, generalized to ROWS x COLS (was hardcoded to 5x5) ──
function [5:0] snake_mask(input [4:0] r, input [4:0] c);
    begin
        if (r == ROWS-1 && c == COLS-1)
            snake_mask = 6'b000000;   // chain end
        else if (r[0] == 1'b0) begin
            if (c < COLS-1) snake_mask = 6'b000100;   // East
            else            snake_mask = 6'b000010;   // South (wrap)
        end else begin
            if (c > 0)      snake_mask = 6'b001000;   // West
            else            snake_mask = 6'b000010;   // South (wrap)
        end
    end
endfunction

reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = (stim_cnt[7:0] == 8'h00);
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};

// ── Wrapper program driver — CELLS addresses now, not fixed 25 ──
reg [9:0] prog_addr = 10'h0;
reg [4:0] prog_row  = 5'h0;
reg [4:0] prog_col  = 5'h0;
reg [1:0] prog_word = 2'h0;
reg       prog_active = 1'b1;

wire [5:0]  prog_snake  = snake_mask(prog_row, prog_col);
wire [31:0] prog_word0 = {13'h0, PID_TOPOLOGY,     6'h0, TOPO_NOR};
wire [31:0] prog_word1 = {13'h0, PID_ROUTING_MASK, 12'h0, prog_snake[3:0]};
wire [31:0] prog_word2 = {13'h0, PID_COMPLETE,     16'h0};
wire [31:0] prog_data  = (prog_word == 2'd0) ? prog_word0 :
                          (prog_word == 2'd1) ? prog_word1 : prog_word2;

always @(posedge clk) begin
    if (rst) begin
        prog_addr   <= 10'h0;
        prog_row    <= 5'h0;
        prog_col    <= 5'h0;
        prog_word   <= 2'h0;
        prog_active <= 1'b1;
    end else if (prog_active) begin
        if (prog_word == 2'd2) begin
            prog_word <= 2'h0;
            if (prog_addr == CELLS-1) begin
                prog_active <= 1'b0;
            end else begin
                prog_addr <= prog_addr + 10'd1;
                if (prog_col == COLS-1) begin
                    prog_col <= 5'h0;
                    prog_row <= prog_row + 5'd1;
                end else begin
                    prog_col <= prog_col + 5'd1;
                end
            end
        end else begin
            prog_word <= prog_word + 2'd1;
        end
    end
end

wire        w0_bus_in_valid = prog_active;
wire [9:0]  w0_bus_in_addr  = prog_addr;
wire [2:0]  w0_bus_in_op    = OP_PROGRAM;
wire [31:0] w0_bus_in_data  = prog_data;

// ── Command-cell mechanism driver (identical to step 3/#146) ──
reg [1:0]  cmd_word = 2'h0;
reg        cmd_trigger = 1'b0;
reg        cmd_arrived = 1'b0;
wire [31:0] cmd_data = (cmd_word == 2'd0) ? {13'h0, PID_TOPOLOGY, 6'h0, TOPO_NOR} :
                       (cmd_word == 2'd1) ? {13'h0, PID_ROUTING_MASK, 16'h0} :
                                            {13'h0, PID_COMPLETE, 16'h0};
always @(posedge clk) begin
    if (rst) begin
        cmd_word    <= 2'h0;
        cmd_trigger <= 1'b0;
        cmd_arrived <= 1'b0;
    end else begin
        cmd_trigger <= stim_cnt[13];
        cmd_arrived <= stim_cnt[13] && (stim_cnt[6:0] != 7'h7F);
        if (cmd_arrived) cmd_word <= (cmd_word == 2'd2) ? 2'd0 : (cmd_word + 2'd1);
    end
end

// ── Per-cell signal arrays — 2D, sized to ROWS x COLS ──
wire [31:0] c_dout_n[0:ROWS-1][0:COLS-1], c_dout_s[0:ROWS-1][0:COLS-1];
wire [31:0] c_dout_e[0:ROWS-1][0:COLS-1], c_dout_w[0:ROWS-1][0:COLS-1];
wire        c_fire_n[0:ROWS-1][0:COLS-1], c_fire_s[0:ROWS-1][0:COLS-1];
wire        c_fire_e[0:ROWS-1][0:COLS-1], c_fire_w[0:ROWS-1][0:COLS-1];
wire        c_ready [0:ROWS-1][0:COLS-1];
wire        c_ackn  [0:ROWS-1][0:COLS-1], c_acks [0:ROWS-1][0:COLS-1];
wire        c_acke  [0:ROWS-1][0:COLS-1], c_ackw [0:ROWS-1][0:COLS-1];

wire        wbus_valid[0:CELLS];
wire [9:0]  wbus_addr [0:CELLS];
wire [2:0]  wbus_op   [0:CELLS];
wire [31:0] wbus_data [0:CELLS];

assign wbus_valid[0] = w0_bus_in_valid;
assign wbus_addr[0]  = w0_bus_in_addr;
assign wbus_op[0]    = w0_bus_in_op;
assign wbus_data[0]  = w0_bus_in_data;

wire [31:0] w_prog_data [0:ROWS-1][0:COLS-1];
wire        w_prog_valid[0:ROWS-1][0:COLS-1];
wire        w_program_out[0:ROWS-1][0:COLS-1];
wire        w_freeze[0:ROWS-1][0:COLS-1], w_hold[0:ROWS-1][0:COLS-1], w_fbint[0:ROWS-1][0:COLS-1];
wire        w_reemit[0:ROWS-1][0:COLS-1], w_update[0:ROWS-1][0:COLS-1], w_selfupd[0:ROWS-1][0:COLS-1];
wire        c_program_done[0:ROWS-1][0:COLS-1];
wire        cmd_program_out[0:ROWS-1][0:COLS-1];

genvar r, c;
generate
for (r = 0; r < ROWS; r = r + 1) begin : ROW
    for (c = 0; c < COLS; c = c + 1) begin : COL

        localparam integer FLAT = r*COLS + c;

        wire [31:0] diag_word = {30'h0, c_program_done[r][c], c_ready[r][c]};

        cell_wrapper_v2 #(.ADDR(FLAT[9:0])) WRAP (
            .clk(clk), .rst(rst),
            .bus_in_valid(wbus_valid[FLAT]), .bus_in_addr(wbus_addr[FLAT]),
            .bus_in_op(wbus_op[FLAT]),       .bus_in_data(wbus_data[FLAT]),
            .bus_out_valid(wbus_valid[FLAT+1]), .bus_out_addr(wbus_addr[FLAT+1]),
            .bus_out_op(wbus_op[FLAT+1]),       .bus_out_data(wbus_data[FLAT+1]),
            .cell_prog_data_out(w_prog_data[r][c]), .cell_prog_arrived_out(w_prog_valid[r][c]),
            .cell_program_out(w_program_out[r][c]), .cell_program_done_in(c_program_done[r][c]),
            .cell_freeze_out(w_freeze[r][c]), .cell_hold_out(w_hold[r][c]),
            .cell_fb_internal_out(w_fbint[r][c]), .cell_a_reemit_out(w_reemit[r][c]),
            .cell_a_update_out(w_update[r][c]), .cell_a_self_update_out(w_selfupd[r][c]),
            .cell_out_buffer(c_dout_n[r][c]), .cell_diag_in(diag_word)
        );

        cell_command_v1 CMD (
            .clk(clk), .rst(rst),
            .trigger_in(cmd_trigger),
            .program_done_in(c_program_done[r][c]),
            .program_out(cmd_program_out[r][c])
        );

        unicell_stripped_v1 #(.CELL_ID({r[4:0], c[6:0]})) CELL (
            .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),

            .data_in_n((r==0) ? ((c==0) ? seed_data : 32'h0) : c_dout_s[r-1][c]),
            .arrived_n((r==0) ? ((c==0) ? seed_pulse : 1'b0) : c_fire_s[r-1][c]),
            .data_in_s((r==ROWS-1) ? 32'h0 : c_dout_n[r+1][c]),
            .arrived_s((r==ROWS-1) ? 1'b0  : c_fire_n[r+1][c]),
            .data_in_e((c==COLS-1) ? 32'h0 : c_dout_w[r][c+1]),
            .arrived_e((c==COLS-1) ? 1'b0  : c_fire_w[r][c+1]),
            .data_in_w((c==0) ? 32'h0 : c_dout_e[r][c-1]),
            .arrived_w((c==0) ? 1'b0  : c_fire_e[r][c-1]),

            .data_out_n(c_dout_n[r][c]), .fire_n(c_fire_n[r][c]),
            .data_out_s(c_dout_s[r][c]), .fire_s(c_fire_s[r][c]),
            .data_out_e(c_dout_e[r][c]), .fire_e(c_fire_e[r][c]),
            .data_out_w(c_dout_w[r][c]), .fire_w(c_fire_w[r][c]),

            .ready_out(c_ready[r][c]),
            .ready_in_n((r==0) ? 1'b1 : c_ready[r-1][c]),
            .ready_in_s((r==ROWS-1) ? 1'b1 : c_ready[r+1][c]),
            .ready_in_e((c==COLS-1) ? 1'b1 : c_ready[r][c+1]),
            .ready_in_w((c==0) ? 1'b1 : c_ready[r][c-1]),

            .ack_out_n(c_ackn[r][c]), .ack_out_s(c_acks[r][c]),
            .ack_out_e(c_acke[r][c]), .ack_out_w(c_ackw[r][c]),
            .ack_in_n((r==0) ? 1'b0 : c_acks[r-1][c]),
            .ack_in_s((r==ROWS-1) ? 1'b0 : c_ackn[r+1][c]),
            .ack_in_e((c==COLS-1) ? 1'b0 : c_ackw[r][c+1]),
            .ack_in_w((c==0) ? 1'b0 : c_acke[r][c-1]),

            .cmd_in_n(32'h0), .cmd_in_s(32'h0), .cmd_in_e(32'h0), .cmd_in_w(32'h0),
            .cmd_out_n(), .cmd_out_s(), .cmd_out_e(), .cmd_out_w(),

            .freeze_in(w_freeze[r][c]),
            .hold_in(w_hold[r][c]),
            .fb_internal_in(w_fbint[r][c]),
            .a_reemit_in(w_reemit[r][c]),
            .a_update_in(w_update[r][c]),
            .a_self_update_in(w_selfupd[r][c]),

            .program_in(w_program_out[r][c] | cmd_program_out[r][c]),
            .program_done(c_program_done[r][c]),

            .prog_data_in_n(w_prog_data[r][c]), .prog_data_in_s(32'h0),
            .prog_data_in_e(32'h0), .prog_data_in_w(cmd_data),
            .prog_arrived_in_n(w_prog_valid[r][c]), .prog_arrived_in_s(1'b0),
            .prog_arrived_in_e(1'b0), .prog_arrived_in_w(cmd_arrived),
            .prog_ack_out_n(), .prog_ack_out_s(), .prog_ack_out_e(), .prog_ack_out_w()
        );

    end
end
endgenerate

wire chain_tail_bit = wbus_data[CELLS][0] ^ wbus_valid[CELLS];
wire cmd_activity = cmd_program_out[0][0] ^ cmd_program_out[2][5] ^ cmd_program_out[4][9];

wire all_ready;
genvar rr, cc;
wire [ROWS*COLS-1:0] ready_flat;
generate
for (rr = 0; rr < ROWS; rr = rr + 1) begin : RRDY
    for (cc = 0; cc < COLS; cc = cc + 1) begin : CRDY
        assign ready_flat[rr*COLS+cc] = c_ready[rr][cc];
    end
end
endgenerate
assign all_ready = &ready_flat;

assign LED0_N = all_ready;
assign LED1_N = ~(stim_cnt[23] ^ chain_tail_bit ^ cmd_activity);

endmodule
