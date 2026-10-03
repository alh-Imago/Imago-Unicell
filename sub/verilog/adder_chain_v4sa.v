// adder_chain_v4sa.v -- points.md #908: a parameterized chain of NSTAGES
// adder_cell_v4sa instances, point-to-point, ack flowing backward stage to
// stage, built to get real timing figures at scale (Alan's own request: single
// unit first, then a 10x10 = 100-cell matrix).
//
// Each stage's real sum feeds the next stage's in_a; in_b at each stage is a
// distinct rotation of the same live LFSR (not a shared, identical signal) so
// no two ports on any one stage -- or across stages -- are provably related,
// matching the anti-collapse discipline #889's own methodology established.
// ack_out from stage i+1 feeds ack_in of stage i (the real, point-to-point
// backward handshake); the chain's own first stage gets real external
// stimulus, and its last stage's ack_in is driven by whatever the surrounding
// harness supplies (a real periodic tick for the full hardware build, or a
// testbench-controlled signal for the small-scale correctness/backpressure
// tests this file's own testbench runs first).
`default_nettype none
`timescale 1ns / 1ps

module adder_chain_v4sa #(
    parameter NSTAGES = 100
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        freeze_in,

    input  wire         cfg_valid,

    input  wire [31:0]  chain_in,
    input  wire         chain_valid_in,
    output wire          chain_ack_out,     // backward, out of the whole chain's first stage

    output wire [31:0]  chain_out,
    output wire         chain_valid_out,
    input  wire         chain_ack_in,       // the real external consumer, at the chain's far end

    input  wire [31:0]  lfsr                // live, non-constant per-stage operand source
);

    wire [31:0] stage_data  [0:NSTAGES];
    wire        stage_valid [0:NSTAGES];
    wire        stage_ack   [0:NSTAGES];

    assign stage_data[0]  = chain_in;
    assign stage_valid[0] = chain_valid_in;
    assign chain_ack_out  = stage_ack[0];

    assign chain_out       = stage_data[NSTAGES];
    assign chain_valid_out = stage_valid[NSTAGES];
    assign stage_ack[NSTAGES] = chain_ack_in;

    genvar i;
    generate
        for (i = 0; i < NSTAGES; i = i + 1) begin : STAGE
            // A distinct rotation of lfsr per stage -- a real, compile-time-constant
            // shift amount per generate iteration, not a runtime-variable select.
            wire [31:0] in_b_i = ({lfsr, lfsr} >> (i % 32));

            adder_cell_v4sa #(.CELL_ID(i[15:0])) U (
                .clk(clk), .rst(rst), .freeze_in(freeze_in),
                .cfg_valid(cfg_valid), .cfg_data(32'h0),
                .in_a(stage_data[i]), .in_b(in_b_i), .valid_in(stage_valid[i]),
                .ack_out(stage_ack[i]),
                .data_out(stage_data[i+1]), .valid_out(stage_valid[i+1]),
                .ack_in(stage_ack[i+1])
            );
        end
    endgenerate

endmodule
