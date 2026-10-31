`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0, b1 = 1, b2 = 1, b3 = 1;
    wire latch, dclk, ddata, buzz; wire [5:0] led;
    hexn_demo_top_v1 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .BTN1_N(b1), .BTN2_N(b2), .BTN3_N(b3), .DISP_LATCH(latch), .DISP_CLK(dclk), .DISP_DATA(ddata), .BUZZER(buzz), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, round, tg, ms_wait, k, shown; reg [1:0] pick; reg want_right;
    task press(input [1:0] which); begin case (which) 0: b1 = 0; 1: b2 = 0; default: b3 = 0; endcase end endtask
    task release_all; begin b1 = 1; b2 = 1; b3 = 1; end endtask
    task ms_ticks(input integer n); begin repeat (n * 10) @(posedge clk); end endtask
    initial begin
        // wait for the table to load and the first target to appear
        wait (T.st == 3 || T.st == 2); 
        for (round = 0; round < 6; round = round + 1) begin
            wait (T.st == 3); #1;                               // target shown
            tg = T.tgt; ms_wait = 40 + round * 37;             // reaction time in ms
            if (T.val2 !== {12'h000, 4'd1 + tg[3:0]}) begin $display("FAIL round %0d: target display %h for target %0d", round, T.val2, tg + 1); fails = fails + 1; end
            if (led[3:1] !== ~(3'b001 << tg)) begin $display("FAIL round %0d: LED %b", round, led); fails = fails + 1; end
            ms_ticks(ms_wait);
            want_right = (round % 3 != 2);                      // every third round presses a wrong button
            pick = want_right ? tg[1:0] : (tg[1:0] + 1) % 3;
            press(pick);
            wait (T.st == 5); repeat (20) @(posedge clk);
            shown = T.val2;
            // expect the BCD of ms_wait (the counter stops within a tick or two of the press)
            begin : chk
                integer got;
                got = T.n3 * 1000 + T.n2 * 100 + T.n1 * 10 + T.n0;
                if (got < ms_wait - 1 || got > ms_wait + 2) begin $display("FAIL round %0d: time %0d, wanted %0d", round, got, ms_wait); fails = fails + 1; end
            end
            if (want_right && ms_wait < 256 && T.pred !== 1'b1) begin $display("FAIL round %0d: right button, %0d ms, not a good hit", round, ms_wait); fails = fails + 1; end
            if (!want_right && T.pred !== 1'b0) begin $display("FAIL round %0d: wrong button counted as good", round); fails = fails + 1; end
            if (!want_right && shown[15:12] !== 4'hE) begin $display("FAIL round %0d: wrong button should show E, shows %h", round, shown); fails = fails + 1; end
            if (want_right && shown !== {T.n3, T.n2, T.n1, T.n0}) begin $display("FAIL round %0d: display %h", round, shown); fails = fails + 1; end
            $display("round %0d: target %0d, pressed %0d after %0d ms -> display %h, good hit %b", round, tg + 1, pick + 1, ms_wait, shown, T.pred);
            ms_ticks(5); release_all; ms_ticks(8); press(0); ms_ticks(2); release_all; ms_ticks(8);   // dismiss with a tap
        end
        // slow right press: over 256 ms must not be a good hit
        wait (T.st == 3); tg = T.tgt; ms_ticks(400); press(tg[1:0]); wait (T.st == 5); repeat (20) @(posedge clk);
        if (T.pred !== 1'b0) begin $display("FAIL slow right press counted as good"); fails = fails + 1; end
        $display("slow press: pred %b", T.pred); release_all;
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (40000000) @(posedge clk); $display("TIMEOUT state %0d", T.st); $finish; end
endmodule
