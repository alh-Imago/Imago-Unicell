// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design -- see LICENSE-HARDWARE and NOTICE
//
// merge_cell_v4sa.v -- the MERGE core for the Flex (handshake) family (Alan, after ledger #954).
//
// WHY A CORE AND NOT GLUE. In the original architecture every cell can take several upstream faces: a merge is a property of the cell. The flex cells
// (v4sa) each have ONE input, so a merge needs a place to live. A first version put selection logic ("an arbiter") in the generator's emitted glue and it
// worked (the whole cordic ran), but Alan's ruling is that the system is built from KNOWN, verified core designs and that arbitrary hand-woven glue at
// particular points goes against the idea of it. So the merge is a core, with its own bench, like every other cell.
//
// WHAT THE VM DOES, AND WHY A PLAIN OR IS WRONG HERE. The VM ORs arrivals in the same tick. Under a handshake two sources can BOTH stay valid for as long
// as a cell is busy; a plain OR would then consume both and FUSE two separate items into one corrupt value. So the merge has explicit, selectable modes:
//
//   cfg_data[1:0] = mode
//     0  A only      pass in_a; in_b is never accepted (a one-path "merge": a configurable pass-through)
//     1  B only      pass in_b; in_a is never accepted
//     2  ARBITRATE   either source, one at a time: grant one, acknowledge ONLY that one, rotate priority after every grant (round-robin: neither can
//                    starve). Right when the two paths are alternatives (a branch's two outcomes rejoining -- the cordic's `gather`).
//     3  JOIN-OR     WAIT for BOTH sources, then output in_a | in_b and acknowledge both together. Right when the two paths are halves of ONE item to be
//                    combined -- the "free OR" used as a feature -- made deterministic: it no longer depends on the two items happening to arrive in the
//                    same cycle.
//
// PROTOCOL (the family's, read from adder_cell_v4sa.v / ram_cell_v4sa.v): a cell captures at an edge where it is not `pending`; the result is registered
// (out_buffer) and `valid_out = pending` is held until `ack_in` is high at an edge. An input's `ack_out_*` is the cell's READY for that input, so a transfer
// is an edge where `valid_in_*` and `ack_out_*` are both high. Like every v4sa cell: one item per two cycles, `freeze_in` gates everything, configuration
// arms the cell and clears its state. Hence ONE cycle of added latency and storage, exactly like a relay.
//
// ORDER. No cell can restore the order of items between two paths (that needs per-item tags). A merge is only well-defined when at most one item is in
// flight in the region it joins (true of the loop-style designs that use merges; the compiler never emits one). Mode 3 does not have the problem: it
// takes one item from each side per output.
`default_nettype none
`timescale 1ns / 1ps

module merge_cell_v4sa #(
    parameter [15:0] CELL_ID = 16'h0000,
    parameter        WIDTH   = 32
) (
    input  wire              clk,
    input  wire              rst,
    input  wire              freeze_in,
    input  wire              cfg_valid,
    input  wire [31:0]       cfg_data,      // [1:0] = mode (see above)
    input  wire [WIDTH-1:0]  in_a,
    input  wire              valid_in_a,
    output wire              ack_out_a,     // ready for A
    input  wire [WIDTH-1:0]  in_b,
    input  wire              valid_in_b,
    output wire              ack_out_b,     // ready for B
    output wire [WIDTH-1:0]  data_out,
    output wire              valid_out,
    input  wire              ack_in
);
    reg [1:0]       mode       = 2'd2;
    reg             armed      = 1'b0;
    reg             pending    = 1'b0;
    reg             rr         = 1'b0;      // arbitrate: 1 = B has priority when both are valid
    reg [WIDTH-1:0] out_buffer = {WIDTH{1'b0}};

    wire ready = armed && !pending && !freeze_in;
    wire m_a   = (mode == 2'd0);
    wire m_b   = (mode == 2'd1);
    wire m_arb = (mode == 2'd2);
    wire m_or  = (mode == 2'd3);

    // who is granted this cycle (modes 0-2); mode 3 takes both
    wire g_a = m_a ? valid_in_a : (m_arb ? (valid_in_a && (!valid_in_b || !rr)) : 1'b0);
    wire g_b = m_b ? valid_in_b : (m_arb ? (valid_in_b && !g_a)                  : 1'b0);
    wire take = m_or ? (valid_in_a && valid_in_b) : (g_a || g_b);
    wire [WIDTH-1:0] val = m_or ? (in_a | in_b) : (g_a ? in_a : in_b);

    // ready levels: a transfer happens only for the source(s) actually taken
    assign ack_out_a = ready && (m_or ? valid_in_b : g_a);
    assign ack_out_b = ready && (m_or ? valid_in_a : g_b);

    assign data_out  = out_buffer;
    assign valid_out = pending;

    always @(posedge clk) begin
        if (rst) begin
            mode       <= 2'd2;
            armed      <= 1'b0;
            pending    <= 1'b0;
            rr         <= 1'b0;
            out_buffer <= {WIDTH{1'b0}};
        end else if (cfg_valid) begin
            mode       <= cfg_data[1:0];
            armed      <= 1'b1;
            pending    <= 1'b0;
            rr         <= 1'b0;
            out_buffer <= {WIDTH{1'b0}};
        end else if (!freeze_in) begin
            if (pending) begin
                if (ack_in) pending <= 1'b0;
            end else if (ready && take) begin
                out_buffer <= val;
                pending    <= 1'b1;
                if (m_arb) rr <= g_a;       // the loser gets priority next time
            end
        end
    end
endmodule
