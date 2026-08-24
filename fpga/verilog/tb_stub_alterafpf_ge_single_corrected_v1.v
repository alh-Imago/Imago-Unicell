`timescale 1ns / 1ps
// tb_stub_alterafpf_ge_single_corrected_v1.v -- SIMULATION-ONLY stand-in
// for the real, REASONED-PLACEHOLDER comparison IP entity
// dsp_compare_wrapper_v1.v now assumes (points.md #474). Real, assumed
// (not confirmed) port list: clk/clk_en/dataa/datab/n/reset/result,
// no start/done (combinational operations complete within one cycle
// by definition). Deliberately NOT real IEEE-754 comparison semantics
// -- a simple, deterministic placeholder purely for verifying this
// wrapper's own real protocol timing. Must NEVER be used in a real
// synthesis run. Replace this whole file once Alan's own real
// generated IP confirms or corrects the real port list.
module alterafpf_ge_single (
    input  wire        clk,
    input  wire        clk_en,
    input  wire        reset,
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire [7:0]  n,
    output reg          result
);
    always @(posedge clk) begin
        if (reset) result <= 1'b0;
        else result <= (dataa != datab);   // NOT real IEEE-754 comparison -- see header
    end
endmodule
