`timescale 1ns/1ps
// tb_hexn_open10_v1: SAVE AND LOAD OF THE NEURAL JUDGE'S WEIGHTS (table space 6) through the whole open unit v10 over SPI. +dir holds w0.hex (8 words, the starting values), ops.hex (64-bit command words in the layout of tools/hexn_neural_check_v1.py: [63:62] 0 eval / 1 learn, [61] m2, [60:51] t, [50:9] x) and probe.hex (one eval word).
// The run hooks of the judge (nj_ge, nj_gl, nj_x, nj_t, nj_m2) are driven by hierarchical name; they are never driven in the design. Printed lines (parsed by the python test): Y <y> per op; W <k> <word> (the 8 values saved after the ops); Z <y> (probe after loading zeros); P <y> (probe after loading the saved words back); W2 <k> <word> (saved again after that); S <k> <word> (a save attempted while the judge is busy: the sentinel words must stay); P2 <y> (probe after a load attempted while busy); G <k> <word> (values saved after the refused load: unchanged).
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0;
    wire SPI_MISO, READY; wire [5:0] led;
    tri1 [15:0] pool;
//MASTER//
    hexn_open_top_v10 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .POOL(pool), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer i, k, nops, seq = 40; reg [8*200:1] dir, fn;
    reg [31:0] w0 [0:7]; reg [63:0] ops [0:1023]; reg [63:0] probe [0:0]; reg [31:0] saved [0:7];
    localparam SENT = 32'hDEADBEEF;
    task wait_idle; begin rd_reg(8'd10); while (rv[4]) rd_reg(8'd10); end endtask
    task load(input [3:0] sp, input [15:0] base, input integer n); begin wr_reg(8'd17, {sp, 12'd0, 16'd0} | (base << 16) | n); seq = seq + 1; wr_reg(8'd19, seq); repeat (4) @(negedge clk); wait_idle; end endtask
    task save(input [3:0] sp, input [15:0] base, input integer n); begin wr_reg(8'd30, {sp, 12'd0, 16'd0} | (base << 16) | n); seq = seq + 1; wr_reg(8'd31, seq); repeat (4) @(negedge clk); wait_idle; end endtask
    task run_op(input [63:0] w, input integer tag); begin
        @(negedge clk); T.nj_x = w[50:9]; T.nj_t = w[60:51]; T.nj_m2 = w[61]; if (w[63:62] == 2'd1) T.nj_gl = 1; else T.nj_ge = 1;
        @(negedge clk); T.nj_gl = 0; T.nj_ge = 0; @(posedge T.nj_done); @(negedge clk);
        if (tag == 0) $display("Y %0d", $signed(T.nj_y)); else if (tag == 1) $display("Z %0d", $signed(T.nj_y)); else if (tag == 2) $display("P %0d", $signed(T.nj_y)); else $display("P2 %0d", $signed(T.nj_y));
    end endtask
    task put8(input [31:0] a); begin for (i = 0; i < 8; i = i + 1) wbuf[i] = a; wr_words(16'd0, 8); end endtask
    initial begin
        if (!$value$plusargs("dir=%s", dir) || !$value$plusargs("nops=%d", nops)) begin $display("FAIL args"); $finish; end
        $sformat(fn, "%0s/w0.hex", dir); $readmemh(fn, w0); $sformat(fn, "%0s/ops.hex", dir); $readmemh(fn, ops); $sformat(fn, "%0s/probe.hex", dir); $readmemh(fn, probe);
        wait (T.init_done); repeat (40) @(negedge clk);
        // A: load the starting values (space 6), run the ops, save
        for (i = 0; i < 8; i = i + 1) wbuf[i] = w0[i]; wr_words(16'd0, 8); load(4'd6, 0, 8);
        for (k = 0; k < nops; k = k + 1) run_op(ops[k], 0);
        save(4'd6, 300, 0); rd_words(16'd300, 8); for (i = 0; i < 8; i = i + 1) begin saved[i] = rbuf[i]; $display("W %0d %h", i, rbuf[i]); end
        // B: wipe to zeros, probe, load the saved words back, probe, save again
        put8(32'd0); load(4'd6, 0, 8); run_op(probe[0], 1);
        for (i = 0; i < 8; i = i + 1) wbuf[i] = saved[i]; wr_words(16'd0, 8); load(4'd6, 0, 8); run_op(probe[0], 2);
        save(4'd6, 400, 8); rd_words(16'd400, 8); for (i = 0; i < 8; i = i + 1) $display("W2 %0d %h", i, rbuf[i]);
        // C: the judge is busy: a save must not write, a load must not change the judge
        T.nj_run = 1;
        for (i = 0; i < 8; i = i + 1) wbuf[i] = SENT; wr_words(16'd500, 8); save(4'd6, 500, 8); rd_words(16'd500, 8); for (i = 0; i < 8; i = i + 1) $display("S %0d %h", i, rbuf[i]);
        put8(32'd0); load(4'd6, 0, 8);
        T.nj_run = 0; repeat (4) @(negedge clk);
        run_op(probe[0], 3); save(4'd6, 600, 8); rd_words(16'd600, 8); for (i = 0; i < 8; i = i + 1) $display("G %0d %h", i, rbuf[i]);
        $display("DONE"); $finish;
    end
    initial begin repeat (100000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
