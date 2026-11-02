`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk; reg s = 0, c = 0, t = 0; wire q; integer errs = 0, i; reg exp;
    hexn_latch_core_v1 dut (.clk(clk), .set_in(s), .clear_in(c), .toggle_in(t), .q(q));
    task step(input ss, input cc, input tt); begin
        @(negedge clk); s = ss; c = cc; t = tt;
        exp = cc ? 1'b0 : ss ? 1'b1 : tt ? ~exp : exp;
        @(negedge clk); s = 0; c = 0; t = 0;
        if (q !== exp) begin errs = errs + 1; $display("FAIL set=%b clear=%b toggle=%b: q=%b want %b", ss, cc, tt, q, exp); end
    end endtask
    initial begin
        exp = 0; repeat (2) @(negedge clk);
        step(1,0,0); step(0,0,1); step(0,0,1); step(1,0,1); step(0,1,0); step(1,1,0); step(1,0,0); step(1,1,1); step(0,0,1); step(0,0,0);
        for (i = 0; i < 40; i = i + 1) step($random, $random, $random);
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED %0d", errs);
        $finish;
    end
endmodule
