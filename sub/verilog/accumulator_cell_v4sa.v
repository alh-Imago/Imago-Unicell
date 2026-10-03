// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v4sa.v -- points.md #911: the "Flex-Sub" shape (ack+freeze
// per #906, real WIDTH parameter per #909/#910) applied to accumulator, the
// second cell in the family with genuine per-cycle arithmetic, continuing the
// ALU story #908-#910 built. Same real wrinkle as accumulator_cell_v4s.v: the
// original distinguishes increment from decrement by WHICH cardinal direction
// an arrival came from, not by data content -- two dedicated one-bit event
// pulses (inc_pulse/dec_pulse), not two data operands.
//
// A real, pre-existing bug fixed here, not inherited silently: accumulator_cell_
// v4s.v already had a WIDTH parameter internally, but its data_out PORT stayed
// hardcoded [31:0] regardless -- the external interface never actually reflected
// a narrower width correctly. Fixed here: data_out is genuinely [WIDTH-1:0].
//
// ack/freeze: identical shape and reasoning to adder_cell_v4sa.v -- standard
// ready/valid (valid_out stays high until ack_in, not a one-shot pulse),
// freeze_in global and gating the entire update including cfg_valid's own
// effect. See adder_cell_v4sa.v's own header for the full "why this is not a
// retreat from physics, not control" reasoning -- unchanged here.
//
// pulse_mode is a real function distinction (not cardinality machinery),
// unchanged from accumulator_cell_v4s.v: 0 = continuous (every real inc/dec
// is its own offer, pending/ack-gated like any other v4sa cell), 1 = pulse
// (the running total resets to zero and offers exactly once, only when its
// magnitude crosses the configured threshold).
//
// cfg_data field map, unchanged from accumulator_cell_v4s.v:
//   [7:0]   step_amount -- unsigned magnitude applied per inc/dec pulse
//   [8]     pulse_mode  -- 0=continuous, 1=reset-after-threshold-hit
//   [24:9]  threshold   -- pulse_mode only, unsigned magnitude to cross
`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire         inc_pulse,
    input  wire         dec_pulse,
    output wire         ack_out,      // backward, to whoever drives inc_pulse/dec_pulse

    output wire [WIDTH-1:0]  data_out,
    output wire               valid_out,   // stays high until ack_in, not a one-shot pulse
    input  wire               ack_in       // backward, from the one fixed downstream receiver
);

    reg [7:0]  step_amount = 8'h0;
    reg        pulse_mode  = 1'b0;
    reg [15:0] threshold   = 16'h0;
    reg        armed       = 1'b0;
    reg        pending     = 1'b0;   // holding a real, not-yet-consumed offer

    reg signed [WIDTH-1:0] accumulator = 0;
    reg signed [WIDTH-1:0] out_buffer  = 0;

    // ── The real accumulate logic -- unchanged semantics from v4c/v4s ───
    wire signed [WIDTH-1:0] step_ext = {{(WIDTH-8){1'b0}}, step_amount};
    wire signed [WIDTH-1:0] delta = (inc_pulse && !dec_pulse) ?  step_ext :
                                     (dec_pulse && !inc_pulse) ? -step_ext :
                                                                  {WIDTH{1'b0}};
    wire signed [WIDTH-1:0] next_accumulator = accumulator + delta;
    wire signed [WIDTH-1:0] threshold_ext = {{(WIDTH-16){1'b0}}, threshold};
    wire signed [WIDTH-1:0] abs_next_acc  = next_accumulator[WIDTH-1] ? -next_accumulator : next_accumulator;
    wire threshold_hit = pulse_mode && (inc_pulse || dec_pulse) &&
                         (threshold != 16'h0) && (abs_next_acc >= threshold_ext);

    // A real event happened this cycle, in the sense that matters for
    // offering a new value: continuous mode offers on every real inc/dec;
    // pulse mode offers only when the threshold is actually crossed.
    wire real_event = pulse_mode ? threshold_hit : (inc_pulse || dec_pulse);

    assign data_out  = out_buffer;
    assign valid_out = pending;
    assign ack_out   = armed && !pending && !freeze_in;

    always @(posedge clk) begin
        if (rst) begin
            step_amount  <= 8'h0;
            pulse_mode   <= 1'b0;
            threshold    <= 16'h0;
            armed        <= 1'b0;
            pending      <= 1'b0;
            accumulator  <= 0;
            out_buffer   <= 0;
        end else if (cfg_valid) begin
            step_amount  <= cfg_data[7:0];
            pulse_mode   <= cfg_data[8];
            threshold    <= cfg_data[24:9];
            armed        <= 1'b1;
            pending      <= 1'b0;
            accumulator  <= 0;
            out_buffer   <= 0;
        end else if (!freeze_in) begin
            // The running total itself updates on every real inc/dec,
            // REGARDLESS of pending/ack -- an accumulator keeps counting even
            // while its last offer is still waiting to be taken, same as the
            // original v4c/v4s semantics. Only the OFFER (pending/out_buffer)
            // is ack-gated.
            if (inc_pulse || dec_pulse) begin
                accumulator <= (pulse_mode && threshold_hit) ? {WIDTH{1'b0}} : next_accumulator;
            end

            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (real_event) begin
                out_buffer <= next_accumulator;
                pending    <= 1'b1;
            end
        end
    end

endmodule
