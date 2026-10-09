// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_unicell_super_test_v3.v — points.md #573: the full 8-core self-
// test top-level for unicell_super_v3.v, never previously built as a
// standalone Quartus target (only top_super_v3_branch_test_v1.v, the
// branch-cell-only slice from #548/#550, existed). Cloned from
// top_unicell_super_test_v2.v (real Quartus baseline 305 ALM /
// 99.57 MHz, #526), extended with the same real branch-cell round
// already proven through core_select routing in tb_unicell_super_v3.v
// (#542) and on real silicon standalone (#530). Built now specifically
// to give a real, same-session, apples-to-apples Quartus baseline
// against top_unicell_super_test_v4.v's own shared-storage version --
// the actual comparative round #565 item 2 calls for (ALM/Fmax, one
// real internal register set per core vs. one real shared register).
//
// Same self-test discipline as every other top-level here: an ISSP
// debug probe (#528/#529's own JTAG-readable pattern, not LED-
// dependent) exposes err_sticky + heartbeat.
`default_nettype none
`timescale 1ns / 1ps

module top_unicell_super_test_v3 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

// ── Clock/reset — same convention as every other project here ──────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── The super cell itself ───────────────────────────────────────────
reg         cfg_valid = 0;
reg  [79:0] cfg_data  = 80'h0;
reg  [31:0] data_in_n = 0, data_in_w = 0;
reg         arrived_n = 0, arrived_w = 0;
reg         ack_in_e  = 0;

wire [31:0] data_out_n, data_out_e;
wire        fire_e;
wire [4:0]  status_core_select;

