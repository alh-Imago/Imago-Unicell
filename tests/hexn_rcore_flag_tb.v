`timescale 1ns/1ps
module tb;
    parameter FACES = 4;
    reg clk = 0; always #5 clk = ~clk;
    reg [FACES-1:0] fi_d = 0, fi_f = 0; wire [FACES-1:0] fo_d, fo_f; reg cfg_en = 0, cfg_in = 0; wire cfg_out;
    hexn_rcore_flag_v1 #(.FACES(FACES)) U (.clk(clk), .fi_d(fi_d), .fi_f(fi_f), .fo_d(fo_d), .fo_f(fo_f), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(cfg_out));
    integer fails = 0, t, j, k; reg [31:0] lf = 32'hACE1ACE1; reg [2:0] sel [0:FACES-1]; reg [FACES-1:0] ed, ef; reg [3*FACES-1:0] allbits; integer b;
    function [31:0] nxt(input [31:0] x); begin nxt = {x[30:0], x[31] ^ x[21] ^ x[1] ^ x[0]}; end endfunction
    initial begin
        repeat (3) @(negedge clk);
        for (t = 0; t < 200; t = t + 1) begin
            for (j = 0; j < FACES; j = j + 1) begin lf = nxt(nxt(lf)); sel[j] = lf[2:0]; end            // indexes up to 7: FACES..7 must read constant 0
            for (j = 0; j < FACES; j = j + 1) allbits[3*j +: 3] = sel[j];
            cfg_en = 1; for (b = 3*FACES-1; b >= 0; b = b - 1) begin cfg_in = allbits[b]; @(negedge clk); end cfg_en = 0;
            for (k = 0; k < 3; k = k + 1) begin
                lf = nxt(nxt(lf)); fi_d = lf[FACES-1:0]; lf = nxt(nxt(lf)); fi_f = lf[FACES-1:0];
                ed = 0; ef = 0; for (j = 0; j < FACES; j = j + 1) begin ed[j] = (sel[j] < FACES) ? fi_d[sel[j]] : 1'b0; ef[j] = (sel[j] < FACES) ? fi_f[sel[j]] : 1'b0; end
                @(negedge clk);
                if (fo_d !== ed || fo_f !== ef) begin fails = fails + 1; if (fails < 5) $display("FAIL t=%0d d %b/%b f %b/%b", t, fo_d, ed, fo_f, ef); end
            end
        end
        if (cfg_out !== allbits[3*FACES-1]) begin fails = fails + 1; $display("FAIL cfg_out"); end
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
endmodule
