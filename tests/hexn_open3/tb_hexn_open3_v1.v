`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0, b1 = 1, b2 = 1, b3 = 1;
    wire SPI_MISO, READY, latch, dclk, ddata, buzz; wire [5:0] led;
//MASTER//
    hexn_open_top_v3 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY),
        .BTN1_N(b1), .BTN2_N(b2), .BTN3_N(b3), .DISP_LATCH(latch), .DISP_CLK(dclk), .DISP_DATA(ddata), .BUZZER(buzz), .LED_N(led));
    integer fails = 0, i, bad, n1, n2, r1, r2, seq = 7; reg [8*200:1] dir, fn;
    reg [31:0] s1 [0:255]; reg [31:0] e1 [0:255]; reg [31:0] s2 [0:255]; reg [31:0] e2 [0:255];
    task check(input cond, input [255:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task wait_idle; begin rd_reg(8'd10); while (rv[6]) rd_reg(8'd10); end endtask
    task run_batch(input integer cnt, input integer outbase); begin wr_reg(8'd24, (outbase << 16) | cnt); seq = seq + 1; wr_reg(8'd25, seq); repeat (20) @(negedge clk); wait_idle; end endtask
    initial begin
        if (!$value$plusargs("dir=%s", dir) || !$value$plusargs("n1=%d", n1) || !$value$plusargs("r1=%d", r1) || !$value$plusargs("n2=%d", n2) || !$value$plusargs("r2=%d", r2)) begin $display("FAIL args"); $finish; end
        $sformat(fn, "%0s/s1.hex", dir); $readmemh(fn, s1); $sformat(fn, "%0s/e1.hex", dir); $readmemh(fn, e1);
        $sformat(fn, "%0s/s2.hex", dir); $readmemh(fn, s2); $sformat(fn, "%0s/e2.hex", dir); $readmemh(fn, e2);
        wait (T.init_done); repeat (40) @(negedge clk);
        // batch 1: table LOAD words + BIAS + SCORE words in ONE stream
        wr_reg(8'd16, 32'h3); repeat (10) @(negedge clk); rd_reg(8'd10); check(rv[1:0] === 2'd3 && rv[6] === 1'b0, "mode 3, engine idle");
        for (i = 0; i < 128; i = i + 1) wbuf[i] = s1[i]; wr_words(16'd0, 128);
        for (i = 0; i < n1 - 128; i = i + 1) wbuf[i] = s1[128 + i]; wr_words(16'd128, n1 - 128);
        run_batch(n1, 400);
        rd_reg(8'd10); check(rv[15:8] === r1[7:0], "results-written counter equals the number of SCORE words");
        rd_words(16'd400, r1); bad = 0; for (i = 0; i < r1; i = i + 1) if (rbuf[i] !== e1[i]) bad = bad + 1;
        check(bad == 0, "batch 1: every result equals the reference (loads and scores in one stream)");
        // mode 0 then 3 again: the weights stay, the bias is cleared, so batch 2 sends its own BIAS word first
        wr_reg(8'd16, 32'h0); repeat (10) @(negedge clk); wr_reg(8'd16, 32'h3); repeat (10) @(negedge clk);
        for (i = 0; i < n2; i = i + 1) wbuf[i] = s2[i]; wr_words(16'd0, n2);
        run_batch(n2, 600);
        rd_words(16'd600, r2); bad = 0; for (i = 0; i < r2; i = i + 1) if (rbuf[i] !== e2[i]) bad = bad + 1;
        check(bad == 0, "batch 2 after a mode change: weights kept, new bias applied");
        // the personalities still work after all this: mode 2 Morse core ready
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); repeat (50) @(negedge clk); rd_reg(8'd10); check(rv[3] === 1'b1, "Morse mode still starts");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (60000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
