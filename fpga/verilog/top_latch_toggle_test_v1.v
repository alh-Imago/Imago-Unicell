// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_latch_toggle_test_v1.v — first real Quartus attempt for
// latch_cell_v1.v's own toggle_dir (points.md #522) -- sim-verified
// clean (tb_latch_cell_v1.v) but never yet touched real silicon.
// Standalone instance, same "SIZE/TIMING CHECK" discipline this
// session's other new self-tests already established.
//
// THE REAL CLAIM BEING CHECKED ON SILICON: set on N, clear on S,
// toggle on W, offer on E. A single toggle from the reset state (0)
// must flip to 1; a second toggle must flip back to 0 (a genuine
// flip both directions, not a disguised set). Then SET+TOGGLE the
// SAME cycle must land on SET's own value (the real CLEAR>SET>TOGGLE
// priority chain), confirming priority resolves correctly in real
// silicon, not just simulation.
`default_nettype none
`timescale 1ns / 1ps

module top_latch_toggle_test_v1 (
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
reg  [31:0] data_in_n = 0;
reg         arrived_n = 0, arrived_s = 0, arrived_w = 0;
reg         ack_in_e  = 0;

wire [31:0] data_out_e;
wire        fire_e;

latch_cell_v1 #(.CELL_ID(16'h0003)) DUT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(arrived_s), .arrived_e(1'b0), .arrived_w(arrived_w),
    .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_latched()
);

// cfg_data[63:0], per latch_cell_v1.v's own real field map:
// {48'h0 reserved, toggle_dir(4), downstream_mask(4), clear_dir(4), set_dir(4)}
// set=N, clear=S, downstream=E, toggle=W.
localparam [63:0] CFG_TOG = {48'h0, 4'b1000, 4'b0100, 4'b0010, 4'b0001};

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG=0, S_TOG1=1, S_ACK1=2, S_CHECK1=3,
    S_TOG2=4, S_ACK2=5, S_CHECK2=6,
    S_SET_TOG=7, S_ACK3=8, S_CHECK3=9, S_DONE=10;

reg [4:0] state = S_CFG;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG;
        cfg_valid <= 0; cfg_data <= 64'h0;
        arrived_n <= 0; arrived_s <= 0; arrived_w <= 0; ack_in_e <= 0;
        data_in_n <= 0;
        settle_cnt <= 0;
        err_sticky <= 1'b0;
    end else begin
        cfg_valid <= 1'b0;
        arrived_n <= 1'b0; arrived_s <= 1'b0; arrived_w <= 1'b0;
        ack_in_e  <= 1'b0;
        settle_cnt <= settle_cnt + 5'd1;

        case (state)
            S_CFG: begin
                cfg_valid <= 1'b1; cfg_data <= CFG_TOG;
                settle_cnt <= 0; state <= S_TOG1;
            end
            // ═══ Toggle from 0 -> 1 ═══
            S_TOG1: if (settle_cnt >= SETTLE) begin
                arrived_w <= 1'b1; settle_cnt <= 0; state <= S_ACK1;
            end
            S_ACK1: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK1;
            end
            S_CHECK1: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_TOG2;
            end
            // ═══ Toggle again -- 1 -> 0, a genuine flip ═══
            S_TOG2: if (settle_cnt >= SETTLE) begin
                arrived_w <= 1'b1; settle_cnt <= 0; state <= S_ACK2;
            end
            S_ACK2: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK2;
            end
            S_CHECK2: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b0) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_SET_TOG;
            end
            // ═══ SET + TOGGLE same cycle -- SET must win (real
            // CLEAR>SET>TOGGLE priority chain) ═══
            S_SET_TOG: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'h1; arrived_n <= 1'b1; arrived_w <= 1'b1;
                settle_cnt <= 0; state <= S_ACK3;
            end
            S_ACK3: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK3;
            end
            S_CHECK3: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
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

endmodule
