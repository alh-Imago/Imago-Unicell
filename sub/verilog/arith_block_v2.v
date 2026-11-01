`default_nettype none
`timescale 1ns / 1ps
// arith_block_v2: arith_block_v1 (kept unchanged) plus a 3-way compare and an accumulate mode.
// MEASUREMENT PROTOTYPE (1 Nov 2026). cfg_data[2:0] = mode, cfg_data[15:8] = step (accumulate).
//   0 add (a+b)   1 sub (a-b)   2 ge (signed a>=b -> 1/0)
//   3 cmp3 (signed: 0 a<b, 1 a==b, 2 a>b)   [the arithmetic of branch_cell_v4s's is_low/is_equal; NOT its routing, held registers or emit mux]
//   4 accumulate: in_a[0]=inc, in_a[1]=dec pulses, total += +-step, out = new total (the continuous mode of
//     accumulator_cell_v4s, 32-bit; NOT its pulse_mode / threshold logic). Config clears the total, as the cell does.
// SHARED=1: ONE 33-bit adder serves every mode. SHARED=0: a separate adder/comparators/accumulator adder per function, output mux.
module arith_block_v2 #(parameter SHARED = 1) (
    input  wire clk, input wire rst, input wire cfg_valid, input wire [31:0] cfg_data,
    input  wire [31:0] in_a, input wire [31:0] in_b, input wire valid_in,
    output wire [31:0] data_out, output wire valid_out
);
    reg [2:0] mode = 3'd0; reg [7:0] step = 8'h0; reg armed = 1'b0;
    reg [31:0] total = 32'h0; reg [31:0] out_buffer = 32'h0; reg valid_out_r = 1'b0;
    reg [31:0] result;
    wire inc = in_a[0], dec = in_a[1];
    wire pulse = (mode == 3'd4) && (inc || dec);
    wire [31:0] step_ext = {24'b0, step};
    generate if (SHARED) begin : g_shared
        wire acc = (mode == 3'd4);
        wire sub = (mode == 3'd1) || (mode == 3'd2) || (mode == 3'd3) || (acc && dec && !inc);
        wire [31:0] opa = acc ? total : in_a;
        wire [31:0] opb = acc ? ((inc ^ dec) ? step_ext : 32'h0) : in_b;
        wire [32:0] a33 = {opa[31], opa};
        wire [32:0] b33 = {opb[31], opb} ^ {33{sub}};
        wire [32:0] s33 = a33 + b33 + {32'b0, sub};
        always @* case (mode)
            3'd2: result = {31'h0, ~s33[32]};
            3'd3: result = s33[32] ? 32'd0 : (s33 == 33'd0) ? 32'd1 : 32'd2;
            default: result = s33[31:0];
        endcase
    end else begin : g_naive
        wire [31:0] b_in = (mode == 3'd1) ? ~in_b : in_b;
        wire [31:0] sum; wire cout;
        adder_v1 #(.WIDTH(32)) ADD (.a(in_a), .b(b_in), .cin(mode == 3'd1), .sum(sum), .cout(cout));
        wire ge = ($signed(in_a) >= $signed(in_b));
        wire lt = ($signed(in_a) < $signed(in_b)), eq = (in_a == in_b);
        wire [31:0] delta = (inc && !dec) ? step_ext : (dec && !inc) ? -step_ext : 32'h0;
        wire [31:0] next = total + delta;
        always @* case (mode)
            3'd2: result = {31'h0, ge};
            3'd3: result = lt ? 32'd0 : eq ? 32'd1 : 32'd2;
            3'd4: result = next;
            default: result = sum;
        endcase
    end endgenerate
    assign data_out = out_buffer; assign valid_out = valid_out_r;
    always @(posedge clk) begin
        if (rst) begin mode <= 3'd0; step <= 8'h0; armed <= 1'b0; total <= 32'h0; out_buffer <= 32'h0; valid_out_r <= 1'b0; end
        else if (cfg_valid) begin mode <= cfg_data[2:0]; step <= cfg_data[15:8]; armed <= 1'b1; total <= 32'h0; out_buffer <= 32'h0; valid_out_r <= 1'b0; end
        else begin
            if (pulse) total <= result;
            out_buffer  <= result;
            valid_out_r <= armed && ((mode == 3'd4) ? (inc || dec) : valid_in);
        end
    end
endmodule
