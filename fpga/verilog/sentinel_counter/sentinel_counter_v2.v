// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// sentinel_counter_v2.v — a deliberate CLONE of `sentinel_counter_v1.v`
// (never modify a proven file in place), fixing a real Quartus
// synthesis failure confirmed on real hardware.
//
// THE REAL PROBLEM, confirmed via a real Quartus build, not predicted:
// `sentinel_issp_bridge_v1.v` referenced `SENTINEL.out_frozen`,
// `SENTINEL.err_negative`, `SENTINEL.err_overflow` directly --
// hierarchical references into another module's internal signals.
// This works fine in simulation (a common debug convenience already
// used elsewhere in this project's own testbenches) but is NOT
// synthesizable in real hardware -- a universal EDA limitation, not a
// Quartus-specific quirk: `Error (10207): can't resolve reference to
// object "out_frozen"`. Synthesizable RTL must communicate across
// module boundaries only through declared ports.
//
// THE FIX: two new output ports, `err_negative_flag`/`err_overflow_
// flag`, exposing the individual error causes that `err_flag` alone
// (already a real port on v1) can't distinguish between -- Alan's own
// explicit ask was to see "the error states" (plural), not just
// whether an error occurred. `out_frozen` itself needed no new port --
// it's already exactly `need_data_flag` (`assign need_data_flag =
// out_frozen;` in the original file), a genuine alias, not something
// requiring separate exposure.
//
// Everything else is byte-for-byte identical to `sentinel_counter_v1.
// v` -- same diff logic, same freeze/flag mechanism, same power-on-
// frozen default (`#287`), same chain_length_configured guard against
// the chain_length=0 degenerate case (`#288`). Confirmed via
// regression against v1's own proven test vectors.
`default_nettype none
`timescale 1ns / 1ps

module sentinel_counter_v2 #(
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

    // ── New in v2: the two individual error causes, as real ports ──
    output wire                    err_negative_flag,  // diff < 0 latched
    output wire                    err_overflow_flag,  // diff >= 2*chain_length latched

    output wire signed [DIFF_WIDTH:0] diff_out        // debug/status — one bit wider to show sign
);

    reg signed [DIFF_WIDTH:0] diff = 0;   // one bit wider than chain_length to represent negative
    reg out_frozen  = 1'b1;   // power-on: frozen (#287) -- see v1's own header for the reasoning
    reg err_negative = 1'b0;   // diff < 0 latched
    reg err_overflow = 1'b0;   // diff >= 2*chain_length latched

    wire diff_would_go_negative = (diff == 0) && collect_pulse && !feed_pulse;
    wire [DIFF_WIDTH:0] double_chain_length = {1'b0, chain_length} << 1;
    // chain_length==0 degenerate-state guard (#288) -- see v1's own
    // header for the full reasoning.
    wire chain_length_configured = (chain_length != {DIFF_WIDTH{1'b0}});

    always @(posedge clk) begin
        if (rst) begin
            diff         <= 0;
            out_frozen   <= 1'b1;
            err_negative <= 1'b0;
            err_overflow <= 1'b0;
        end else begin
            case ({feed_pulse, collect_pulse})
                2'b10: diff <= diff + 1;
                2'b01: diff <= diff - 1;
                default: diff <= diff;
            endcase

            if (out_wrap_pulse) out_frozen <= 1'b1;
            else if (host_unfreeze_pulse) out_frozen <= 1'b0;

            if (host_unfreeze_pulse) err_negative <= 1'b0;
            else if (diff < 0) err_negative <= 1'b1;

            if (host_unfreeze_pulse) err_overflow <= 1'b0;
            else if (chain_length_configured && diff >= $signed(double_chain_length)) err_overflow <= 1'b1;
        end
    end

    assign diff_out = diff;

    assign need_data_flag     = out_frozen;
    assign results_ready_flag = out_frozen && (diff == 0);
    assign safe_to_intervene  = need_data_flag && results_ready_flag;

    assign err_negative_flag = err_negative;
    assign err_overflow_flag = err_overflow;
    assign err_flag          = err_negative || err_overflow;
    assign freeze_out        = out_frozen || err_negative;
    assign freeze_in         = err_overflow;

endmodule
