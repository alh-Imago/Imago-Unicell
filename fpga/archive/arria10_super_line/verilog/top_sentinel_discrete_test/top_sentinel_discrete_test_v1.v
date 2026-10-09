// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_sentinel_discrete_test_v1.v — points.md #294/#295/#297's design,
// made real-hardware-buildable. NOT YET BUILT — prepared project. Real
// synthesizable version of the proven `tb_sentinel_discrete_full_v1.v`
// topology: accumulator_cell_v1.v -> compare_cell_v1.v -> latch_cell_
// v1.v, the first real Quartus attempt for any of these three cells.
//
// Same real self-test discipline as every other top-level here: no
// fixed literal stimulus values (the `#283`/`#286` constant-propagation
// lesson) — the feed count genuinely varies pass to pass via a
// free-running offset, so Quartus can't optimize the real logic away.
//
// Self-test FSM replicates the exact proven sequence from `tb_
// sentinel_discrete_full_v1.v`: feed past the threshold (crossing it,
// confirming the latch sets), collect back below it WITHOUT unfreezing
// (confirming genuinely sticky — the honest gap `#295` found and
// `#297` closed), then genuine recovery (unfreeze, confirming it
// clears). LED0 heartbeats; LED1 (active-low: LIT=error) should never
// light on correct hardware.
`default_nettype none
`timescale 1ns / 1ps

module top_sentinel_discrete_test_v1 (
    input  wire CLK_100M,
    output wire LED0_N,
    output wire LED1_N
);

localparam [3:0] DIR_N = 4'b0001, DIR_S = 4'b0010, DIR_E = 4'b0100, DIR_W = 4'b1000;

// ── Clock/reset — same convention as every other project here ──────────
reg [1:0] div_cnt = 2'b00;
always @(posedge CLK_100M) div_cnt <= div_cnt + 2'd1;
wire clk = div_cnt[1];   // 25 MHz

