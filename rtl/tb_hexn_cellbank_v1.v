`timescale 1ns/1ps
// Lattice bank with CELL MODE (hexn_bank_v12 inside hexn_lattice_<shape>_v11): trains the bank from +stim=FILE (written by tools/hexn_cellbank_check_v1.py) with the trainer commands, then runs trials, each in mode 0 (detectors only) or mode 1
// (detectors, glue buffer, one full cell), back to back without a reset. Prints per trial: R mode ans_valid ans_class cnt[0..K-1] cap[0..K-1] cell_fwd cell_cnt.  Macro LAT = lattice module name; parameters K, NB, AW.
module tb_hexn_cellbank_v1;
    parameter K = 7, NB = 18, AW = 7, S = 16;
    reg clk = 0, rst = 1, tr_start = 0, run_start = 0, cell_mode = 0; reg [2:0] tr_cmd = 0;
    reg [NB-1:0] bits = 0; reg [$clog2(K)-1:0] lab = 0; reg [5:0] t_in = 8; reg [2*K-1:0] lc = 0; reg [AW-1:0] cthr = 0;
    wire tr_busy, run_busy, run_done, ans_valid; wire [$clog2(K)-1:0] ans_class; wire [4*K-1:0] cnt; wire [4:0] ccnt; wire [AW-1:0] cfwd; wire [3*K-1:0] cap;
    `LAT #(.K(K), .NB(NB), .AW(AW), .S(S)) dut(.clk(clk), .rst(rst), .tr_start(tr_start), .tr_cmd(tr_cmd), .tr_busy(tr_busy), .s_bits(bits), .s_label(lab), .t_in(t_in),
        .run_start(run_start), .run_busy(run_busy), .run_done(run_done), .ans_valid(ans_valid), .ans_class(ans_class), .cnt_flat(cnt), .cell_mode(cell_mode), .lane_cfg(lc), .cell_thr(cthr), .cell_cnt(ccnt), .cell_fwd(cfwd), .cap_flat(cap),
        .cap_ad({$clog2(K*NB+1){1'b0}}), .peek_ad({$clog2(K*NB+1){1'b0}}));
    always #5 clk = ~clk;
    integer fd, n, i, k, ntr, tr, v, y, TT; reg [1023:0] fn; reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1]; reg [NB-1:0] m;
    task go(input [2:0] c); begin
        @(posedge clk); #1 tr_cmd = c; tr_start = 1; @(posedge clk); #1 tr_start = 0;
        while (tr_busy) @(posedge clk); #1;
    end endtask
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("need +stim=FILE"); $finish; end
        fd = $fopen(fn, "r"); n = $fscanf(fd, "%d %d\n", TT, ntr);
        for (i = 0; i < K*S; i = i + 1) begin n = $fscanf(fd, "%d %h\n", y, m); yy[i] = y; bb[i] = m; end
        t_in = TT;
        repeat (3) @(posedge clk); #1 rst = 0;
        go(1);
        for (i = 0; i < K*S; i = i + 1) begin bits = bb[i]; lab = yy[i]; go(2); end
        go(3);
        for (i = 0; i < K*S; i = i + 1) begin bits = bb[i]; lab = yy[i]; go(4); end
        go(5);
        for (tr = 0; tr < ntr; tr = tr + 1) begin
            n = $fscanf(fd, "%d %h %d", v, m, y); cell_mode = v; bits = m; cthr = y;
            for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%d", v); lc[2*i +: 2] = v; end
            @(posedge clk); #1 run_start = 1; @(posedge clk); #1 run_start = 0;
            while (!run_done) @(posedge clk); while (run_busy) @(posedge clk); @(posedge clk); #1;
            $write("R %0d %0d %0d", cell_mode, ans_valid, ans_class); for (k = 0; k < K; k = k + 1) $write(" %0d", cnt[4*k +: 4]);
            for (k = 0; k < K; k = k + 1) $write(" %0d", cap[3*k +: 3]); $write(" %0d %0d\n", cfwd, ccnt);
        end
        $finish;
    end
endmodule
