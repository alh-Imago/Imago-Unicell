`timescale 1ns/1ps
// testbench for hexn_ramroute_v6 (trigger-driven): data on face 0, pulse on face 1, output on face 3.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [5:0] fi = 0; wire [5:0] fo; reg cfg_en = 0, cfg_in = 0; wire cfg_out;
    hexn_ramroute_v6 dut (.clk(clk), .fi(fi), .fo(fo), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(cfg_out));
    integer errs = 0, i, k;
    reg [28:0] cw; reg [255:0] cap;
    task cfgload(input [1:0] mode);
        begin
            cw = 0; cw[17:0] = {3'd5, 3'd4, 3'd3, 3'd2, 3'd1, 3'd0};
            cw[19:18] = mode; cw[22:20] = 3'd0; cw[25:23] = 3'd3; cw[28:26] = 3'd1;
            for (k = 28; k >= 0; k = k - 1) begin @(negedge clk); cfg_en = 1; cfg_in = cw[k]; end
            @(negedge clk); cfg_en = 0; repeat (3) @(negedge clk);
        end
    endtask
    // one word: bit 0 + start pulse at clock 0; release pulses at the given clocks (0 = none); capture fo[3] after each edge
    task run(input [31:0] w, input integer rel1, input integer rel2, input integer n);
        begin
            for (i = 0; i < n; i = i + 1) begin
                @(negedge clk);
                fi[0] = (i < 32) ? w[i] : 1'b0;
                fi[1] = (i == 0) || (rel1 > 0 && i == rel1) || (rel2 > 0 && i == rel2);
                #4 cap[i] = fo[3];            // value after the previous edge
            end
            @(negedge clk); fi = 0; repeat (4) @(negedge clk);
        end
    endtask
    // find the word in cap starting exactly at index `at`
    function ok_at(input integer at, input [31:0] w);
        integer b; reg [31:0] t;
        begin t = 0; for (b = 0; b < 32; b = b + 1) t[b] = cap[at + b]; ok_at = (t == w); end
    endfunction
    task chk(input [31:0] w, input integer rel, input integer firstidx, input [255:0] name);
        begin
            if (ok_at(firstidx, w)) $display("PASS %0s: release at clock %0d, word starts at capture index %0d", name, rel, firstidx);
            else begin errs = errs + 1; $display("FAIL %0s: release at %0d, word not at index %0d (cap low bits %b)", name, rel, firstidx, cap[firstidx +: 8]); end
        end
    endtask
    initial begin
        @(negedge clk);
        cfgload(2'd1);
        // hold: release 40 clocks after the start (whole word waited), 5 clocks after (early streaming), 20, 31
        run(32'hA5C3_1E7F, 40, 0, 110); chk(32'hA5C3_1E7F, 40, 40 + 3, "hold late release");
        run(32'hDEAD_BEEF, 5,  0, 110); chk(32'hDEAD_BEEF, 5, 5 + 3, "hold early release 5");
        run(32'h8000_0001, 20, 0, 110); chk(32'h8000_0001, 20, 20 + 3, "hold early release 20");
        run(32'h1234_5678, 31, 0, 110); chk(32'h1234_5678, 31, 31 + 3, "hold early release 31");
        run(32'hFFFF_0F0F, 33, 0, 110); chk(32'hFFFF_0F0F, 33, 33 + 3, "hold release 33");
        // empty again after the read: a second word through the same cell works (checked by the runs above following each other)
        cfgload(2'd2);
        run(32'hC0DE_F00D, 12, 60, 140);
        chk(32'hC0DE_F00D, 12, 12 + 3, "repeat first replay");
        chk(32'hC0DE_F00D, 60, 60 + 3, "repeat second replay");
        if (errs == 0) $display("ALL PASS"); else $display("SOME FAILED");
        $finish;
    end
endmodule
