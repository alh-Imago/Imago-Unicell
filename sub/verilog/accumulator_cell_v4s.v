// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// accumulator_cell_v4s.v -- stripped version of accumulator_cell_v4c.v's real
// function. One real wrinkle, worth stating plainly: the original distinguishes
// "increment" from "decrement" by WHICH cardinal direction an arrival came from
// (inc_dir/dec_dir masks), not by any value the arrival carries -- the incoming
// data_in value is never even used for inc/dec; the step size comes entirely from
// a fixed, configured step_amount. Stripped to fixed ports, that becomes two
// dedicated one-bit EVENT pulses (inc_pulse, dec_pulse) instead of two 32-bit data
// operands -- the same "one dedicated wire per real role the function needs"
// principle as adder_cell_v4s's in_a/in_b, just applied to events instead of data.
//
// Same mechanical strip otherwise: no addon chain, no downstream mask/ack, fixed
// latency, boot-load config only. See sub/README.md / adder_cell_v4s.v.
//
// pulse_mode is a REAL function distinction (not cardinality machinery) and is
// kept faithfully: 0 = continuous (data_out always mirrors the running total;
// valid_out fires whenever a real inc/dec event happens), 1 = pulse (the running
// total resets to zero and fires exactly once, only when its magnitude crosses
// the configured threshold).
//
// cfg_data field map:
//   [7:0]   step_amount -- unsigned magnitude applied per inc/dec pulse
//   [8]     pulse_mode  -- 0=continuous, 1=reset-after-threshold-hit
//   [24:9]  threshold   -- pulse_mode only, unsigned magnitude to cross
`default_nettype none
`timescale 1ns / 1ps

module accumulator_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,

    input  wire         inc_pulse,
    input  wire         dec_pulse,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg [7:0]  step_amount = 8'h0;
    reg        pulse_mode  = 1'b0;
    reg [15:0] threshold   = 16'h0;
    reg        armed       = 1'b0;

    reg signed [WIDTH-1:0] accumulator = 0;
    reg signed [WIDTH-1:0] out_buffer  = 0;
    reg                    valid_out_r = 1'b0;

    // ── The real accumulate logic -- unchanged semantics from v4c ───────
    wire signed [WIDTH-1:0] step_ext = {{(WIDTH-8){1'b0}}, step_amount};
    wire signed [WIDTH-1:0] delta = (inc_pulse && !dec_pulse) ?  step_ext :
                                     (dec_pulse && !inc_pulse) ? -step_ext :
                                                                  {WIDTH{1'b0}};
    wire signed [WIDTH-1:0] next_accumulator = accumulator + delta;
    wire signed [WIDTH-1:0] threshold_ext = {{(WIDTH-16){1'b0}}, threshold};
    wire signed [WIDTH-1:0] abs_next_acc  = next_accumulator[WIDTH-1] ? -next_accumulator : next_accumulator;
    wire threshold_hit = pulse_mode && (inc_pulse || dec_pulse) &&
                         (threshold != 16'h0) && (abs_next_acc >= threshold_ext);

    assign data_out  = out_buffer[31:0];
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            step_amount  <= 8'h0;
            pulse_mode   <= 1'b0;
            threshold    <= 16'h0;
            armed        <= 1'b0;
            accumulator  <= 0;
            out_buffer   <= 0;
            valid_out_r  <= 1'b0;
        end else if (cfg_valid) begin
            step_amount  <= cfg_data[7:0];
            pulse_mode   <= cfg_data[8];
            threshold    <= cfg_data[24:9];
            armed        <= 1'b1;
            accumulator  <= 0;
            out_buffer   <= 0;
            valid_out_r  <= 1'b0;
        end else begin
            if (inc_pulse || dec_pulse) begin
                accumulator <= (pulse_mode && threshold_hit) ? {WIDTH{1'b0}} : next_accumulator;
            end

            if (pulse_mode) begin
                if (threshold_hit) out_buffer <= next_accumulator;
                // else: hold the last snapshot -- pulse mode only ever
                // presents a fresh value at the moment it actually fires.
            end else begin
                out_buffer <= next_accumulator;   // continuous: always mirrors the running total
            end

            valid_out_r <= armed && (pulse_mode ? threshold_hit : (inc_pulse || dec_pulse));
        end
    end

endmodule
