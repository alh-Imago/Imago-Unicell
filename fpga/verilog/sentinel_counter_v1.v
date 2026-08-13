// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sentinel_counter_v1.v — first real RTL for points.md #279's FULL
// SENTINEL SYSTEM design (Alan's own design, resolving BOTH of #257's
// originally-open questions). DRAFT — sim-verified only, no Quartus
// data yet.
//
// A standalone, reusable module — NOT tied to any specific cell or
// chain. Any two "endpoints" of a real model can be wired to it: A's
// own successful-feed pulse, B's own successful-collect pulse. This
// matches #279's own framing directly: "the compiler always had to
// know the depth and timing of each model" — chain_length is a
// per-model config value the compiler supplies, not something this
// module derives.
//
// THE DIFF (#279): diff = A's feed count - B's collect count, starts
// at 0, rises toward roughly chain_length during steady-state
// operation (a real pipeline has latency -- chain_length in-flight
// items at any instant during steady operation is the expected
// occupancy, not an arbitrary starting value).
//
// THE FREEZE/FLAG MECHANISM (#279, Alan's own design):
//   - Starts FROZEN at power-on (not running) — Alan's own question,
//     answered directly: real usage never pre-fills the whole memory
//     area, so the read side must never be free-running before the
//     host's first load either. This reuses the exact same protocol
//     as every later reload, with no special-casing (see the state
//     declaration below for why this falls out naturally).
//   - out_wrap_pulse (external input -- the OUT-side address counter's
//     own wrap-to-0 event, detected OUTSIDE this module by watching
//     `addr==WRAP_AT && advance_en` on the existing, already-proven
//     addr_counter_v1.v -- never modified, just observed) sets
//     `out_frozen` and raises `need_data_flag`.
//   - `results_ready_flag` raises only once out_frozen AND diff has
//     drained to exactly 0 -- the precise, deterministic "run
//     genuinely finished" signal, replacing an earlier idle-timeout
//     idea that was explicitly rejected mid-design for needing an
//     unprincipled per-model tuned constant.
//   - `safe_to_intervene` is the AND of both -- Alan's own crucial
//     correction: OUT freezing alone doesn't prove the pipeline is
//     drained, only that no NEW data is entering. Only the AND means
//     it's genuinely safe for the host to read results, reload input,
//     and unfreeze both ends.
//   - `host_unfreeze_pulse` (external input) clears `out_frozen`,
//     resuming normal operation with fresh data already reloaded by
//     the host by this point.
//
// ERROR CONDITIONS (#279):
//   - diff < 0 (B collected more than A ever sent -- impossible in a
//     correct system) -> `freeze_out` asserted immediately (even if
//     the natural wrap hasn't happened), `err_flag` raised.
//   - diff >= 2*chain_length (far more in flight than the pipeline
//     could legitimately hold -- a principled bound, double the
//     maximum a healthy chain of that depth should ever hold) ->
//     `freeze_in` asserted, `err_flag` raised.
//   - Both error flags are STICKY (require `host_unfreeze_pulse` to
//     clear, same as the normal-completion path) -- an error should
//     never silently self-heal. Confirmed directly, worth stating
//     explicitly: `host_unfreeze_pulse` clears the LATCHED FLAG, but if
//     the underlying condition (`diff` still out of range) hasn't
//     actually been resolved by the host, the error re-latches on the
//     very next cycle once the pulse ends. This is deliberate, safe
//     behavior, not a bug -- a host can't paper over a genuinely
//     unresolved fault by pulsing unfreeze alone; real recovery
//     requires the host to actually address the underlying condition
//     (e.g. draining enough in-flight data to bring `diff` back under
//     threshold) before or during the unfreeze pulse.
`default_nettype none
`timescale 1ns / 1ps

