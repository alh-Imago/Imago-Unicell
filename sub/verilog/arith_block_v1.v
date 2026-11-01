`default_nettype none
`timescale 1ns / 1ps
// arith_block_v1: ONE sub-style position that can be an adder, a subtracter or a
// signed >= comparer, chosen by a config word (cfg_data[1:0]): 0 add, 1 sub, 2 ge.
// MEASUREMENT PROTOTYPE (1 Nov 2026), spec section 9 of Project doc claude/config-gate-spec.md.
// Same shell as adder_cell_v4s / compare_cell_v4s (armed, out_buffer, valid_out_r,
// cfg load drops a word offered on the cfg clock).
//   SHARED = 1: one 33-bit adder serves add, sub and ge (ge = NOT sign of a-b, 33-bit).
//   SHARED = 0: naive select: a separate adder (add/sub, as adder_cell_v4s) and a
//               separate signed comparator, output chosen by a mux. No sharing.
// NOT included: accumulator, branch, mask, shift, latch (see the spec for why).
module arith_block_v1 #(
    parameter SHARED = 1
) (
    input  wire        clk,
    input  wire        rst,
    input  wire        cfg_valid,
    input  wire [31:0] cfg_data,
    input  wire [31:0] in_a,
    input  wire [31:0] in_b,
    input  wire        valid_in,
    output wire [31:0] data_out,
    output wire        valid_out
);
    reg [1:0]  mode        = 2'd0;
    reg        armed       = 1'b0;
    reg [31:0] out_buffer  = 32'h0;
    reg        valid_out_r = 1'b0;
    reg [31:0] result;

    generate if (SHARED) begin : g_shared
        wire sub = (mode != 2'd0);
        wire [32:0] a33 = {in_a[31], in_a};
        wire [32:0] b33 = {in_b[31], in_b} ^ {33{sub}};
        wire [32:0] s33 = a33 + b33 + {32'b0, sub};
        always @* result = (mode == 2'd2) ? {31'h0, ~s33[32]} : s33[31:0];
    end else begin : g_naive
        wire [31:0] adder_b_in = (mode == 2'd1) ? ~in_b : in_b;
        wire [31:0] sum; wire cout;
        adder_v1 #(.WIDTH(32)) ADD (.a(in_a), .b(adder_b_in), .cin(mode == 2'd1), .sum(sum), .cout(cout));
        wire ge = ($signed(in_a) >= $signed(in_b));
        always @* result = (mode == 2'd2) ? {31'h0, ge} : sum;
    end endgenerate

    assign data_out  = out_buffer;
    assign valid_out = valid_out_r;
    always @(posedge clk) begin
        if (rst) begin
            mode <= 2'd0; armed <= 1'b0; out_buffer <= 32'h0; valid_out_r <= 1'b0;
        end else if (cfg_valid) begin
            mode <= cfg_data[1:0]; armed <= 1'b1; valid_out_r <= 1'b0;
        end else begin
            out_buffer  <= result;
            valid_out_r <= armed && valid_in;
        end
    end
endmodule
