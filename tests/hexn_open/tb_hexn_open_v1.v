`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0, b1 = 1, b2 = 1, b3 = 1;
    wire SPI_MISO, READY, latch, dclk, ddata, buzz; wire [5:0] led;
//MASTER//
    hexn_open_top_v1 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY),
        .BTN1_N(b1), .BTN2_N(b2), .BTN3_N(b3), .DISP_LATCH(latch), .DISP_CLK(dclk), .DISP_DATA(ddata), .BUZZER(buzz), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i, n, bad;
    task ms_ticks(input integer k); begin repeat (k * 10) @(posedge clk); end endtask
    task check(input cond, input [255:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task sym(input integer dash, input integer gapms); begin b1 = 0; ms_ticks(dash ? 480 : 160); b1 = 1; ms_ticks(gapms); end endtask
    initial begin
        repeat (40) @(negedge clk);
        rd_reg(8'd0); check(rv === 32'h57320002, "ID is 0x57320002");
        wr_reg(8'd16, 32'h0); rd_reg(8'd16); check(rv === 32'h0, "mode 0 after reset");
        wr_reg(8'd20, 32'hDEADBEEF); rd_reg(8'd20); check(rv === 32'hDEADBEEF, "config register 20 reads back");
        // long transfers through the scratch RAM: 64 words (fails on v1) and 200 words in one transaction
        for (i = 0; i < 64; i = i + 1) wbuf[i] = 32'hA5000000 + i * 977;
        wr_words(16'd0, 64); rd_words(16'd0, 64); bad = 0; for (i = 0; i < 64; i = i + 1) if (rbuf[i] !== 32'hA5000000 + i * 977) bad = bad + 1;
        check(bad == 0, "64-word write and read back exact");
        for (i = 0; i < 200; i = i + 1) wbuf[i] = 32'h5A000000 + i * 31337;
        wr_words(16'd100, 200); rd_words(16'd100, 200); bad = 0; for (i = 0; i < 200; i = i + 1) if (rbuf[i] !== 32'h5A000000 + i * 31337) bad = bad + 1;
        check(bad == 0, "200-word write and read back exact");
        // mode 2: Morse key  (O = ---, then a letter gap)
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); ms_ticks(20); rd_reg(8'd10); check(rv[3:0] === 4'b1010, "status: mode 2, Morse core ready");
        check(T.RC.st === 3'd0 || T.RC.st === 3'd1, "reaction core idle in mode 2");
        sym(1, 160); sym(1, 160); sym(1, 480); ms_ticks(10); check(T.MC.c3 === 6'd14, "Morse: --- decodes as O");
        // mode 1: reaction game
        wr_reg(8'd16, 32'h1); wait (T.RC.st == 3); #1; rd_reg(8'd10); check(rv[3:0] === 4'b0101, "status: mode 1, reaction core ready");
        check(T.MC.c3 === 6'd62, "Morse core reset when it is not chosen");
        ms_ticks(120); case (T.RC.tgt) 0: b1 = 0; 1: b2 = 0; default: b3 = 0; endcase wait (T.RC.st == 5); repeat (20) @(posedge clk);
        check(T.RC.right === 1'b1 && T.RC.pred === 1'b1, "reaction: right button, 120 ms is a good hit"); b1 = 1; b2 = 1; b3 = 1; ms_ticks(10);
        // back to Morse: it restarts clean
        wr_reg(8'd16, 32'h2); wait (T.MC.loaded); ms_ticks(20); sym(0, 160); sym(1, 160); sym(0, 160); sym(0, 480); ms_ticks(10); check(T.MC.c3 === 6'd11, "Morse after switching back: .-.. decodes as L");
        wr_reg(8'd16, 32'h0); ms_ticks(10); check(READY === 1'b0 && T.en === 1'b0 && buzz !== 1'b0, "mode 0: nothing running, display blank, buzzer off");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (80000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
