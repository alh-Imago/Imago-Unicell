// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_super_v3_branch_test_v1.v — points.md #548: the FIRST real
// Quartus attempt for unicell_super_v3.v, the 8-core shell
// (points.md #542) -- sim-verified clean (tb_unicell_super_v3.v,
// 12/12) but never yet on real silicon. Focused specifically on
// branch cell working through core_select routing -- the genuinely
// NEW capability this build needs to confirm; the other 7 cores
// already have real Quartus history via v1/v2 (#524/#526).
//
// THE REAL SHAPE, exactly matching tb_unicell_super_v3.v's own
// branch cell test and top_branch_cell_test_v1.v's own already-
// silicon-confirmed standalone design (#530/#541): upstream on N,
// reference seeded to 8. LOW(5) fires with marker 1. EQUAL(8) fires
// with marker 2. HIGH(10) is genuinely suppressed, checked over a
// real window, not absence-by-omission. Both real outcomes AND the
// real suppression checked on real silicon for the first time
// through the v3 shell's own core_select routing.
`default_nettype none
`timescale 1ns / 1ps

module top_super_v3_branch_test_v1 (
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
reg  [79:0] cfg_data = 0;
reg  [31:0] data_in_n = 0;
reg         arrived_n = 0;
reg         ack_in_e = 0;

wire [31:0] data_out_e;
wire        fire_e;

unicell_super_v3 DUT (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

function [79:0] pack(input [4:0] sel, input [41:0] core_cfg);
    pack = {13'b0, 20'h0, core_cfg, sel};
endfunction

localparam [4:0] SEL_BRANCH = 5'd7;

// Real branch cell config, per branch_cell_v1.v's own field map --
// IDENTICAL design to the one already confirmed on real silicon
// standalone (#530/#541): upstream_dir=N, LOW fires marker=1, EQUAL
// fires marker=2, HIGH genuinely suppressed (emit_high=0), both
// outcomes routed to E.
localparam [41:0] BR_CFG = {
    1'b0,      // [41]    rolling_mode
    4'h0,      // [40:37] route_high (unused, emit_high=0)
    4'b0100,   // [36:33] route_equal = E
    4'b0100,   // [32:29] route_low   = E
    1'b0,      // [28]    emit_high (genuine suppression)
    1'b1,      // [27]    emit_equal
    1'b1,      // [26]    emit_low
    7'd0,      // [25:19] fixed_value_high (unused)
    7'd2,      // [18:12] fixed_value_equal -- marker
    7'd1,      // [11:5]  fixed_value_low   -- marker
    1'b0,      // [4]     value_source_high
    1'b1,      // [3]     value_source_equal
    1'b1,      // [2]     value_source_low
    2'd0       // [1:0]   upstream_dir -- N
};

localparam [4:0] SETTLE = 5'd16;
localparam [4:0]
    S_CFG=0, S_SEED=1, S_LOW=2, S_ACK1=3, S_CHECK_LOW=4,
    S_EQ=5, S_ACK2=6, S_CHECK_EQ=7,
    S_HIGH=8, S_WATCH=9, S_DONE=10;

reg [4:0] state = S_CFG;
reg [4:0] settle_cnt = 0;
reg       err_sticky = 1'b0;
reg [5:0] suppress_watch_cnt = 0;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG;
        cfg_valid <= 0; cfg_data <= 80'h0;
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
                cfg_valid <= 1'b1; cfg_data <= pack(SEL_BRANCH, BR_CFG);
                settle_cnt <= 0; state <= S_SEED;
            end
            // Seed the reference to 8 -- the first real arrival,
            // held-reference mechanism.
            S_SEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd8; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_LOW;
            end
            // LOW: 5 < 8 -- must fire with the LOW marker (1)
            S_LOW: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd5; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_ACK1;
            end
            S_ACK1: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK_LOW;
            end
            S_CHECK_LOW: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd1) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_EQ;
            end
            // EQUAL: 8 == 8 -- must fire with the EQUAL marker (2)
            S_EQ: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd8; arrived_n <= 1'b1;
                settle_cnt <= 0; state <= S_ACK2;
            end
            S_ACK2: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; settle_cnt <= 0; state <= S_CHECK_EQ;
            end
            S_CHECK_EQ: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd2) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_HIGH;
            end
            // HIGH: 10 > 8 -- must NOT fire at all, checked over a
            // real window (genuine suppression, not absence-by-
            // omission)
            S_HIGH: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd10; arrived_n <= 1'b1;
                suppress_watch_cnt <= 0;
                state <= S_WATCH;
            end
            S_WATCH: begin
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

// points.md #529: real, JTAG-readable pass/fail, independent of the
// still-open LED-wiring question.
debug_issp_probe_v1 DEBUG_PROBE (
    .err_sticky(err_sticky),
    .heartbeat(hb_cnt[23])
);

endmodule
