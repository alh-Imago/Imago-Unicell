// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// invert_addon_v1.v — third real ADDON in the nano/stripped line
// (points.md #253/#303/#309-#311). The simplest possible addon,
// faithfully ported from `archeology/full-cell/verilog/
// unicell64_v3.v`'s `invert_out` flag (`cmd_latch[25]`) — output-side
// only by definition, a single bitwise NOT gated by an enable, never
// touches the gate computation itself.
//
// cfg bit, deliberately NOT a cmd_latch bit (per #174's own resolved
// addon-delivery decision):
//   invert_en — 1=invert every bit of the output this cycle, 0=pass
//               through unchanged
`default_nettype none
`timescale 1ns / 1ps

module invert_addon_v1 (
    input  wire        invert_en,
    input  wire [31:0] data_in,
    output wire [31:0] data_out
);

    assign data_out = invert_en ? ~data_in : data_in;

endmodule
