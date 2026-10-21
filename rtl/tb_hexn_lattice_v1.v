`timescale 1ns/1ps
// LATTICE variant (compile with -DLATMOD=hexn_lattice_SHAPE_v1). End to end: trains the bank from a stimulus file (+stim=FILE from tools/hexn_bank_stim_v1.py) with the trainer commands, then classifies every test sample with the run-time detectors and prints
// 'label bits pred c0 .. c(K-1)' per test sample (pred = -1 when the answer is not valid), then 'CLOCKS n'.
module tb_hexn_lattice_v1;
    parameter K = 4, NB = 12, AW = 6, S = 16, NT = 200;
    reg clk = 0, rst = 1, tr_start = 0, run_start = 0; reg [2:0] tr_cmd = 0;
    reg [NB-1:0] bits = 0; reg [$clog2(K)-1:0] lab = 0; reg [5:0] t_in = 0;
    wire tr_busy, run_busy, run_done, ans_valid; wire [$clog2(K)-1:0] ans_class; wire [4*K-1:0] cnt;
    `LATMOD #(.K(K), .NB(NB), .AW(AW), .S(S)) dut(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(tr_busy), .s_bits(bits), .s_label(lab), .t_in(t_in),
        .run_start(run_start), .run_busy(run_busy), .run_done(run_done), .ans_valid(ans_valid), .ans_class(ans_class), .cnt_flat(cnt));
    always #5 clk = ~clk;
    integer fd, n, i, k, KK, NN, SS, TT, y, b, clocks = 0, pred;
    reg [1023:0] fn;
    reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1];
    always @(posedge clk) clocks <= clocks + 1;
    task go(input [2:0] c); begin
        @(posedge clk); #1 tr_cmd = c; tr_start = 1; @(posedge clk); #1 tr_start = 0;
        while (tr_busy) @(posedge clk); #1;
    end endtask
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("need +stim=FILE"); $finish; end
        fd = $fopen(fn, "r"); n = $fscanf(fd, "%d %d %d %d\n", KK, NN, SS, TT);
        for (i = 0; i < K*S; i = i + 1) begin n = $fscanf(fd, "%d %d\n", y, b); yy[i] = y; bb[i] = b; end
        t_in = TT;
        repeat (3) @(posedge clk); #1 rst = 0;
        go(1);
        for (i = 0; i < K*S; i = i + 1) begin bits = bb[i]; lab = yy[i]; go(2); end
        go(3);
        for (i = 0; i < K*S; i = i + 1) begin bits = bb[i]; lab = yy[i]; go(4); end
        go(5);
        n = 1;
        while (n > 0 && !$feof(fd)) begin
            n = $fscanf(fd, "%d %d", y, b);
            if (n == 2) begin
                for (k = 0; k < K; k = k + 1) n = $fscanf(fd, "%d", i);   // skip the expected counts on the line
                bits = b; @(posedge clk); #1 run_start = 1; @(posedge clk); #1 run_start = 0;
                while (!run_done) @(posedge clk); @(posedge clk); #1;
                pred = ans_valid ? ans_class : -1;
                $write("%0d %0d %0d", y, b, pred); for (k = 0; k < K; k = k + 1) $write(" %0d", cnt[4*k +: 4]); $write("\n");
                n = 1;
            end else n = 0;
        end
        $display("CLOCKS %0d", clocks);
        $finish;
    end
endmodule
