`timescale 1ns/1ps
module tb;
  reg clk = 0, rst = 1, st = 0, sf = 0, ss = 0, own = 0; reg [11:0] x = 0;
  wire busy; wire [11:0] wpos, wneg; wire signed [11:0] acc_own, acc_oth; wire [7:0] n_own, n_oth;
  hexn_tally_serial_v1 #(.PUSH_OWN(3), .T(8)) d (.clk(clk), .rst(rst), .start_train(st), .start_final(sf), .start_score(ss), .own(own), .x(x), .busy(busy), .wpos(wpos), .wneg(wneg), .acc_own(acc_own), .acc_oth(acc_oth), .n_own(n_own), .n_oth(n_oth));
  always #5 clk = ~clk;
  integer fd, r, i, o; reg [11:0] xs [0:63]; reg ows [0:63]; reg [11:0] xb;
  initial begin
    fd = $fopen("/tmp/tally_stim.txt", "r");
    for (i = 0; i < 64; i = i + 1) begin r = $fscanf(fd, "%d %b\n", o, xb); ows[i] = o[0]; xs[i] = xb; end
    #12 rst = 0;
    for (i = 0; i < 64; i = i + 1) begin @(negedge clk); x = xs[i]; own = ows[i]; st = 1; @(negedge clk); st = 0; while (busy) @(negedge clk); end
    @(negedge clk); sf = 1; @(negedge clk); sf = 0; while (busy) @(negedge clk);
    for (i = 0; i < 64; i = i + 1) begin @(negedge clk); x = xs[i]; own = ows[i]; ss = 1; @(negedge clk); ss = 0; while (busy) @(negedge clk); end
    @(negedge clk);
    $display("%0d %0d %0d %0d %0d %0d", wpos, wneg, acc_own, acc_oth, n_own, n_oth); $finish;
  end
endmodule
