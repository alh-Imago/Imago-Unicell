// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_sentinel_gather_1way_v1.v — Level 1 of the real scale family
// Alan asked for (1/3/9/27, each a genuinely separate, standalone
// buildable/testable unit, not one module switched by a parameter --
// "other users... may want just a few chains not lots"). Level 3
// (`top_sentinel_gather_shared_bram_v1.v`, #412-#415) is proven; this
// is the trivial base case, built to confirm the single-chain building
// block (addr_counter_v1 + accumulator + sentinel_counter_v1 + shared
// BRAM read) works completely on its own before anything is arbitrated
// across multiple chains.
//
// THE REAL SIMPLIFICATION at N=1, not a shortcut: with only one
// source, there is nothing to arbitrate -- no collector, no command
// sequencer, no round-robin `seq_index`/`active_dir_idx` needed at
// all. The header's own offer connects DIRECTLY to the queue. The one
// real thing that must still be reused precisely: `#414`/`#415`'s own
// hard-won readiness discipline ("data in then confirm, not ready...
// then capture") -- even with a single chain, the accumulator's own
// `want_to_offer` is unconditionally true from config time, so without
// a `fresh` gate the header would still offer its stale/default value
// before its own first real capture completes. Here `fresh` resets on
// every NEW read issue (there being no per-round boundary to key off,
// unlike the 3-way case's `col_program_done`) and sets once that same
// read's own capture lands.
`default_nettype none
`timescale 1ns / 1ps

module top_sentinel_gather_1way_v1 (
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

// ── The one chain's own address counter — WRAP_AT=3, matching the
// same 4-value block size used throughout this whole line of work. ──
wire [2:0] ac1_addr;
reg  ac1_advance_en = 0;
addr_counter_v1 #(.WIDTH(3), .WRAP_AT(3'd3)) AC1 (.clk(clk), .rst(rst), .advance_en(ac1_advance_en), .addr(ac1_addr));

// ── The one shared BRAM read port -- trivially satisfies #412's own
// "1 in, 1 out" constraint, since there is only ever one consumer. ──
reg        bram_cmd_valid = 1'b0;
reg        bram_cmd_op    = 1'b0;   // 0=READ, 1=WRITE -- shared across preload and normal reads
reg [2:0]  bram_cmd_addr  = 3'd0;
reg [39:0] bram_cmd_wdata = 40'h0;
wire       bram_rdata_valid;
wire [39:0] bram_rdata;

bram_controller_v1 #(.ADDR_WIDTH(3), .DATA_WIDTH(40)) BRAM (
    .clk(clk), .rst(rst),
    .cmd_valid(bram_cmd_valid), .cmd_op(bram_cmd_op),
    .cmd_addr(bram_cmd_addr), .cmd_wdata(bram_cmd_wdata),
    .rdata_valid(bram_rdata_valid), .rdata(bram_rdata), .write_done()
);

// ── Header (accumulator) — direct connection to the queue, no
// collector in between since there's nothing to arbitrate. ──
reg h1_cfg_valid = 0;
reg [79:0] h1_cfg_data = 80'h0;
reg h1_arrived_n = 0;
reg [31:0] h1_data_in_n = 0;
wire [31:0] h1_data_out_s;
wire h1_fire_s;
wire h1_ready_in_s;
wire h1_ack_out_s;
wire h1_ack_in_s;
wire h1_freeze;

// ── Queue (terminal RAM cell), directly connected to the header ──
reg q_cfg_valid = 0;
reg [79:0] q_cfg_data = 80'h0;
reg q_ack_in_n = 0;
wire q_ack_out_w;
wire [31:0] q_data_out_n;

