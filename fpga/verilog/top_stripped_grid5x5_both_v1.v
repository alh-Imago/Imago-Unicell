// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_stripped_grid5x5_both_v1.v — STEP 4 of the points.md #103
// measurement campaign: the SAME 25-cell grid as steps 1-3, with BOTH
// cell_wrapper_v1 (#99) AND cell_cardinal_cmd_v1 (#100) attached to every
// cell simultaneously, both genuinely active (real address/data traffic,
// same driver sequence feeding both in parallel — not just one dressed up
// as idle logic). This measures whether the combined cost is roughly
// additive against steps 2+3's individual deltas, or worse (shared
// routing/fan-out pressure competing for the same resources, per #103's
// own framing of why this step exists).
//
// The WRAPPER drives the cell's actual cfg_valid/cfg_data (the cheaper,
// already-proven mechanism, per #109/#111's comparison) — the cardinal
// command channel is fully present and doing its own real relay work in
// parallel, but its own cfg output is NOT wired to the cell (arbitrating
// two simultaneous config-drivers into one port is a separate design
// question, out of scope for this pure-cost measurement). Its output is
// still routed to an observable sink so it can't be optimized away.
`default_nettype none
`timescale 1ns / 1ps

module top_stripped_grid5x5_both_v1 (
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

reg [31:0] stim_cnt = 32'h0;
always @(posedge clk) if (!rst) stim_cnt <= stim_cnt + 32'h1;
wire        seed_pulse = (stim_cnt[7:0] == 8'h00);
wire [31:0] seed_data  = {stim_cnt[15:0], stim_cnt[31:16]};

// ── ONE shared program driver, feeding BOTH mechanisms in parallel — same
// stimulus, so the measured delta reflects both hardware paths being
// present and active, not an asymmetric driver difference. ──
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

// ── Data grid signal arrays (identical to steps 1-3) ──
wire [31:0] c_dout_n[0:4][0:4], c_dout_s[0:4][0:4], c_dout_e[0:4][0:4], c_dout_w[0:4][0:4];
wire        c_fire_n[0:4][0:4], c_fire_s[0:4][0:4], c_fire_e[0:4][0:4], c_fire_w[0:4][0:4];
wire        c_ready [0:4][0:4];
wire        c_ackn  [0:4][0:4], c_acks [0:4][0:4], c_acke [0:4][0:4], c_ackw [0:4][0:4];

// ── Wrapper daisy-chain (identical to step 2) ──
wire        wbus_valid[0:25];
wire [4:0]  wbus_addr [0:25];
wire        wbus_op   [0:25];
wire [31:0] wbus_data [0:25];
assign wbus_valid[0] = prog_active;
assign wbus_addr[0]  = prog_addr;
assign wbus_op[0]    = 1'b0;
assign wbus_data[0]  = prog_data;
wire [127:0] w_cfg_data[0:4][0:4];
wire         w_cfg_valid[0:4][0:4];

// ── Cardinal command channel signal arrays (identical to step 3) ──
wire        cv_n[0:4][0:4], cv_s[0:4][0:4], cv_e[0:4][0:4], cv_w[0:4][0:4];
wire [4:0]  ca_n[0:4][0:4], ca_s[0:4][0:4], ca_e[0:4][0:4], ca_w[0:4][0:4];
wire        co_n[0:4][0:4], co_s[0:4][0:4], co_e[0:4][0:4], co_w[0:4][0:4];
wire [31:0] cd_n[0:4][0:4], cd_s[0:4][0:4], cd_e[0:4][0:4], cd_w[0:4][0:4];
wire [127:0] cmd_cfg_data[0:4][0:4];   // NOT wired to the cell — observable sink only
wire         cmd_cfg_valid[0:4][0:4];

genvar r, c;
generate
for (r = 0; r < 5; r = r + 1) begin : ROW
    for (c = 0; c < 5; c = c + 1) begin : COL

        localparam integer FLAT = r*5 + c;
        localparam [5:0] MY_SNAKE_MASK = snake_mask(r[2:0], c[2:0]);

        // ── Wrapper — drives the cell's real cfg_valid/cfg_data ──
        cell_wrapper_v1 #(.ADDR(FLAT[4:0])) WRAP (
            .clk(clk), .rst(rst),
            .bus_in_valid(wbus_valid[FLAT]), .bus_in_addr(wbus_addr[FLAT]),
            .bus_in_op(wbus_op[FLAT]),       .bus_in_data(wbus_data[FLAT]),
            .bus_out_valid(wbus_valid[FLAT+1]), .bus_out_addr(wbus_addr[FLAT+1]),
            .bus_out_op(wbus_op[FLAT+1]),       .bus_out_data(wbus_data[FLAT+1]),
            .cell_cfg_valid(w_cfg_valid[r][c]), .cell_cfg_data(w_cfg_data[r][c]),
            .cell_out_buffer(c_dout_n[r][c]),   .cell_ready(c_ready[r][c])
        );

        // ── Cardinal command channel — fully active in parallel, same
        // stimulus, but NOT wired to the cell's cfg port (see header). ──
        cell_cardinal_cmd_v1 #(
            .ADDR(FLAT[4:0]),
            .RELAY_DIR( MY_SNAKE_MASK[0] ? 2'b00 :
                        MY_SNAKE_MASK[1] ? 2'b01 :
                        MY_SNAKE_MASK[2] ? 2'b10 : 2'b11 ),
            .RELAY_NONE( MY_SNAKE_MASK == 6'b0 )
        ) CMD (
            .clk(clk), .rst(rst),

            .cmdv_in_n((r==0) ? ((c==0) ? prog_active : 1'b0) : cv_s[r-1][c]),
            .cmda_in_n((r==0) ? ((c==0) ? prog_addr   : 5'h0) : ca_s[r-1][c]),
            .cmdo_in_n((r==0) ? 1'b0 : co_s[r-1][c]),
            .cmdd_in_n((r==0) ? ((c==0) ? prog_data   : 32'h0) : cd_s[r-1][c]),

            .cmdv_in_s((r==4) ? 1'b0 : cv_n[r+1][c]),
            .cmda_in_s((r==4) ? 5'h0 : ca_n[r+1][c]),
            .cmdo_in_s((r==4) ? 1'b0 : co_n[r+1][c]),
            .cmdd_in_s((r==4) ? 32'h0 : cd_n[r+1][c]),

            .cmdv_in_e((c==4) ? 1'b0 : cv_w[r][c+1]),
            .cmda_in_e((c==4) ? 5'h0 : ca_w[r][c+1]),
            .cmdo_in_e((c==4) ? 1'b0 : co_w[r][c+1]),
            .cmdd_in_e((c==4) ? 32'h0 : cd_w[r][c+1]),

            .cmdv_in_w((c==0) ? 1'b0 : cv_e[r][c-1]),
            .cmda_in_w((c==0) ? 5'h0 : ca_e[r][c-1]),
            .cmdo_in_w((c==0) ? 1'b0 : co_e[r][c-1]),
            .cmdd_in_w((c==0) ? 32'h0 : cd_e[r][c-1]),

            .cmdv_out_n(cv_n[r][c]), .cmda_out_n(ca_n[r][c]), .cmdo_out_n(co_n[r][c]), .cmdd_out_n(cd_n[r][c]),
            .cmdv_out_s(cv_s[r][c]), .cmda_out_s(ca_s[r][c]), .cmdo_out_s(co_s[r][c]), .cmdd_out_s(cd_s[r][c]),
            .cmdv_out_e(cv_e[r][c]), .cmda_out_e(ca_e[r][c]), .cmdo_out_e(co_e[r][c]), .cmdd_out_e(cd_e[r][c]),
            .cmdv_out_w(cv_w[r][c]), .cmda_out_w(ca_w[r][c]), .cmdo_out_w(co_w[r][c]), .cmdd_out_w(cd_w[r][c]),

            .cell_cfg_valid(cmd_cfg_valid[r][c]), .cell_cfg_data(cmd_cfg_data[r][c]),
            .cell_out_buffer(c_dout_n[r][c])
        );

        unicell_stripped_v1 #(.CELL_ID({8'h0, r[3:0], c[3:0]})) CELL (
            .clk(clk), .rst(rst),
            .cfg_valid(w_cfg_valid[r][c]), .cfg_data(w_cfg_data[r][c]),

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



            .fb_internal_in(1'b0)
        );

    end
end
endgenerate

// ── Observable sinks for both chains' tails — neither can be optimized
// away, even though only the wrapper drives the real cell config.
// points.md #113 fix: the FIRST version of this only reduced 5 of 25
// cardinal-command cells' cfg outputs into this sink (the diagonal) --
// meaning Quartus could legitimately prove the other 20 cells' address-
// match/word-assembly logic (the expensive part, per step 3/#111) had no
// observable effect and strip it out, understating the true combined
// cost. Fixed: reduce ALL 25 cells' cfg_valid and a representative data
// bit into the sink, so nothing can be proven dead. ──
wire cmd_cfg_valid_any =
      cmd_cfg_valid[0][0] | cmd_cfg_valid[0][1] | cmd_cfg_valid[0][2] | cmd_cfg_valid[0][3] | cmd_cfg_valid[0][4]
    | cmd_cfg_valid[1][0] | cmd_cfg_valid[1][1] | cmd_cfg_valid[1][2] | cmd_cfg_valid[1][3] | cmd_cfg_valid[1][4]
    | cmd_cfg_valid[2][0] | cmd_cfg_valid[2][1] | cmd_cfg_valid[2][2] | cmd_cfg_valid[2][3] | cmd_cfg_valid[2][4]
    | cmd_cfg_valid[3][0] | cmd_cfg_valid[3][1] | cmd_cfg_valid[3][2] | cmd_cfg_valid[3][3] | cmd_cfg_valid[3][4]
    | cmd_cfg_valid[4][0] | cmd_cfg_valid[4][1] | cmd_cfg_valid[4][2] | cmd_cfg_valid[4][3] | cmd_cfg_valid[4][4];

wire cmd_cfg_data_any =
      cmd_cfg_data[0][0][0] ^ cmd_cfg_data[0][1][0] ^ cmd_cfg_data[0][2][0] ^ cmd_cfg_data[0][3][0] ^ cmd_cfg_data[0][4][0]
    ^ cmd_cfg_data[1][0][0] ^ cmd_cfg_data[1][1][0] ^ cmd_cfg_data[1][2][0] ^ cmd_cfg_data[1][3][0] ^ cmd_cfg_data[1][4][0]
    ^ cmd_cfg_data[2][0][0] ^ cmd_cfg_data[2][1][0] ^ cmd_cfg_data[2][2][0] ^ cmd_cfg_data[2][3][0] ^ cmd_cfg_data[2][4][0]
    ^ cmd_cfg_data[3][0][0] ^ cmd_cfg_data[3][1][0] ^ cmd_cfg_data[3][2][0] ^ cmd_cfg_data[3][3][0] ^ cmd_cfg_data[3][4][0]
    ^ cmd_cfg_data[4][0][0] ^ cmd_cfg_data[4][1][0] ^ cmd_cfg_data[4][2][0] ^ cmd_cfg_data[4][3][0] ^ cmd_cfg_data[4][4][0];

wire wrapper_tail_bit  = wbus_data[25][0]  ^ wbus_valid[25];
wire cardinal_tail_bit = cd_n[4][4][0] ^ cv_n[4][4];
wire cmd_cfg_activity  = cmd_cfg_valid_any | cmd_cfg_data_any;

wire all_ready = c_ready[0][0] & c_ready[0][1] & c_ready[0][2] & c_ready[0][3] & c_ready[0][4]
                & c_ready[1][0] & c_ready[1][1] & c_ready[1][2] & c_ready[1][3] & c_ready[1][4]
                & c_ready[2][0] & c_ready[2][1] & c_ready[2][2] & c_ready[2][3] & c_ready[2][4]
                & c_ready[3][0] & c_ready[3][1] & c_ready[3][2] & c_ready[3][3] & c_ready[3][4]
                & c_ready[4][0] & c_ready[4][1] & c_ready[4][2] & c_ready[4][3] & c_ready[4][4];

assign LED0_N = all_ready;
assign LED1_N = ~(stim_cnt[23] ^ wrapper_tail_bit ^ cardinal_tail_bit ^ cmd_cfg_activity);

endmodule
