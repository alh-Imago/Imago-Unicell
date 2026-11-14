// tb_bram_char.v - simulate bram_char_top and decode its UART report (fast baud, short pause)
`timescale 1ns/1ps
module tb_bram_char;
    reg clk = 0; always #5 clk = ~clk;
    wire tx; wire [5:0] led_n;
    bram_char_top #(.BAUD_DIV(8), .GAPBIT(12)) dut (.clk(clk), .uart_rx(1'b1), .uart_tx(tx), .led_n(led_n));
    // behavioural receiver: 8 clocks per bit
    reg [7:0] ch; integer n = 0, lines = 0; reg [8*340-1:0] line;
    always begin
        @(negedge tx);
        repeat (12) @(posedge clk);                     // to the middle of bit 0
        begin : rx
            integer i; reg [7:0] b;
            for (i = 0; i < 8; i = i + 1) begin b[i] = tx; repeat (8) @(posedge clk); end
            if (b == 8'h0A) begin
                lines = lines + 1;
                if (lines == `LINES) begin $display("LINE %0s", line); $finish; end
                n = 0;
            end else if (b != 8'h0D) begin line = {line[8*339-1:0], b}; n = n + 1; end
        end
    end
    initial begin #400000000; $display("TIMEOUT"); $finish; end
endmodule