module sentinel_counter_v1 #(
    parameter DIFF_WIDTH = 16   // must be wide enough for 2*chain_length + margin
) (
    input  wire                    clk,
    input  wire                    rst,

    input  wire                    feed_pulse,      // A's own successful-feed event
    input  wire                    collect_pulse,   // B's own successful-collect event
    input  wire [DIFF_WIDTH-1:0]   chain_length,     // compiler-supplied, per-model config

    input  wire                    out_wrap_pulse,   // OUT-side counter's own wrap-to-0 event
    input  wire                    host_unfreeze_pulse,

    output wire                    freeze_out,       // drive into the OUT-side chain's freeze_in
    output wire                    freeze_in,        // drive into the IN-side chain's freeze_in
    output wire                    need_data_flag,    // OUT has frozen, host should reload
    output wire                    results_ready_flag,// diff==0 while frozen -- genuinely finished
    output wire                    safe_to_intervene, // AND of both -- Alan's own correction
    output wire                    err_flag,          // either error condition latched

    output wire signed [DIFF_WIDTH:0] diff_out        // debug/status — one bit wider to show sign
);

    reg signed [DIFF_WIDTH:0] diff = 0;   // one bit wider than chain_length to represent negative
    // NOTE: out_frozen defaults to FROZEN (1), not running (0) --
    // Alan's own question, answered directly: real usage never
    // pre-fills the whole memory area, so the read side must not be
    // free-running from power-on either. Starting frozen means the
    // host's very first data load uses the EXACT SAME protocol as
    // every later reload -- no special-casing needed, confirmed by
    // checking `results_ready_flag`'s own definition below
    // (`out_frozen && diff==0`): at power-on, nothing has been fed or
    // collected yet, so `diff` is already 0 -- meaning
    // `results_ready_flag`/`safe_to_intervene` correctly assert
    // immediately at power-on too, telling the host "safe to load now"
    // before any run has ever happened.
    reg out_frozen  = 1'b1;
    reg err_negative = 1'b0;   // diff < 0 latched
    reg err_overflow = 1'b0;   // diff >= 2*chain_length latched

    wire diff_would_go_negative = (diff == 0) && collect_pulse && !feed_pulse;
    wire [DIFF_WIDTH:0] double_chain_length = {1'b0, chain_length} << 1;

    always @(posedge clk) begin
        if (rst) begin
            diff         <= 0;
            out_frozen   <= 1'b1;   // power-on: frozen, waiting for the host's first load
            err_negative <= 1'b0;
            err_overflow <= 1'b0;
        end else begin
            // The diff itself — a simple net counter, +1 on feed,
            // -1 on collect, both in the same cycle is a genuine net
            // zero change (handled naturally by signed addition).
            case ({feed_pulse, collect_pulse})
                2'b10: diff <= diff + 1;
                2'b01: diff <= diff - 1;
                default: diff <= diff;   // 2'b00 (no change) or 2'b11 (net zero)
            endcase

            // OUT-side freeze — set on wrap, cleared only by explicit
            // host action (never self-clears).
            if (out_wrap_pulse) out_frozen <= 1'b1;
            else if (host_unfreeze_pulse) out_frozen <= 1'b0;

            // Error latches — sticky, cleared only by explicit host
            // action. `host_unfreeze_pulse` must take PRIORITY over the
            // ongoing condition check: an earlier draft checked the
            // condition first, so if `diff` was still at/past threshold
            // at the exact cycle unfreeze fired (which it always is,
            // since nothing else changes `diff` during the unfreeze
            // pulse itself), the error silently re-latched instead of
            // clearing — confirmed directly via iverilog (PART 3's
            // unfreeze check failed). `host_unfreeze_pulse` represents
            // the host having already resolved the underlying issue, so
            // it must unconditionally win, not be subordinate to a
            // stale condition read.
            if (host_unfreeze_pulse) err_negative <= 1'b0;
            else if (diff < 0) err_negative <= 1'b1;

            if (host_unfreeze_pulse) err_overflow <= 1'b0;
            else if (diff >= $signed(double_chain_length)) err_overflow <= 1'b1;
        end
    end

    assign diff_out = diff;

    assign need_data_flag     = out_frozen;
    assign results_ready_flag = out_frozen && (diff == 0);
    assign safe_to_intervene  = need_data_flag && results_ready_flag;   // literally the same
                                                                          // condition here, but
                                                                          // exposed separately per
                                                                          // #279's own literal
                                                                          // framing — the host is
                                                                          // expected to AND them.
    assign err_flag    = err_negative || err_overflow;
    assign freeze_out   = out_frozen || err_negative;
    assign freeze_in    = err_overflow;

endmodule
