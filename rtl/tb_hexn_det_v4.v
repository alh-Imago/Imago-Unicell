`timescale 1ns/1ps
// Test bench for hexn_det_v4: reads stimulus and expected margins produced by tools/hexn_det_v4_check_v1.py (an independent Python model) and compares every window.
module tb_hexn_det_v4;
    parameter NB = 12, AW = 8, PL = 10, NWIN = 400;
    reg clk = 0, rst = 1, ph_start = 0; reg [NB-1:0] rx = 0, w_pos = 0, w_neg = 0; reg signed [AW:0] thr = 0;
    wire signed [AW+1:0] margin;
    hexn_det_v4 #(.NB(NB), .AW(AW)) dut(.clk(clk), .rst(rst), .ph_start(ph_start), .rx(rx), .w_pos(w_pos), .w_neg(w_neg), .cfg_thr(thr), .margin(margin));
    always #5 clk = ~clk;
    reg [31:0] rxm [0:NWIN*PL-1]; reg [31:0] wpm [0:NWIN-1]; reg [31:0] wnm [0:NWIN-1]; reg [31:0] thm [0:NWIN-1]; reg [31:0] exm [0:NWIN-1];
    integer w, t, bad = 0;
    initial begin
        $readmemh("rx.hex", rxm); $readmemh("wp.hex", wpm); $readmemh("wn.hex", wnm); $readmemh("th.hex", thm); $readmemh("ex.hex", exm);
        repeat (3) @(posedge clk); #1 rst = 0;
        for (w = 0; w <= NWIN; w = w + 1) begin
            // window w: ph_start on its first clock; the margin of window w-1 is latched on that clock edge
            for (t = 0; t < PL; t = t + 1) begin
                ph_start = (t == 0);
                if (w < NWIN) begin rx = rxm[w*PL+t][NB-1:0]; w_pos = wpm[w][NB-1:0]; w_neg = wnm[w][NB-1:0]; thr = thm[w][AW:0]; end
                @(posedge clk); #1;
                if (t == 0 && w > 0) begin
                    if ($signed(margin) !== $signed(exm[w-1][AW+1:0])) begin bad = bad + 1; if (bad < 6) $display("MISMATCH window %0d: got %0d expected %0d", w-1, $signed(margin), $signed(exm[w-1][AW+1:0])); end
                end
            end
        end
        if (bad == 0) $display("TB DET V4 PASS: %0d windows, NB=%0d AW=%0d", NWIN, NB, AW); else $display("TB DET V4 FAIL: %0d mismatches", bad);
        $finish;
    end
endmodule
