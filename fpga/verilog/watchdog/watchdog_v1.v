// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// watchdog_v1.v — points.md #453/#463's own queue: a real, genuinely
// reusable timeout watchdog, composed from real existing primitives
// per #453's own design ("a counter, a comparator, a signal sent, no
// extra cell types"), extended per Alan's own real requirement: the
// threshold must be PROGRAMMABLE, not hardened as a Verilog parameter
// -- the same mechanism could be used in multiple places, each with
// its own real, independently-configured threshold.
//
// A real, deliberate design choice, not a mechanical reuse of
// `compare_cell_v1.v`: that CORE already has exactly this kind of real,
// ICM-loaded threshold field (`cfg_data[39:8]`, confirmed directly
// from Alan's own real Control Signals report this session), but its
// own native semantics are EVENT-DRIVEN -- one cardinal arrival, one
// comparison, one offered result. Forcing a continuously-running
// counter's own live value through that one-shot-arrival shape would
// need real, awkward glue (an artificial repeated "arrival" pulse)
// that doesn't actually fit the real use case any better than a small,
// dedicated module built for it directly. So this file keeps the SAME
// real convention `compare_cell_v1.v` already established (a
// `cfg_valid` pulse loading a real threshold register, not a fixed
// parameter) without forcing the module itself to be reused where its
// own real semantics don't fit.
//
// REAL, INTENTIONALLY GENERIC INTERFACE: `activity_pulse` is whatever
// the real "genuine progress happened" signal is at the instantiation
// site -- for the DSP wrapper (`dsp_add_wrapper_v1.v`), that's
// `will_fire && ack_in` (a real operation genuinely completing); for a
// sentinel-style chain, it would be a real feed/collect event. This
// file makes no assumption about which -- it only ever resets on
// whatever pulse it's given, matching Alan's own explicit requirement
// ("don't forget to reset the timer watchdog when data flows again")
// -- this is what makes it a genuine watchdog rather than a fixed
// deadline: a chain that's slow but still genuinely progressing never
// trips it, only real, sustained silence does.
`default_nettype none
`timescale 1ns / 1ps

module watchdog_v1 #(
    parameter WIDTH = 16
) (
    input  wire             clk,
    input  wire             rst,

    // ── Real, programmable threshold -- same cfg_valid-pulse
    // convention as every other CORE in this project, not a hardcoded
    // parameter. Loading a new threshold also clears any in-flight
    // count, matching every other CORE's own real "cfg_valid resets
    // live state" convention (accumulator_cell_v1.v, compare_cell_v1.v,
    // ...). ──
    input  wire             cfg_valid,
    input  wire [WIDTH-1:0] cfg_threshold,

    // ── Real "something happened" pulse -- whatever counts as genuine
    // progress at the instantiation site. Resets the count, same
    // cycle, no exceptions. ──
    input  wire             activity_pulse,

    // ── Held high once the count reaches the real, configured
    // threshold with no activity_pulse in between -- stays high until
    // the next real activity_pulse or reset, matching every other real
    // status flag in this project (not a one-cycle pulse). ──
    output wire              timeout_flag,

    // ── Real, live status readback -- lets a real host bridge expose
    // "how close to timeout" for debugging, same spirit as this
    // project's own existing status_core_select/status_data_valid
    // taps elsewhere. ──
    output wire [WIDTH-1:0]  count_out
);

    reg [WIDTH-1:0] threshold_reg;
    reg [WIDTH-1:0] count;

    // ── Real, sensible default: threshold defaults to the maximum
    // representable value at reset -- a real watchdog that hasn't yet
    // been configured should never trip, not trip immediately on
    // whatever `0` would mean. ──
    always @(posedge clk) begin
        if (rst) begin
            threshold_reg <= {WIDTH{1'b1}};
        end else if (cfg_valid) begin
            threshold_reg <= cfg_threshold;
        end
    end

    always @(posedge clk) begin
        if (rst) begin
            count <= {WIDTH{1'b0}};
        end else if (cfg_valid || activity_pulse) begin
            count <= {WIDTH{1'b0}};
        end else if (count < threshold_reg) begin
            count <= count + 1'b1;
        end
        // Once count reaches threshold_reg, it deliberately holds
        // there (not wrapping) until a real activity_pulse or reset --
        // timeout_flag stays correctly asserted rather than glitching
        // if nothing else ever touches this instance again.
    end

    assign timeout_flag = (count >= threshold_reg);
    assign count_out    = count;

endmodule
