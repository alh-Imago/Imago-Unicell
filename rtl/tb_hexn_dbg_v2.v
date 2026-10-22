`timescale 1ns/1ps
// Byte-level test of the board top (hexn_tang_top_v8): this testbench plays the host. It sends the training and test samples from a stimulus file (+stim=FILE, tools/hexn_bank_stim_v1.py) as serial bytes, reads the replies,
// and prints 'label bits pred c0 .. c(K-1)' per test sample (pred -1 = answer not valid), then 'CLOCKS n'. Compile with -DLATMOD=hexn_lattice_<shape>_v1 -DNCLS=<cells> -DCLKDIV=8.
`ifndef NCLS
`define NCLS 7
`endif
`ifndef NBW
`define NBW 18
`endif
`ifndef CLKDIV
`define CLKDIV 8
`endif
// DEBUG COMMANDS test: after training, ACCUM sample 0 then DUMP, DUMPSUMS, ECHO, PROBE, CAP, PEEK, printing every reply byte as 'B n' in that order (decoded and checked by tools/hexn_dbg_check_v2.py).
// (v2: clone of tb_hexn_tang_top_v1.v, left untouched; NB wires, 3 sample bytes, board top v8.)
module tb_hexn_dbg_v2;
    localparam K = `NCLS, NB = `NBW, S = 16, CD = `CLKDIV;
    reg clk = 0, rxd = 1; wire txd; wire [5:0] led;
    hexn_tang_top_v8 dut(.clk(clk), .uart_rx(rxd), .uart_tx(txd), .led(led));
    always #5 clk = ~clk;
    integer fd, n, i, k, KK, NN, SS, TT, y, b, clocks = 0, pred;
    reg [1023:0] fn; reg [7:0] r;
    reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1];
    always @(posedge clk) clocks <= clocks + 1;
    task sendb(input [7:0] d); integer j; begin
        rxd = 0; repeat (CD) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin rxd = d[j]; repeat (CD) @(posedge clk); end
        rxd = 1; repeat (CD) @(posedge clk);
    end endtask
    task recvb(output [7:0] d); integer j; begin
        while (txd !== 1'b0) @(posedge clk);
        repeat (CD + CD/2) @(posedge clk);
        for (j = 0; j < 8; j = j + 1) begin d[j] = txd; repeat (CD) @(posedge clk); end
    end endtask
    task expect_ack; reg [7:0] a; begin recvb(a); if (a !== 8'hA5) $display("BAD ACK %h", a); end endtask
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("need +stim=FILE"); $finish; end
        fd = $fopen(fn, "r"); n = $fscanf(fd, "%d %d %d %d\n", KK, NN, SS, TT);
        for (i = 0; i < K*S; i = i + 1) begin n = $fscanf(fd, "%d %d\n", y, b); yy[i] = y; bb[i] = b; end
        repeat (400) @(posedge clk);
        sendb(8'h01); expect_ack;
        for (i = 0; i < K*S; i = i + 1) begin sendb(8'h02); sendb(yy[i]); sendb(bb[i] & 8'hff); sendb((bb[i] >> 8) & 8'hff); sendb((bb[i] >> 16) & 8'hff); expect_ack; end
        sendb(8'h03); sendb(TT); expect_ack;
        for (i = 0; i < K*S; i = i + 1) begin sendb(8'h04); sendb(yy[i]); sendb(bb[i] & 8'hff); sendb((bb[i] >> 8) & 8'hff); sendb((bb[i] >> 16) & 8'hff); expect_ack; end
        sendb(8'h05); expect_ack;
        sendb(8'h04); sendb(yy[0]); sendb(bb[0] & 8'hff); sendb((bb[0] >> 8) & 8'hff); sendb((bb[0] >> 16) & 8'hff); expect_ack;
        sendb(8'h07); for (i = 0; i < 7*K; i = i + 1) begin recvb(r); $display("B %0d", r); end
        sendb(8'h08); for (i = 0; i < 4*K; i = i + 1) begin recvb(r); $display("B %0d", r); end
        sendb(8'h0c); for (i = 0; i < 5; i = i + 1) begin recvb(r); $display("B %0d", r); end
        sendb(8'h0a); for (i = 0; i < 2*K; i = i + 1) begin recvb(r); $display("B %0d", r); end
        sendb(8'h0d); for (i = 0; i < K*NB + 2; i = i + 1) begin recvb(r); $display("B %0d", r); end
        sendb(8'h0b); for (i = 0; i < K*NB; i = i + 1) begin recvb(r); $display("B %0d", r); end
        $display("CLOCKS %0d", clocks);
        $finish;
    end
endmodule
