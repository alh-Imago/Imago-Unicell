// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// top_sentinel_gather_bram_v1.v — the first real, self-contained proof that
// #279's FULL SENTINEL SYSTEM (real RTL: `sentinel_counter_v1.v`,
// standalone-proven at #281, never before wired into a real chain) and
// the header/collector/queue gather mechanism (#397/#403/#404/#406/
// #407, Quartus-confirmed on real silicon numbers) work TOGETHER, for
// the first time anywhere in this project.
//
// Alan's own scoping for this build: "start with the data in first...
// if the chains actually do some kind of work as well, just to prove
// the results are correct." Three real chains, each doing genuine
// accumulation (not just relaying a static preloaded value like
// `top_collector_mechanism_v1.v`'s own H1/H2/H3), each independently
// wrapping and freezing on its own schedule via its own
// `sentinel_counter_v1` instance -- matching Alan's own direct
// description of the intended behavior, verified against the real,
// already-built RTL before any of this was written: "the run is data
// out to end, counter reaches top and reset, that is then frozen until
// reset and new data is loaded, once the data has been reloaded, then
// its restarted."
//
// REAL, HONEST SCOPE: this proves the DATA-IN side only. The real host
// reload (fresh data actually replacing what's in each chain's own
// block, over JTAG/ISSP) is NOT built here -- each chain's own
// `host_unfreeze_pulse` is driven once by this file's own self-test
// FSM, standing in for that eventual real host action, purely to prove
// the freeze/unfreeze STATE MACHINE genuinely works end-to-end with
// real chain hardware attached, not to claim the JTAG round trip
// itself is done. No real BRAM read exists yet either -- each chain's
// own address value stands in directly as its own data (a clearly
// synthetic source), not a real memory read.
//
// TOPOLOGY: 3 "smart chains" (addr_counter_v1 -> unicell_super_v1
// configured as an accumulator -> sentinel_counter_v1 watching that
// chain's own feed/ack activity) feeding the EXACT SAME collector +
// command sequencer + queue topology `top_collector_mechanism_v1.v`
// already built and Quartus-proved -- reused entirely unchanged, not
// re-derived.
//
// THE REAL WIRING DECISION, worked out precisely before writing this,
// not guessed: feed happens WITH the counter's CURRENT address (not
// the next one), immediately followed by advancing the counter for
// NEXT time -- this removes any need for a special first-feed case,
// since `addr_counter_v1.v` already resets to 0, a valid first value.
// `feed_pulse` (sentinel) = that same feed event. `collect_pulse`
// (sentinel) = the collector's own ack back to this chain
// (`ack_in_s`-equivalent) -- which ALSO paces the NEXT feed (the
// project's own standing "pace against the consumer's own ack"
// discipline, `addr_counter_v1.v`'s own header, `#408`'s "control is
// handed to the chain" principle). `chain_length = 1` -- a direct
// point-to-point relationship for this topology, not a deep pipeline.
// `sentinel_counter_v1`'s own `freeze_out` (documented for exactly
// this purpose: "drive into the OUT-side chain's freeze_in") feeds
// directly into that chain's own accumulator `freeze_in` port,
// confirmed against `accumulator_cell_v1.v`'s own RTL to correctly
// block only NEW offers (`want_to_offer`), not disturb an
// already-in-flight one -- so the block's own LAST value is never lost
// to a premature freeze.
`default_nettype none
`timescale 1ns / 1ps

