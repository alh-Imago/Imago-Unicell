`timescale 1ns/1ps
// tb_hexn_loader_v1: loader + hexn_cfgbank_v2 (K = 7, NB = 18, AW = 7). Loads random settings for 7 detectors, checks the store holds exactly them; then loads a DIFFERENT set over it and checks again; then a partial load (3 detectors) followed by a full load and checks again.
module tb_hexn_loader_v1;
    localparam K = 7, NB = 18, AW = 7;
    reg clk = 0, rst = 1; always #5 clk = ~clk;
    reg start = 0; reg [NB-1:0] wp, wn; reg [AW-1:0] thr; wire busy, w_we, w_wp, w_wn, t_we; wire [AW-1:0] t_val;
    wire [K*NB-1:0] w_pos, w_neg; wire [K*AW-1:0] thr_flat;
    hexn_loader_v1 #(.NB(NB), .AW(AW)) ld(.clk(clk), .rst(rst), .start(start), .wp(wp), .wn(wn), .thr(thr), .busy(busy), .w_we(w_we), .w_wp(w_wp), .w_wn(w_wn), .t_we(t_we), .t_val(t_val));
    hexn_cfgbank_v2 #(.K(K), .NB(NB), .AW(AW)) cfg(.clk(clk), .rst(rst), .w_we(w_we), .w_ad({$clog2(K*NB+1){1'b0}}), .wp(w_wp), .wn(w_wn), .t_we(t_we), .t_k({$clog2(K){1'b0}}), .t_val(t_val), .w_pos(w_pos), .w_neg(w_neg), .thr_flat(thr_flat));
    reg [NB-1:0] ewp [0:K-1]; reg [NB-1:0] ewn [0:K-1]; reg [AW-1:0] ethr [0:K-1];
    integer bad = 0, k, tests = 0;
    task make_set(input integer seed); integer i; begin
        for (i = 0; i < K; i = i + 1) begin ewp[i] = $random(seed); ewn[i] = $random(seed) & ~ewp[i]; ethr[i] = $random(seed); end
    end endtask
    task load_det(input integer i); begin
        @(posedge clk); wp <= ewp[i]; wn <= ewn[i]; thr <= ethr[i]; start <= 1; @(posedge clk); start <= 0;
        while (busy) @(posedge clk);
    end endtask
    task check(input [255:0] name); integer i; begin
        tests = tests + 1;
        for (i = 0; i < K; i = i + 1)
            if (w_pos[i*NB +: NB] !== ewp[i] || w_neg[i*NB +: NB] !== ewn[i] || thr_flat[i*AW +: AW] !== ethr[i]) begin bad = bad + 1; $display("MISMATCH %0s detector %0d: wp %h/%h wn %h/%h thr %h/%h", name, i, w_pos[i*NB +: NB], ewp[i], w_neg[i*NB +: NB], ewn[i], thr_flat[i*AW +: AW], ethr[i]); end
    end endtask
    integer sd = 12345;
    initial begin
        repeat (3) @(posedge clk); rst <= 0; repeat (2) @(posedge clk);
        make_set(sd); for (k = 0; k < K; k = k + 1) load_det(k); check("first full load");
        make_set(sd); for (k = 0; k < K; k = k + 1) load_det(k); check("second full load over the first");
        make_set(sd); for (k = 0; k < 3; k = k + 1) load_det(k);          // partial load, chain left misaligned
        make_set(sd); for (k = 0; k < K; k = k + 1) load_det(k); check("full load after a partial one");
        if (bad == 0) $display("PASS tb_hexn_loader_v1: %0d checks of 7 detectors, 0 mismatches", tests); else $display("FAIL tb_hexn_loader_v1: %0d mismatches", bad);
        $finish;
    end
    initial begin #2000000; $display("FAIL tb_hexn_loader_v1: timeout"); $finish; end
endmodule
