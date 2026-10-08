// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// latch_cell_v4s.v -- stripped version of latch_cell_v4c.v's real function. Same
// wrinkle as accumulator_cell_v4s.v: the original distinguishes SET/CLEAR/TOGGLE
// by which cardinal direction an arrival came from, not by data content -- so
// this becomes three dedicated one-bit event pulses instead of three masks.
//
// One simplification worth stating precisely: the original's SET only actually
// fires when the arriving value's bit 0 is 1 (a real #295 bug fix -- an arrival
// carrying 0 is silently a no-op, functionally IDENTICAL to no request at all).
// So a single `set_in` pulse (asserted = a real set request) is exactly
// equivalent to that original behaviour -- there is no case where the original's
// "arrival with value 0" did anything different from "no arrival," so no separate
// value line is needed here.
//
// Priority CLEAR > SET > TOGGLE, unchanged from the original.
//
// No config fields at all for the core function -- unlike the other v4s cells,
// there is nothing left to configure once direction masks are removed. cfg_valid
// still exists purely to arm the cell (gate it until boot-load has happened once),
// matching every other v4s cell's safety convention.
`default_nettype none
`timescale 1ns / 1ps

module latch_cell_v4s #(
    parameter [15:0] CELL_ID = 16'h0000
) (
    input  wire        clk,
    input  wire        rst,

    input  wire         cfg_valid,
    input  wire [31:0]  cfg_data,   // unused by this cell's function; kept for a
                                     // uniform port shape across the v4s family

    input  wire         set_in,
    input  wire         clear_in,
    input  wire         toggle_in,

    output wire [31:0]  data_out,
    output wire         valid_out
);

    reg        armed       = 1'b0;
    reg        latched     = 1'b0;
    reg        out_buffer  = 1'b0;
    reg        valid_out_r = 1'b0;

    // ── The real priority logic -- unchanged from v4c: CLEAR > SET > TOGGLE ──
    wire next_latched = clear_in ? 1'b0 : set_in ? 1'b1 : toggle_in ? ~latched : latched;
    wire any_event = set_in || clear_in || toggle_in;

    assign data_out  = {31'h0, out_buffer};
    assign valid_out = valid_out_r;

    always @(posedge clk) begin
        if (rst) begin
            armed       <= 1'b0;
            latched     <= 1'b0;
            out_buffer  <= 1'b0;
            valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            armed       <= 1'b1;
            latched     <= 1'b0;
            out_buffer  <= 1'b0;
            valid_out_r <= 1'b0;
        end else begin
            if (any_event) latched <= next_latched;
            out_buffer  <= next_latched;
            valid_out_r <= armed && any_event;
        end
    end

endmodule
