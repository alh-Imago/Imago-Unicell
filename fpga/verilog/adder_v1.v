// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// adder_v1.v — a small, standalone, genuinely arithmetic N-bit adder.
// points.md #245/#246: NOT a fabric cell, and deliberately not built as
// one. Checked directly against unicell_stripped_v1.v's own gate table
// (every g0-g9 term is a purely bitwise, per-bit-uniform NOR-derived
// Boolean combination — none of them carry information between bit
// positions) and against the FULL cell's own `loop_back` mechanism
// (unicell64_v3.v, cmd_latch[31] — feeds the SAME NOR-decomposition
// `computed_output` back as the next A, confirmed via its own module
// header: "Gate computation is UNCHANGED from the FULL cell"). Neither
// cell type has ever had a real arithmetic primitive — binary addition
// needs a carry chain, and nothing in either gate table produces one.
// This is that missing primitive, built as ordinary dedicated hardware,
// the same category as the existing div_cnt clock divider, not routed
// through the NOR-universal cell fabric at all.
//
// Plain behavioral `+` rather than a hand-built structural ripple-carry
// -- Quartus maps this directly onto Arria 10's own dedicated ALM carry
// chains, which will always be more efficient than a manually-structured
// equivalent. Purely combinational; register the output externally
// (see addr_counter_v1.v) if a clocked accumulator is needed.
`default_nettype none
`timescale 1ns / 1ps

module adder_v1 #(
    parameter WIDTH = 32
) (
    input  wire [WIDTH-1:0] a,
    input  wire [WIDTH-1:0] b,
    input  wire             cin,
    output wire [WIDTH-1:0] sum,
    output wire             cout
);

    assign {cout, sum} = {1'b0, a} + {1'b0, b} + {{WIDTH{1'b0}}, cin};

endmodule
