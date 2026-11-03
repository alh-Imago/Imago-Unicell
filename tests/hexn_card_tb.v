`timescale 1ns/1ps
// Test bench for the assembled hexn_card_top: +rx=FILE (one '0'/'1' per line, the level of uart_rx at each clock, $readmemb), +n=CLOCKS. Prints "cycle level" for every change of uart_tx (and the first level).
module tb #(parameter CLKDIV = 8);
    reg clk = 0; always #5 clk = ~clk;
    reg mem [0:4194303]; reg rx = 1; wire tx; wire [5:0] led; integer n = 0, i, cyc = 0; reg txp = 1'bx; reg [1023:0] fn;
    hexn_card_top #(.CLKDIV(CLKDIV)) dut (.clk(clk), .uart_rx(rx), .uart_tx(tx), .led(led));
    initial begin
        if (!$value$plusargs("rx=%s", fn) || !$value$plusargs("n=%d", n)) begin $display("FAIL args"); $finish; end
        $readmemb(fn, mem, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            rx = mem[i]; #1; @(posedge clk); #1;
            if (tx !== txp) begin $display("%0d %b", i, tx); txp = tx; end
        end
        $finish;
    end
endmodule
