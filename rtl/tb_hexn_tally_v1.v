`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, train_en = 0, score_en = 0, own = 0; reg [11:0] x = 0;
  wire [11:0] wpos, wneg; wire signed [4:0] score; wire signed [11:0] acc_own, acc_oth; wire [7:0] n_own, n_oth;
  hexn_tally_v1 #(.PUSH_OWN(3), .T(8)) d (.clk(clk), .rst(rst), .train_en(train_en), .score_en(score_en), .own(own), .x(x), .wpos(wpos), .wneg(wneg), .score(score), .acc_own(acc_own), .acc_oth(acc_oth), .n_own(n_own), .n_oth(n_oth));
  always #5 clk = ~clk;
  integer fd, r, i; reg [11:0] xs [0:63]; reg ows [0:63]; reg [11:0] xb; integer o;
  initial begin
    fd = $fopen("/tmp/tally_stim.txt", "r");
    for (i = 0; i < 64; i = i + 1) begin r = $fscanf(fd, "%d %b\n", o, xb); ows[i] = o[0]; xs[i] = xb; end
    #12 rst = 0;
    for (i = 0; i < 64; i = i + 1) begin @(negedge clk); x = xs[i]; own = ows[i]; train_en = 1; @(negedge clk); train_en = 0; end
    for (i = 0; i < 64; i = i + 1) begin @(negedge clk); x = xs[i]; own = ows[i]; score_en = 1; @(negedge clk); score_en = 0; end
    @(negedge clk);
    $display("%0d %0d %0d %0d %0d %0d", wpos, wneg, acc_own, acc_oth, n_own, n_oth); $finish;
  end
endmodule
