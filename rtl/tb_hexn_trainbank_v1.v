`timescale 1ns/1ps
// Runs the training bank on a stimulus file written by tools/hexn_trainbank_stim_v1.py (+stim=FILE) and prints 'k wpos wneg thr' per detector, then 'CLOCKS n'.
module tb_hexn_trainbank_v1;
    parameter K = 4, NB = 12, AW = 6, S = 16;
    reg clk = 0, rst = 1, start = 0; reg [2:0] cmd = 0;
    reg [NB-1:0] bits = 0; reg [$clog2(K)-1:0] lab = 0; reg [5:0] t_in = 0;
    wire busy; wire [K*NB-1:0] wp, wn; wire [K*AW-1:0] thr;
    hexn_trainbank_v1 #(.K(K), .NB(NB), .AW(AW), .S(S)) dut(.clk(clk), .rst(rst), .start(start), .cmd(cmd), .s_bits(bits), .s_label(lab), .t_in(t_in), .busy(busy), .w_pos(wp), .w_neg(wn), .thr_flat(thr));
    always #5 clk = ~clk;
    integer fd, n, i, k, KK, NN, SS, TT, y, b, clocks = 0;
    reg [1023:0] fn;
    reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1];
    always @(posedge clk) clocks <= clocks + 1;
    task go(input [2:0] c); begin
        @(posedge clk); #1 cmd = c; start = 1; @(posedge clk); #1 start = 0;
        while (busy) @(posedge clk); #1;
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
        for (k = 0; k < K; k = k + 1) $display("%0d %0d %0d %0d", k, wp[k*NB +: NB], wn[k*NB +: NB], thr[k*AW +: AW]);
        $display("CLOCKS %0d", clocks);
        $finish;
    end
endmodule
