`timescale 1ns/1ps
// Byte-level test of the board top v10 (NCELL leaky cells): plays the host over the serial link (CLKDIV 8). Trains the bank from +stim=FILE (tools/hexn_cellbank_check_v4.py writes it, format of tb_hexn_cellbank_v3.v: per trial mode, bits, leak, then per cell threshold and K lane codes).
// Mode 0: RUN (0x06). Mode 1: SETLEAK (0x10), LOADCELLN (0x11) for every cell, RUNCELLN (0x12): reply = per cell output burst count and forward total, then K captured burst lengths. Prints the line format of tb_hexn_cellbank_v3.v:
// 'R mode ans_valid ans_class cnt[0..K-1] cap[0..K-1] then per cell fwd cnt'. Compile with -DLATMOD=hexn_lattice_<shape>_v14 -DNCLS=<K> -DNCELL=<NC> -DCLKDIV=8.
`ifndef NCLS
`define NCLS 7
`endif
`ifndef NBW
`define NBW 18
`endif
`ifndef CLKDIV
`define CLKDIV 8
`endif
`ifndef NCELL
`define NCELL 1
`endif
module tb_hexn_cell_top_v2;
    localparam K = `NCLS, NB = `NBW, S = 16, CD = `CLKDIV, NC = `NCELL;
    reg clk = 0, rxd = 1; wire txd; wire [5:0] led;
    hexn_tang_top_v10 dut(.clk(clk), .uart_rx(rxd), .uart_tx(txd), .led(led));
    always #5 clk = ~clk;
    integer fd, n, i, k, c, ntr, tr, v, y, TT, mode, lk; reg [1023:0] fn; reg [NB-1:0] bb [0:K*S-1]; integer yy [0:K*S-1]; reg [NB-1:0] m; reg [39:0] lc40 [0:NC-1]; integer cth [0:NC-1]; reg [7:0] st; reg [7:0] cnts [0:31]; reg [7:0] caps [0:31]; reg [7:0] cc [0:NC-1]; reg [7:0] fw [0:NC-1];
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
            n = $fscanf(fd, "%d %h %d", mode, m, lk);
            for (c = 0; c < NC; c = c + 1) begin
                n = $fscanf(fd, "%d", cth[c]); lc40[c] = 0;
                for (i = 0; i < K; i = i + 1) begin n = $fscanf(fd, "%d", v); lc40[c][2*i +: 2] = v; end
            end
            if (mode == 0) begin
                sendb(8'h06); send3(m); recvb(st); for (k = 0; k < K; k = k + 1) recvb(cnts[k]);
                $write("R 0 %0d %0d", st[7], st[4:0]); for (k = 0; k < K; k = k + 1) $write(" %0d", cnts[k]);
                for (k = 0; k < K; k = k + 1) $write(" 0"); for (c = 0; c < NC; c = c + 1) $write(" 0 0"); $write("\n");
            end else begin
                sendb(8'h10); sendb(lk); expect_ack;
                for (c = 0; c < NC; c = c + 1) begin
                    sendb(8'h11); sendb(c); sendb(cth[c]); sendb(lc40[c][7:0]); sendb(lc40[c][15:8]); sendb(lc40[c][23:16]); sendb(lc40[c][31:24]); sendb(lc40[c][39:32]); expect_ack;
                end
                sendb(8'h12); send3(m); for (c = 0; c < NC; c = c + 1) begin recvb(cc[c]); recvb(fw[c]); end for (k = 0; k < K; k = k + 1) recvb(caps[k]);
                $write("R 1 0 0"); for (k = 0; k < K; k = k + 1) $write(" 0"); for (k = 0; k < K; k = k + 1) $write(" %0d", caps[k]);
                for (c = 0; c < NC; c = c + 1) $write(" %0d %0d", fw[c], cc[c]); $write("\n");
            end
        end
        $finish;
    end
endmodule
