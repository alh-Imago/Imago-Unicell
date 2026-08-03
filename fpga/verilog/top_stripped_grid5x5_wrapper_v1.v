// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_grid5x5_wrapper_v1.v — STEP 2 of the points.md #103
// measurement campaign, RETROFITTED (points.md #128) to cell_wrapper_v2
// (#127) -- the wrapper's real, current design. PROGRAM now injects its 3
// words through each cell's ordinary North data port instead of writing
// cfg_data directly, and each cell's 6 control lines (freeze/hold/
// fb_internal/a_reemit/a_update/a_self_update) are now wired to the
// wrapper's persistent per-line latches instead of tied to 1'b0.
//
// Since PROGRAM shares the North port with normal grid data flow, each
// cell's North input is a simple 2:1 mux: wrapper's injection when THAT
// cell's own program_out is asserted, otherwise the normal grid neighbor
// (or the free-running seed at cell (0,0)) -- exactly Alan's own framing:
// programming can pause the data flow without needing a dedicated wire,
// since programming_active already takes top priority in the cell
// regardless of which direction a word arrives on.
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_grid5x5_wrapper_v1 (
    input  wire CLK_100M,
    output wire LED0_N,     // lit (low) whenever ANY of the 25 cells is NOT ready
    output wire LED1_N      // heartbeat
);

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

// ── Same snake routing_mask function as step 1 (#104) ──
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

// ── Program driver: walks address 0..24, 3 words per address, via the
// wrapper's PROGRAM opcode (was op=0, now OP_PROGRAM explicitly). ──
reg [4:0] prog_addr = 5'h0;
reg [1:0] prog_word = 2'h0;
reg       prog_active = 1'b1;

wire [2:0] prog_r = prog_addr / 5;
wire [2:0] prog_c = prog_addr % 5;
wire [31:0] prog_word0 = {22'h0, TOPO_NOR};
wire [31:0] prog_word1 = 32'h0;
wire [31:0] prog_word2 = {26'h0, snake_mask(prog_r, prog_c)};
wire [31:0] prog_data  = (prog_word == 2'd0) ? prog_word0 :
                          (prog_word == 2'd1) ? prog_word1 : prog_word2;

always @(posedge clk) begin
    if (rst) begin
        prog_addr   <= 5'h0;
        prog_word   <= 2'h0;
        prog_active <= 1'b1;
    end else if (prog_active) begin
        if (prog_word == 2'd2) begin
            prog_word <= 2'h0;
            if (prog_addr == 5'd24) prog_active <= 1'b0;
            else                    prog_addr   <= prog_addr + 5'd1;
        end else begin
            prog_word <= prog_word + 2'd1;
        end
    end
end

wire        w0_bus_in_valid = prog_active;
wire [4:0]  w0_bus_in_addr  = prog_addr;
wire [2:0]  w0_bus_in_op    = OP_PROGRAM;
wire [31:0] w0_bus_in_data  = prog_data;

// ── Per-cell signal arrays — identical grid interconnect to step 1 ──
wire [31:0] c_dout_n[0:4][0:4], c_dout_s[0:4][0:4], c_dout_e[0:4][0:4], c_dout_w[0:4][0:4];
wire        c_fire_n[0:4][0:4], c_fire_s[0:4][0:4], c_fire_e[0:4][0:4], c_fire_w[0:4][0:4];
wire        c_ready [0:4][0:4];
wire        c_ackn  [0:4][0:4], c_acks [0:4][0:4], c_acke [0:4][0:4], c_ackw [0:4][0:4];

// ── Wrapper daisy-chain signal arrays — 3-bit op now (was 1-bit in v1) ──
wire        wbus_valid[0:25];
wire [4:0]  wbus_addr [0:25];
wire [2:0]  wbus_op   [0:25];
wire [31:0] wbus_data [0:25];

assign wbus_valid[0] = w0_bus_in_valid;
assign wbus_addr[0]  = w0_bus_in_addr;
assign wbus_op[0]    = w0_bus_in_op;
assign wbus_data[0]  = w0_bus_in_data;

// ── Per-cell wrapper<->cell signal arrays (v2's expanded interface) ──
wire [31:0] w_prog_data [0:4][0:4];
wire        w_prog_valid[0:4][0:4];
wire        w_program_out[0:4][0:4];
wire        w_freeze[0:4][0:4], w_hold[0:4][0:4], w_fbint[0:4][0:4];
wire        w_reemit[0:4][0:4], w_update[0:4][0:4], w_selfupd[0:4][0:4];
wire        c_program_done[0:4][0:4];

genvar r, c;
generate
for (r = 0; r < 5; r = r + 1) begin : ROW
    for (c = 0; c < 5; c = c + 1) begin : COL

        localparam integer FLAT = r*5 + c;

        // Simplified DIAG word for this cost measurement -- {program_done,
        // ready_out} only; a_arrived/pending_ack aren't exposed as ports
        // on unicell_stripped_v1 (internal regs), so a full DIAG readback
        // would need those added as real ports -- flagged as future work,
        // not needed for measuring the wrapper's own area/Fmax cost here.
        wire [31:0] diag_word = {30'h0, c_program_done[r][c], c_ready[r][c]};

        cell_wrapper_v2 #(.ADDR(FLAT[4:0])) WRAP (
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

        unicell_stripped_v1 #(.CELL_ID({8'h0, r[3:0], c[3:0]})) CELL (
            .clk(clk), .rst(rst), .cfg_valid(1'b0), .cfg_data(128'h0),

            // North: 2:1 mux -- wrapper's PROGRAM injection when asserting
            // program_out for THIS cell, else the normal grid neighbor
            // (or the free-running seed at cell (0,0)).
            .data_in_n(w_program_out[r][c] ? w_prog_data[r][c] :
                       (r==0) ? ((c==0) ? seed_data : 32'h0) : c_dout_s[r-1][c]),
            .arrived_n(w_program_out[r][c] ? w_prog_valid[r][c] :
                       (r==0) ? ((c==0) ? seed_pulse : 1'b0) : c_fire_s[r-1][c]),
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

            .freeze_in(w_freeze[r][c]),
            .hold_in(w_hold[r][c]),
            .fb_internal_in(w_fbint[r][c]),
            .a_reemit_in(w_reemit[r][c]),
            .a_update_in(w_update[r][c]),
            .a_self_update_in(w_selfupd[r][c]),
            .program_in(w_program_out[r][c]),
            .program_done(c_program_done[r][c])
        );

    end
end
endgenerate

wire chain_tail_bit = wbus_data[25][0] ^ wbus_valid[25];

wire all_ready = c_ready[0][0] & c_ready[0][1] & c_ready[0][2] & c_ready[0][3] & c_ready[0][4]
                & c_ready[1][0] & c_ready[1][1] & c_ready[1][2] & c_ready[1][3] & c_ready[1][4]
                & c_ready[2][0] & c_ready[2][1] & c_ready[2][2] & c_ready[2][3] & c_ready[2][4]
                & c_ready[3][0] & c_ready[3][1] & c_ready[3][2] & c_ready[3][3] & c_ready[3][4]
                & c_ready[4][0] & c_ready[4][1] & c_ready[4][2] & c_ready[4][3] & c_ready[4][4];

assign LED0_N = all_ready;
assign LED1_N = ~(stim_cnt[23] ^ chain_tail_bit);

endmodule
