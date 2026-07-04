// SPDX-License-Identifier: CERN-OHL-P-2.0
// Copyright (c) 2026 Imago UniCell Project
// Hardware design — see LICENSE-HARDWARE and NOTICE
// bram_dp_v3.v — true dual-port BRAM buffer, the "BRAM as universal primitive"
// inter-zone data channel (docs/design-notes/bram_load_protocol.md +
// sessions/latest.md "I/O via BRAM-direct"). Written in the standard
// true-dual-port inference pattern (independent clock-a/clock-b style ports
// sharing one clock domain here) so Quartus infers an M20K block rather than
// distributed logic. Port A is the WRITE side (a fired cell's output lands
// here); port B is the READ side (a downstream zone/consumer pulls it back
// out). Same shape whether the two sides are two zones on one card, or a
// host DMA on one side and a zone on the other — the "universal primitive"
// point: one memory, multiple roles, distinguished only by who's driving
// which port this cycle.
`default_nettype none
`timescale 1ns / 1ps

module bram_dp_v3 #(
    parameter ADDR_W = 8,          // 256 words default -- widen for a real card
    parameter DATA_W = 32
) (
    input  wire                  clk,

    // Port A -- write side
    input  wire [ADDR_W-1:0]     a_addr,
    input  wire [DATA_W-1:0]     a_wdata,
    input  wire                  a_we,
    output reg  [DATA_W-1:0]     a_rdata,   // registered read (1-cycle latency, same as real BRAM)

    // Port B -- read side (can also write, if a future role needs it)
    input  wire [ADDR_W-1:0]     b_addr,
    input  wire [DATA_W-1:0]     b_wdata,
    input  wire                  b_we,
    output reg  [DATA_W-1:0]     b_rdata
);

    reg [DATA_W-1:0] mem [0:(1<<ADDR_W)-1];

    // Port A
    always @(posedge clk) begin
        if (a_we) mem[a_addr] <= a_wdata;
        a_rdata <= mem[a_addr]; // registered read -- matches real BRAM latency;
                                 // the "trigger on bridge-out, not BRAM-out" rule
                                 // from sessions/latest.md applies to consumers of
                                 // a_rdata/b_rdata, not to this module itself.
    end

    // Port B
    always @(posedge clk) begin
        if (b_we) mem[b_addr] <= b_wdata;
        b_rdata <= mem[b_addr];
    end

endmodule
