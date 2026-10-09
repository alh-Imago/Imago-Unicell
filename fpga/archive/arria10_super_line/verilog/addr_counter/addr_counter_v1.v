// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
//
// addr_counter_v1.v — free-running, ack-gated, wrapping address counter.
// points.md #243-#246: the address generator the BRAM-interface design
// note needed. Built on adder_v1.v, NOT the NOR-cell fabric (points.md
// #245: no arithmetic primitive exists in either cell type's gate table
// -- checked directly, not assumed). Same category of "ordinary
// dedicated hardware sitting alongside the fabric" as the existing
// div_cnt clock divider.
//
// advance_en (points.md #245): deliberately NOT a free-running enable.
// ram_cell_v1.v genuinely has ack-based handshaking both directions
// (checked directly against #235's RTL) -- so this counter's advance_en
// should be driven by the chain-head RAM cell's own ack (e.g. its
// ack_out toward this counter's side, once that interface exists),
// pacing the address against real consumption. Advancing blindly every
// cycle would let the counter race ahead of an un-consumed fetch and
// overwrite it before the chain ever sees it.
//
// WRAP_AT is inclusive: the counter wraps to 0 the cycle AFTER reaching
// this value, giving a (WRAP_AT+1)-deep circular address range --
// exactly the circular-buffer addressing points.md #244 described
// ("once it reaches the end, it restarts").
`default_nettype none
`timescale 1ns / 1ps

module addr_counter_v1 #(
    parameter WIDTH   = 32,
    parameter [WIDTH-1:0] WRAP_AT = {WIDTH{1'b1}}  // default: full range, wraps at 2^WIDTH-1
) (
    input  wire              clk,
    input  wire              rst,
    input  wire              advance_en,  // pace against the consumer's own ack -- see header
    output reg  [WIDTH-1:0]  addr
);

    wire [WIDTH-1:0] next_linear;
    wire             unused_cout;

    adder_v1 #(.WIDTH(WIDTH)) INC (
        .a(addr),
        .b({{(WIDTH-1){1'b0}}, 1'b1}),  // +1
        .cin(1'b0),
        .sum(next_linear),
        .cout(unused_cout)
    );

    wire [WIDTH-1:0] next_addr = (addr == WRAP_AT) ? {WIDTH{1'b0}} : next_linear;

    always @(posedge clk) begin
        if (rst) addr <= {WIDTH{1'b0}};
        else if (advance_en) addr <= next_addr;
    end

endmodule
