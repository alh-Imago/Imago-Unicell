`timescale 1ns/1ps
// tb_arith_block_v9: stimulus and expected outputs per clock from a Python model (tests/vm/test_arith_block_v9_v1.py). +f=<file>, +n=<rows>; WIDTH set with -P tb.WIDTH=
module tb;
    parameter WIDTH = 18;
    reg clk = 0; always #5 clk = ~clk;
    reg rst = 1, cv = 0, vi = 0; reg [31:0] cd = 0; reg [WIDTH-1:0] a = 0, b = 0; wire [WIDTH-1:0] o; wire ov;
    arith_block_v9 #(.WIDTH(WIDTH)) U (.clk(clk), .rst(rst), .cfg_valid(cv), .cfg_data(cd), .in_a(a), .in_b(b), .valid_in(vi), .data_out(o), .valid_out(ov));
    reg [255:0] mem [0:65535]; reg [8*200:1] fn; integer n, i, bad = 0; reg [255:0] r; reg [31:0] ed;
    initial begin
        if (!$value$plusargs("f=%s", fn) || !$value$plusargs("n=%d", n)) begin $display("FAIL args"); $finish; end
        $readmemh(fn, mem); repeat (3) @(negedge clk); rst = 0;
        for (i = 0; i < n; i = i + 1) begin
            r = mem[i]; cv = r[224 +: 1]; cd = r[192 +: 32]; a = r[160 +: 32]; b = r[128 +: 32]; vi = r[96 +: 1];
            ed = r[32 +: 32]; @(negedge clk);
            if (ov !== r[64 +: 1] || o !== ed[WIDTH-1:0]) begin bad = bad + 1; if (bad < 6) $display("row %0d: got valid %b data %h expected valid %b data %h", i, ov, o, r[64 +: 1], r[32 +: 32]); end
        end
        if (bad == 0) $display("PASS %0d rows", n); else $display("FAIL %0d bad", bad); $finish;
    end
endmodule
