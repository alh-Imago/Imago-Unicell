`default_nettype none
`timescale 1ns / 1ps
// hexn_bnet_map_v1 (8 Nov 2026): MAP RECORDER AND MATCHER, the part by which the judge recalls "I have seen this before" (Alan 18:43, direction doc section 32). The map of a run = which cells of layers 2 and 3 fired at least once (NB bits, set by 'fire' during the run, cleared by 'clr'). 'start' compares the live map with each of M stored maps (one per clock, read from a RAM the host fills) and keeps the TWO best by overlap (Jaccard: shared cells / cells in either, compared by cross multiplication, no division). done=1 when finished; best/second index and their shared and union counts are read out.
// Fuzzy use (two maps that both match): the host reads both indices and both scores.
module hexn_bnet_map_v1 #(parameter NB = 128, parameter M = 16, parameter MW = 4) (
    input wire clk, input wire clr, input wire [NB-1:0] fire,
    input wire w_en, input wire [MW-1:0] w_idx, input wire [NB-1:0] w_map, input wire start,
    output reg done, output reg [MW-1:0] b1, output reg [MW-1:0] b2, output reg [7:0] i1, output reg [7:0] u1, output reg [7:0] i2, output reg [7:0] u2, output wire [NB-1:0] live_o);
    reg [NB-1:0] live = 0; assign live_o = live;
    reg [NB-1:0] store [0:M-1]; always @(posedge clk) if (w_en) store[w_idx] <= w_map;
    always @(posedge clk) if (clr) live <= {NB{1'b0}}; else live <= live | fire;
    reg running = 0; reg [MW:0] k = 0;
    wire [NB-1:0] st = store[k[MW-1:0]]; wire [NB-1:0] a = live & st, o = live | st;
    integer q; reg [7:0] ci, cu;
    always_comb begin ci = 0; cu = 0; for (q = 0; q < NB; q = q + 1) begin ci = ci + a[q]; cu = cu + o[q]; end end
    // candidate beats best if ci/cu > i1/u1  <=>  ci*u1 > i1*cu (an empty union scores 0)
    wire [15:0] l1 = ci * u1, r1 = i1 * cu, l2 = ci * u2, r2 = i2 * cu;
    wire beats1 = (cu != 0) && (l1 > r1 || u1 == 0), beats2 = (cu != 0) && (l2 > r2 || u2 == 0);
    initial begin done = 0; b1 = 0; b2 = 0; i1 = 0; u1 = 0; i2 = 0; u2 = 0; end
    always @(posedge clk) begin
        if (start && !running) begin running <= 1; k <= 0; done <= 0; i1 <= 0; u1 <= 0; i2 <= 0; u2 <= 0; b1 <= 0; b2 <= 0; end
        else if (running) begin
            if (beats1) begin i2 <= i1; u2 <= u1; b2 <= b1; i1 <= ci; u1 <= cu; b1 <= k[MW-1:0]; end
            else if (beats2) begin i2 <= ci; u2 <= cu; b2 <= k[MW-1:0]; end
            if (k == M - 1) begin running <= 0; done <= 1; end else k <= k + 1'b1;
        end
    end
endmodule
