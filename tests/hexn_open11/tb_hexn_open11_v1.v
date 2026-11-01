`timescale 1ns/1ps
// tb_hexn_open11_v1: table space 7 = the PATTERN BANK (64 x 32) through the whole open unit v11 over SPI: load and save in the generic paths.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0;
    wire SPI_MISO, READY; wire [5:0] led;
    tri1 [15:0] pool;
//MASTER//
    hexn_open_top_v11 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .POOL(pool), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i, bad, seq = 70; reg [8*200:1] dir, fn;
    reg [31:0] c_pat [0:63]; reg [31:0] c_big [0:127]; reg [31:0] c_new [0:63]; reg [31:0] pre0 [0:63];
    localparam SENT = 32'hDEADBEEF;
    task check(input cond, input [639:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task wait_idle; begin rd_reg(8'd10); while (rv[4]) rd_reg(8'd10); end endtask
    task sentinel(input [15:0] a, input integer n); begin for (i = 0; i < n; i = i + 1) wbuf[i] = SENT; wr_words(a, n); end endtask
    task load(input [3:0] sp, input [15:0] base, input integer n); begin wr_reg(8'd17, {sp, 12'd0, 16'd0} | (base << 16) | n); seq = seq + 1; wr_reg(8'd19, seq); wait_idle; end endtask
    task save(input [3:0] sp, input [15:0] base, input integer n); begin wr_reg(8'd30, {sp, 12'd0, 16'd0} | (base << 16) | n); seq = seq + 1; wr_reg(8'd31, seq); repeat (4) @(negedge clk); wait_idle; end endtask
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("FAIL args"); $finish; end
        $sformat(fn, "%0s/c_pat.hex", dir); $readmemh(fn, c_pat); $sformat(fn, "%0s/c_big.hex", dir); $readmemh(fn, c_big); $sformat(fn, "%0s/c_new.hex", dir); $readmemh(fn, c_new);
        wait (T.init_done); repeat (40) @(negedge clk);
        for (i = 0; i < 64; i = i + 1) pre0[i] = T.TB.pre[i];
        // ---- A: after power-up every slot is 0; save count 0 = exactly 64 words
        sentinel(16'd300, 80); save(4'd7, 300, 0); rd_words(16'd300, 68); bad = 0; for (i = 0; i < 64; i = i + 1) if (rbuf[i] !== 32'd0) bad = bad + 1;
        check(bad == 0, "A: after power-up the pattern bank is all zero"); check(rbuf[64] === SENT && rbuf[67] === SENT, "A: a save with count 0 writes exactly 64 words");
        // ---- B: load 64 words, save them back
        for (i = 0; i < 64; i = i + 1) wbuf[i] = c_pat[i]; wr_words(16'd0, 64); load(4'd7, 0, 64);
        bad = 0; for (i = 0; i < 64; i = i + 1) if (T.TB.pat[i] !== c_pat[i]) bad = bad + 1; check(bad == 0, "B: 64 words loaded into the pattern RAM");
        sentinel(16'd600, 80); save(4'd7, 600, 0); rd_words(16'd600, 66); bad = 0; for (i = 0; i < 64; i = i + 1) if (rbuf[i] !== c_pat[i]) bad = bad + 1;
        check(bad == 0 && rbuf[64] === SENT, "B: saved back, all 64 words equal what was loaded");
        // ---- C: a load of 100 words: the 36 beyond the bank are dropped, NOT wrapped onto slots 0..35
        for (i = 0; i < 100; i = i + 1) wbuf[i] = c_big[i]; wr_words(16'd0, 100); load(4'd7, 0, 100);
        bad = 0; for (i = 0; i < 64; i = i + 1) if (T.TB.pat[i] !== c_big[i]) bad = bad + 1; check(bad == 0, "C: a load of 100 words keeps the first 64 and drops the rest (no wrap)");
        // ---- D: a short load of 10 words changes only slots 0..9
        for (i = 0; i < 10; i = i + 1) wbuf[i] = c_new[i]; wr_words(16'd0, 10); load(4'd7, 0, 10);
        bad = 0; for (i = 0; i < 10; i = i + 1) if (T.TB.pat[i] !== c_new[i]) bad = bad + 1; for (i = 10; i < 64; i = i + 1) if (T.TB.pat[i] !== c_big[i]) bad = bad + 1;
        check(bad == 0, "D: a load of 10 words changes slots 0 to 9 only");
        // ---- E: the other table spaces were not touched by any of this
        bad = 0; for (i = 0; i < 64; i = i + 1) if (T.TB.pre[i] !== pre0[i]) bad = bad + 1; check(bad == 0, "E: the preset RAM (space 5) is unchanged");
        // ---- F: a save to a scratch base that would run past the scratch RAM is refused
        sentinel(16'd1000, 24); save(4'd7, 1000, 64); rd_words(16'd1000, 24); check(rbuf[0] === SENT && rbuf[23] === SENT, "F: a save that would run past the scratch RAM writes nothing");
        // ---- G: 'restore factory defaults' (cfg23) sets every slot back to 0
        seq = seq + 1; wr_reg(8'd23, seq); repeat (8) @(negedge clk); wait (T.init_done); wait_idle; repeat (10) @(negedge clk);
        bad = 0; for (i = 0; i < 64; i = i + 1) if (T.TB.pat[i] !== 32'd0) bad = bad + 1; check(bad == 0, "G: the factory restore clears the pattern bank");
        bad = 0; for (i = 0; i < 64; i = i + 1) if (T.TB.pre[i] !== pre0[i]) bad = bad + 1; check(bad == 0, "G: and the presets are the factory presets again");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (50000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
