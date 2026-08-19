// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_collector_mechanism_v1.v — the first real, self-contained,
// Quartus-buildable top-level for the header/collector/command/queue
// RAM-interface mechanism (points.md #381/#382/#390/#395/#396/#397).
// Directly follows `tests/fpga/tb_full_collector_mechanism_v1.v`'s own
// proven wiring and 3-round sequence (3 headers, 1 collector, 1 command
// sequencer, 1 queue, as genuinely separate physical instances) — same
// self-test FSM/LED discipline as `top_unicell_super_test_v1.v`.
//
// The ONE real, new piece of RTL this top-level required, not present
// in the testbench: `#397`'s own honestly-flagged gap -- "readiness-
// gating in this test is testbench-driven... not yet derived from the
// command sequencer's own state automatically." A self-contained board
// has no host to drive that gating, so it is derived here, for the
// first time, directly and combinationally from the sequencer's own
// `seq_index`: only the currently-selected header's `ready_in` toward
// the collector is ever asserted. This is the smallest real addition
// that makes the already-proven mechanism autonomous.
//
// Scope: the flat 3-header case only (the one actually proven at RTL
// level, #397) -- NOT the full 27-leaf hierarchical tree (#402, VM-level
// only so far). Building THIS first, smallest-proven-unit-first, gives
// a real per-chain ALM/Fmax baseline the 27-leaf estimate in
// `docs/stripped-cell/design-notes/ram_interface_collector_mechanism.md`
// can be checked against, rather than jumping straight to an unbuilt,
// much bigger design.
`default_nettype none
`timescale 1ns / 1ps

