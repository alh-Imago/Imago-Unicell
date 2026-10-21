`timescale 1ns/1ps
// Byte-level test of the board top (hexn_tang_top_v1): this testbench plays the host. It sends the training and test samples from a stimulus file (+stim=FILE, tools/hexn_bank_stim_v1.py) as serial bytes, reads the replies,
// and prints 'label bits pred c0 .. c(K-1)' per test sample (pred -1 = answer not valid), then 'CLOCKS n'. Compile with -DLATMOD=hexn_lattice_<shape>_v1 -DNCLS=<cells> -DCLKDIV=8.
`ifndef NCLS
`define NCLS 7
`endif
`ifndef CLKDIV
`define CLKDIV 8
`endif
module tb_hexn_tang_top_v1;
    localparam K = `NCLS, NB = 12, S = 16, CD = `CLKDIV;
    reg clk = 0, rxd = 1; wire txd; wire [5:0] led;
    hexn_tang_top_v1 dut(.clk(clk), .uart_rx(rxd), .uart_tx(txd), .led(led));
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
        for (i = 0; i < K*S; i = i + 1) begin sendb(8'h02); sendb(yy[i]); sendb(bb[i] & 8'hff); sendb(bb[i] >> 8); expect_ack; end
        sendb(8'h03); sendb(TT); expect_ack;
        for (i = 0; i < K*S; i = i + 1) begin sendb(8'h04); sendb(yy[i]); sendb(bb[i] & 8'hff); sendb(bb[i] >> 8); expect_ack; end
        sendb(8'h05); expect_ack;
        n = 1;
        while (n > 0 && !$feof(fd)) begin
            n = $fscanf(fd, "%d %d", y, b);
            if (n == 2) begin
                for (k = 0; k < K; k = k + 1) n = $fscanf(fd, "%d", i);
                sendb(8'h06); sendb(b & 8'hff); sendb(b >> 8);
                recvb(r); pred = r[7] ? (r & 8'h1f) : -1;
                $write("%0d %0d %0d", y, b, pred);
                for (k = 0; k < K; k = k + 1) begin recvb(r); $write(" %0d", r); end
                $write("\n"); n = 1;
            end else n = 0;
        end
        $display("CLOCKS %0d", clocks);
        $finish;
    end
endmodule
