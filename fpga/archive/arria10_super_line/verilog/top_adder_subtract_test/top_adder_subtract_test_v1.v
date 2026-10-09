// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_adder_subtract_test_v1.v — first real Quartus attempt for
// adder_cell_v1.v's own subtract_mode (points.md #521) -- sim-verified
// clean (tb_adder_cell_v1.v) but never yet touched real silicon.
// top_adder_chain50_v1.v already exists but only ever configures
// subtract_mode=0 (plain add) -- this is the real, dedicated check for
// the NEW mode specifically. Standalone instance, same "SIZE/TIMING
// CHECK" discipline top_adder_chain50_v1.v already established.
//
// THE REAL CLAIM BEING CHECKED ON SILICON: A=23 (first arrival, N),
// B=7 (second arrival, W), subtract_mode=1 -> must produce 16 (23-7),
// not 30 (23+7). A second pair, A=7 B=23, must produce a genuine
// BORROW -- -16 in two's complement (0xFFFFFFF0) -- confirming the
// carry-chain hardware genuinely computes a signed result, not just a
// same-magnitude check that could pass by coincidence.
`default_nettype none
`timescale 1ns / 1ps

module top_adder_subtract_test_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

reg         cfg_valid = 0;
reg  [63:0] cfg_data  = 0;
reg  [31:0] data_in_n = 0, data_in_w = 0;
reg         arrived_n = 0, arrived_w = 0;
reg         ack_in_e  = 0;

wire [31:0] data_out_e;
wire        fire_e;

adder_cell_v1 #(.CELL_ID(16'h0002)) DUT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(data_in_w),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(arrived_w),
    .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_data_valid(), .status_a_arrived()
);

// cfg_data[63:0], per adder_cell_v1.v's own real field map:
// {55'h0 reserved, subtract_mode(1), upstream_mask(4), downstream_mask(4)}
// upstream = N|W (A arrives N, B arrives W), downstream = E.
localparam [63:0] CFG_SUB = {55'h0, 1'b1, 4'b1001, 4'b0100};

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG=0, S_A1=1, S_A1_WAIT=2, S_B1=3, S_B1_WAIT=4, S_ACK1=5, S_CHECK1=6,
    S_A2=7,  S_A2_WAIT=8, S_B2=9, S_B2_WAIT=10, S_ACK2=11, S_CHECK2=12,
    S_DONE=13;

reg [4:0] state = S_CFG;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG;
        cfg_valid <= 0; cfg_data <= 64'h0;
        arrived_n <= 0; arrived_w <= 0; ack_in_e <= 0;
        data_in_n <= 0; data_in_w <= 0;
        settle_cnt <= 0;
        err_sticky <= 1'b0;
    end else begin
        cfg_valid <= 1'b0;
        arrived_n <= 1'b0;
        arrived_w <= 1'b0;
        ack_in_e  <= 1'b0;
        settle_cnt <= settle_cnt + 5'd1;

        case (state)
            S_CFG: begin
                cfg_valid <= 1'b1; cfg_data <= CFG_SUB;
                settle_cnt <= 0; state <= S_A1;
            end
            // ═══ 23 - 7 = 16, no borrow ═══
            S_A1: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd23; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_A1_WAIT;
            end
            S_A1_WAIT: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_B1;
            end
            S_B1: begin
                data_in_w <= 32'd7; arrived_w <= 1'b1;
                settle_cnt <= 0; state <= S_B1_WAIT;
            end
            S_B1_WAIT: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_ACK1;
            end
            S_ACK1: begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK1;
            end
            S_CHECK1: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd16) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_A2;
            end
            // ═══ 7 - 23 = -16 -- a real borrow, two's complement
            // 0xFFFFFFF0. Same config, no reconfigure needed. ═══
            S_A2: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd7; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_A2_WAIT;
            end
            S_A2_WAIT: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_B2;
            end
            S_B2: begin
                data_in_w <= 32'd23; arrived_w <= 1'b1;
                settle_cnt <= 0; state <= S_B2_WAIT;
            end
            S_B2_WAIT: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_ACK2;
            end
            S_ACK2: begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK2;
            end
            S_CHECK2: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'hFFFFFFF0) err_sticky <= 1'b1;
                state <= S_DONE;
            end
            S_DONE: begin
                // test complete, result latched in err_sticky, stays here
            end
            default: state <= S_CFG;
        endcase
    end
end

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~err_sticky;   // active-low: LIT = error

// points.md #529/#531: same real ISSP debug channel proven on the
// branch cell test -- a JTAG-readable pass/fail that doesn't depend
// on whether LED0_N/LED1_N actually reach a physical LED on this
// board (the still-open real question from #528).
debug_issp_probe_v1 DEBUG_PROBE (
    .err_sticky(err_sticky),
    .heartbeat(hb_cnt[23])
);

endmodule
