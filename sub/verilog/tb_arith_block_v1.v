`default_nettype none
`timescale 1ns / 1ps
// Both variants of arith_block_v1 against the arithmetic, plus the existing
// adder_cell_v4s (add/sub) as a cross-check. 3 modes x many (a,b) incl. extremes.
module tb_arith_block_v1;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, a = 0, b = 0; reg vin = 0;
    wire [31:0] o1, o0, oa; wire v1, v0, va;
    arith_block_v1 #(.SHARED(1)) S (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o1), .valid_out(v1));
    arith_block_v1 #(.SHARED(0)) N (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o0), .valid_out(v0));
    adder_cell_v4s AC (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(oa), .valid_out(va));
    integer m, i, bad = 0, n = 0; reg [31:0] want;
    reg [31:0] ex [0:7];
    task try(input [31:0] x, input [31:0] y);
        begin
            a = x; b = y; vin = 1; @(negedge clk); vin = 0; @(negedge clk);
            case (m) 0: want = x + y; 1: want = x - y; default: want = ($signed(x) >= $signed(y)) ? 32'd1 : 32'd0; endcase
            n = n + 1;
            if (o1 !== want || o0 !== want) begin bad = bad + 1; if (bad < 6) $display("MISMATCH m=%0d a=%h b=%h want=%h shared=%h naive=%h", m, x, y, want, o1, o0); end
            if (m < 2 && oa !== want && m != 2) begin bad = bad + 1; if (bad < 6) $display("adder_cell MISMATCH m=%0d", m); end
        end
    endtask
    initial begin
        ex[0]=0; ex[1]=1; ex[2]=32'hFFFFFFFF; ex[3]=32'h7FFFFFFF; ex[4]=32'h80000000; ex[5]=32'h80000001; ex[6]=32'h12345678; ex[7]=32'hFFFFFFFE;
        repeat (3) @(negedge clk); rst = 0;
        for (m = 0; m < 3; m = m + 1) begin
            cfgd = m; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (i = 0; i < 64; i = i + 1) try(ex[i[5:3]], ex[i[2:0]]);
            for (i = 0; i < 400; i = i + 1) try($urandom, $urandom);
            for (i = 0; i < 100; i = i + 1) begin try($urandom, $urandom); try(32'h7FFFFFFF - ($urandom % 3), 32'h7FFFFFFF - ($urandom % 3)); end
        end
        if (bad == 0) $display("ALL ARITH BLOCK TESTS PASS (%0d checks, both variants)", n); else $display("ARITH BLOCK FAILED: %0d of %0d", bad, n);
        $finish;
    end
endmodule
