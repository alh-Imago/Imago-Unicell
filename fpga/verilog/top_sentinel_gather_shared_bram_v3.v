// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// v3 (#430's queue item 2, extension to the full mechanism): cloned
// from v2 (#437's own real, Quartus-proven 314 ALM / 179.99 MHz
// baseline, left untouched) to replace v2's own self-test FSM entirely
// with `host_bridge_sentinel_gather_v1.v` -- a real, external,
// JTAG-driven host now configures every cell, preloads the shared BRAM,
// unfreezes every chain, and drives the round-robin one round at a
// time, exactly as a real host would over actual hardware (extending
// #441/#442's own proven single-cell bridge pattern to this full
// 3-chain mechanism, per those entries' own stated "separate, later
// work"). A real architectural fact confirmed against v2's own RTL
// before building this (not assumed): the round-robin does NOT
// free-run once armed -- `round_start_pulse` is a direct registered
// copy of `advance_trigger`, not derived from `round_complete_pulse`,
// so a real host must issue one ADVANCE per round. A real, stated
// protocol discipline this file's own design depends on: the host must
// ICM_LOAD every cell, BRAM_WRITE all preload data, and UNFREEZE every
// chain BEFORE the first ADVANCE -- the shared BRAM command channel
// uses simple OR-arbitration between host commands and the mechanism's
// own internal automatic reads (identical in structure to v2's own
// preload/internal-read muxing), safe only as long as that discipline
// holds, not a formally collision-proof design. One real design
// improvement made along the way, not just a mechanical port: QUEUE's
// own `ack_in_n` is now `assign q_ack_in_n = col_fire_e` (unconditional
// ack, matching this project's own standing "never gate the offering
// side" discipline) instead of v2's own self-test-FSM-timed pulse.
// Sim-verified clean end to end: all 12 real rounds produced via real
// simulated host commands, matching v2's own proven expected results
// exactly, zero regression on v2 itself (`points.md` #443).
//
// v2 (#430's queue item 1): cloned from v1 (#426's own real, Quartus-
// proven 347 ALM / 188.86 MHz baseline, left untouched) to wire
// `collector_relay_v1.v` (#428) into the COLLECTOR role in place of
// the general-purpose `unicell_super_v1` shell + `cell_command_
// sequencer_v1:SEQ` pair. Real consequences of that swap, worked out
// precisely rather than patched piecemeal: the collector needs no cfg/
// program interface at all now (removed entirely, no `col_cfg_valid`/
// `col_status_core_select`/`CFG_COL`/`S_CHECK_SEL`); the round-robin
// index that used to live inside the sequencer (`seq_index`) is now a
// trivial local 0/1/2 counter (`active_dir_idx`) advanced directly by
// the collector's own real fire+ack handshake completing
// (`round_complete_pulse = col_fire_e && col_ack_in_e`), with
// `round_start_pulse` standing in for the old `col_program_done` as
// the "this round's index is now valid" signal everywhere it was used
// (freshness gating, shared-BRAM read arbitration, `fired_this_round`).
// Sim-verified clean end to end: all 12 rounds correct, deterministic,
// `err_sticky` stays 0 throughout, matching v1's own proven behavior
// exactly (`points.md` #436).
//
// top_sentinel_gather_shared_bram_v3.v — the first real, self-contained proof that
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