module top_sentinel_gather_bram_v1 (
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

// ── Per-chain address counters — WRAP_AT=3 gives a 4-value block
// (0,1,2,3) per chain, small and fast to simulate, matching #409's own
// block-partitioned addressing concept (each chain owns its own local,
// bounded range; no cross-chain coordination needed). ──
wire [2:0] ac1_addr, ac2_addr, ac3_addr;
reg  ac1_advance_en = 0, ac2_advance_en = 0, ac3_advance_en = 0;

addr_counter_v1 #(.WIDTH(3), .WRAP_AT(3'd3)) AC1 (.clk(clk), .rst(rst), .advance_en(ac1_advance_en), .addr(ac1_addr));
addr_counter_v1 #(.WIDTH(3), .WRAP_AT(3'd3)) AC2 (.clk(clk), .rst(rst), .advance_en(ac2_advance_en), .addr(ac2_addr));
addr_counter_v1 #(.WIDTH(3), .WRAP_AT(3'd3)) AC3 (.clk(clk), .rst(rst), .advance_en(ac3_advance_en), .addr(ac3_addr));

// ── Chain 1 (north of collector, accumulator) ──
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

// ── Chain 2 (south of collector, accumulator) ──
reg h2_cfg_valid = 0;
reg [79:0] h2_cfg_data = 80'h0;
reg h2_arrived_n = 0;
reg [31:0] h2_data_in_n = 0;
wire [31:0] h2_data_out_n;
wire h2_fire_n;
wire h2_ready_in_n;
wire h2_ack_out_n;
wire h2_ack_in_n;
wire h2_freeze;

// ── Chain 3 (west of collector, accumulator) ──
reg h3_cfg_valid = 0;
reg [79:0] h3_cfg_data = 80'h0;
reg h3_arrived_n = 0;
reg [31:0] h3_data_in_n = 0;
wire [31:0] h3_data_out_e;
wire h3_fire_e;
wire h3_ready_in_e;
wire h3_ack_out_e;
wire h3_ack_in_e;
wire h3_freeze;

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
reg q_ack_in_n = 0;
wire q_ack_out_w;
wire [31:0] q_data_out_n;

// ── Command sequencer — same 3-value cycle as the proven mechanism;
// the round-robin naturally WRAPS (already confirmed, #397), so 12
// real rounds (4 visits per chain) reuse this completely unchanged. ──
wire seq_program_out;
wire [31:0] seq_prog_data_out;
wire seq_prog_arrived_out;
reg advance_trigger = 0;
wire [1:0] seq_index;

reg        active_dir_valid = 1'b0;
reg [1:0]  active_dir_idx   = 2'd0;
always @(posedge clk) begin
    if (rst) begin
        active_dir_valid <= 1'b0;
        active_dir_idx   <= 2'd0;
    end else if (col_program_done) begin
        active_dir_valid <= 1'b1;
        active_dir_idx   <= seq_index;
    end
end

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

// ── THE NEW WIRING for this build: each chain's own sentinel_counter_v1,
// watching that chain's own real feed/collect activity. feed_pulse =
// this cycle's own feed-into-accumulator event (data = the counter's
// CURRENT address, fed immediately, then the counter advances for next
// time -- no special first-feed case needed, addr_counter_v1.v already
// resets to a valid 0). collect_pulse = the collector's own ack back to
// this chain, which ALSO paces the next feed (same signal drives both,
// a deliberate net-zero-diff steady state, confirmed against
// sentinel_counter_v1.v's own 2'b11 case -- both pulses in the same
// cycle are handled as a genuine net-zero change, not a priority
// conflict). ──
wire h1_out_wrap_pulse = (ac1_addr == 3'd3) && ac1_advance_en;
wire h1_freeze_out, h1_need_data, h1_results_ready, h1_safe, h1_err;
reg  h1_host_unfreeze = 1'b0;
sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT1 (
    .clk(clk), .rst(rst),
    .feed_pulse(h1_arrived_n), .collect_pulse(h1_ack_in_s),
    .chain_length(8'd1),
    .out_wrap_pulse(h1_out_wrap_pulse), .host_unfreeze_pulse(h1_host_unfreeze),
    .freeze_out(h1_freeze_out), .freeze_in(),
    .need_data_flag(h1_need_data), .results_ready_flag(h1_results_ready),
    .safe_to_intervene(h1_safe), .err_flag(h1_err), .diff_out()
);
// ── Alan's own precise correction to the design, worth recording
// exactly: "the order should be data in, advances count, counter now
// using a comparator say i have reached my limit, thus is frozen to be
// reprogrammed, the data now moves to the head cell of the chain, the
// next cycle the counter has been reset and sits in a frozen state
// awaiting the rearm signal." The counter's own freeze (stop counting)
// and the accumulator's own freeze (stop OFFERING what it already
// holds) are NOT the same thing, and this file's own first attempt
// wrongly conflated them into one signal (`freeze_out` gating BOTH the
// address counter's `advance_en` AND the accumulator's own `freeze_in`
// -- confirmed via direct trace to strand the final, wrap-triggering
// value: captured correctly, but its own OFFER never got a chance to
// initiate, since `want_to_offer` was already blocked by the same
// signal that (correctly) stopped further counting).
//
// The real fix: `freeze_out` stops the COUNTER (feed_trigger/advance_en)
// immediately, matching Alan's own "counter... is frozen" -- but the
// ACCUMULATOR's own `freeze_in` is gated on `results_ready_flag`
// instead (`out_frozen && diff==0`, already exactly the right signal,
// no new logic needed) -- which only asserts once the wrap-triggering
// value's own delivery is CONFIRMED complete (the ack that sets diff
// back to 0 has already happened by construction), matching "the data
// now moves to the head cell of the chain" BEFORE the chain's own
// ability to offer is finally locked down too. ──
assign h1_freeze = h1_results_ready;
assign h2_freeze = h2_results_ready;
assign h3_freeze = h3_results_ready;

wire h2_out_wrap_pulse = (ac2_addr == 3'd3) && ac2_advance_en;
wire h2_freeze_out, h2_need_data, h2_results_ready, h2_safe, h2_err;
reg  h2_host_unfreeze = 1'b0;
sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT2 (
    .clk(clk), .rst(rst),
    .feed_pulse(h2_arrived_n), .collect_pulse(h2_ack_in_n),
    .chain_length(8'd1),
    .out_wrap_pulse(h2_out_wrap_pulse), .host_unfreeze_pulse(h2_host_unfreeze),
    .freeze_out(h2_freeze_out), .freeze_in(),
    .need_data_flag(h2_need_data), .results_ready_flag(h2_results_ready),
    .safe_to_intervene(h2_safe), .err_flag(h2_err), .diff_out()
);

wire h3_out_wrap_pulse = (ac3_addr == 3'd3) && ac3_advance_en;
wire h3_freeze_out, h3_need_data, h3_results_ready, h3_safe, h3_err;
reg  h3_host_unfreeze = 1'b0;
sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT3 (
    .clk(clk), .rst(rst),
    .feed_pulse(h3_arrived_n), .collect_pulse(h3_ack_in_e),
    .chain_length(8'd1),
    .out_wrap_pulse(h3_out_wrap_pulse), .host_unfreeze_pulse(h3_host_unfreeze),
    .freeze_out(h3_freeze_out), .freeze_in(),
    .need_data_flag(h3_need_data), .results_ready_flag(h3_results_ready),
    .safe_to_intervene(h3_safe), .err_flag(h3_err), .diff_out()
);

// ── Feed generation, REAL BRAM READ version (extends the proven
// #410 design): on a feed_trigger (start, or paced by this chain's own
// ack), issue a real READ command to this chain's own BRAM at its
// CURRENT address, advance the counter for next time, then feed the
// accumulator with the GENUINELY READ value one cycle later
// (`rdata_valid`'s own real, single-stage synchronous latency,
// `bram_controller_v1.v`'s own proven timing -- not assumed, confirmed
// against that module's own header). Each chain owns its own small,
// separate BRAM instance -- the real, physical form of #409's block-
// partitioned addressing: no cross-chain address coordination needed,
// each chain's own local counter only ever reaches into its own memory. ──
reg h1_start_pulse = 0, h2_start_pulse = 0, h3_start_pulse = 0;
wire h1_feed_trigger = (h1_start_pulse || h1_ack_in_s) && !h1_freeze_out;
wire h2_feed_trigger = (h2_start_pulse || h2_ack_in_n) && !h2_freeze_out;
wire h3_feed_trigger = (h3_start_pulse || h3_ack_in_e) && !h3_freeze_out;

reg  b1_cmd_valid = 0, b2_cmd_valid = 0, b3_cmd_valid = 0;
reg [2:0] b1_cmd_addr = 0, b2_cmd_addr = 0, b3_cmd_addr = 0;
wire b1_rdata_valid, b2_rdata_valid, b3_rdata_valid;
wire [39:0] b1_rdata, b2_rdata, b3_rdata;

bram_controller_v1 #(.ADDR_WIDTH(3), .DATA_WIDTH(40)) BRAM1 (
    .clk(clk), .rst(rst),
    .cmd_valid(b1_cmd_valid), .cmd_op(bram_cmd_op), .cmd_addr(b1_cmd_addr), .cmd_wdata(bram_cmd_wdata),
    .rdata_valid(b1_rdata_valid), .rdata(b1_rdata), .write_done()
);
bram_controller_v1 #(.ADDR_WIDTH(3), .DATA_WIDTH(40)) BRAM2 (
    .clk(clk), .rst(rst),
    .cmd_valid(b2_cmd_valid), .cmd_op(bram_cmd_op), .cmd_addr(b2_cmd_addr), .cmd_wdata(bram_cmd_wdata),
    .rdata_valid(b2_rdata_valid), .rdata(b2_rdata), .write_done()
);
bram_controller_v1 #(.ADDR_WIDTH(3), .DATA_WIDTH(40)) BRAM3 (
    .clk(clk), .rst(rst),
    .cmd_valid(b3_cmd_valid), .cmd_op(bram_cmd_op), .cmd_addr(b3_cmd_addr), .cmd_wdata(bram_cmd_wdata),
    .rdata_valid(b3_rdata_valid), .rdata(b3_rdata), .write_done()
);

// Preload writes and normal feed-reads share these same BRAM command
// lines -- combined here as the SOLE driver (single always block,
// avoiding the earlier multiple-driver bug this file already hit once).
wire preload_wr_1 = (state == S_PRELOAD) && (preload_idx < 4);
wire preload_wr_2 = (state == S_PRELOAD) && (preload_idx >= 4) && (preload_idx < 8);
wire preload_wr_3 = (state == S_PRELOAD) && (preload_idx >= 8) && (preload_idx < 12);

always @(posedge clk) begin
    // Issue the real read (or, during preload, write) this cycle...
    b1_cmd_valid <= h1_feed_trigger || preload_wr_1;
    b1_cmd_addr  <= preload_wr_1 ? preload_idx[2:0] : ac1_addr;
    ac1_advance_en <= h1_feed_trigger;

    b2_cmd_valid <= h2_feed_trigger || preload_wr_2;
    b2_cmd_addr  <= preload_wr_2 ? (preload_idx[2:0] - 3'd4) : ac2_addr;
    ac2_advance_en <= h2_feed_trigger;

    b3_cmd_valid <= h3_feed_trigger || preload_wr_3;
    b3_cmd_addr  <= preload_wr_3 ? (preload_idx[2:0] - 3'd0) : ac3_addr;
    ac3_advance_en <= h3_feed_trigger;

    // ...and feed the accumulator once the REAL read genuinely completes
    // (one cycle later, bram_controller_v1's own proven latency). During
    // preload, rdata_valid never pulses (writes don't generate it, per
    // bram_controller_v1's own confirmed logic), so this is naturally
    // inert until the real gather phase begins.
    h1_arrived_n <= b1_rdata_valid;
    h1_data_in_n <= b1_rdata[31:0];

    h2_arrived_n <= b2_rdata_valid;
    h2_data_in_n <= b2_rdata[31:0];

    h3_arrived_n <= b3_rdata_valid;
    h3_data_in_n <= b3_rdata[31:0];
end


unicell_super_v1 #(.CELL_ID(16'h0020)) H1 (
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

unicell_super_v1 #(.CELL_ID(16'h0021)) H2 (
    .clk(clk), .rst(rst),
    .cfg_valid(h2_cfg_valid), .cfg_data(h2_cfg_data),
    .data_in_n(h2_data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h2_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(h2_data_out_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(h2_fire_n), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(h2_ready_in_n), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(h2_ack_out_n), .ack_out_s(), .ack_out_e(), .ack_out_w(),
    .ack_in_n(h2_ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(h2_freeze),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

unicell_super_v1 #(.CELL_ID(16'h0022)) H3 (
    .clk(clk), .rst(rst),
    .cfg_valid(h3_cfg_valid), .cfg_data(h3_cfg_data),
    .data_in_n(h3_data_in_n), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(32'h0),
    .arrived_n(h3_arrived_n), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(1'b0),
    .data_out_n(), .data_out_s(), .data_out_e(h3_data_out_e), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(h3_fire_e), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(h3_ready_in_e), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(h3_ack_out_e), .ack_out_w(),
    .ack_in_n(1'b0), .ack_in_s(1'b0), .ack_in_e(h3_ack_in_e), .ack_in_w(1'b0),
    .freeze_in(h3_freeze),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

unicell_super_v1 #(.CELL_ID(16'h0023)) COLLECTOR (
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

unicell_super_v1 #(.CELL_ID(16'h0024)) QUEUE (
    .clk(clk), .rst(rst),
    .cfg_valid(q_cfg_valid), .cfg_data(q_cfg_data),
    .data_in_n(32'h0), .data_in_s(32'h0), .data_in_e(32'h0), .data_in_w(col_data_out_e),
    .arrived_n(1'b0), .arrived_s(1'b0), .arrived_e(1'b0), .arrived_w(col_fire_e),
    .data_out_n(q_data_out_n), .data_out_s(), .data_out_e(), .data_out_w(),
    .fire_n(), .fire_s(), .fire_e(), .fire_w(),
    .ready_out(),
    .ready_in_n(1'b1), .ready_in_s(1'b1), .ready_in_e(1'b1), .ready_in_w(1'b1),
    .ack_out_n(), .ack_out_s(), .ack_out_e(), .ack_out_w(q_ack_out_w),
    .ack_in_n(q_ack_in_n), .ack_in_s(1'b0), .ack_in_e(1'b0), .ack_in_w(1'b0),
    .freeze_in(1'b0),
    .program_in(1'b0), .program_done(),
    .prog_data_in_n(32'h0), .prog_data_in_s(32'h0), .prog_data_in_e(32'h0), .prog_data_in_w(32'h0),
    .prog_arrived_in_n(1'b0), .prog_arrived_in_s(1'b0), .prog_arrived_in_e(1'b0), .prog_arrived_in_w(1'b0),
    .status_core_select()
);

assign col_ack_in_e = q_ack_out_w;

// ── Real verification: confirm each chain's own read genuinely
// returns what was preloaded (100/200/300 + address), not just trust
// the wiring. Checked directly against b*_cmd_addr, which still holds
// the address that was just read (unchanged until this chain's own
// NEXT feed, many cycles later than this one-cycle read latency). ──
reg bram_check_err = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        bram_check_err <= 1'b0;
    end else begin
        if (b1_rdata_valid && (b1_rdata[31:0] !== (32'd100 + {29'h0, b1_cmd_addr})))
            bram_check_err <= 1'b1;
        if (b2_rdata_valid && (b2_rdata[31:0] !== (32'd200 + {29'h0, b2_cmd_addr})))
            bram_check_err <= 1'b1;
        if (b3_rdata_valid && (b3_rdata[31:0] !== (32'd300 + {29'h0, b3_cmd_addr})))
            bram_check_err <= 1'b1;
    end
end

// ── Self-test FSM ── config -> per-chain unfreeze+start -> 12 real
// gather rounds (4 visits per chain, round-robin, matching the
// sequencer's own already-proven wrap behavior) -> verify EVERY
// round's captured value against the expected running sum for
// whichever chain was active, not just the final one.
localparam [79:0] CFG_H1  = {13'b0, 20'b0, 30'b0, {4'b0010, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_H2  = {13'b0, 20'b0, 30'b0, {4'b0001, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_H3  = {13'b0, 20'b0, 30'b0, {4'b0100, 4'b0000, 4'b0001}, 5'd3};
localparam [79:0] CFG_COL = {13'b0, 20'b0, 6'b0, 6'b000100, 1'b1, 10'b0, 5'd0};
localparam [79:0] CFG_Q   = {22'b0, {32'h0, 1'b0, 1'b0, 4'b1000, 4'b0001}, 5'd1};

localparam [5:0]
    S_CFG_H        = 0,
    S_PRELOAD      = 10,
    S_CFG_COL_Q    = 1,
    S_UNFREEZE     = 2,
    S_START        = 3,
    S_CHECK_SEL    = 4,
    S_ROUND_START  = 5,
    S_ROUND_WAIT_PROG = 6,
    S_ROUND_WAIT_ACK  = 7,
    S_ROUND_CHECK  = 8,
    S_DONE         = 9;

reg [5:0] state = S_CFG_H;
reg [7:0] settle_cnt = 0;
reg [3:0] preload_idx = 0;
reg       bram_cmd_op = 1'b0;
reg [39:0] bram_cmd_wdata = 40'h0;
reg       err_sticky = 1'b0;
reg [15:0] wait_cnt = 0;
reg [3:0] round_idx = 0;   // 0..11 -- 4 visits per chain, round-robin

localparam [7:0] SETTLE = 8'd16;

// Real, direct correction from tracing, not assumption: `accumulator_
// cell_v1.v` is a pure EVENT COUNTER (increments by 1 on each arrival
// on its configured inc direction) -- it does NOT sum `data_in_n`'s own
// numeric payload. Confirmed directly via sim trace (h1acc read 1 after
// the first feed regardless of the fed address value, not 0+addr).
// This is still real, verifiable per-chain work -- a genuine running
// count of how many items this chain has processed -- just not the
// value-sum this file originally assumed before checking.
function [31:0] expected_sum;
    input [1:0] visit;
    begin
        case (visit)
            2'd0: expected_sum = 32'd1;
            2'd1: expected_sum = 32'd2;
            2'd2: expected_sum = 32'd3;
            2'd3: expected_sum = 32'd4;
            default: expected_sum = 32'd0;
        endcase
    end
endfunction

always @(posedge clk) begin
    if (rst) begin
        state <= S_CFG_H;
        h1_cfg_valid <= 0; h2_cfg_valid <= 0; h3_cfg_valid <= 0;
        col_cfg_valid <= 0; q_cfg_valid <= 0;
        h1_start_pulse <= 0; h2_start_pulse <= 0; h3_start_pulse <= 0;
        h1_host_unfreeze <= 0; h2_host_unfreeze <= 0; h3_host_unfreeze <= 0;
        advance_trigger <= 0;
        q_ack_in_n <= 0;
        settle_cnt <= 0; wait_cnt <= 0; round_idx <= 0;
        err_sticky <= 1'b0;
    end else begin
        h1_cfg_valid <= 0; h2_cfg_valid <= 0; h3_cfg_valid <= 0;
        col_cfg_valid <= 0; q_cfg_valid <= 0;
        h1_start_pulse <= 0; h2_start_pulse <= 0; h3_start_pulse <= 0;
        h1_host_unfreeze <= 0; h2_host_unfreeze <= 0; h3_host_unfreeze <= 0;
        advance_trigger <= 0;
        q_ack_in_n <= 0;
        settle_cnt <= settle_cnt + 8'd1;

        case (state)
            S_CFG_H: begin
                h1_cfg_valid <= 1; h1_cfg_data <= CFG_H1;
                h2_cfg_valid <= 1; h2_cfg_data <= CFG_H2;
                h3_cfg_valid <= 1; h3_cfg_data <= CFG_H3;
                settle_cnt <= 0;
                preload_idx <= 0;
                state <= S_PRELOAD;
            end
            // Real BRAM preload -- writes 4 distinct, chain-identifying
            // values into each of the 3 chains' own separate BRAMs
            // (chain N, address i -> value 100*N + i), so a later read
            // can be verified against a REAL, known value, not just
            // trusted. One real WRITE per cycle, 12 total.
            S_PRELOAD: begin
                bram_cmd_op <= 1'b1;   // OP_WRITE
                if (preload_idx < 4) begin
                    bram_cmd_wdata <= {8'h0, 32'd100 + {29'h0, preload_idx}};
                end else if (preload_idx < 8) begin
                    bram_cmd_wdata <= {8'h0, 32'd200 + {29'h0, (preload_idx - 4'd4)}};
                end else if (preload_idx < 12) begin
                    bram_cmd_wdata <= {8'h0, 32'd300 + {29'h0, (preload_idx - 4'd8)}};
                end
                if (preload_idx >= 4'd11) begin
                    bram_cmd_op <= 1'b0;   // back to READ for the real gather phase
                    settle_cnt <= 0;
                    state <= S_CFG_COL_Q;
                end else begin
                    preload_idx <= preload_idx + 4'd1;
                end
            end
            S_CFG_COL_Q: if (settle_cnt >= SETTLE) begin
                col_cfg_valid <= 1; col_cfg_data <= CFG_COL;
                q_cfg_valid   <= 1; q_cfg_data   <= CFG_Q;
                settle_cnt <= 0;
                state <= S_UNFREEZE;
            end
            // Sentinel starts FROZEN at power-on (#287's own real fix) --
            // this pulse stands in for the real host's first data load,
            // not built here, only its EFFECT (unfreezing) exercised.
            S_UNFREEZE: if (settle_cnt >= SETTLE) begin
                h1_host_unfreeze <= 1; h2_host_unfreeze <= 1; h3_host_unfreeze <= 1;
                settle_cnt <= 0;
                state <= S_START;
            end
            S_START: if (settle_cnt >= SETTLE) begin
                h1_start_pulse <= 1; h2_start_pulse <= 1; h3_start_pulse <= 1;
                settle_cnt <= 0;
                state <= S_CHECK_SEL;
            end
            S_CHECK_SEL: if (settle_cnt >= SETTLE) begin
                if (col_status_core_select != 5'd0) err_sticky <= 1'b1;
                settle_cnt <= 0; state <= S_ROUND_START;
            end

            S_ROUND_START: if (settle_cnt >= SETTLE) begin
                advance_trigger <= 1;
                wait_cnt <= 0;
                state <= S_ROUND_WAIT_PROG;
            end
            S_ROUND_WAIT_PROG: begin
                wait_cnt <= wait_cnt + 16'd1;
                if (col_program_done) begin
                    q_ack_in_n <= 1;
                    wait_cnt <= 0;
                    state <= S_ROUND_WAIT_ACK;
                end else if (wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_ROUND_CHECK;
                end
            end
            S_ROUND_WAIT_ACK: begin
                wait_cnt <= wait_cnt + 16'd1;
                if (col_ack_in_e) begin
                    state <= S_ROUND_CHECK;
                end else if (wait_cnt >= 16'd400) begin
                    err_sticky <= 1'b1;
                    state <= S_ROUND_CHECK;
                end
            end
            S_ROUND_CHECK: begin
                if (q_data_out_n !== expected_sum(round_idx / 3)) err_sticky <= 1'b1;
                if (round_idx == 4'd11) begin
                    state <= S_DONE;
                end else begin
                    round_idx <= round_idx + 4'd1;
                    settle_cnt <= 0;
                    state <= S_ROUND_START;
                end
            end

            S_DONE: begin
                // Real, direct sentinel-flag confirmation, not just the
                // gather mechanism's own value checks: every chain must
                // have genuinely completed its own block and reported it.
                if (!h1_safe || !h2_safe || !h3_safe) err_sticky <= 1'b1;
                if (bram_check_err) err_sticky <= 1'b1;
                if (h1_err || h2_err || h3_err) err_sticky <= 1'b1;
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
