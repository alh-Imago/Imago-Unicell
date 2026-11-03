`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg clear = 0, cfg_en = 0, cfg_in = 0; reg [3:0] fd = 0, ff = 0; wire [3:0] od, of; wire co;
    hexn_tile_lt_v1 #(.FACES(4)) t (.clk(clk), .clear(clear), .fi_d(fd), .fi_f(ff), .fo_d(od), .fo_f(of), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    // word: ROUTE 0 | SELS W=3 | SELC N=0 | SELT S=2 | RMASK E
    localparam W = 25; reg [W-1:0] word; integer i, errs = 0;
    task chk(input [255:0] what, input exp); begin if (od[1] !== exp || of[1] !== 1'b0) begin errs = errs + 1; $display("FAIL %0s: q=%b f=%b want %b", what, od[1], of[1], exp); end end endtask
    task pulse(input integer face); begin ff[face] = 1; @(posedge clk); #1 ff[face] = 0; @(posedge clk); #1; end endtask
    initial begin
        word = 0; word[12 +: 3] = 3; word[15 +: 3] = 0; word[18 +: 3] = 2; word[21 +: 4] = 4'b0010;
        @(posedge clk); cfg_en = 1; for (i = W-1; i >= 0; i = i - 1) begin cfg_in = word[i]; @(posedge clk); #1; end cfg_en = 0; repeat (2) @(posedge clk); #1;
        chk("idle low", 0);
        pulse(3); chk("set by W", 1);
        pulse(2); chk("toggle by S", 0);
        pulse(2); chk("toggle again", 1);
        pulse(0); chk("clear by N", 0);
        ff[3] = 1; ff[0] = 1; @(posedge clk); #1 ff = 0; @(posedge clk); #1; chk("clear wins over set", 0);
        pulse(3); chk("set", 1); clear = 1; repeat (3) @(posedge clk); #1 clear = 0; chk("wipe", 0);
        if (errs == 0) $display("PASS"); else $display("ERRORS %0d", errs);
        $finish;
    end
endmodule