module top_sentinel_gather_shared_bram_v3 (
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
wire h1_cfg_valid;
wire [79:0] h1_cfg_data;
reg h1_arrived_n = 0;
reg [31:0] h1_data_in_n = 0;
wire [31:0] h1_data_out_s;
wire h1_fire_s;
wire h1_ready_in_s;
wire h1_ack_out_s;
wire h1_ack_in_s;
wire h1_freeze;

// ── Chain 2 (south of collector, accumulator) ──
wire h2_cfg_valid;
wire [79:0] h2_cfg_data;
reg h2_arrived_n = 0;
reg [31:0] h2_data_in_n = 0;
wire [31:0] h2_data_out_n;
wire h2_fire_n;
wire h2_ready_in_n;
wire h2_ack_out_n;
wire h2_ack_in_n;
wire h2_freeze;

// ── Chain 3 (west of collector, accumulator) ──
wire h3_cfg_valid;
wire [79:0] h3_cfg_data;
reg h3_arrived_n = 0;
reg [31:0] h3_data_in_n = 0;
wire [31:0] h3_data_out_e;
wire h3_fire_e;
wire h3_ready_in_e;
wire h3_ack_out_e;
wire h3_ack_in_e;
wire h3_freeze;

// ── Collector (center) — now collector_relay_v1 (#428), a dedicated
// static combiner replacing the general-purpose unicell_super_v1 shell
// + cell_command_sequencer_v1 pair (#427's own principle: this piece
// never needs to become a different core at runtime, so it shouldn't
// pay the shell's own reconfigurability tax). No cfg/program interface
// at all -- it listens on all 3 static cardinal inputs simultaneously,
// distinguished by arrival direction alone, gated by the SAME
// round-robin readiness signals already guaranteeing mutual exclusion
// (`collector_relay_v1.v`'s own header). ──
wire [31:0] col_data_out_e;
wire col_fire_e;
wire col_ack_in_e;

// ── Queue (east of collector, terminal RAM cell) ──
wire q_cfg_valid;
wire [79:0] q_cfg_data;
wire q_ack_in_n;
// Real design (v3, host-driven): QUEUE acks whenever the collector
// genuinely fires, unconditionally -- matching this project's own
// standing "never gate the offering side" discipline (the same
// discipline every accumulator's own ack_out already follows). This
// REPLACES v2's own self-test FSM pulse (which pre-armed q_ack_in_n
// one cycle ahead of the real data, timed to fit that FSM's own
// round-tracking state machine) with the simpler, more robust real
// behavior a genuine host-driven design should have -- no state
// machine needed to get the timing right at all.
assign q_ack_in_n = col_fire_e;
wire [4:0] q_status_core_select;
wire q_ack_out_w;
wire [31:0] q_data_out_n;

// ── Command sequencer — same 3-value cycle as the proven mechanism;
// the round-robin naturally WRAPS (already confirmed, #397), so 12
// real rounds (4 visits per chain) reuse this completely unchanged. ──
// ── Round-robin index generator, replacing cell_command_sequencer_v1's
// own role (#428, #430 queue item 1): collector_relay_v1 needs no
// runtime reprogramming at all, so the round-robin index is now just a
// trivial local counter -- 0,1,2,0,... matching the exact sequence
// `cell_command_sequencer_v1`'s own `seq_index` produced (checked
// directly against its RTL: starts at 0, holds through a round,
// advances only once that round genuinely completes). `round_start_
// pulse` replaces `col_program_done` as the "this round's index is now
// valid" signal downstream; `round_complete_pulse` (the collector's
// own real fire+ack handshake completing) replaces the old
// `program_done_in` feedback that used to drive SEQ's own advance. ──
wire advance_trigger;
wire round_complete_pulse = col_fire_e && col_ack_in_e;

reg        active_dir_valid  = 1'b0;
reg [1:0]  active_dir_idx    = 2'd0;
reg        round_start_pulse = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        active_dir_valid  <= 1'b0;
        active_dir_idx    <= 2'd0;
        round_start_pulse <= 1'b0;
    end else begin
        round_start_pulse <= advance_trigger;
        if (advance_trigger) active_dir_valid <= 1'b1;
        if (round_complete_pulse)
            active_dir_idx <= (active_dir_idx == 2'd2) ? 2'd0 : active_dir_idx + 2'd1;
    end
end

reg fired_this_round = 1'b0;
// A real bug this shared-BRAM redesign exposed that #410's own original
// design never hit: `fired_this_round` was a SINGLE flag shared across
// all 3 headers, latching on ANY of their ack signals. With the added
// multi-cycle shared-BRAM read latency, a PREVIOUS chain's own
// still-pending offer can complete its ack LATE, bleeding into the
// NEXT chain's own round-robin window -- incorrectly masking that
// chain even though IT never fired. Confirmed directly via sim trace:
// `h2_ready_in_n` dropped just 2 cycles after becoming 1, with
// `h2_fire_n`/`h2_ack_in_n` never having asserted, while the
// collector's own `pending_ack` jumped to 4 that same cycle -- a stale
// ack from a DIFFERENT chain, not H2's own. Fixed by scoping the latch
// to the CURRENTLY ACTIVE chain's own ack only.
always @(posedge clk) begin
    if (rst) begin
        fired_this_round <= 1'b0;
    end else if (round_start_pulse) begin
        fired_this_round <= 1'b0;
    end else if ((active_dir_idx == 2'd0 && h1_ack_in_s) ||
                 (active_dir_idx == 2'd1 && h2_ack_in_n) ||
                 (active_dir_idx == 2'd2 && h3_ack_in_e)) begin
        fired_this_round <= 1'b1;
    end
end

// THE REAL FIX (Alan's own precise framing): "data in then confirm, not
// ready and waiting confirm then capture." Readiness must be gated on
// having ALREADY genuinely captured real data (`h*_primed`, set the
// instant a real `h*_arrived_n` first fires) -- not just on whose
// logical turn the round-robin says it is. Without this, a chain's own
// FIRST visit exposed its continuously-live, pre-capture DEFAULT value
// to the collector before its real shared-BRAM read ever completed
// (confirmed directly via trace, `#414`) -- the mechanism's own fault,
// not the self-test's expectation, since the collector had no way to
// tell a genuine value from a not-yet-arrived one. Each chain's own
// true first visit now correctly becomes a "priming" round with
// nothing gathered (a safe, honest outcome), not a stale value that
// merely looks legitimate.
assign h1_ready_in_s = active_dir_valid && (active_dir_idx == 2'd0) && !fired_this_round && h1_fresh;
assign h2_ready_in_n = active_dir_valid && (active_dir_idx == 2'd1) && !fired_this_round && h2_fresh;
assign h3_ready_in_e = active_dir_valid && (active_dir_idx == 2'd2) && !fired_this_round && h3_fresh;

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
wire [4:0] h1_status_core_select;
wire  h1_host_unfreeze;
// Real bug found via sim, fixed here: an accumulator's own `want_to_
// offer` (`accumulator_cell_v1.v`) is true from config time onward,
// REGARDLESS of whether it has ever captured a real value yet
// (`data_valid` is a continuously-live status, not gated on "has real
// data arrived"). Confirmed directly via a numbered feed/ack trace:
// H2's own ACK #1 (accumulator reading 0, its power-on default) landed
// BEFORE its own FEED #1 ever fired -- a genuine offer-and-ack of the
// chain's DEFAULT state, before the real shared-BRAM read for its own
// first round ever completed. The sentinel's own diff tracking sees
// this as a collect with no matching earlier feed, dipping negative
// and tripping the deliberately-sticky error latch even though the
// real counts are otherwise correct. Fixed narrowly: each chain's own
// sentinel only counts a collect once that chain has had at least one
// REAL feed -- the actual offer/ack protocol to the collector is
// untouched, only the SENTINEL's own bookkeeping is gated.
reg h1_primed = 1'b0, h2_primed = 1'b0, h3_primed = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        h1_primed <= 1'b0; h2_primed <= 1'b0; h3_primed <= 1'b0;
    end else begin
        if (h1_arrived_n) h1_primed <= 1'b1;
        if (h2_arrived_n) h2_primed <= 1'b1;
        if (h3_arrived_n) h3_primed <= 1'b1;
    end
end

// A second, more general form of the same real bug, found by re-testing
// after the first fix rather than assuming it was complete: `primed`
// only ever latches ONCE (true forever after a chain's first-ever real
// capture) -- it correctly fixed the very-first-visit case, but every
// LATER visit still exposed readiness the same cycle THAT round's own
// new read was triggered, before THAT round's own capture had
// completed -- confirmed directly: the one-round lag reappeared
// starting exactly at each chain's SECOND visit. The real, general fix
// needs to be PER-ROUND, not one-time: `h*_fresh` resets the instant a
// NEW round begins for that chain (matching Alan's own framing --
// "data in then confirm, not ready... then capture" -- applied to
// every round, not just the first), and sets only once THAT round's
// own capture has genuinely completed.
reg h1_fresh = 1'b0, h2_fresh = 1'b0, h3_fresh = 1'b0;
always @(posedge clk) begin
    if (rst) begin
        h1_fresh <= 1'b0; h2_fresh <= 1'b0; h3_fresh <= 1'b0;
    end else begin
        if (round_start_pulse && active_dir_idx == 2'd0) h1_fresh <= 1'b0;
        else if (h1_arrived_n) h1_fresh <= 1'b1;

        if (round_start_pulse && active_dir_idx == 2'd1) h2_fresh <= 1'b0;
        else if (h2_arrived_n) h2_fresh <= 1'b1;

        if (round_start_pulse && active_dir_idx == 2'd2) h3_fresh <= 1'b0;
        else if (h3_arrived_n) h3_fresh <= 1'b1;
    end
end

sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT1 (
    .clk(clk), .rst(rst),
    .feed_pulse(h1_arrived_n), .collect_pulse(h1_ack_in_s && h1_primed),
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
wire [4:0] h2_status_core_select;
wire  h2_host_unfreeze;
sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT2 (
    .clk(clk), .rst(rst),
    .feed_pulse(h2_arrived_n), .collect_pulse(h2_ack_in_n && h2_primed),
    .chain_length(8'd1),
    .out_wrap_pulse(h2_out_wrap_pulse), .host_unfreeze_pulse(h2_host_unfreeze),
    .freeze_out(h2_freeze_out), .freeze_in(),
    .need_data_flag(h2_need_data), .results_ready_flag(h2_results_ready),
    .safe_to_intervene(h2_safe), .err_flag(h2_err), .diff_out()
);

wire h3_out_wrap_pulse = (ac3_addr == 3'd3) && ac3_advance_en;
wire h3_freeze_out, h3_need_data, h3_results_ready, h3_safe, h3_err;
wire [4:0] h3_status_core_select;
wire  h3_host_unfreeze;
sentinel_counter_v1 #(.DIFF_WIDTH(8)) SENT3 (
    .clk(clk), .rst(rst),
    .feed_pulse(h3_arrived_n), .collect_pulse(h3_ack_in_e && h3_primed),
    .chain_length(8'd1),
    .out_wrap_pulse(h3_out_wrap_pulse), .host_unfreeze_pulse(h3_host_unfreeze),
    .freeze_out(h3_freeze_out), .freeze_in(),
    .need_data_flag(h3_need_data), .results_ready_flag(h3_results_ready),
    .safe_to_intervene(h3_safe), .err_flag(h3_err), .diff_out()
);

// ── THE REAL REDESIGN (#412's own correction): ONE shared BRAM read
// port serving all 3 chains, arbitrated by REUSING the exact same
// round-robin gating (`active_dir_idx`) that already decides whose
// turn it is to offer to the collector -- no separate arbitration
// mechanism needed, since only one chain is ever "current" at a time
// anyway. #409's own block-partitioned addressing becomes real here
// for the first time: each chain's own local counter (0-3) is offset
// by its own fixed block base (0/4/8) to form the real address into
// the ONE shared memory.
//
// The read is issued exactly once per round, the same cycle
// `round_start_pulse` fires (#428's own simplification: since
// `collector_relay_v1` needs no reprogramming, `active_dir_idx` is
// already valid and stable the same cycle -- no separate live
// sequencer index to read ahead of its own NBA update anymore).
// `read_owner` records which chain this in-flight read belongs to, so
// the response (one cycle later, `bram_controller_v1.v`'s own proven
// single-stage latency) routes back to the correct chain and no other.
localparam [3:0] CHAIN1_BASE = 4'd0, CHAIN2_BASE = 4'd4, CHAIN3_BASE = 4'd8;

wire [3:0] shared_read_addr = (active_dir_idx == 2'd0) ? (CHAIN1_BASE + {1'b0, ac1_addr}) :
                               (active_dir_idx == 2'd1) ? (CHAIN2_BASE + {1'b0, ac2_addr}) :
                                                           (CHAIN3_BASE + {1'b0, ac3_addr});
wire this_chain_frozen = (active_dir_idx == 2'd0) ? h1_freeze_out :
                          (active_dir_idx == 2'd1) ? h2_freeze_out : h3_freeze_out;
wire shared_read_trigger = round_start_pulse && !this_chain_frozen;

reg        shared_cmd_valid = 1'b0;
reg [3:0]  shared_cmd_addr  = 4'd0;
reg        bram_cmd_op      = 1'b0;
reg [39:0] bram_cmd_wdata   = 40'h0;
reg [1:0]  read_owner       = 2'd0;
wire       shared_rdata_valid;
wire       shared_write_done;
wire [39:0] shared_rdata;

bram_controller_v1 #(.ADDR_WIDTH(4), .DATA_WIDTH(40)) SHARED_BRAM (
    .clk(clk), .rst(rst),
    .cmd_valid(shared_cmd_valid), .cmd_op(bram_cmd_op),
    .cmd_addr(shared_cmd_addr), .cmd_wdata(bram_cmd_wdata),
    .rdata_valid(shared_rdata_valid), .rdata(shared_rdata), .write_done(shared_write_done)
);

// ── v3 (host-driven): the shared BRAM command channel is now
// arbitrated between the mechanism's own internal automatic reads
// (`shared_read_trigger`) and the host bridge's own real BRAM_READ/
// BRAM_WRITE commands (`bridge_bram_cmd_valid`) -- the SAME simple
// OR-based structure v2's own preload/internal-read muxing already
// used (`preload_active || shared_read_trigger`), just swapping a
// fixed self-test sequence for real host-supplied commands. Safe as
// long as the host follows the REAL, STATED PROTOCOL DISCIPLINE this
// file's own header lays out: ICM_LOAD every cell, BRAM_WRITE all
// preload data, and UNFREEZE every chain BEFORE the first ADVANCE --
// `shared_read_trigger` is genuinely false throughout that whole
// window (it only ever fires in response to `round_start_pulse`,
// itself only driven by `advance_trigger`, which the host hasn't
// pulsed yet), so no real collision can occur AS LONG AS that
// discipline holds. This is NOT a formally arbitrated, collision-proof
// design for a host that violates the discipline (e.g. issuing a BRAM
// command while rounds are actively running) -- internal reads win
// that race by construction below, a real, low-probability, stated
// limitation, not glossed over. `read_owner` gains a genuine 4th value
// (2'd3, "host-owned") so a host-issued read's own response never gets
// misrouted into h1/h2/h3_arrived_n, which only ever check for
// read_owner values 0/1/2. ──
wire bridge_bram_cmd_valid;
wire bridge_bram_cmd_op;
wire [3:0] bridge_bram_cmd_addr;
wire [39:0] bridge_bram_cmd_wdata;

always @(posedge clk) begin
    shared_cmd_valid <= shared_read_trigger || bridge_bram_cmd_valid;
    shared_cmd_addr  <= shared_read_trigger ? shared_read_addr : bridge_bram_cmd_addr;
    bram_cmd_op      <= shared_read_trigger ? 1'b0 : bridge_bram_cmd_op;   // internal reads are always READ
    bram_cmd_wdata   <= bridge_bram_cmd_wdata;   // only meaningful when the host issues a real WRITE
    if (shared_read_trigger || bridge_bram_cmd_valid)
        read_owner <= shared_read_trigger ? active_dir_idx : 2'd3;

    h1_arrived_n   <= shared_rdata_valid && (read_owner == 2'd0);
    h1_data_in_n   <= shared_rdata[31:0];
    ac1_advance_en <= shared_rdata_valid && (read_owner == 2'd0);

    h2_arrived_n   <= shared_rdata_valid && (read_owner == 2'd1);
    h2_data_in_n   <= shared_rdata[31:0];
    ac2_advance_en <= shared_rdata_valid && (read_owner == 2'd1);

    h3_arrived_n   <= shared_rdata_valid && (read_owner == 2'd2);
    h3_data_in_n   <= shared_rdata[31:0];
    ac3_advance_en <= shared_rdata_valid && (read_owner == 2'd2);
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
    .status_core_select(h1_status_core_select)
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
    .status_core_select(h2_status_core_select)
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
    .status_core_select(h3_status_core_select)
);

collector_relay_v1 COLLECTOR (
    .clk(clk), .rst(rst),
    .data_in_a(h1_data_out_s), .data_in_b(h2_data_out_n), .data_in_c(h3_data_out_e),
    .arrived_a(h1_fire_s),     .arrived_b(h2_fire_n),     .arrived_c(h3_fire_e),
    .ack_out_a(h1_ack_in_s),   .ack_out_b(h2_ack_in_n),   .ack_out_c(h3_ack_in_e),
    .data_out(col_data_out_e), .fire(col_fire_e),
    .ready_in(1'b1), .ack_in(col_ack_in_e)
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
    .status_core_select(q_status_core_select)
);

assign col_ack_in_e = q_ack_out_w;

// ── Real host bridge (v3): replaces v2's own self-test FSM entirely.
// ICM_LOAD/UNFREEZE/ADVANCE/BRAM_READ/BRAM_WRITE all now come from a
// real external host over JTAG, per this file's own header discipline
// (preload/configure everything BEFORE the first ADVANCE). ──
host_bridge_sentinel_gather_v1 BRIDGE (
    .clk(clk), .rst(rst),
    .bram_cmd_valid(bridge_bram_cmd_valid), .bram_cmd_op(bridge_bram_cmd_op),
    .bram_cmd_addr(bridge_bram_cmd_addr), .bram_cmd_wdata(bridge_bram_cmd_wdata),
    .bram_rdata_valid(shared_rdata_valid), .bram_rdata(shared_rdata),
    .bram_write_done(shared_write_done),
    .icm_cfg_data(icm_cfg_data),
    .icm_cfg_valid_h1(h1_cfg_valid), .icm_cfg_valid_h2(h2_cfg_valid),
    .icm_cfg_valid_h3(h3_cfg_valid), .icm_cfg_valid_q(q_cfg_valid),
    .unfreeze_h1(h1_host_unfreeze), .unfreeze_h2(h2_host_unfreeze), .unfreeze_h3(h3_host_unfreeze),
    .advance_trigger(advance_trigger),
    .status_core_select_h1(h1_status_core_select), .status_core_select_h2(h2_status_core_select),
    .status_core_select_h3(h3_status_core_select), .status_core_select_q(q_status_core_select),
    .h1_need_data(h1_need_data), .h1_results_ready(h1_results_ready), .h1_safe(h1_safe), .h1_err(h1_err),
    .h2_need_data(h2_need_data), .h2_results_ready(h2_results_ready), .h2_safe(h2_safe), .h2_err(h2_err),
    .h3_need_data(h3_need_data), .h3_results_ready(h3_results_ready), .h3_safe(h3_safe), .h3_err(h3_err),
    .q_data_out_n(q_data_out_n)
);

wire [79:0] icm_cfg_data;
assign h1_cfg_data = icm_cfg_data;
assign h2_cfg_data = icm_cfg_data;
assign h3_cfg_data = icm_cfg_data;
assign q_cfg_data  = icm_cfg_data;

reg [23:0] hb_cnt = 0;
always @(posedge clk) hb_cnt <= hb_cnt + 24'd1;

assign LED0_N = ~hb_cnt[23];
assign LED1_N = ~(h1_err || h2_err || h3_err);

endmodule
