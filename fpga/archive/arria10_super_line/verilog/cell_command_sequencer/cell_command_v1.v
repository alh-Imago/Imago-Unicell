// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// cell_command_v1.v — the "command cell" per points.md #123, built as its
// own dedicated, minimal companion module (same pattern already proven
// twice today: cell_wrapper_v1.v, cell_cardinal_cmd_v1.v — sits alongside
// a cell, doesn't touch unicell_stripped_v1.v's now-confirmed-correct
// core, #125).
//
// Confirmed, repeatedly, across #123's design conversation: the command
// cell carries NO config data itself, and knows nothing about where the
// actual 3 program words come from — those arrive at the target through
// the target's own ordinary data_in ports, from anywhere. The command
// cell's ENTIRE job is holding one control line (program_in) high for the
// duration of a transfer, asserted on a trigger, released once
// program_done confirms all 96 bits landed and were applied.
`default_nettype none
`timescale 1ns / 1ps

module cell_command_v1 (
    input  wire clk,
    input  wire rst,

    // ── Trigger: data arrival, per Alan's own framing ("if data arrives
    // it's triggered"). A simple level/pulse from wherever decides this
    // transfer should start — could be a raw external signal, or (per
    // #123's branched-selection idea) a comparator's live match result.
    // This module doesn't care which — it just needs SOMETHING to start
    // on. ──
    input  wire trigger_in,

    // ── The target's own program_done, fed straight back. ──
    input  wire program_done_in,

    // ── The one thing this module actually does. ──
    output reg  program_out
);

always @(posedge clk) begin
    if (rst) begin
        program_out <= 1'b0;
    end else if (!program_out && trigger_in) begin
        program_out <= 1'b1;   // start holding the line
    end else if (program_out && program_done_in) begin
        program_out <= 1'b0;   // confirmed done — release
    end
end

endmodule
