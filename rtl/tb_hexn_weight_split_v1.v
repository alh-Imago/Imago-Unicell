// tb_hexn_weight_split_v1: judge J learns, its port P1 saves into the splitter S, the 16 bytes leave with random stalls; a FRESH judge K is loaded from those bytes through S2 -> port P2 in several orders; K must equal J.
// +MODE=0 self-checks. +MODE=1 learns (+SEED), saves, writes bytes.txt ("addr half byte"). +MODE=2 reads bytes.hex (16 bytes, low byte of each address first) and loads K, then dumps K's weights to got_w.txt.
`timescale 1ns/1ps
module tb_hexn_weight_split_v1;
  parameter WB = 14;
  reg clk = 0, rst = 1; always #5 clk = ~clk;
  reg go_learn = 0, go_eval = 0, m2 = 0; reg [41:0] x = 0; reg signed [9:0] t = 0; reg idle = 1; reg rd = 0;
  wire signed [9:0] y; wire done; wire [127:0] wfJ, wfK; wire jw; wire [3:0] ja; wire signed [15:0] jd;
  wire ov; wire [3:0] oa; wire signed [15:0] od; wire ol; wire e1;
  hexn_neural_v1 #(.WB(WB)) J (.clk(clk), .rst(rst), .go_eval(go_eval), .go_learn(go_learn), .x(x), .t(t), .m2(m2), .w_wr(jw), .w_addr(ja), .w_data(jd), .y(y), .done(done), .w_flat(wfJ));
  hexn_weight_port_v1 P1 (.clk(clk), .rst(rst), .idle(idle), .rd_start(rd), .w_flat(wfJ), .out_valid(ov), .out_addr(oa), .out_data(od), .out_last(ol), .in_valid(1'b0), .in_addr(4'd0), .in_data(16'sd0), .w_wr(jw), .w_addr(ja), .w_data(jd), .err_busy(e1));
  reg b_ready = 0; wire bv; wire [3:0] ba; wire bh; wire [7:0] bd; wire bl; wire pv1; wire [3:0] pa1; wire signed [15:0] pd1; wire ep1, eo1;
  hexn_weight_split_v1 S (.clk(clk), .rst(rst), .w_valid(ov), .w_addr(oa), .w_data(od), .w_last(ol), .b_valid(bv), .b_ready(b_ready), .b_addr(ba), .b_half(bh), .b_data(bd), .b_last(bl),
                          .l_valid(1'b0), .l_addr(4'd0), .l_half(1'b0), .l_data(8'd0), .p_valid(pv1), .p_addr(pa1), .p_data(pd1), .err_pair(ep1), .err_over(eo1));
  // receiving side
  reg lv = 0; reg [3:0] la = 0; reg lh = 0; reg [7:0] ld = 0; wire pv2; wire [3:0] pa2; wire signed [15:0] pd2; wire ep2, eo2;
  hexn_weight_split_v1 S2 (.clk(clk), .rst(rst), .w_valid(1'b0), .w_addr(4'd0), .w_data(16'sd0), .w_last(1'b0), .b_valid(), .b_ready(1'b0), .b_addr(), .b_half(), .b_data(), .b_last(),
                           .l_valid(lv), .l_addr(la), .l_half(lh), .l_data(ld), .p_valid(pv2), .p_addr(pa2), .p_data(pd2), .err_pair(ep2), .err_over(eo2));
  wire kw; wire [3:0] ka; wire signed [15:0] kd; wire e2;
  hexn_neural_v1 #(.WB(WB)) K (.clk(clk), .rst(rst), .go_eval(1'b0), .go_learn(1'b0), .x(x), .t(t), .m2(m2), .w_wr(kw), .w_addr(ka), .w_data(kd), .y(), .done(), .w_flat(wfK));
  hexn_weight_port_v1 P2 (.clk(clk), .rst(rst), .idle(1'b1), .rd_start(1'b0), .w_flat(wfK), .out_valid(), .out_addr(), .out_data(), .out_last(), .in_valid(pv2), .in_addr(pa2), .in_data(pd2), .w_wr(kw), .w_addr(ka), .w_data(kd), .err_busy(e2));
  integer mode, seed, bad = 0, i, j, f, nb, stall; reg [31:0] s; reg [7:0] cb [0:15]; reg ch [0:15]; reg [3:0] ca [0:15]; reg [7:0] hx [0:15]; reg cl [0:15]; reg lastseen;
  always @(posedge clk) if (bv && b_ready) begin cb[nb] <= bd; ca[nb] <= ba; ch[nb] <= bh; cl[nb] <= bl; nb <= nb + 1; end
  task nextcmd; begin s = s * 1664525 + 1013904223; for (j = 0; j < 7; j = j + 1) x[j*6 +: 6] = (s >> (j * 3)) % 24; t = ($unsigned(s >> 8) % 513) - 256; m2 = s[30]; end endtask
  task learn1; begin nextcmd; idle = 0; go_learn = 1; @(posedge clk); #1 go_learn = 0; while (!done) begin @(posedge clk); #1; end @(posedge clk); #1; idle = 1; end endtask
  task chk(input ok, input [255:0] what); begin if (!ok) begin bad = bad + 1; $display("FAIL %0s", what); end end endtask
  task save_and_collect(input stalls); integer n; begin
    nb = 0; rd = 1; @(posedge clk); #1 rd = 0;
    n = 0; while (nb < 16 && n < 400) begin b_ready = stalls ? ($urandom % 3 == 0) : 1'b1; @(posedge clk); #1; n = n + 1; end
    b_ready = 0; repeat (4) begin @(posedge clk); #1; end end endtask
  task sendbyte(input [3:0] a, input h, input [7:0] d, input integer gap); begin la = a; lh = h; ld = d; lv = 1; @(posedge clk); #1 lv = 0; repeat (gap) begin @(posedge clk); #1; end end endtask
  task resetK; begin rst = 1; repeat (2) begin @(posedge clk); #1; end rst = 0; @(posedge clk); #1; end endtask
  initial begin
    if (!$value$plusargs("MODE=%d", mode)) mode = 0; if (!$value$plusargs("SEED=%d", seed)) seed = 1; s = seed;
    repeat (3) @(posedge clk); #1 rst = 0; @(posedge clk); #1;
    if (mode == 2) begin
      $readmemh("bytes.hex", hx);
      for (j = 0; j < 16; j = j + 1) sendbyte(j / 2, j % 2, hx[j], 1);
      repeat (4) begin @(posedge clk); #1; end
      f = $fopen("got_w.txt", "w"); for (j = 0; j < 8; j = j + 1) $fwrite(f, "%0d\n", $signed(wfK[j*16 +: 16])); $fclose(f);
    end else begin
      for (i = 0; i < 250; i = i + 1) learn1;
      save_and_collect(mode == 0);
      if (mode == 1) begin
        f = $fopen("bytes.txt", "w"); for (j = 0; j < 16; j = j + 1) $fwrite(f, "%0d %0d %0d\n", ca[j], ch[j], cb[j]); $fclose(f);
      end else begin
        chk(nb == 16, "16 bytes sent");
        for (j = 0; j < 16; j = j + 1) begin
          chk(ca[j] === j / 2 && ch[j] === (j % 2), "byte order: address, low then high");
          chk(cb[j] === (ch[j] ? wfJ[(ca[j]*16 + 8) +: 8] : wfJ[(ca[j]*16) +: 8]), "byte equals the live weight half");
          chk(cl[j] === (j == 15), "last flag only on the final byte");
        end
        chk(ep1 === 0 && eo1 === 0 && e1 === 0, "no errors on the save side");
        // reassemble in order, with gaps
        resetK_bench;
      end
    end
    if (mode == 0) begin if (bad == 0) $display("ALL WEIGHT SPLIT TESTS PASS"); else $display("WEIGHT SPLIT FAILED: %0d", bad); end
    $finish;
  end
  // ---- reassembly scenarios (MODE 0)
  task resetK_bench; reg [127:0] refw; begin
    refw = wfJ;
    // A: low then high, gaps of 1
    resetK; for (j = 0; j < 16; j = j + 1) sendbyte(ca[j], ch[j], cb[j], 1); repeat (4) begin @(posedge clk); #1; end
    chk(wfK === refw, "A: in order, K equals J"); chk(ep2 === 0, "A: no pair error");
    // B: high byte first for each address, no gaps
    resetK; for (j = 0; j < 8; j = j + 1) begin sendbyte(j, 1, cb[2*j+1], 0); sendbyte(j, 0, cb[2*j], 0); end repeat (4) begin @(posedge clk); #1; end
    chk(wfK === refw, "B: high first, K equals J"); chk(ep2 === 0, "B: no pair error");
    // C: random gaps, random half order per address
    resetK; for (j = 0; j < 8; j = j + 1) begin s = s * 1664525 + 1013904223; if (s[20]) begin sendbyte(j, 0, cb[2*j], s[5:4]); sendbyte(j, 1, cb[2*j+1], s[7:6]); end else begin sendbyte(j, 1, cb[2*j+1], s[5:4]); sendbyte(j, 0, cb[2*j], s[7:6]); end end
    repeat (4) begin @(posedge clk); #1; end
    chk(wfK === refw, "C: random order and gaps, K equals J"); chk(ep2 === 0, "C: no pair error");
    // D: an incomplete pair is dropped, never written: low of 2, then low of 3, then high of 3
    resetK; sendbyte(2, 0, 8'hAA, 1); sendbyte(3, 0, cb[6], 1); sendbyte(3, 1, cb[7], 1); repeat (4) begin @(posedge clk); #1; end
    chk(ep2 === 1, "D: incomplete pair flagged"); chk($signed(wfK[2*16 +: 16]) === 0, "D: half a weight was NOT written"); chk(wfK[3*16 +: 16] === refw[3*16 +: 16], "D: the complete pair after it was written");
    // E: a lone half is never written
    resetK; sendbyte(5, 1, 8'h7F, 4); repeat (4) begin @(posedge clk); #1; end
    chk($signed(wfK[5*16 +: 16]) === 0, "E: lone half not written");
    // F: a second save while the first is still being sent is ignored and flagged
    nb = 0; rd = 1; @(posedge clk); #1 rd = 0; repeat (14) begin @(posedge clk); #1; end rd = 1; @(posedge clk); #1 rd = 0; repeat (6) begin @(posedge clk); #1; end
    b_ready = 1; repeat (30) begin @(posedge clk); #1; end b_ready = 0;
    chk(eo1 === 1, "F: save during sending flagged"); chk(nb == 16, "F: still exactly 16 bytes");
  end endtask
endmodule
