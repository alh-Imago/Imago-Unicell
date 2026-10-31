`timescale 1ns/1ps
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg key = 0;
    wire SPI_MISO, READY; wire [5:0] led;
    tri1 [15:0] pool; reg [15:0] ext = 16'hFFFF, ext_oe = 16'h0000;           // the outside world: a button pressed = drive its pin low
    genvar g; generate for (g = 0; g < 16; g = g + 1) begin : X assign pool[g] = ext_oe[g] ? ext[g] : 1'bz; end endgenerate
//MASTER//
    hexn_open_top_v4 #(.TICK(10), .DEBMS(3), .RSTW(4)) T (.BOARD_CLK(clk), .KEY_S1(key), .SPI_SCLK(sclk), .SPI_CS_N(cs_n), .SPI_MOSI(mosi), .SPI_MISO(SPI_MISO), .READY(READY), .POOL(pool), .LED_N(led));
    defparam T.SH.DWELL = 20; defparam T.SH.HALF = 2;
    integer fails = 0, k; reg saw12, saw6;
    task ms_ticks(input integer n); begin repeat (n * 10) @(posedge clk); end endtask
    task check(input cond, input [255:0] what); begin if (!cond) begin $display("FAIL %0s", what); fails = fails + 1; end else $display("ok %0s", what); end endtask
    task press(input integer pin); begin ext[pin] = 0; ext_oe[pin] = 1; end endtask
    task unpress(input integer pin); begin ext_oe[pin] = 0; ext[pin] = 1; end endtask
    always @(negedge pool[12]) saw12 = 1; always @(negedge pool[6]) saw6 = 1;   // the buzzer is ACTIVE LOW: a beep is a falling edge
    task game(input integer base, output reg ok);                          // start a round, press the target button on pool pin base+tgt after 170 ms
        begin wr_reg(8'd16, 32'h0); ms_ticks(5); wr_reg(8'd16, 32'h1); wait (T.RC.st == 3); #1; ms_ticks(170);
              press(base + T.RC.tgt); wait (T.RC.st == 5); repeat (20) @(posedge clk); ok = (T.RC.right === 1'b1 && T.RC.pred === 1'b1); ms_ticks(120); unpress(base + T.RC.tgt); ms_ticks(10); end
    endtask
    reg ok;
    initial begin
        saw12 = 0; saw6 = 0; wait (T.init_done); repeat (40) @(negedge clk);
        game(0, ok); check(ok, "default wiring: pool pins 0..2 are the buttons, a good hit scores");
        // move the three buttons to pool pins 9, 10, 11 (selector = pin XOR default 0, 1, 2)
        wr_reg(8'd26, 32'h0 | (9 ^ 0) | ((10 ^ 1) << 4) | ((11 ^ 2) << 8));
        game(9, ok); check(ok, "buttons moved to pool pins 9..11: a good hit scores");
        wr_reg(8'd16, 32'h0); ms_ticks(5); wr_reg(8'd16, 32'h1); wait (T.RC.st == 3); #1; ms_ticks(10);
        press(0); press(1); press(2); ms_ticks(300); check(T.RC.st == 3, "the old button pins now do nothing"); unpress(0); unpress(1); unpress(2);
        // live levels: hold pool pin 13 low and read it back through the status register bits 31:16
        press(13); ms_ticks(2); rd_reg(8'd10); check(rv[16+13] === 1'b0 && rv[16+14] === 1'b1, "status bits 31:16 show the live pin levels (13 low, 14 high)"); unpress(13);
        // move the buzzer to pool pin 12: the beep appears there and no longer on the old pin 6
        wr_reg(8'd27, 32'h0 | ((12 ^ 6) << 12)); saw12 = 0; saw6 = 0;
        game(9, ok); check(ok && saw12, "buzzer moved to pool pin 12: it beeps there"); check(!saw6, "and the old buzzer pin 6 stays quiet");
        // back to the default wiring
        wr_reg(8'd26, 32'h0); wr_reg(8'd27, 32'h0); saw12 = 0; saw6 = 0; game(0, ok); check(ok && saw6 && !saw12, "register 0 = default wiring again (buzzer back on pin 6)");
        if (fails == 0) $display("PASS"); else $display("FAIL %0d", fails);
        $finish;
    end
    initial begin repeat (60000000) @(posedge clk); $display("TIMEOUT"); $finish; end
endmodule