module top_collector_mechanism_v1 (
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

// ── Header 1 (north of collector) ──
reg h1_cfg_valid = 0;
reg [79:0] h1_cfg_data = 80'h0;
reg h1_arrived_n = 0;
wire [31:0] h1_data_out_s;
wire h1_fire_s;
wire h1_ready_in_s;
wire h1_ack_out_s;
wire h1_ack_in_s;

// ── Header 2 (south of collector) ──
reg h2_cfg_valid = 0;
reg [79:0] h2_cfg_data = 80'h0;
reg h2_arrived_n = 0;
wire [31:0] h2_data_out_n;
wire h2_fire_n;
wire h2_ready_in_n;
wire h2_ack_out_n;
wire h2_ack_in_n;

// ── Header 3 (west of collector) ──
reg h3_cfg_valid = 0;
reg [79:0] h3_cfg_data = 80'h0;
reg h3_arrived_n = 0;
wire [31:0] h3_data_out_e;
wire h3_fire_e;
wire h3_ready_in_e;
wire h3_ack_out_e;
wire h3_ack_in_e;

// ── Collector (center) ──
reg col_cfg_valid = 0;
reg [79:0] col_cfg_data = 80'h0;
wire [31:0] col_data_out_e;
wire col_fire_e;
wire col_ack_in_e;
wire col_program_done;
wire [4:0] col_status_core_select;

// ── Queue (east of collector, terminal RAM cell) ──
reg q_cfg_valid = 0;
reg [79:0] q_cfg_data = 80'h0;
reg q_ack_in_w = 0;
wire q_ack_out_w;
reg q_ack_in_n = 0;   // dummy drain ack -- simulates a real downstream consumer

// ── Command sequencer -- 3-value cycle: N, S, W (matching the 3 headers) ──
wire seq_program_out;
wire [31:0] seq_prog_data_out;
wire seq_prog_arrived_out;
reg advance_trigger = 0;
wire [1:0] seq_index;

// ── THE NEW PIECE: autonomous ready_in gating -- replaces the
// testbench's own manual per-round h1_ready_in_s/h2_ready_in_n/
// h3_ready_in_e control. Matches the exact same VALUE_0/1/2 -> header
// assignment the testbench proved: index 0 selects H1 (N-relay), index
// 1 selects H2 (S-relay), index 2 selects H3 (W-relay).
//
// A REAL BUG found and fixed via sim, not assumed correct from the
// testbench's own text: gating directly on the sequencer's own
// `seq_index` is ambiguous -- `seq_index` names the round about to be
// (or being) programmed, not the round whose cardinal_edge write has
// actually been CONFIRMED applied. `seq_index==0` is true both before
// the very first round ever begins (cardinal_edge still at its
// power-on default, consume-mode) AND once round 1 is genuinely
// relay-armed -- releasing a header's readiness on the first case let
// it deliver into a collector that was still in consume mode, which
// silently STORES the first arrival as an ordinary operand rather than
// relaying it; the header's own continuously-live re-offer then landed
// as a genuine SECOND operand, triggering a real, spurious two-input
// gate computation and fire -- consuming the queue's one-shot capture
// before round 1's real delivery ever got a chance. `active_dir_idx`
// below is captured the instant `col_program_done` actually pulses --
// only a CONFIRMED-applied direction ever releases its header. ──
reg        active_dir_valid = 1'b0;
reg [1:0]  active_dir_idx   = 2'd0;
always @(posedge clk) begin
    if (rst) begin
        active_dir_valid <= 1'b0;
        active_dir_idx   <= 2'd0;
    end else if (col_program_done) begin
        active_dir_valid <= 1'b1;
        active_dir_idx   <= seq_index;   // seq_index still holds the
                                          // JUST-completed round's own
                                          // index this same cycle (NBA
                                          // semantics -- the sequencer's
                                          // own seq_index<=... update
                                          // resolves alongside this read,
                                          // not before it).
    end
end

// A SECOND real bug, matching #397's own Finding 5 exactly, found and
// fixed here for the first time in synthesizable RTL (the testbench
// only ever needed to fix it at the host/simulation-control level):
// `active_dir_idx` alone stays fixed for the ENTIRE round -- including
// the whole drain/settle window -- so a continuously-live header kept
// re-offering and getting re-relayed repeatedly after its own first,
// correct delivery, since nothing dropped its readiness until the
// NEXT round's programming completed. `fired_this_round` closes that
// window immediately: cleared the instant a new round's programming is
// confirmed (`col_program_done`), set the instant that round's own
// relay is observed (`col_fire_e`) -- masking the active header's own
// readiness for the remainder of the round, not just until the next
// one begins.
// A FIFTH real bug, matching #397's own Finding 5 more precisely than
// the first attempt at this fix: masking off `fired_this_round` from
// `col_fire_e` (a registered wire, one hop downstream of the actual
// accept decision) leaves exactly one cycle where a header, having
// just been acked and become ready again on its OWN side, can sneak in
// a SECOND legitimate relay of its own value before the mask lands --
// confirmed directly via sim (col_pend re-asserted to 4 the cycle
// immediately after correctly clearing to 0). The header's own ack
// signal (`h1_ack_in_s`/`h2_ack_in_n`/`h3_ack_in_e`) is the lowest-
// latency real signal for "this round's one expected offer was just
// consumed" -- using it closes the race with zero extra register hops.
reg fired_this_round = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        fired_this_round <= 1'b0;
    end else if (col_program_done) begin
        fired_this_round <= 1'b0;
    end else if (h1_ack_in_s || h2_ack_in_n || h3_ack_in_e) begin
        fired_this_round <= 1'b1;
    end
end

assign h1_ready_in_s = active_dir_valid && (active_dir_idx == 2'd0) && !fired_this_round;
assign h2_ready_in_n = active_dir_valid && (active_dir_idx == 2'd1) && !fired_this_round;
assign h3_ready_in_e = active_dir_valid && (active_dir_idx == 2'd2) && !fired_this_round;

cell_command_sequencer_v1 #(
    .VALUE_0(4'b0001), .VALUE_1(4'b0010), .VALUE_2(4'b1000), .VALUE_3(4'b0000),
    .SEQUENCE_LEN(2'd3)
) SEQ (
    .clk(clk), .rst(rst),
    .advance_trigger(advance_trigger),
    .program_done_in(col_program_done),
    .program_out(seq_program_out),
    .prog_data_out(seq_prog_data_out),
    .prog_arrived_out(seq_prog_arrived_out),
    .seq_index(seq_index)
);

unicell_super_v1 #(.CELL_ID(16'h0010)) H1 (
    .clk(clk), .rst(rst),
    .cfg_valid(h1_cfg_valid), .cfg_data(h1_cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h1_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(h1_data_out_s), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(h1_fire_s), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(h1_ready_in_s), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(h1_ack_out_s), .ack_out_e(), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(h1_ack_in_s), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

unicell_super_v1 #(.CELL_ID(16'h0011)) H2 (
    .clk(clk), .rst(rst),
    .cfg_valid(h2_cfg_valid), .cfg_data(h2_cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h2_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(h2_data_out_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(h2_fire_n), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(h2_ready_in_n), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(h2_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(h2_ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

unicell_super_v1 #(.CELL_ID(16'h0012)) H3 (
    .clk(clk), .rst(rst),
    .cfg_valid(h3_cfg_valid), .cfg_data(h3_cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h3_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(h3_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(h3_fire_e), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(h3_ready_in_e), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(h3_ack_out_e), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(h3_ack_in_e), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

// Collector -- receives H1 on its own N, H2 on its own S, H3 on its own W;
// relays whichever is currently selected out its own E, toward the queue.
unicell_super_v1 #(.CELL_ID(16'h0013)) COLLECTOR (
    .clk(clk), .rst(rst),
    .cfg_valid(col_cfg_valid), .cfg_data(col_cfg_data),
    .data_in_n(h1_data_out_s), .data_in_s(h2_data_out_n), .data_in_e(32'h0), .data_in_w(h3_data_out_e),
    .arrived_n(h1_fire_s), .arrived_s(h2_fire_n), .arrived_e(1'b0), .arrived_w(h3_fire_e),
    .data_out_n(), .data_out_s(), .data_out_e(col_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(col_fire_e), .fire_w(),
    .ready_out(),
    .ready_in_n(h1_ready_in_s), .ready_in_s(h2_ready_in_n), .ready_in_e(1'b1), .ready_in_w(h3_ready_in_e),
    .ack_out_n(h1_ack_in_s), .ack_out_s(h2_ack_in_n), .ack_out_e(), .ack_out_w(h3_ack_in_e),
    .ack_in_n(h1_ack_out_s), .ack_in_s(h2_ack_out_n), .ack_in_e(col_ack_in_e), .ack_in_w(h3_ack_out_e),
    .freeze_in(1'b0),
    .program_in(seq_program_out), .program_done(col_program_done),
    .prog_data_in_n(seq_prog_data_out), .prog_data_in_s(seq_prog_data_out),
    .prog_data_in_e(seq_prog_data_out), .prog_data_in_w(seq_prog_data_out),
    .prog_arrived_in_n(seq_prog_arrived_out), .prog_arrived_in_s(1'b0),
    .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select(col_status_core_select)
);

// Queue -- a real RAM cell, terminal, receives from the collector on its own W.
unicell_super_v1 #(.CELL_ID(16'h0014)) QUEUE (
    .clk(clk), .rst(rst),
    .cfg_valid(q_cfg_valid), .cfg_data(q_cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(col_data_out_e),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(col_fire_e),
    .data_out_n(), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(q_ack_out_w),
    .ack_in_n(q_ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(q_ack_in_w),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

assign col_ack_in_e = q_ack_out_w;   // collector's own downstream ack comes from the queue

// ── Self-test FSM -- reproduces tb_full_collector_mechanism_v1.v's own
// proven sequence exactly (config load, 3 pre-increments, 3 rounds +
// wraparound), but autonomously: no external stimulus, ready_in gating
// now self-derived from seq_index above instead of host-driven. ──
localparam [79:0] CFG_H1  = {13'b0, 20'b0, 30'b0, {4'b0010, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_H2  = {13'b0, 20'b0, 30'b0, {4'b0001, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_H3  = {13'b0, 20'b0, 30'b0, {4'b0100, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_COL = {13'b0, 20'b0, 6'b0, 6'b000100, 1'b1, 10'b0, 5'd0};
localparam [79:0] CFG_Q   = {22'b0, {32'h0, 1'b0, 1'b0, 4'b1000, 4'b0001}, 5'd1};

localparam [5:0]
    S_CFG_H       = 0,
    S_PRE_H1      = 1,
    S_PRE_H2A     = 2,
    S_PRE_H2B     = 3,
    S_PRE_H3A     = 4,
    S_PRE_H3B     = 5,
    S_PRE_H3C     = 6,
    S_CFG_COL_Q   = 7,
    S_CHECK_SEL   = 8,
    S_R1_START    = 9,
    S_R1_WAIT_PROG = 10,
    S_R1_WAIT_ACK = 11,
    S_R1_CHECK    = 12,
    S_R2_START    = 13,
    S_R2_WAIT_PROG = 14,
    S_R2_WAIT_ACK = 15,
    S_R2_CHECK    = 16,
    S_R3_START    = 17,
    S_R3_WAIT_PROG = 18,
    S_R3_WAIT_ACK = 19,
    S_R3_CHECK    = 20,
    S_DONE        = 21;

reg [5:0] state = S_CFG_H;
reg [7:0] settle_cnt = 0;
reg       err_sticky = 1'b0;
reg [15:0] fire_wait_cnt = 0;
reg [15:0] ack_wait_cnt = 0;

localparam [4:0] SETTLE = 5'd16;
// A real Verilog width bug found and fixed via sim, not assumed: `SETTLE
// << 3` truncates to SETTLE's own declared 5-bit width (16<<3=128 wraps
// to 0 mod 32), silently defeating the wider post-fire settle margin
// this needed. A properly-sized constant avoids the ambiguity entirely.
localparam [15:0] POST_FIRE_SETTLE = 16'd128;

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG_H;
        h1_cfg_valid <= 0; h2_cfg_valid <= 0; h3_cfg_valid <= 0;
        col_cfg_valid <= 0; q_cfg_valid <= 0;
        h1_arrived_n <= 0; h2_arrived_n <= 0; h3_arrived_n <= 0;
        advance_trigger <= 0;
        q_ack_in_n <= 0; q_ack_in_w <= 0;
        settle_cnt <= 0; fire_wait_cnt <= 0; ack_wait_cnt <= 0;
        err_sticky <= 1'b0;
    end else begin
        h1_cfg_valid <= 0; h2_cfg_valid <= 0; h3_cfg_valid <= 0;
        col_cfg_valid <= 0; q_cfg_valid <= 0;
        h1_arrived_n <= 0; h2_arrived_n <= 0; h3_arrived_n <= 0;
        advance_trigger <= 0;
        q_ack_in_n <= 0;
        settle_cnt <= settle_cnt + 8'd1;

        case (state)
            // ═══ load H1/H2/H3 as accumulators, downstream toward the collector.
            // Real ordering, matching tb_full_collector_mechanism_v1.v exactly:
            // headers are pre-incremented WHILE the collector remains
            // unconfigured (disarmed, start_flag=0) -- deliver()'s own
            // effective_freeze gating means an unarmed collector simply
            // rejects/retries any early arrival rather than consuming it.
            // Configuring the collector BEFORE pre-increment (this file's
            // own first, wrong attempt) let it actively gate-consume the
            // headers' early fires in cardinal_edge=0 (default consume)
            // mode, corrupting state -- found and fixed via real sim, not
            // assumed correct from the testbench's own text alone. ═══
            S_CFG_H: begin
                h1_cfg_valid <= 1; h1_cfg_data <= CFG_H1;
                h2_cfg_valid <= 1; h2_cfg_data <= CFG_H2;
                h3_cfg_valid <= 1; h3_cfg_data <= CFG_H3;
                settle_cnt <= 0;
                state <= S_PRE_H1;
            end

            // ═══ pre-increment: H1 x1, H2 x2, H3 x3 -- distinct real values ═══
            S_PRE_H1: if (settle_cnt >= SETTLE) begin
                h1_arrived_n <= 1; settle_cnt <= 0; state <= S_PRE_H2A;
            end
            S_PRE_H2A: if (settle_cnt >= SETTLE) begin
                h2_arrived_n <= 1; settle_cnt <= 0; state <= S_PRE_H2B;
            end
            S_PRE_H2B: if (settle_cnt >= SETTLE) begin
                h2_arrived_n <= 1; settle_cnt <= 0; state <= S_PRE_H3A;
            end
            S_PRE_H3A: if (settle_cnt >= SETTLE) begin
                h3_arrived_n <= 1; settle_cnt <= 0; state <= S_PRE_H3B;
            end
            S_PRE_H3B: if (settle_cnt >= SETTLE) begin
                h3_arrived_n <= 1; settle_cnt <= 0; state <= S_PRE_H3C;
            end
            S_PRE_H3C: if (settle_cnt >= SETTLE) begin
                h3_arrived_n <= 1; settle_cnt <= 0; state <= S_CFG_COL_Q;
            end
            S_CFG_COL_Q: if (settle_cnt >= SETTLE) begin
                col_cfg_valid <= 1; col_cfg_data <= CFG_COL;
                q_cfg_valid   <= 1; q_cfg_data   <= CFG_Q;
                settle_cnt <= 0;
                state <= S_CHECK_SEL;
            end
            S_CHECK_SEL: if (settle_cnt >= SETTLE) begin
                if (col_status_core_select != 5'd0) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_R1_START;
            end

            // ═══ ROUND 1: seq_index=0 -> H1 selected (ready_in self-gated above) ═══
            // ═══ THE REAL ROOT CAUSE, found via sim after several false
            // starts, worth recording precisely: the collector's own
            // `ready_in_e` is hardwired to 1 (matching the proven
            // testbench's own same simplification) -- meaning it ALWAYS
            // offers toward the queue the instant it has something,
            // completely independent of whether the queue can actually
            // accept it. The queue only captures when its OWN
            // `data_valid` is 0. Round 1 works immediately because the
            // queue starts empty. Every later round FAILS to complete on
            // its own -- the collector's own offer sits pending forever,
            // never acked -- because the queue is still holding the
            // PREVIOUS round's un-drained value. Earlier versions of this
            // FSM tried draining AFTER waiting for that round's own ack,
            // which can never arrive because the drain is the very thing
            // that unblocks it -- a real ordering inversion, not a
            // timing-margin problem. The fix: drain the queue FIRST,
            // unconditionally, at the start of every round (a safe no-op
            // when there's nothing to drain, confirmed from `ram_cell_v1`'s
            // own `next_pending_ack` formula: acking an already-zero
            // `pending_ack` changes nothing) -- only then does that
            // round's real capture+ack have any chance to happen. ═══

            // ═══ ROUND 1: seq_index=0 -> H1 selected (ready_in self-gated above) ═══
            // ═══ A FOURTH real bug, found via sim, precisely completing the
            // picture: draining the queue AT THE SAME TIME as pulsing
            // advance_trigger races the reprogramming itself -- the queue
            // can (and did, confirmed directly) capture whatever the
            // collector is STILL relaying from the PREVIOUS round's
            // cardinal_edge before the new round's reprogramming has
            // actually landed, a stale capture of the wrong header's
            // value. The real, correct order, now precisely known:
            //   1. advance_trigger -> reprogramming begins
            //   2. WAIT for col_program_done (cardinal_edge, active_dir_idx,
            //      and header masking are now ALL genuinely correct for
            //      this round -- confirmed, not assumed)
            //   3. ONLY THEN drain the queue (safe: nothing new has been
            //      captured yet, and reprogramming is already done, so
            //      there's no stale-value window left to race)
            //   4. WAIT for col_ack_in_e -- the real, correctly-selected
            //      header's own value genuinely reaching the queue
            //   5. CHECK ═══

            // ═══ ROUND 1: seq_index=0 -> H1 selected (ready_in self-gated above) ═══
            S_R1_START: if (settle_cnt >= SETTLE) begin
                advance_trigger <= 1;
                fire_wait_cnt <= 0;
                state <= S_R1_WAIT_PROG;
            end
            S_R1_WAIT_PROG: begin
                fire_wait_cnt <= fire_wait_cnt + 16'd1;
                if (col_program_done) begin
                    q_ack_in_n <= 1;   // safe no-op here (queue starts empty)
                    fire_wait_cnt <= 0;
                    state <= S_R1_WAIT_ACK;
                end else if (fire_wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;   // reprogramming never completed -- real fault
                    state <= S_R1_CHECK;
                end
            end
            S_R1_WAIT_ACK: begin
                fire_wait_cnt <= fire_wait_cnt + 16'd1;
                if (col_ack_in_e) begin
                    state <= S_R1_CHECK;
                end else if (fire_wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;   // never fired/acked -- real fault
                    state <= S_R1_CHECK;
                end
            end
            S_R1_CHECK: begin
                if (seq_index != 2'd1) err_sticky <= 1'b1;
                if (QUEUE.CORE_RAM.data_reg !== 32'd1) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_R2_START;
            end

            // ═══ ROUND 2: seq_index=1 -> H2 selected ═══
            S_R2_START: if (settle_cnt >= SETTLE) begin
                advance_trigger <= 1;
                fire_wait_cnt <= 0;
                state <= S_R2_WAIT_PROG;
            end
            S_R2_WAIT_PROG: begin
                fire_wait_cnt <= fire_wait_cnt + 16'd1;
                if (col_program_done) begin
                    q_ack_in_n <= 1;   // drains round 1's leftover value, now safely
                    fire_wait_cnt <= 0;
                    state <= S_R2_WAIT_ACK;
                end else if (fire_wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_R2_CHECK;
                end
            end
            S_R2_WAIT_ACK: begin
                fire_wait_cnt <= fire_wait_cnt + 16'd1;
                if (col_ack_in_e) begin
                    state <= S_R2_CHECK;
                end else if (fire_wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_R2_CHECK;
                end
            end
            S_R2_CHECK: begin
                if (seq_index != 2'd2) err_sticky <= 1'b1;
                if (QUEUE.CORE_RAM.data_reg !== 32'd2) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_R3_START;
            end

            // ═══ ROUND 3 + wraparound: seq_index=2 -> H3 selected ═══
            S_R3_START: if (settle_cnt >= SETTLE) begin
                advance_trigger <= 1;
                fire_wait_cnt <= 0;
                state <= S_R3_WAIT_PROG;
            end
            S_R3_WAIT_PROG: begin
                fire_wait_cnt <= fire_wait_cnt + 16'd1;
                if (col_program_done) begin
                    q_ack_in_n <= 1;   // drains round 2's leftover value, now safely
                    fire_wait_cnt <= 0;
                    state <= S_R3_WAIT_ACK;
                end else if (fire_wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_R3_CHECK;
                end
            end
            S_R3_WAIT_ACK: begin
                fire_wait_cnt <= fire_wait_cnt + 16'd1;
                if (col_ack_in_e) begin
                    state <= S_R3_CHECK;
                end else if (fire_wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_R3_CHECK;
                end
            end
            S_R3_CHECK: begin
                if (seq_index != 2'd0) err_sticky <= 1'b1;   // real wraparound check
                if (QUEUE.CORE_RAM.data_reg !== 32'd3) err_sticky <= 1'b1;
                state <= S_DONE;
            end

            S_DONE: begin
                // test complete, result latched in err_sticky, stays here
            end

            default: state <= S_CFG_H;
        endcase
    end
end

// ── Heartbeat + error report, same convention as every other
// self-test top-level here. ──
reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~err_sticky;   // active-low: LIT = error

endmodule
