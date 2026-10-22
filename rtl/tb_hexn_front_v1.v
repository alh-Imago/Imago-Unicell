`timescale 1ns/1ps
// Interface test: reads trials from +stim=FILE (written by tools/hexn_front_check_v1.py), runs each through hexn_front_v1 (K detectors -> glue buffer -> one full cell) back to back WITHOUT a reset between trials (so stale bursts from the
// previous trial are present), and prints per trial: the K captured burst lengths, the cell's forward total at the end of its forward phase, and the cell's output burst count.
module tb_hexn_front_v1;
    parameter K = 19, NB = 18, AW = 7;
    reg clk = 0, rst = 1, start = 0; wire busy, done;
    reg [NB-1:0] bits = 0; reg [K*NB-1:0] wp = 0, wn = 0; reg [K*AW-1:0] th = 0; reg [2*K-1:0] lc = 0; reg [AW-1:0] cthr = 0;
    wire [4:0] cnt; wire [3*K-1:0] cap; wire [K-1:0] dtx, gout; wire [AW-1:0] cfwd;
    hexn_front_v1 #(.K(K), .NB(NB), .AW(AW)) dut(.clk(clk), .rst(rst), .start(start), .busy(busy), .done(done), .s_bits(bits), .w_pos(wp), .w_neg(wn), .thr_flat(th), .lane_cfg(lc), .cell_thr(cthr), .cell_cnt(cnt), .cap_flat(cap), .det_tx(dtx), .glue_out(gout), .cell_fwd(cfwd));
    always #5 clk = ~clk;
    integer fd, n, i, ntr, tr, v; reg [1023:0] fn; reg [NB-1:0] m;
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("need +stim=FILE"); $finish; end
        fd = $fopen(fn, "r"); n = $fscanf(fd, "%d\n", ntr);
        repeat (3) @(posedge clk); #1 rst = 0;
        for (tr = 0; tr < ntr; tr = tr + 1) begin
            n = $fscanf(fd, "%h", m); bits = m;
            for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%h", m); wp[i*NB +: NB] = m; end
            for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%h", m); wn[i*NB +: NB] = m; end
            for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%d", v); th[i*AW +: AW] = v; end
            for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%d", v); lc[2*i +: 2] = v; end
            n = $fscanf(fd, "%d\n", v); cthr = v;
            @(posedge clk); #1 start = 1; @(posedge clk); #1 start = 0;
            while (!done) @(posedge clk); #1;
            $write("R"); for (i = 0; i < K; i = i + 1) $write(" %0d", cap[3*i +: 3]); $write(" %0d %0d\n", cfwd, cnt);
        end
        $finish;
    end
endmodule