// ── Sentinel — freeze_out stops the counter immediately on wrap;
// results_ready_flag (asserting only once the wrap-triggering value's
// own delivery is CONFIRMED complete, #410's own established fix)
// gates the accumulator's own freeze_in, so the last value is never
// stranded. ──
// Real bug found via sim, fixed here: the ORIGINAL wrap detection
// fired the moment the wrap-causing READ was ISSUED (`ac1_advance_en`
// pulsing on address 3), not when that read's own capture genuinely
// landed -- the exact same class of bug already found and fixed twice
// in #414/#415 (readiness exposed before data was confirmed), this
// time in the wrap/freeze path instead of the collector-readiness
// path. Confirmed directly via a bounded [WRAP]/[ACK] trace: wrap
// fired at h1acc=3 (BEFORE the 4th capture), permanently freezing the
// accumulator's own ability to offer before that 4th value ever
// completed its own offer+ack. Fixed the same way #415 fixed its own
// version of this: decouple "the address counter physically wraps" (a
// real, immediate, correct hardware event) from "the SENTINEL is told
// about it" (must wait until that SAME read's own capture lands).
wire h1_addr_will_wrap = (ac1_addr == 3'd3) && ac1_advance_en;
reg  wrap_pending = 1'b0;
always @(posedge clk) begin
    if (rst) wrap_pending <= 1'b0;
    else if (h1_addr_will_wrap) wrap_pending <= 1'b1;
    else if (h1_arrived_n) wrap_pending <= 1'b0;   // this specific capture has now landed
end
wire h1_out_wrap_pulse = wrap_pending && h1_arrived_n;
wire h1_freeze_out, h1_need_data, h1_results_ready, h1_safe, h1_err;
reg  h1_host_unfreeze = 1'b0;

// `fresh` (#415's own real fix, adapted for the no-round-robin case):
// resets the instant a NEW read is issued, sets once that SAME read's
// own capture lands -- prevents the continuously-live accumulator from
// ever offering its stale/default state before real data has arrived.
reg h1_fresh = 1'b0;

sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT1 (
    .clk(clk), .rst(rst),
    .feed_pulse(h1_arrived_n), .collect_pulse(h1_ack_in_s && h1_fresh),
    .chain_length(8'd1),
    .out_wrap_pulse(h1_out_wrap_pulse), .host_unfreeze_pulse(h1_host_unfreeze),
    .freeze_out(h1_freeze_out), .freeze_in(),
    .need_data_flag(h1_need_data), .results_ready_flag(h1_results_ready),
    .safe_to_intervene(h1_safe), .err_flag(h1_err), .diff_out()
);
assign h1_freeze = h1_results_ready;

// ── Feed generation: no round-robin, no sequencer -- the header is
// simply ready whenever it has fresh data and isn't frozen. Read
// pacing matches #410's own original discipline directly: the NEXT
// read is triggered by THIS chain's own prior ack (there being only
// one chain, no shared-port contention to arbitrate at all), plus a
// one-shot start pulse to kick off the very first read. ──
assign h1_ready_in_s = h1_fresh && !fired_this_round;
reg fired_this_round = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        fired_this_round <= 1'b0;
    end else if (bram_read_trigger) begin
        fired_this_round <= 1'b0;
    end else if (h1_ack_in_s) begin
        fired_this_round <= 1'b1;
    end
end

reg h1_start_pulse = 0;
wire h1_feed_trigger = (h1_start_pulse || h1_ack_in_s) && !h1_freeze_out;
wire bram_read_trigger = h1_feed_trigger;

reg [3:0] preload_idx = 0;
wire preload_active = (state == S_PRELOAD) && (preload_idx < 4'd4);

always @(posedge clk) begin
    bram_cmd_valid <= bram_read_trigger || preload_active;
    bram_cmd_addr  <= preload_active ? preload_idx[2:0] : ac1_addr;
    ac1_advance_en <= bram_read_trigger;

    if (bram_read_trigger) h1_fresh <= 1'b0;
    else if (bram_rdata_valid) h1_fresh <= 1'b1;

    h1_arrived_n <= bram_rdata_valid;
    h1_data_in_n <= bram_rdata[31:0];
end

unicell_super_v1 #(.CELL_ID(16'h0030)) H1 (
    .clk(clk), .rst(rst),
    .cfg_valid(h1_cfg_valid), .cfg_data(h1_cfg_data),
    .data_in_n(h1_data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h1_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(h1_data_out_s), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(h1_fire_s), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(h1_ready_in_s), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(h1_ack_out_s), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(h1_ack_in_s), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(h1_freeze),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

unicell_super_v1 #(.CELL_ID(16'h0031)) QUEUE (
    .clk(clk), .rst(rst),
    .cfg_valid(q_cfg_valid), .cfg_data(q_cfg_data),
    .data_in_n(h1_data_out_s), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h1_fire_s), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(q_data_out_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(h1_ack_in_s), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(q_ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

// ── Self-test FSM: config -> preload -> unfreeze -> start -> 4 real
// rounds (this chain's own full block) -> verify every value + final
// sentinel confirmation. ──
localparam [79:0] CFG_H1 = {13'b0, 20'b0, 30'b0, {4'b0010, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_Q  = {22'b0, {32'h0, 1'b0, 1'b0, 4'b0001, 4'b0001}, 5'd1};

localparam [4:0]
    S_CFG_H     = 0,
    S_PRELOAD   = 1,
    S_UNFREEZE  = 2,
    S_START     = 3,
    S_ROUND_WAIT = 4,
    S_ROUND_CHECK = 5,
    S_ROUND_DRAIN = 6,
    S_DONE      = 7;

reg [4:0] state = S_CFG_H;
reg [7:0] settle_cnt = 0;
reg       err_sticky = 1'b0;
reg [15:0] wait_cnt = 0;
reg [1:0] round_idx = 0;   // 0..3 -- one chain, one 4-value block

localparam [7:0] SETTLE = 8'd16;

function [31:0] expected_count;
    input [1:0] visit;
    begin
        case (visit)
            2'd0: expected_count = 32'd1;
            2'd1: expected_count = 32'd2;
            2'd2: expected_count = 32'd3;
            2'd3: expected_count = 32'd4;
            default: expected_count = 32'd0;
        endcase
    end
endfunction

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG_H;
        h1_cfg_valid <= 0; q_cfg_valid <= 0;
        h1_start_pulse <= 0; h1_host_unfreeze <= 0;
        q_ack_in_n <= 0;
        settle_cnt <= 0; wait_cnt <= 0; round_idx <= 0; preload_idx <= 0;
        err_sticky <= 1'b0;
    end else begin
        h1_cfg_valid <= 0; q_cfg_valid <= 0;
        h1_start_pulse <= 0; h1_host_unfreeze <= 0;
        q_ack_in_n <= 0;
        settle_cnt <= settle_cnt + 8'd1;

        case (state)
            S_CFG_H: begin
                h1_cfg_valid <= 1; h1_cfg_data <= CFG_H1;
                settle_cnt <= 0;
                preload_idx <= 0;
                state <= S_PRELOAD;
            end
            S_PRELOAD: begin
                bram_cmd_op <= 1'b1;
                bram_cmd_wdata <= {8'h0, 32'd100 + {28'h0, preload_idx}};
                if (preload_idx >= 4'd3) begin
                    settle_cnt <= 0;
                    state <= S_UNFREEZE;
                end else begin
                    preload_idx <= preload_idx + 4'd1;
                end
            end
            S_UNFREEZE: if (settle_cnt >= SETTLE) begin
                bram_cmd_op <= 1'b0;
                q_cfg_valid <= 1; q_cfg_data <= CFG_Q;
                h1_host_unfreeze <= 1;
                settle_cnt <= 0;
                state <= S_START;
            end
            S_START: if (settle_cnt >= SETTLE) begin
                h1_start_pulse <= 1;
                wait_cnt <= 0;
                state <= S_ROUND_WAIT;
            end
            S_ROUND_WAIT: begin
                wait_cnt <= wait_cnt + 16'd1;
                if (h1_ack_in_s) begin
                    state <= S_ROUND_CHECK;
                end else if (wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_ROUND_CHECK;
                end
            end
            S_ROUND_CHECK: begin
                if (q_data_out_n !== expected_count(round_idx)) err_sticky <= 1'b1;
                q_ack_in_n <= 1;
                if (round_idx == 2'd3) begin
                    state <= S_DONE;
                end else begin
                    round_idx <= round_idx + 2'd1;
                    wait_cnt <= 0;
                    state <= S_ROUND_WAIT;
                end
            end
            S_DONE: begin
                if (!h1_safe) err_sticky <= 1'b1;
                if (h1_err) err_sticky <= 1'b1;
            end
            default: state <= S_CFG_H;
        endcase
    end
end

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~err_sticky;

endmodule
