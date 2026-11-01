`default_nettype none
`timescale 1ns / 1ps
// arith_block_v7: SHIFT_CF=1 (fine 0-3 + even coarse taps 0,4,8,12,16) against the plain shift reference and against the v6 shifter (SHIFT_CF=0), every amount 0..31, both directions,
// edge and random data; other modes spot-checked so a break elsewhere shows. in_a/in_b left stale after each word on purpose.
module tb_arith_block_v7;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg cfgv = 0; reg [31:0] cfgd = 0, a = 0, b = 0; reg vin = 0;
    wire [31:0] oC, o0; wire vC, v0;
    arith_block_v7 #(.SHARED(1), .NANO_TT(1), .SHIFT_CF(1)) C (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(oC), .valid_out(vC));
    arith_block_v7 #(.SHARED(1), .NANO_TT(1), .SHIFT_CF(0)) P (.clk(clk), .rst(rst), .cfg_valid(cfgv), .cfg_data(cfgd), .in_a(a), .in_b(b), .valid_in(vin), .data_out(o0), .valid_out(v0));
    integer bad = 0, n = 0, i, t, m; reg [31:0] want; reg [17:0] x;
    task word(input [31:0] x_, input [31:0] y_);
        begin a = x_; b = y_; vin = 1; @(negedge clk); #1; if (!(vC && v0)) begin bad = bad + 1; if (bad < 8) $display("NO ANSWER m=%0d", m); end vin = 0; @(negedge clk); end
    endtask
    task chk(input [31:0] w);
        begin n = n + 1; if (oC !== w || o0 !== w) begin bad = bad + 1; if (bad < 8) $display("MISMATCH m=%0d t=%0d a=%h want=%h cf=%h v6=%h", m, t, a, w, oC, o0); end end
    endtask
    initial begin
        repeat (3) @(negedge clk); rst = 0;
        for (m = 5; m <= 6; m = m + 1) begin
            cfgd = m; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (t = 0; t < 32; t = t + 1) for (i = 0; i < 40; i = i + 1) begin
                x = (i == 0) ? 18'h3FFFF : (i == 1) ? 18'h00001 : (i == 2) ? 18'h20000 : $urandom;
                word({$urandom} & 32'hFFFC0000 | {14'b0, x}, ($urandom & 32'hFFFFFFE0) | t);
                want = (m == 5) ? {14'b0, (a[17:0] << t) & 18'h3FFFF} : {14'b0, (a[17:0] >> t)};
                if (t >= 18) want = 32'h0;
                chk(want);
            end
        end
        for (m = 0; m <= 1; m = m + 1) begin
            cfgd = m; cfgv = 1; @(negedge clk); cfgv = 0; @(negedge clk);
            for (i = 0; i < 100; i = i + 1) begin word($urandom, $urandom); chk((m == 0) ? a + b : a - b); end
        end
        if (bad == 0) $display("ALL ARITH BLOCK V7 TESTS PASS (%0d checks, fine+coarse shifter vs reference and vs v6 shifter)", n); else $display("ARITH BLOCK V7 FAILED: %0d of %0d", bad, n);
        $finish;
    end
endmodule