reg [3:0] rst_sr = 4'hF;
always @(posedge clk) rst_sr <= {rst_sr[2:0], 1'b0};
wire rst = rst_sr[3];

// ── One-shot configuration — 3 cells, one cycle, per-instance cfg_valid ──
localparam [63:0] CFG_ACC = {27'h0, 16'h0000, 1'b0, 8'h01, DIR_E, DIR_S, DIR_N};   // inc=N, dec=S, offer=E, step_amount=1 explicit (#506/#515)
localparam [63:0] CFG_CMP = {24'h0, 32'sd8, DIR_N, DIR_E};                 // threshold=8, in=N, offer=E
localparam [63:0] CFG_LAT = {52'h0, DIR_E, DIR_S, DIR_N};                  // set=N, clear=S, offer=E

reg cfg_pulse = 1'b0;
reg [2:0] cfg_step = 3'd0;
reg trigger_reconfig = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        cfg_step  <= 3'd0;
        cfg_pulse <= 1'b0;
    end else if (trigger_reconfig) begin
        cfg_step <= 3'd0;   // real fix: re-arm the config pulse every
                             // pass, not just once at power-on -- an
                             // earlier draft never reconfigured after
                             // the first pass, meaning the accumulator
                             // carried over between passes and made
                             // S_CHECK3's "expect cleared" check
                             // fundamentally wrong from pass 2 onward
                             // (found via direct trace of ACC.accumulator
                             // across passes, not assumed)
    end else if (cfg_step == 3'd0) begin
        cfg_pulse <= 1'b1;
        cfg_step  <= 3'd1;
    end else if (cfg_step == 3'd1) begin
        cfg_pulse <= 1'b0;
        cfg_step  <= 3'd2;
    end
end
wire cfg_active = cfg_pulse;

// ════════════════════════════════════════════════════════════════════
reg feed_pulse = 0, collect_pulse = 0;
wire [31:0] acc_data_out_e;
wire acc_fire_e, cmp_ready_o, cmp_ack_out_n;

accumulator_cell_v1 #(.CELL_ID(16'h0003), .WIDTH(32)) ACC (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_ACC),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(feed_pulse), .arrived_s(collect_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(acc_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(acc_fire_e), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(cmp_ready_o), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cmp_ack_out_n), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(), .status_negative()
);

wire [31:0] cmp_data_out_e;
wire cmp_fire_e, lat_ready_o, lat_ack_out_n;

compare_cell_v1 #(.CELL_ID(16'h0004)) CMP (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_CMP),
    .data_in_n(acc_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(acc_fire_e), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(cmp_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(cmp_fire_e), .fire_w(),
    .ready_out(cmp_ready_o),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(lat_ready_o), .ready_in_w(1'b1),
    .ack_out_n(cmp_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(lat_ack_out_n), .ack_in_w(1'b0),
    .freeze_in(1'b0), .status_data_valid()
);

reg unfreeze_pulse = 0;
wire [31:0] lat_data_out_e;
wire lat_fire_e;
reg cons_ack = 0;

latch_cell_v1 #(.CELL_ID(16'h0006)) LAT (
    .clk(clk), .rst(rst), .cfg_valid(cfg_active), .cfg_data(CFG_LAT),
    .data_in_n(cmp_data_out_e), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(cmp_fire_e), .arrived_s(unfreeze_pulse), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(lat_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(lat_fire_e), .fire_w(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(lat_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(cons_ack), .ack_in_w(1'b0),
    .freeze_in(1'b0), .ready_out(lat_ready_o), .status_latched()
);

// ════════════════════════════════════════════════════════════════════
// Self-test FSM — genuinely varying feed count each pass (#283/#286's
// own lesson: literal constants let Quartus optimize real logic away).
// ════════════════════════════════════════════════════════════════════
localparam S_CFGWAIT  = 4'd0,
           S_FEED     = 4'd1, S_FEED_WAIT  = 4'd2,
           S_CHECK1   = 4'd3,
           S_COLLECT  = 4'd4, S_COLLECT_WAIT = 4'd5,
           S_CHECK2   = 4'd6,
           S_UNFREEZE = 4'd7, S_UNFREEZE_WAIT = 4'd8,
           S_CHECK3   = 4'd9,
           S_RUN      = 4'd10;

reg [3:0]  state = S_CFGWAIT;
reg [3:0]  feed_count = 0;
reg [3:0]  feed_target = 4'd9;
reg [3:0]  collect_count = 0;
reg [4:0]  settle_cnt = 0;
reg        err_sticky = 0;
reg [23:0] heartbeat = 0;
reg [15:0] pass_offset = 0;

localparam SETTLE = 5'd20;

always @(posedge clk) begin
    feed_pulse    <= 1'b0;
    collect_pulse <= 1'b0;
    unfreeze_pulse <= 1'b0;
    cons_ack      <= 1'b0;
    heartbeat     <= heartbeat + 24'h1;

    if (rst) begin
        state <= S_CFGWAIT;
        feed_count <= 0; collect_count <= 0; settle_cnt <= 0;
        err_sticky <= 0; pass_offset <= 0;
    end else begin
        case (state)
            S_CFGWAIT: if (!cfg_active && cfg_step == 3'd2) begin
                feed_target <= 4'd9 + pass_offset[1:0];
                state <= S_FEED;
            end

            S_FEED: begin
                if (feed_count < feed_target) begin
                    feed_pulse <= 1'b1;
                    feed_count <= feed_count + 4'd1;
                    settle_cnt <= 0;
                    state <= S_FEED_WAIT;
                end else begin
                    state <= S_CHECK1;
                end
            end
            S_FEED_WAIT: begin
                settle_cnt <= settle_cnt + 5'd1;
                if (settle_cnt >= SETTLE) state <= S_FEED;
            end

            S_CHECK1: begin
                if (lat_data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
                collect_count <= 0;
                state <= S_COLLECT;
            end

            S_COLLECT: begin
                if (collect_count < 4'd3) begin
                    collect_pulse <= 1'b1;
                    collect_count <= collect_count + 4'd1;
                    settle_cnt <= 0;
                    state <= S_COLLECT_WAIT;
                end else begin
                    state <= S_CHECK2;
                end
            end
            S_COLLECT_WAIT: begin
                settle_cnt <= settle_cnt + 5'd1;
                if (settle_cnt >= SETTLE) state <= S_COLLECT;
            end

            S_CHECK2: begin
                if (lat_data_out_e[0] !== 1'b1) err_sticky <= 1'b1;
                state <= S_UNFREEZE;
            end

            S_UNFREEZE: begin
                unfreeze_pulse <= 1'b1;
                settle_cnt <= 0;
                state <= S_UNFREEZE_WAIT;
            end
            S_UNFREEZE_WAIT: begin
                settle_cnt <= settle_cnt + 5'd1;
                if (settle_cnt >= SETTLE) state <= S_CHECK3;
            end

            S_CHECK3: begin
                if (lat_data_out_e[0] !== 1'b0) err_sticky <= 1'b1;
                state <= S_RUN;
            end

            S_RUN: begin
                pass_offset <= pass_offset + 16'h1;
                feed_count <= 0;
                trigger_reconfig <= 1'b1;
                state <= S_CFGWAIT;
            end

            default: state <= S_CFGWAIT;
        endcase

        if (lat_fire_e) cons_ack <= 1'b1;
        if (state != S_RUN) trigger_reconfig <= 1'b0;
    end
end

assign LED0_N = ~heartbeat[21];
assign LED1_N = ~err_sticky;

endmodule
