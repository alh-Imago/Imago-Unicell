`timescale 1ns/1ps
// Byte-level test of the board top v9 with CELL MODE: this testbench plays the host over the serial link (CLKDIV 8). It trains the bank from +stim=FILE (tools/hexn_cellbank_check_v1.py writes it), then per trial sends either RUN (0x06, mode 0:
// reply = status byte and K burst counts) or LOADCELL (0x0E) + RUNCELL (0x0F) (mode 1: reply = cell output burst count, cell forward total, K captured burst lengths), and prints 'R mode ans_valid ans_class cnt[0..K-1] cap[0..K-1] fwd cellcnt'
// (fields that the mode does not return are printed as 0). Compile with -DLATMOD=hexn_lattice_<shape>_v11 -DNCLS=<cells> -DCLKDIV=8.
`ifndef NCLS
`define NCLS 7
`endif
`ifndef NBW
`define NBW 18
`endif
`ifndef CLKDIV
`define CLKDIV 8
`endif
module tb_hexn_cell_top_v1;
    localparam K = `NCLS, NB = `NBW, S = 16, CD = `CLKDIV;
    reg clk = 0, rxd = 1; wire txd; wire [5:0] led;
    hexn_tang_top_v9 dut(.clk(clk), .uart_rx(rxd), .uart_tx(txd), .led(led));
    always #5 clk = ~clk;
    integer fd, n, i, k, ntr, tr, v, y, TT, mode, cthr; reg [1023:0] fn; reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1]; reg [NB-1:0] m; reg [39:0] lc40; reg [7:0] r, st, cc, fw; reg [7:0] cnts [0:31]; reg [7:0] caps [0:31];
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
    task send3(input [NB-1:0] b); begin sendb(b[7:0]); sendb(b[15:8]); sendb({6'b0, b[17:16]}); end endtask
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("need +stim=FILE"); $finish; end
        fd = $fopen(fn, "r"); n = $fscanf(fd, "%d %d\n", TT, ntr);
        for (i = 0; i < K*S; i = i + 1) begin n = $fscanf(fd, "%d %h\n", y, m); yy[i] = y; bb[i] = m; end
        repeat (400) @(posedge clk);
        sendb(8'h01); expect_ack;
        for (i = 0; i < K*S; i = i + 1) begin sendb(8'h02); sendb(yy[i]); send3(bb[i]); expect_ack; end
        sendb(8'h03); sendb(TT); expect_ack;
        for (i = 0; i < K*S; i = i + 1) begin sendb(8'h04); sendb(yy[i]); send3(bb[i]); expect_ack; end
        sendb(8'h05); expect_ack;
        for (tr = 0; tr < ntr; tr = tr + 1) begin
            n = $fscanf(fd, "%d %h %d", mode, m, cthr); lc40 = 0;
            for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%d", v); lc40[2*i +: 2] = v; end
            if (mode == 0) begin
                sendb(8'h06); send3(m); recvb(st); for (k = 0; k < K; k = k + 1) recvb(cnts[k]);
                $write("R 0 %0d %0d", st[7], st[4:0]); for (k = 0; k < K; k = k + 1) $write(" %0d", cnts[k]);
                for (k = 0; k < K; k = k + 1) $write(" 0"); $write(" 0 0\n");
            end else begin
                sendb(8'h0e); sendb(cthr); sendb(lc40[7:0]); sendb(lc40[15:8]); sendb(lc40[23:16]); sendb(lc40[31:24]); sendb(lc40[39:32]); expect_ack;
                sendb(8'h0f); send3(m); recvb(cc); recvb(fw); for (k = 0; k < K; k = k + 1) recvb(caps[k]);
                $write("R 1 0 0"); for (k = 0; k < K; k = k + 1) $write(" 0"); for (k = 0; k < K; k = k + 1) $write(" %0d", caps[k]); $write(" %0d %0d\n", fw, cc);
            end
        end
        $finish;
    end
endmodule
