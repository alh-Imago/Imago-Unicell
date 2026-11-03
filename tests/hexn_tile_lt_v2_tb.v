`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg clear = 0, cfg_en = 0, cfg_in = 0; reg [3:0] fd = 0, ff = 0; wire [3:0] od, of; wire co;
    hexn_tile_lt_v2 #(.FACES(4)) t (.clk(clk), .clear(clear), .fi_d(fd), .fi_f(ff), .fo_d(od), .fo_f(of), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    localparam W = 25; reg [W-1:0] word; integer i, errs = 0, words = 0, ones = 0, clk_n = 0; reg [255:0] lastv;
    always @(posedge clk) begin clk_n <= clk_n + 1; if (of[1]) begin words <= words + 1; if (od[1]) ones <= ones + 1; end end
    // pulse on a face, wait 40 clocks, expect exactly one new word whose value is exp
    task step(input integer face, input exp, input integer n);
        integer w0, o0; begin
        w0 = words; o0 = ones; ff[face] = 1; @(posedge clk); #1 ff[face] = 0; repeat (40) @(posedge clk); #1;
        if (words != w0 + n || (n == 1 && (ones - o0) != exp)) begin errs = errs + 1; $display("FAIL step face %0d: words %0d->%0d ones %0d->%0d want value %0d", face, w0, words, o0, ones, exp); end
    end endtask
    initial begin
        word = 0; word[12 +: 3] = 3; word[15 +: 3] = 0; word[18 +: 3] = 2; word[21 +: 4] = 4'b0010;
        @(posedge clk); cfg_en = 1; for (i = W-1; i >= 0; i = i - 1) begin cfg_in = word[i]; @(posedge clk); #1; end cfg_en = 0; repeat (2) @(posedge clk); #1;
        if (words != 0) begin errs = errs + 1; $display("FAIL idle sends"); end
        step(3, 1, 1);   // set by W
        step(2, 0, 1);   // toggle by S -> off
        step(2, 1, 1);   // toggle -> on
        step(0, 0, 1);   // clear by N
        ff[3] = 1; ff[0] = 1; @(posedge clk); #1 ff = 0; repeat (40) @(posedge clk); #1;   // set + clear same clock: clear wins, one word 0
        if (words != 5) begin errs = errs + 1; $display("FAIL clear-wins words %0d", words); end
        // two pulses 3 clocks apart: level changes twice, one word (reports the first)
        ff[3] = 1; @(posedge clk); #1 ff = 0; repeat (2) @(posedge clk); #1; ff[2] = 1; @(posedge clk); #1 ff = 0; repeat (40) @(posedge clk); #1;
        if (words != 6) begin errs = errs + 1; $display("FAIL gap words %0d", words); end
        step(0, 0, 1);   // clear -> reports 0
        step(3, 1, 1); clear = 1; repeat (3) @(posedge clk); #1 clear = 0;
        step(2, 1, 1);   // toggle after wipe: level was wiped to 0, so toggle -> 1
        if (errs == 0) $display("PASS"); else $display("ERRORS %0d", errs);
        $finish;
    end
endmodule
