// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// dsp_add_wrapper_v1.v — points.md #453/#461/#462: the first real DSP
// float wrapper, per #453's own design ("even the DSP if can be just a
// RAM cell, it's only passing data after all"). Confirms directly, not
// assumed: Arria 10's hardened floating-point mode (#461, checked
// against multiple real Intel sources) provides a real IEEE-754
// single-precision adder inside every DSP block, real megafunction
// name `alterafpf_add_single` (#462), real confirmed 3-cycle latency.
//
// REAL ARCHITECTURAL PLACEMENT, per #427's own already-established
// precedent (the BRAM interface is dedicated, one-time infrastructure,
// not part of the user-programmable substrate, so it shouldn't pay the
// super carrier shell's own reconfigurability tax): this wrapper is
// DEDICATED GLUE, not a new CORE inside unicell_super_v1's own
// core_select mux. It sits BETWEEN two ordinary unicell_super_v1
// instances configured as RAM cores (exactly like this project's own
// proven `QUEUE` instance in v3) -- one capturing/offering the two
// real fabric-side operands, one capturing/offering the real result --
// with the real hard DSP IP living entirely in this wrapper's own
// glue, outside the fabric's own logic. This is deliberately consistent
// with "topology is computation": from the fabric's own perspective,
// this wrapper is just another cardinal-style neighbor, using the SAME
// offer/arrived/ack protocol every other cell already uses -- no
// special introspection into a RAM cell's own internal register is
// needed or used.
//
// A REAL, CONFIRMED architectural validation, not assumed: #453's own
// earlier real correction (pipeline latency needs NO new shell
// mechanism -- the event-driven handshake already tolerates arbitrary
// delay) holds up directly here. The real DSP add operation takes a
// real, confirmed 3 clock cycles (#462) -- trivially short relative to
// what the existing patient capture/offer pattern was already built to
// handle. No new handshake primitive needed, exactly as predicted.
//
// REAL, HONEST SCOPE: the exact Verilog port names of the real
// `alterafpf_add_single` megafunction were NOT independently confirmed
// (#462's own stated gap) -- this file uses the standard, decades-
// documented Altera megafunction convention (`dataa`/`datab`/`clock`/
// `result`) as the reasonable default, clearly flagged here for real
// confirmation once Alan generates the actual IP via IP Catalog, same
// "build now, confirm against real generation" pattern already proven
// for the ISSP bridges (#441-#445). `tb_stub_alterafpf_add_single_v1.v`
// is a SIMULATION-ONLY stand-in matching this assumed interface --
// verifies this wrapper's own real protocol logic (dual-operand
// capture, the real 3-cycle wait, result offer) independent of whether
// the exact IP port names turn out to need adjustment.
`default_nettype none
`timescale 1ns / 1ps

module dsp_add_wrapper_v1 (
    input  wire        clk,
    input  wire        rst,

    // ── Operand A input (cardinal-style, matching collector_relay_v1's
    // own real a/b/c naming convention for non-cardinal-direction
    // multi-input ports) ──
    input  wire [31:0] data_in_a,
    input  wire        arrived_a,
    output wire         ack_out_a,

    // ── Operand B input ──
    input  wire [31:0] data_in_b,
    input  wire        arrived_b,
    output wire         ack_out_b,

    // ── Result output (single cardinal-style offer, matching
    // collector_relay_v1's own real single-output convention) ──
    output reg  [31:0] data_out,
    output wire         fire,
    input  wire         ready_in,
    input  wire         ack_in
);

    // ── Real, confirmed latency (#462): alterafpf_add_single takes
    // exactly 3 real clock cycles. Tracked explicitly with a counter
    // rather than assuming the real megafunction exposes its own
    // "valid" flag -- simple single-precision ALTFP megafunctions
    // often don't, per the standard Altera convention; the caller is
    // expected to know and account for the fixed, deterministic
    // latency externally. If the real generated IP turns out to expose
    // its own valid/done signal, this counter-based wait can be
    // replaced with that real signal directly -- a strictly simpler
    // change than the reverse. ──
    localparam ADD_LATENCY = 3;

    reg [31:0] latched_a, latched_b;
    reg        primed_a, primed_b;
    reg [1:0]  wait_cnt;
    reg        computing;
    reg        result_ready;

    // ── Real, unconditional-style ack, mirroring collector_relay_v1's
    // own exact proven pattern -- combinational, asserted the instant a
    // real operand can be accepted, never gated behind an extra
    // registered delay (this project's own standing "never gate the
    // offering side" discipline). ──
    assign ack_out_a = arrived_a && !primed_a && !computing;
    assign ack_out_b = arrived_b && !primed_b && !computing;

    wire both_primed = primed_a && primed_b;

    wire [31:0] add_result;
    alterafpf_add_single DSP_ADD (
        .dataa  (latched_a),
        .datab  (latched_b),
        .clock  (clk),
        .result (add_result)
    );

    // ── Real, held offer, mirroring collector_relay_v1's own exact
    // proven `want_to_offer`/`will_fire` pattern -- `fire` stays high
    // continuously once the real result is ready, until the real
    // downstream neighbor acks it. A one-cycle pulse here was an
    // earlier, real bug caught before this file was trusted: checking
    // `fire` combined with `ack_in` in the SAME always block that also
    // sets `fire` would have read `fire`'s OLD (pre-edge) value, one
    // real cycle late relative to when the result actually became
    // available -- the same class of timing bug this project has
    // caught and fixed before (`#414`'s own "op-reset landing same
    // cycle" class of issue). ──
    wire will_fire = result_ready && ready_in;
    assign fire = will_fire;

    always @(posedge clk) begin
        if (rst) begin
            latched_a    <= 32'h0;
            latched_b    <= 32'h0;
            primed_a     <= 1'b0;
            primed_b     <= 1'b0;
            wait_cnt     <= 2'd0;
            computing    <= 1'b0;
            result_ready <= 1'b0;
            data_out     <= 32'h0;
        end else begin
            // ── Real capture: each operand latches independently,
            // whichever arrives first -- no assumption either side
            // arrives before the other, matching the fabric's own
            // real, patient, event-driven discipline. ──
            if (ack_out_a) begin
                latched_a <= data_in_a;
                primed_a  <= 1'b1;
            end
            if (ack_out_b) begin
                latched_b <= data_in_b;
                primed_b  <= 1'b1;
            end

            // ── Once both real operands are captured, fire the real
            // DSP operation and wait the real, confirmed 3-cycle
            // latency. ──
            if (both_primed && !computing) begin
                computing <= 1'b1;
                wait_cnt  <= 2'd0;
            end else if (computing && !result_ready) begin
                if (wait_cnt == ADD_LATENCY - 1) begin
                    data_out     <= add_result;
                    result_ready <= 1'b1;
                end else begin
                    wait_cnt <= wait_cnt + 2'd1;
                end
            end

            // ── Once the real downstream neighbor acks the result,
            // the wrapper is free to accept a new pair of operands --
            // matching every other cell's own real "offer held until
            // acked" discipline, not fire-and-forget. ──
            if (will_fire && ack_in) begin
                computing    <= 1'b0;
                result_ready <= 1'b0;
                primed_a     <= 1'b0;
                primed_b     <= 1'b0;
            end
        end
    end

endmodule
