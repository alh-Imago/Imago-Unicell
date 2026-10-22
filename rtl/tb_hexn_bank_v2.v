`timescale 1ns/1ps
// Equivalence test: the lattice bank with the old run timing (hexn_bank_v10 + hexn_det_v2, 2*2*PL clocks per run) and the new one without the feedback phase (hexn_bank_v11 + hexn_det_v3, 2*PL clocks) receive the SAME training
// commands and the SAME test samples; every run compares answer, answer validity and all K burst counts, and the run lengths are measured. Macros: LATA / LATB = module names, K, NB, AW.
// Training data: K random class patterns, 16 noisy copies each (each wire flips with chance about 1/4 .. 1/8), then test samples at several noise levels. Prints 'RESULT runs N mismatches M old_clocks A new_clocks B'.
module tb_hexn_bank_v2;
    parameter K = 7, NB = 18, AW = 7, S = 16, NT = 600;
    reg clk = 0, rst = 1, tr_start = 0, run_start = 0; reg [2:0] tr_cmd = 0;
    reg [NB-1:0] bits = 0; reg [$clog2(K)-1:0] lab = 0; reg [5:0] t_in = 8;
    wire trb_a, trb_b, rb_a, rb_b, rd_a, rd_b, av_a, av_b; wire [$clog2(K)-1:0] ac_a, ac_b; wire [4*K-1:0] cnt_a, cnt_b;
    wire [K*NB-1:0] wpa, wna, wpb, wnb; wire [K*AW-1:0] tha, thb;
    `LATA #(.K(K), .NB(NB), .AW(AW), .S(S)) a(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(trb_a), .s_bits(bits), .s_label(lab), .t_in(t_in), .run_start(run_start), .run_busy(rb_a), .run_done(rd_a),
        .ans_valid(av_a), .ans_class(ac_a), .cnt_flat(cnt_a), .dbg_wpos(wpa), .dbg_wneg(wna), .dbg_thr(tha), .cap_ad({$clog2(K*NB+1){1'b0}}), .peek_ad({$clog2(K*NB+1){1'b0}}));
    `LATB #(.K(K), .NB(NB), .AW(AW), .S(S)) b(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(trb_b), .s_bits(bits), .s_label(lab), .t_in(t_in), .run_start(run_start), .run_busy(rb_b), .run_done(rd_b),
        .ans_valid(av_b), .ans_class(ac_b), .cnt_flat(cnt_b), .dbg_wpos(wpb), .dbg_wneg(wnb), .dbg_thr(thb), .cap_ad({$clog2(K*NB+1){1'b0}}), .peek_ad({$clog2(K*NB+1){1'b0}}));
    always #5 clk = ~clk;
    integer i, k, j, n, mism = 0, runs = 0, ca, cb, y, q, seed = 12345; reg [NB-1:0] tpl [0:K-1]; reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1]; reg [NB-1:0] m;
    function [NB-1:0] noisy(input [NB-1:0] t, input integer lvl); integer w; reg [NB-1:0] r; begin r = t; for (w = 0; w < NB; w = w + 1) if (($random(seed) & 255) < lvl) r[w] = ~r[w]; noisy = r; end endfunction
    task go(input [2:0] c); begin
        @(posedge clk); #1 tr_cmd = c; tr_start = 1; @(posedge clk); #1 tr_start = 0;
        while (trb_a | trb_b) @(posedge clk); #1;
    end endtask
    initial begin
        for (k = 0; k < K; k = k + 1) for (j = 0; j < NB; j = j + 1) tpl[k][j] = $random(seed) & 1;
        for (k = 0; k < K; k = k + 1) for (i = 0; i < S; i = i + 1) begin bb[k*S+i] = noisy(tpl[k], 38); yy[k*S+i] = k; end
        repeat (3) @(posedge clk); #1 rst = 0;
        go(1);
        for (i = 0; i < K*S; i = i + 1) begin bits = bb[i]; lab = yy[i]; go(2); end
        go(3);
        for (i = 0; i < K*S; i = i + 1) begin bits = bb[i]; lab = yy[i]; go(4); end
        go(5);
        if (wpa !== wpb || wna !== wnb || tha !== thb) begin $display("TRAINED SETTINGS DIFFER (should be identical)"); mism = mism + 1; end
        for (n = 0; n < NT; n = n + 1) begin
            y = n % K; q = (n / K) % 6; bits = noisy(tpl[y], q * 16);
            if (n % 17 == 0) bits = $random(seed);
            @(posedge clk); #1 run_start = 1; @(posedge clk); #1 run_start = 0;
            ca = 0; cb = 0;
            while (!(rd_a & rd_b) && ca < 400) begin @(posedge clk); if (rb_a) ca = ca + 1; if (rb_b) cb = cb + 1; end
            // done pulses can come at different clocks: wait for both
            while (rb_a | rb_b) begin @(posedge clk); if (rb_a) ca = ca + 1; if (rb_b) cb = cb + 1; end
            @(posedge clk); #1;
            runs = runs + 1;
            if (cnt_a !== cnt_b || av_a !== av_b || (av_a && ac_a !== ac_b)) begin mism = mism + 1; if (mism < 6) $display("DIFF sample %0d bits %h: old v=%0d c=%0d cnt=%h | new v=%0d c=%0d cnt=%h", n, bits, av_a, ac_a, cnt_a, av_b, ac_b, cnt_b); end
            if (n == 0) $display("run length in clocks: old %0d new %0d", ca, cb);
        end
        $display("RESULT runs %0d mismatches %0d", runs, mism);
        $finish;
    end
endmodule
