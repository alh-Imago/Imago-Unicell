`timescale 1ns/1ps
module tb; reg clk = 0; always #5 clk = ~clk;
  reg ws = 0; reg [5:0] fi = 0; wire [5:0] fo; reg cfg_en = 0, cfg_in = 0; wire co;
  hexn_scell_v1 U (.clk(clk), .ws(ws), .fi(fi), .fo(fo), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
  localparam CW = 42; reg [CW-1:0] cf; integer i, t, k, bad1 = 0, bad2 = 0, bad3 = 0, bad4 = 0, bad5 = 0; reg [15:0] x, y, z; reg [9:0] tmp;
  task load; begin for (i = CW - 1; i >= 0; i = i - 1) begin @(negedge clk); cfg_en = 1; cfg_in = cf[i]; end @(negedge clk); cfg_en = 0; end endtask
  task word(input [15:0] xa, input [15:0] yb, output [15:0] res); integer q; begin res = 0;
    for (q = 0; q <= 17; q = q + 1) begin @(negedge clk); if (q >= 1 && q - 1 < 16) res[q-1] = fo[2]; fi[0] = (q < 16) ? xa[q] : 1'b0; fi[1] = (q < 16) ? yb[q] : 1'b0; ws = (q == 0); end
    end endtask
  initial begin
    // add: a = face 0, b = face 1, result on face 2. cfg order (LSB first in cf): mode, sela, selb, tt, shamt, rmask, rsrc0..5
    cf = 0; cf[2:0] = 1; cf[5:3] = 0; cf[8:6] = 1; cf[23:18] = 6'b000100; load;
    for (t = 0; t < 20; t = t + 1) begin x = $random; y = $random; word(x, y, z); if (z !== ((x + y) & 16'hFFFF)) bad1 = bad1 + 1; end
    $display("add: %0d wrong of 20", bad1);
    cf[2:0] = 2; load; for (t = 0; t < 20; t = t + 1) begin x = $random; y = $random; word(x, y, z); if (z !== ((x - y) & 16'hFFFF)) bad2 = bad2 + 1; end
    $display("subtract: %0d wrong of 20", bad2);
    cf[2:0] = 3; cf[12:9] = 4'b0110; load; for (t = 0; t < 20; t = t + 1) begin x = $random; y = $random; word(x, y, z); if (z !== (x ^ y)) bad3 = bad3 + 1; end
    $display("logic xor: %0d wrong of 20", bad3);
    // route only: rmask = 0, output face 3 copies input face 0 (cross/corner style), output face 5 copies face 1
    cf = 0; cf[24 + 3*3 +: 3] = 0; cf[24 + 3*5 +: 3] = 1; load;
    for (t = 0; t < 40; t = t + 1) begin @(negedge clk); fi = $random; @(negedge clk); @(negedge clk); if (fo[3] !== fi[0] || fo[5] !== fi[1]) bad4 = bad4 + 1; end
    $display("route (copy a face to another face): %0d wrong of 40", bad4);
    if (bad1 + bad2 + bad3 + bad4 == 0) $display("PASS"); else $display("FAIL"); $finish; end
endmodule
