`timescale 1ns / 1ps
// tb_stub_alterafpf_ge_single_v1.v -- SIMULATION-ONLY stand-in for the
// real `alterafpf_ge_single_GE` megafunction. Real, confirmed latency
// NOT independently found for GE specifically (#462's own search
// result was cut off after naming it, before its own cycle count) --
// this stub uses LE's confirmed 1-cycle value as the reasonable
// default, matching dsp_compare_wrapper_v1.v's own stated assumption.
// Deliberately NOT real IEEE-754 comparison semantics -- a simple,
// deterministic placeholder (dataa != datab) purely for verifying
// dsp_compare_wrapper_v1.v's own protocol timing. ONE register stage
// only, matching the real, confirmed single-cycle latency -- caught
// and fixed a real timing bug in the first draft (two chained stages
// would have given 2-cycle latency, not 1) before trusting it.
module alterafpf_ge_single_GE (
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire        clock,
    output reg          result
);
    always @(posedge clock) begin
        result <= (dataa != datab);   // NOT real IEEE-754 GE comparison -- see header
    end
endmodule
