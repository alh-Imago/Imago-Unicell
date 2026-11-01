`timescale 1ns/1ps
// tb_hexn_open7_v1: the REVERSE COPY (save) of the table spaces into the scratch RAM, through the whole open unit v7 over SPI.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0;
    wire SPI_MISO, READY; wire [5:0] led;
    tri1 [15:0] pool;
//MASTER//
    hexn_open_top_v7 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .POOL(pool), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i, bad, seq = 70; reg [8*200:1] dir, fn;
    reg [31:0] c_rt [0:63]; reg [31:0] c_mt [0:63]; reg [31:0] c_dec [0:255]; reg [31:0] c_gly [0:63]; reg [31:0] c_pre [0:63]; reg [31:0] first [0:255];
    localparam SENT = 32'hDEADBEEF;
    task check(input cond, input [639:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task wait_idle; begin rd_reg(8'd10); while (rv[4]) rd_reg(8'd10); end endtask
    task sentinel(input [15:0] a, input integer n); begin for (i = 0; i < n; i = i + 1) wbuf[i] = SENT; wr_words(a, n); end endtask
    task load(input [3:0] sp, input [15:0] base, input integer n); begin wr_reg(8'd17, {sp, 12'd0, 16'd0} | (base << 16) | n); seq = seq + 1; wr_reg(8'd19, seq); wait_idle; end endtask
    task save(input [3:0] sp, input [15:0] base, input integer n); begin wr_reg(8'd30, {sp, 12'd0, 16'd0} | (base << 16) | n); seq = seq + 1; wr_reg(8'd31, seq); repeat (4) @(negedge clk); wait_idle; end endtask
    initial begin
        if (!$value$plusargs("dir=%s", dir)) begin $display("FAIL args"); $finish; end
        $sformat(fn, "%0s/c_rt.hex", dir); $readmemh(fn, c_rt); $sformat(fn, "%0s/c_mt.hex", dir); $readmemh(fn, c_mt); $sformat(fn, "%0s/c_dec.hex", dir); $readmemh(fn, c_dec);
        $sformat(fn, "%0s/c_gly.hex", dir); $readmemh(fn, c_gly); $sformat(fn, "%0s/c_pre.hex", dir); $readmemh(fn, c_pre);
        wait (T.init_done); repeat (40) @(negedge clk);
        // ---- A: the factory reaction table (193 words), count 0 = the space's own size; the word after it must be untouched
        sentinel(16'd300, 200); save(4'd1, 300, 0); rd_words(16'd300, 200); bad = 0; for (i = 0; i < 193; i = i + 1) if (rbuf[i] !== T.TB.rt[i]) bad = bad + 1;
        check(bad == 0 && T.TB.rt_len == 193, "A: factory reaction table saved, 193 words equal the table RAM"); check(rbuf[193] === SENT && rbuf[199] === SENT, "A: nothing written past the table's own length");
        // ---- B: a custom reaction table (40 words), loaded, then saved back
        for (i = 0; i < 40; i = i + 1) wbuf[i] = c_rt[i]; wr_words(16'd0, 40); load(4'd1, 0, 40);
        sentinel(16'd600, 60); save(4'd1, 600, 0); rd_words(16'd600, 44); bad = 0; for (i = 0; i < 40; i = i + 1) if (rbuf[i] !== c_rt[i]) bad = bad + 1;
        check(bad == 0, "B: custom reaction table saved back, all 40 words equal what was loaded"); check(rbuf[40] === SENT && rbuf[43] === SENT, "B: exactly 40 words written (the table's length)");
        // ---- C: explicit smaller count
        sentinel(16'd600, 60); save(4'd1, 600, 10); rd_words(16'd600, 14); bad = 0; for (i = 0; i < 10; i = i + 1) if (rbuf[i] !== c_rt[i]) bad = bad + 1;
        check(bad == 0 && rbuf[10] === SENT, "C: explicit count 10 writes exactly 10 words");
        // ---- D: Morse scorer table (space 2), 30 words
        for (i = 0; i < 30; i = i + 1) wbuf[i] = c_mt[i]; wr_words(16'd0, 30); load(4'd2, 0, 30);
        sentinel(16'd600, 40); save(4'd2, 600, 0); rd_words(16'd600, 34); bad = 0; for (i = 0; i < 30; i = i + 1) if (rbuf[i] !== c_mt[i]) bad = bad + 1;
        check(bad == 0 && rbuf[30] === SENT, "D: Morse scorer table saved, 30 words");
        // ---- E: decode table (space 3, 256 x 6 bits): zero-extended, as the load path takes it
        for (i = 0; i < 256; i = i + 1) wbuf[i] = c_dec[i]; wr_words(16'd0, 256); load(4'd3, 0, 256);
        save(4'd3, 700, 0); rd_words(16'd700, 256); bad = 0; for (i = 0; i < 256; i = i + 1) if (rbuf[i] !== (c_dec[i] & 32'h3F)) bad = bad + 1;
        check(bad == 0, "E: decode table saved (6 bits, zero-extended), all 256");
        // ---- F: glyph table (space 4, 64 x 8 bits)
        for (i = 0; i < 64; i = i + 1) wbuf[i] = c_gly[i]; wr_words(16'd0, 64); load(4'd4, 0, 64);
        sentinel(16'd700, 70); save(4'd4, 700, 0); rd_words(16'd700, 66); bad = 0; for (i = 0; i < 64; i = i + 1) if (rbuf[i] !== (c_gly[i] & 32'hFF)) bad = bad + 1;
        check(bad == 0 && rbuf[64] === SENT, "F: glyph table saved (8 bits), 64 words");
        // ---- G: preset RAM (space 5, 64 x 32)
        for (i = 0; i < 64; i = i + 1) wbuf[i] = c_pre[i]; wr_words(16'd0, 64); load(4'd5, 0, 64);
        sentinel(16'd700, 70); save(4'd5, 700, 0); rd_words(16'd700, 66); bad = 0; for (i = 0; i < 64; i = i + 1) if (rbuf[i] !== c_pre[i]) bad = bad + 1;
        check(bad == 0 && rbuf[64] === SENT, "G: preset RAM saved, 64 words");
        // ---- H: the full cycle. Custom reaction table saved to scratch 600, factory defaults restored, then loaded back from the saved words
        for (i = 0; i < 40; i = i + 1) wbuf[i] = c_rt[i]; wr_words(16'd0, 40); load(4'd1, 0, 40); save(4'd1, 800, 0);
        seq = seq + 1; wr_reg(8'd23, seq); repeat (4) @(negedge clk); wait_idle;
        check(T.TB.rt_len == 193 && (T.TB.rt[0] !== c_rt[0] || T.TB.rt[1] !== c_rt[1]), "H: factory defaults restored (the custom table is gone)");
        load(4'd1, 800, 40);
        bad = 0; for (i = 0; i < 40; i = i + 1) if (T.TB.rt[i] !== c_rt[i]) bad = bad + 1;
        check(bad == 0 && T.TB.rt_len == 40, "H: loading the SAVED words back restores the custom table exactly, length 40");
        // ---- I: refusals write nothing. A block past scratch word 1023, and a space that does not exist
        sentinel(16'd1000, 24); save(4'd1, 1000, 100); rd_words(16'd1000, 24); bad = 0; for (i = 0; i < 24; i = i + 1) if (rbuf[i] !== SENT) bad = bad + 1;
        check(bad == 0, "I: a save that would run past scratch word 1023 is refused, nothing written");
        sentinel(16'd900, 8); save(4'd6, 900, 5); rd_words(16'd900, 8); bad = 0; for (i = 0; i < 8; i = i + 1) if (rbuf[i] !== SENT) bad = bad + 1;
        check(bad == 0, "I: a save of a space that does not exist is refused, nothing written");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (80000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
