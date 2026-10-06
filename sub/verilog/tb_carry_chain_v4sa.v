`timescale 1ns/1ps
// Multi-word add built from the flex adder's carry_out port (#974): a 16-bit add from three 8-bit
// adders. ADD0 = low bytes (carry_enable on, its carry on carry_out); ADD1 = high bytes; ADD2 =
// ADD1's sum + ADD0's carry word (0/1). Handshake joins are the same two-operand join the ICM
// emitter uses. Every result is checked against the plain 16-bit sum, for many pairs.
module tb_carry_chain_v4sa;
    localparam W = 8;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cv = 0; reg [31:0] cd = 0;
    reg [W-1:0] alo, blo, ahi, bhi; reg vin = 0;
    wire a0_ack, a0_v, a0_cv; wire [W-1:0] a0_s, a0_c;
    wire a1_ack, a1_v; wire [W-1:0] a1_s;
    wire a2_ack, a2_v; wire [W-1:0] a2_s;
    wire a1_unused_c_v; wire [W-1:0] a1_unused_c;
    wire a2_unused_c_v; wire [W-1:0] a2_unused_c;
    wire join2 = a1_v & a0_cv;                       // ADD2 takes (ADD1 sum, ADD0 carry) together
    adder_cell_v4sa #(.WIDTH(W), .SECOND_PORT(1)) ADD0 (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cv), .cfg_data(cd),
        .in_a(alo), .in_b(blo), .valid_in(vin), .ack_out(a0_ack), .data_out(a0_s), .valid_out(a0_v), .ack_in(1'b1),
        .carry_out(a0_c), .valid_out_c(a0_cv), .ack_in_c(a2_ack & a1_v));
    adder_cell_v4sa #(.WIDTH(W)) ADD1 (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cv), .cfg_data(32'h0),
        .in_a(ahi), .in_b(bhi), .valid_in(vin), .ack_out(a1_ack), .data_out(a1_s), .valid_out(a1_v), .ack_in(a2_ack & a0_cv),
        .carry_out(a1_unused_c), .valid_out_c(a1_unused_c_v), .ack_in_c(1'b1));
    adder_cell_v4sa #(.WIDTH(W)) ADD2 (.clk(clk), .rst(rst), .freeze_in(1'b0), .cfg_valid(cv), .cfg_data(32'h0),
        .in_a(a1_s), .in_b(a0_c), .valid_in(join2), .ack_out(a2_ack), .data_out(a2_s), .valid_out(a2_v), .ack_in(1'b1),
        .carry_out(a2_unused_c), .valid_out_c(a2_unused_c_v), .ack_in_c(1'b1));
    integer errors = 0, n = 0, i; reg [15:0] A, B, expect_sum; reg [7:0] seen_lo;
    initial begin
        @(posedge clk); @(posedge clk); rst = 0;
        cd = 32'h2; cv = 1; @(posedge clk); #1;               // ADD0 carry_enable (cfg_data bit 1)
        cd = 0; cv = 0;
        for (i = 0; i < 400; i = i + 1) begin
            A = $urandom; B = $urandom;
            if (i == 0) begin A = 16'hFFFF; B = 16'h0001; end
            if (i == 1) begin A = 16'h00FF; B = 16'h0001; end   // carry out of the low byte only
            if (i == 2) begin A = 16'hFFFF; B = 16'hFFFF; end
            expect_sum = A + B;
            while (!(a0_ack && a1_ack)) @(posedge clk);
            alo = A[7:0]; ahi = A[15:8]; blo = B[7:0]; bhi = B[15:8]; vin = 1;
            @(posedge clk); #1; vin = 0;
            seen_lo = a0_s;
            while (!a2_v) @(posedge clk);
            #1;
            n = n + 1;
            if ({a2_s, seen_lo} !== expect_sum) begin errors = errors + 1; $display("FAIL: %h + %h = %h, got %h%h", A, B, expect_sum, a2_s, seen_lo); end
            @(posedge clk); #1;
        end
        if (errors == 0) $display("ALL PASS (%0d 16-bit adds from three 8-bit cells)", n); else $display("FAILURES: %0d", errors);
        $finish;
    end
endmodule
