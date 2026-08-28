// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_branch_cell_test_v1.v — the FIRST real Quartus attempt for
// branch_cell_v1.v, full stop. This core (points.md #500/#504/#497)
// has never touched real silicon in any form -- not through this top,
// not through the shell (it has no real core_select slot in any
// unicell_super_*.v file at all, per icm_v3.py's own honest flag on
// this, #519). Every real ALM/Fmax number for this core is currently
// unknown. Standalone instance, same "SIZE/TIMING CHECK" discipline
// this session's other new self-tests already established.
//
// THE REAL CLAIM BEING CHECKED ON SILICON: upstream on N, reference
// seeded to 8 (the first real arrival). A LOW value (5) must fire on E
// with the LOW outcome's own fixed marker (1). An EQUAL value (8) must
// fire on E with the EQUAL outcome's own fixed marker (2). A HIGH
// value (10) must NOT fire at all -- a genuine SUPPRESSION
// (emit_high=0), checked over a real window, not absence-by-omission.
`default_nettype none
`timescale 1ns / 1ps

module top_branch_cell_test_v1 (
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

branch_cell_v1 #(.CELL_ID(16'h0004)) DUT (
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

// cfg_data[63:0], per branch_cell_v1.v's own real field map:
// upstream_dir=N(0), value_source_low=1, value_source_equal=1,
// value_source_high=0 (irrelevant, emit_high=0), fixed_value_low=1,
// fixed_value_equal=2, fixed_value_high=0, emit_low=1, emit_equal=1,
// emit_high=0 (genuine suppression), route_low=E, route_equal=E,
// route_high=0, rolling_mode=0.
localparam [63:0] CFG_BR = {
    22'h0,              // [63:42] reserved
    1'b0,               // [41]    rolling_mode
    4'h0,               // [40:37] route_high (unused, emit_high=0)
    4'b0100,            // [36:33] route_equal = E
    4'b0100,            // [32:29] route_low   = E
    1'b0,               // [28]    emit_high (genuine suppression)
    1'b1,               // [27]    emit_equal
    1'b1,               // [26]    emit_low
    7'd0,               // [25:19] fixed_value_high (unused)
    7'd2,               // [18:12] fixed_value_equal -- marker
    7'd1,               // [11:5]  fixed_value_low   -- marker
    1'b0,               // [4]     value_source_high
    1'b1,               // [3]     value_source_equal
    1'b1,               // [2]     value_source_low
    2'd0                // [1:0]   upstream_dir -- N
};

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG=0, S_SEED=1, S_WAIT_SEED=2,
    S_LOW=3, S_WAIT_LOW=4, S_ACK_LOW=5, S_CHECK_LOW=6,
    S_EQ=7,  S_WAIT_EQ=8,  S_ACK_EQ=9,  S_CHECK_EQ=10,
    S_HIGH=11, S_WATCH_SUPPRESS=12, S_DONE=13;

reg [4:0] state = S_CFG;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;
reg [5:0] suppress_watch_cnt = 0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG;
        cfg_valid <= 0; cfg_data <= 64'h0;
        arrived_n <= 0; data_in_n <= 0; ack_in_e <= 0;
        settle_cnt <= 0;
        err_sticky <= 1'b0;
        suppress_watch_cnt <= 0;
    end else begin
        cfg_valid <= 1'b0;
        arrived_n <= 1'b0;
        ack_in_e  <= 1'b0;
        settle_cnt <= settle_cnt + 5'd1;

        case (state)
            S_CFG: begin
                cfg_valid <= 1'b1; cfg_data <= CFG_BR;
                settle_cnt <= 0; state <= S_SEED;
            end
            // ═══ Seed the reference to 8 -- the first real arrival,
            // held-reference mechanism (#497) ═══
            S_SEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd8; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_WAIT_SEED;
            end
            S_WAIT_SEED: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_LOW;
            end
            // ═══ LOW: 5 < 8 -- must fire with the LOW marker (1) ═══
            S_LOW: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd5; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_WAIT_LOW;
            end
            S_WAIT_LOW: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_ACK_LOW;
            end
            S_ACK_LOW: begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK_LOW;
            end
            S_CHECK_LOW: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd1) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_EQ;
            end
            // ═══ EQUAL: 8 == 8 -- must fire with the EQUAL marker (2) ═══
            S_EQ: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd8; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_WAIT_EQ;
            end
            S_WAIT_EQ: if (settle_cnt >= SETTLE) begin
                settle_cnt <= 0; state <= S_ACK_EQ;
            end
            S_ACK_EQ: begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK_EQ;
            end
            S_CHECK_EQ: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd2) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_HIGH;
            end
            // ═══ HIGH: 10 > 8 -- must NOT fire at all, checked over a
            // real window (genuine suppression, not absence-by-
            // omission) ═══
            S_HIGH: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd10; arrived_n <= 1'b1;
                suppress_watch_cnt <= 0;
                state <= S_WATCH_SUPPRESS;
            end
            S_WATCH_SUPPRESS: begin
                if (fire_e) err_sticky <= 1'b1;
                suppress_watch_cnt <= suppress_watch_cnt + 6'd1;
                if (suppress_watch_cnt >= 6'd32) state <= S_DONE;
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
