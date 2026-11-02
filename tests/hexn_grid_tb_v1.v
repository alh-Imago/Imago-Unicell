`timescale 1ns/1ps
// tb for hexn_grid_v1 (4 x 4): a bit-serial 8-bit adder built from five cells. Cells (row, col): Pa = (0,2) = 2 copies its NE external input; Pb2 = (3,2) = 14 copies its SE external input; Pb = (2,2) = 10 copies its SE face (= Pb2);
// S = (1,1) = 5 computes the sum bit from NE (Pa), SE (Pb) and E (C); C = (1,2) = 6 keeps the carry from NW (Pa), SW (Pb) and itself.
// Words are 8 data bits and one zero pad bit, back to back. b goes in one clock before a (it has one more hop). Sum bit of stream position m is read at negedge m+3.
module tb; reg clk = 0; always #5 clk = ~clk;
  reg cfg_we = 0; reg [15:0] cfg_cell = 0; reg [6:0] cfg_addr = 0; reg cfg_data = 0; reg [95:0] ext = 0; wire [15:0] o;
  hexn_grid_v1 #(.R(4), .C(4)) G (.clk(clk), .cfg_we(cfg_we), .cfg_cell(cfg_cell), .cfg_addr(cfg_addr), .cfg_data(cfg_data), .ext_in(ext), .o(o));
  integer v, e, t, k, bad = 0; reg [6:0] ad; reg [8:0] sa [0:63]; reg [8:0] sb [0:63]; reg [8:0] got [0:63]; localparam NW = 40;
  task put(input integer cn, input integer ad_, input reg bit_); begin @(negedge clk); cfg_we = 1; cfg_cell = cn; cfg_addr = ad_; cfg_data = bit_; @(negedge clk); cfg_we = 0; end endtask
  function bitof(input integer idx, input integer which); integer w, kk; begin w = idx / 9; kk = idx % 9; if (idx < 0 || w >= NW || kk == 8) bitof = 1'b0; else bitof = which ? sb[w][kk] : sa[w][kk]; end endfunction
  initial begin
    for (v = 0; v < 128; v = v + 1) begin
      ad = v; put(2, v, ad[2]); put(14, v, ad[4]); put(10, v, ad[4]); put(5, v, ad[2] ^ ad[4] ^ ad[0]); put(6, v, (ad[3] & ad[5]) | (ad[3] & ad[6]) | (ad[5] & ad[6]));
    end
    for (t = 0; t < NW; t = t + 1) begin sa[t] = {1'b0, $random}; sb[t] = {1'b0, $random}; got[t] = 0; end
    sa[0] = 9'd255; sb[0] = 9'd1; sa[1] = 9'd255; sb[1] = 9'd255; sa[2] = 9'd0; sb[2] = 9'd0;
    for (e = 0; e < NW * 9 + 6; e = e + 1) begin
      @(negedge clk);
      if (e >= 3 && (e - 3) < NW * 9) got[(e - 3) / 9][(e - 3) % 9] = o[5];
      ext[14*6+4] = bitof(e, 1);          // b first
      ext[2*6+2]  = bitof(e - 1, 0);      // a one clock later
    end
    for (t = 0; t < NW; t = t + 1) if (got[t] !== sa[t][7:0] + sb[t][7:0]) bad = bad + 1;
    $display("%0d wrong of %0d additions (9-bit sums); first: %0d + %0d = %0d", bad, NW, sa[0][7:0], sb[0][7:0], got[0]);
    if (bad == 0) $display("PASS"); else $display("FAIL"); $finish;
  end
endmodule
