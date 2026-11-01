// tb_hexn_weight_port_v1: neural judge + weight port. +MODE=0 self-checks (load/readback, learn then save equals the live weights, a second judge restored from the saved words behaves identically, busy guard);
// +MODE=1 learns from blank (+SEED) then SAVES to saved.txt and logs a 40-command continuation to ref_after.txt; +MODE=2 loads load.hex (8 words) into a FRESH judge and logs the same continuation to got_after.txt.
`timescale 1ns/1ps
module tb_hexn_weight_port_v1;
  parameter WB = 14;
  reg clk = 0, rst = 1; always #5 clk = ~clk;
  reg go_eval = 0, go_learn = 0, m2 = 0; reg [41:0] x = 0; reg signed [9:0] t = 0; reg idle = 1;
  reg rd_start = 0, in_valid = 0; reg [3:0] in_addr = 0; reg signed [15:0] in_data = 0;
  wire signed [9:0] y; wire done; wire [127:0] wf; wire w_wr; wire [3:0] w_addr; wire signed [15:0] w_data;
  wire ov; wire [3:0] oa; wire signed [15:0] od; wire ol; wire err;
  hexn_neural_v1 #(.WB(WB)) J (.clk(clk), .rst(rst), .go_eval(go_eval), .go_learn(go_learn), .x(x), .t(t), .m2(m2), .w_wr(w_wr), .w_addr(w_addr), .w_data(w_data), .y(y), .done(done), .w_flat(wf));
  hexn_weight_port_v1 P (.clk(clk), .rst(rst), .idle(idle), .rd_start(rd_start), .w_flat(wf), .out_valid(ov), .out_addr(oa), .out_data(od), .out_last(ol), .in_valid(in_valid), .in_addr(in_addr), .in_data(in_data), .w_wr(w_wr), .w_addr(w_addr), .w_data(w_data), .err_busy(err));
  // second judge, restored in MODE 0
  reg go_eval2 = 0, go_learn2 = 0; wire signed [9:0] y2; wire done2; wire [127:0] wf2; reg w_wr2 = 0; reg [3:0] w_addr2 = 0; reg signed [15:0] w_data2 = 0;
  hexn_neural_v1 #(.WB(WB)) K (.clk(clk), .rst(rst), .go_eval(go_eval2), .go_learn(go_learn2), .x(x), .t(t), .m2(m2), .w_wr(w_wr2), .w_addr(w_addr2), .w_data(w_data2), .y(y2), .done(done2), .w_flat(wf2));
  integer mode, seed, bad = 0, i, j, f; reg [31:0] s; reg signed [15:0] cap [0:7]; integer ncap; reg [15:0] lh [0:7];
  always @(posedge clk) if (ov) begin cap[oa] <= od; ncap <= ncap + 1; end
  task nextcmd; begin s = s * 1664525 + 1013904223; for (j = 0; j < 7; j = j + 1) x[j*6 +: 6] = (s >> (j * 3)) % 24; t = ($unsigned(s >> 8) % 513) - 256; m2 = s[30]; end endtask
  task cmd(input learn); begin nextcmd; idle = 0; if (learn) go_learn = 1; else go_eval = 1; @(posedge clk); #1 go_eval = 0; go_learn = 0; while (!done) begin @(posedge clk); #1; end @(posedge clk); #1; idle = 1; end endtask
  task cmd_both(input learn); begin nextcmd; idle = 0; if (learn) begin go_learn = 1; go_learn2 = 1; end else begin go_eval = 1; go_eval2 = 1; end @(posedge clk); #1 go_eval = 0; go_learn = 0; go_eval2 = 0; go_learn2 = 0; while (!done) begin @(posedge clk); #1; end @(posedge clk); #1; idle = 1; end endtask
  task save; begin ncap = 0; rd_start = 1; @(posedge clk); #1 rd_start = 0; repeat (12) begin @(posedge clk); #1; end end endtask
  task loadword(input [3:0] a, input signed [15:0] d); begin in_addr = a; in_data = d; in_valid = 1; @(posedge clk); #1 in_valid = 0; @(posedge clk); #1; end endtask
  task chk(input ok, input [255:0] what); begin if (!ok) begin bad = bad + 1; $display("FAIL %0s", what); end end endtask
  task cont(input integer fh); integer q; begin for (q = 0; q < 40; q = q + 1) begin cmd(q % 3 != 0); $fwrite(fh, "%0d", y); for (j = 0; j < 8; j = j + 1) $fwrite(fh, " %0d", $signed(wf[j*16 +: 16])); $fwrite(fh, "\n"); end end endtask
  initial begin
    if (!$value$plusargs("MODE=%d", mode)) mode = 0; if (!$value$plusargs("SEED=%d", seed)) seed = 1; s = seed;
    repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1;
    if (mode == 1) begin
      for (i = 0; i < 300; i = i + 1) cmd(1);
      save; chk(ncap == 8, "8 words saved"); f = $fopen("saved.txt", "w"); for (j = 0; j < 8; j = j + 1) $fwrite(f, "%0d %0d\n", j, cap[j]); $fclose(f);
      for (j = 0; j < 8; j = j + 1) chk($signed(wf[j*16 +: 16]) === cap[j], "snapshot equals live weights");
      s = seed + 1000; f = $fopen("ref_after.txt", "w"); cont(f); $fclose(f);
    end else if (mode == 2) begin
      $readmemh("load.hex", lh); for (j = 0; j < 8; j = j + 1) loadword(j, lh[j]);
      s = seed + 1000; f = $fopen("got_after.txt", "w"); cont(f); $fclose(f);
    end else begin
      // load known words, read back through the port
      for (j = 0; j < 8; j = j + 1) loadword(j, (j * 1111) - 3000);
      for (j = 0; j < 8; j = j + 1) chk($signed(wf[j*16 +: 16]) === (j * 1111) - 3000, "loaded word reached the judge");
      save; for (j = 0; j < 8; j = j + 1) chk(cap[j] === (j * 1111) - 3000, "saved word equals loaded word"); chk(ncap == 8, "8 words streamed");
      // learn, save, restore a second judge, behave alike
      for (i = 0; i < 200; i = i + 1) cmd(1);
      save; for (j = 0; j < 8; j = j + 1) begin chk($signed(wf[j*16 +: 16]) === cap[j], "after learning, snapshot equals live"); w_wr2 = 1; w_addr2 = j; w_data2 = cap[j]; @(posedge clk); #1 w_wr2 = 0; end
      for (j = 0; j < 8; j = j + 1) chk($signed(wf2[j*16 +: 16]) === $signed(wf[j*16 +: 16]), "second judge restored");
      for (i = 0; i < 60; i = i + 1) begin cmd_both(i % 2); chk(y === y2, "same y after restore"); for (j = 0; j < 8; j = j + 1) chk($signed(wf[j*16 +: 16]) === $signed(wf2[j*16 +: 16]), "same weights after restore"); end
      // busy guard: a request while a command is in flight is refused and flagged; a save also refuses a load that arrives with it
      chk(err === 1'b0, "no error so far");
      nextcmd; idle = 0; go_learn = 1; @(posedge clk); #1 go_learn = 0; ncap = 0;
      rd_start = 1; @(posedge clk); #1 rd_start = 0; repeat (12) begin @(posedge clk); #1; end
      chk(ncap == 0, "save refused while busy"); chk(err === 1'b1, "error flagged for busy save");
      while (!done) begin @(posedge clk); #1; end @(posedge clk); #1; idle = 1;
      begin : g1 reg signed [15:0] prev; prev = $signed(wf[0 +: 16]); in_addr = 0; in_data = 16'sd1234; idle = 0; in_valid = 1; @(posedge clk); #1 in_valid = 0; @(posedge clk); #1; idle = 1; chk($signed(wf[0 +: 16]) === prev, "load refused while busy"); end
      if (bad == 0) $display("ALL WEIGHT PORT TESTS PASS"); else $display("WEIGHT PORT FAILED: %0d", bad);
    end
    $finish;
  end
endmodule
