`timescale 1ns / 1ps
// tb_stub_alterafpf_mul_single_v1.v -- SIMULATION-ONLY stand-in for the
// real `alterafpf_mul_single` megafunction (#462, real confirmed
// 3-cycle latency). Same discipline as tb_stub_alterafpf_add_single_v1.v
// -- deliberately NOT real IEEE-754 arithmetic, only real, confirmed
// TIMING.
module alterafpf_mul_single (
    input  wire [31:0] dataa,
    input  wire [31:0] datab,
    input  wire        clock,
    output reg  [31:0] result
);
    reg [31:0] stage1, stage2;
    always @(posedge clock) begin
        stage1 <= dataa & datab;   // NOT real IEEE-754 multiplication -- see header
        stage2 <= stage1;
        result <= stage2;
    end
endmodule