unicell_super_v3 DUT (
    .clk(clk), .rst(rst),
    .cfg_valid(cfg_valid), .cfg_data(cfg_data),
    .data_in_n(data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(data_in_w),
    .arrived_n(arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(arrived_w),
    .data_out_n(data_out_n), .data_out_s(), .data_out_e(data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(fire_e), .fire_w(),
    .ready_out(), .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select(status_core_select)
);

// ── SUPER_LATCH construction, matching tb_unicell_super_v3.v's own
// pack() function exactly. ──
function [79:0] pack(input [4:0] sel, input [41:0] core_cfg);
    pack = {13'b0, 20'h0, core_cfg, sel};
endfunction

localparam [79:0] CFG_RAM   = pack(5'd1, {32'hCAFEBEEF, 1'b1, 1'b1, 4'h0, 4'b0001});
localparam [79:0] CFG_ADDER = pack(5'd2, 42'h094);
localparam [79:0] CFG_ACC   = pack(5'd3, {5'h0, 16'h0, 1'b0, 8'h01, 4'b0100, 4'b0000, 4'b0001});
localparam [79:0] CFG_CMP   = pack(5'd4, {32'sd8, 4'b0001, 4'b0100});
localparam [79:0] CFG_LAT   = pack(5'd5, {30'h0, 4'b0100, 4'b0000, 4'b0001});
localparam [79:0] CFG_NANO  = pack(5'd0, {19'h0, 6'h01, 1'b1, 10'h004});
localparam [79:0] CFG_SEQ   = pack(5'd6, {4'b0, 4'b0100, 2'd1, 8'd0, 8'd0, 8'd66, 8'd55});
// Branch cell (v3, new): upstream=N, LOW->marker1, EQUAL->marker2,
// HIGH genuinely suppressed, all routed to E -- matching
// tb_unicell_super_v3.v's own BR_CFG exactly.
localparam [41:0] BR_CFG = {
    1'b0, 4'h0, 4'b0100, 4'b0100, 1'b0, 1'b1, 1'b1,
    7'd0, 7'd2, 7'd1, 1'b0, 1'b1, 1'b1, 2'd0
};
localparam [79:0] CFG_BRANCH = pack(5'd7, BR_CFG);

reg [4:0] cfg_step = 5'd0;
localparam [4:0] SETTLE = 5'd16;

localparam [5:0]
    S_RAM_CFG=0,  S_RAM_CHECK=1,
    S_ADD_CFG=2,  S_ADD_A=3, S_ADD_A_WAIT=4, S_ADD_B=5, S_ADD_B_WAIT=6,
    S_ADD_ACK=7,  S_ADD_CHECK=8,
    S_ACC_CFG=9,  S_ACC_F1=10, S_ACC_A1=11, S_ACC_F2=12, S_ACC_A2=13,
    S_ACC_F3=14,  S_ACC_A3=15, S_ACC_CHECK=16,
    S_CMP_CFG=17, S_CMP_FEED=18, S_CMP_CHECK=19,
    S_LAT_CFG=20, S_LAT_FEED=21, S_LAT_ACK=22, S_LAT_CHECK=23,
    S_NANO_CFG=24,S_NANO_FEED=25,S_NANO_CHECK=26,
    S_SEQ_CFG=27, S_SEQ_CHECK_INITIAL=28, S_SEQ_ACK1=29, S_SEQ_CHECK2=30,
    S_SEQ_ACK2=31, S_SEQ_CHECK3=32,
    S_BR_CFG=33,  S_BR_SEED=34, S_BR_LOW=35, S_BR_LOW_ACK=36, S_BR_LOW_CHECK=37,
    S_BR_EQ=38,   S_BR_EQ_ACK=39, S_BR_EQ_CHECK=40,
    S_BR_HIGH=41, S_BR_HIGH_CHECK=42,
    S_DONE=43;

reg [5:0]  state = S_RAM_CFG;
reg [4:0]  settle_cnt = 0;
reg        err_sticky = 1'b0;

task do_load(input [79:0] word, input [5:0] next_state);
    begin
        cfg_valid <= 1'b1;
        cfg_data  <= word;
        settle_cnt <= 0;
        state <= next_state;
    end
endtask

always @(posedge clk) begin
    if (rst) begin
        state <= S_RAM_CFG;
        cfg_valid <= 0; cfg_data <= 80'h0;
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
            S_RAM_CFG: do_load(CFG_RAM, S_RAM_CHECK);
            S_RAM_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_n !== 32'hCAFEBEEF) err_sticky <= 1'b1;
                do_load(CFG_ADDER, S_ADD_A);
            end

            S_ADD_A: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd100; arrived_n <= 1'b1;
                state <= S_ADD_A_WAIT; settle_cnt <= 0;
            end
            S_ADD_A_WAIT: if (settle_cnt >= SETTLE) begin
                state <= S_ADD_B; settle_cnt <= 0;
            end
            S_ADD_B: begin
                data_in_w <= 32'd23; arrived_w <= 1'b1;
                state <= S_ADD_B_WAIT; settle_cnt <= 0;
            end
            S_ADD_B_WAIT: if (settle_cnt >= SETTLE) begin
                state <= S_ADD_ACK; settle_cnt <= 0;
            end
            S_ADD_ACK: begin
                ack_in_e <= 1'b1;
                state <= S_ADD_CHECK; settle_cnt <= 0;
            end
            S_ADD_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd123) err_sticky <= 1'b1;
                do_load(CFG_ACC, S_ACC_F1);
            end

            S_ACC_F1: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; state <= S_ACC_A1; settle_cnt <= 0;
            end
            S_ACC_A1: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; state <= S_ACC_F2; settle_cnt <= 0;
            end
            S_ACC_F2: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; state <= S_ACC_A2; settle_cnt <= 0;
            end
            S_ACC_A2: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; state <= S_ACC_F3; settle_cnt <= 0;
            end
            S_ACC_F3: if (settle_cnt >= SETTLE) begin
                arrived_n <= 1'b1; state <= S_ACC_A3; settle_cnt <= 0;
            end
            S_ACC_A3: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; state <= S_ACC_CHECK; settle_cnt <= 0;
            end
            S_ACC_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd3) err_sticky <= 1'b1;
                do_load(CFG_CMP, S_CMP_FEED);
            end

            S_CMP_FEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd10; arrived_n <= 1'b1;
                state <= S_CMP_CHECK; settle_cnt <= 0;
            end
            S_CMP_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
                do_load(CFG_LAT, S_LAT_FEED);
            end

            S_LAT_FEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'h1; arrived_n <= 1'b1;
                state <= S_LAT_ACK; settle_cnt <= 0;
            end
            S_LAT_ACK: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; state <= S_LAT_CHECK; settle_cnt <= 0;
            end
            S_LAT_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
                do_load(CFG_NANO, S_NANO_FEED);
            end

            S_NANO_FEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'hFFFFFFFF; arrived_n <= 1'b1;
                data_in_w <= 32'h00000000; arrived_w <= 1'b1;
                state <= S_NANO_CHECK; settle_cnt <= 0;
            end
            S_NANO_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_n === 32'hxxxxxxxx) err_sticky <= 1'b1;
                do_load(CFG_SEQ, S_SEQ_CHECK_INITIAL);
            end

            S_SEQ_CHECK_INITIAL: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd55) err_sticky <= 1'b1;
                ack_in_e <= 1'b1; state <= S_SEQ_ACK1; settle_cnt <= 0;
            end
            S_SEQ_ACK1: if (settle_cnt >= SETTLE) begin
                state <= S_SEQ_CHECK2; settle_cnt <= 0;
            end
            S_SEQ_CHECK2: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd66) err_sticky <= 1'b1;
                ack_in_e <= 1'b1; state <= S_SEQ_ACK2; settle_cnt <= 0;
            end
            S_SEQ_ACK2: if (settle_cnt >= SETTLE) begin
                state <= S_SEQ_CHECK3; settle_cnt <= 0;
            end
            S_SEQ_CHECK3: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd55) err_sticky <= 1'b1;
                do_load(CFG_BRANCH, S_BR_SEED);
            end

            // ═══ BRANCH — v3's own new core, matching tb_unicell_
            // super_v3.v's own real, substantive sequence: seed the
            // reference at 8, then LOW/EQUAL/HIGH, HIGH genuinely
            // suppressed (checked over a real held window, not a
            // single sample). ═══
            S_BR_SEED: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd8; arrived_n <= 1'b1;
                state <= S_BR_LOW; settle_cnt <= 0;
            end
            S_BR_LOW: if (settle_cnt >= SETTLE) begin
                data_in_n <= 32'd5; arrived_n <= 1'b1;
                state <= S_BR_LOW_ACK; settle_cnt <= 0;
            end
            S_BR_LOW_ACK: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; state <= S_BR_LOW_CHECK; settle_cnt <= 0;
            end
            S_BR_LOW_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd1) err_sticky <= 1'b1;
                state <= S_BR_EQ; settle_cnt <= 0;
            end
            S_BR_EQ: begin
                data_in_n <= 32'd8; arrived_n <= 1'b1;
                state <= S_BR_EQ_ACK; settle_cnt <= 0;
            end
            S_BR_EQ_ACK: if (settle_cnt >= SETTLE) begin
                ack_in_e <= 1'b1; state <= S_BR_EQ_CHECK; settle_cnt <= 0;
            end
            S_BR_EQ_CHECK: if (settle_cnt >= SETTLE) begin
                if (data_out_e !== 32'd2) err_sticky <= 1'b1;
                state <= S_BR_HIGH; settle_cnt <= 0;
            end
            S_BR_HIGH: begin
                data_in_n <= 32'd10; arrived_n <= 1'b1;
                state <= S_BR_HIGH_CHECK; settle_cnt <= 0;
            end
            S_BR_HIGH_CHECK: begin
                // genuine suppression, checked over the WHOLE held
                // window, not a single sample at the end -- matching
                // tb_unicell_super_v3.v's own repeat(20) discipline.
                if (fire_e) err_sticky <= 1'b1;
                if (settle_cnt >= SETTLE * 2) state <= S_DONE;
            end

            S_DONE: begin
                // test complete, result latched in err_sticky
            end

            default: state <= S_RAM_CFG;
        endcase
    end
end

// ── Heartbeat + ISSP-based error report (#528/#529's own pattern --
// LED-independent, JTAG-readable via quartus_stp). ──
reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~err_sticky;

debug_issp_probe_v1 DEBUG_PROBE (
    .err_sticky(err_sticky),
    .heartbeat(hb_cnt[23])
);

endmodule
