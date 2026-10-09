// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_compare_test_v1.v — points.md #548: the FIRST real Quartus
// attempt for compare_cell_v1.v standalone, full stop. Every real
// Quartus number for this core so far has only ever come from within
// the super carrier shell (unicell_super_v1.v/v2.v, #524/#526) --
// this is its own, isolated cost and the first real silicon
// functional confirmation on its own.
//
// THE REAL CLAIM BEING CHECKED ON SILICON: threshold=8, real
// signed >= comparison (confirmed directly against the RTL, not
// assumed). A=10 must produce result_bit=1 (10>=8). A=5 must produce
// result_bit=0 (5<8) -- both real outcomes checked, not just one.
//
// ISSP-equipped from the start (points.md #529's own proven pattern)
// -- LED-based confirmation on this board has an unresolved real
// uncertainty (#528) and the fixed-gap read script has a real
// aliasing risk (#537); debug_issp_poll.tcl is the trustworthy path.
`default_nettype none
`timescale 1ns / 1ps

module top_compare_test_v1 (
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
reg         arrived_n = 0;
reg         ack_in_e  = 0;

wire [31:0] data_out_e;
wire        fire_e;

compare_cell_v1 #(.CELL_ID(16'h0006)) DUT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_data_valid()
);

// cfg_data[63:0], per compare_cell_v1.v's own real field map:
// downstream_mask=E, upstream_mask=N, threshold=8.
localparam [63:0] CFG_CMP = {24'h0, 32'sd8, 4'b0001, 4'b0100};

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG=0, S_HIGH=1, S_ACK1=2, S_CHECK_HIGH=3,
    S_LOW=4, S_ACK2=5, S_CHECK_LOW=6, S_DONE=7;

reg [4:0] state = S_CFG;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG;
        cfg_valid <= 0; cfg_data <= 64'h0;
        arrived_n <= 0; data_in_n <= 0; ack_in_e <= 0;
        settle_cnt <= 0;
        err_sticky <= 1'b0;
    end else begin
        cfg_valid <= 1'b0;
        arrived_n <= 1'b0;
        ack_in_e  <= 1'b0;
        settle_cnt <= settle_cnt + 5'd1;

        case (state)
            S_CFG: begin
                cfg_valid <= 1'b1; cfg_data <= CFG_CMP;
                settle_cnt <= 0; state <= S_HIGH;
            end
            // ═══ 10 >= 8 -- must produce result_bit=1 ═══
            S_HIGH: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd10; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_ACK1;
            end
            S_ACK1: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK_HIGH;
            end
            S_CHECK_HIGH: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_LOW;
            end
            // ═══ 5 < 8 -- must produce result_bit=0 ═══
            S_LOW: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd5; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_ACK2;
            end
            S_ACK2: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK_LOW;
            end
            S_CHECK_LOW: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b0) err_sticky <= 1'b1;
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

// points.md #529: real, JTAG-readable pass/fail, independent of the
// still-open LED-wiring question.
debug_issp_probe_v1 DEBUG_PROBE (
    .err_sticky(err_sticky),
    .heartbeat(hb_cnt[23])
);

endmodule
