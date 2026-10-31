`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg b1 = 1, b2 = 1, key = 0;
    wire latch, dclk, ddata, buzz; wire [5:0] led;
    hexn_morse_top_v1 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .BTN1_N(b1), .BTN2_N(b2), .DISP_LATCH(latch), .DISP_CLK(dclk), .DISP_DATA(ddata), .BUZZER(buzz), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, i;
    task ms_ticks(input integer n); begin repeat (n * 10) @(posedge clk); end endtask
    task sym(input integer dash, input integer gapms); begin b1 = 0; ms_ticks(dash ? 480 : 160); b1 = 1; ms_ticks(gapms); end endtask   // unit 160 ms
    // send a string of '.' and '-' with symbol gaps of 160 ms, then a final gap
    task send(input [8*8-1:0] s, input integer n, input integer finalgap);
        integer k; begin for (k = n - 1; k >= 0; k = k - 1) begin sym(s[8*k +: 8] == "-", (k == 0) ? finalgap : 160); end end endtask
    task expect_last(input [5:0] want, input [255:0] name); begin
        if (T.c3 !== want) begin $display("FAIL %0s: last char %0d, wanted %0d", name, T.c3, want); fails = fails + 1; end else $display("ok %0s -> char %0d", name, T.c3); end endtask
    initial begin
        wait (T.loaded); ms_ticks(20);
        send("...", 3, 480);   ms_ticks(10); expect_last(6'd18, "S (... then 480 ms)");        // letter gap 3 units
        send("---", 3, 480);   ms_ticks(10); expect_last(6'd14, "O (---)");
        send("...", 3, 1300);  ms_ticks(10); expect_last(6'd62, "space after S (word gap)");
        if (T.c0 !== 6'd18 || T.c1 !== 6'd14 || T.c2 !== 6'd18) begin $display("FAIL buffer %0d %0d %0d %0d", T.c0, T.c1, T.c2, T.c3); fails = fails + 1; end
        // note: the third S was typed before the word gap, so the buffer is S O S space
        send(".----", 5, 480); ms_ticks(10); expect_last(6'd27, "1 (.----)");
        send("-.-.", 4, 480);  ms_ticks(10); expect_last(6'd2, "C (-.-.)");
        send("-.--.-", 6, 480); ms_ticks(10); expect_last(6'd63, "6 symbols -> not a character");
        send(".", 1, 1300);     ms_ticks(10); expect_last(6'd62, "E then word gap");
        if (T.c2 !== 6'd4) begin $display("FAIL E missing, buffer %0d %0d %0d %0d", T.c0, T.c1, T.c2, T.c3); fails = fails + 1; end
        b2 = 0; ms_ticks(5); b2 = 1; ms_ticks(5);
        if (T.c0 !== 6'd62 || T.c1 !== 6'd62 || T.c2 !== 6'd62 || T.c3 !== 6'd62) begin $display("FAIL clear"); fails = fails + 1; end
        // Alan's pattern: dashes, dots, dashes with a letter gap between the groups = O S O
        send("---", 3, 480); send("...", 3, 480); send("---", 3, 480); ms_ticks(10);
        if (T.c1 !== 6'd14 || T.c2 !== 6'd18 || T.c3 !== 6'd14) begin $display("FAIL O S O: %0d %0d %0d %0d", T.c0, T.c1, T.c2, T.c3); fails = fails + 1; end else $display("ok --- ... --- -> O S O");
        // sidetone follows the key
        b1 = 0; ms_ticks(30); if (buzz !== 1'b0) begin $display("FAIL buzzer should sound (low) while the key is down"); fails = fails + 1; end b1 = 1; ms_ticks(50);
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (60000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
