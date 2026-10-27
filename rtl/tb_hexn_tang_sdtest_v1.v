`timescale 1ns/1ps
// tb_hexn_tang_sdtest_v1.v -- simulates the SD tier board test against the behavioural SD card (fpga/verilog/sd_card_model_v1.v), with small block numbers (the model holds 64 blocks), and checks the serial report: card ready, three clean regions.
module tb_hexn_tang_sdtest_v1;
    reg clk27 = 0; always #18.5185 clk27 = ~clk27;
    wire [5:0] led; wire utx, sclk, mosi, miso, csn;
    hexn_tang_sdtest_v1 #(.NB(4), .B0(4), .B1(24), .B2(44), .GAP(2000), .INIT_DIV(3), .FAST_DIV(1)) dut (.clk27(clk27), .uart_tx(utx), .led(led), .sd_clk(sclk), .sd_mosi(mosi), .sd_miso(miso), .sd_cs_n(csn));
    sd_card_model_v1 #(.SDHC(1), .BLOCKS(64)) card (.sclk(sclk), .mosi(mosi), .cs_n(csn), .miso(miso));
    reg [7:0] chars [0:140]; integer n = 0, k, bad = 0; reg [7:0] b;
    initial begin
        wait (utx === 1'b1);
        forever begin
            @(negedge utx); #(8680.5 * 1.5); for (k = 0; k < 8; k = k + 1) begin b[k] = utx; #8680.5; end
            if (n < 141) begin chars[n] = b; n = n + 1; end
        end
    end
    function [31:0] f4(input integer base); f4 = {chars[base], chars[base+1], chars[base+2], chars[base+3]}; endfunction
    integer r, o;
    initial begin
        wait (n == 141); #1000;
        if (chars[7] !== "1") begin bad = bad + 1; $display("card not ready in report"); end
        for (r = 0; r < 3; r = r + 1) begin
            o = 30 + 37 * r;
            if (chars[o] !== "R" || chars[o+1] !== 8'h30 + r) begin bad = bad + 1; $display("region %0d: bad tag", r); end
            if (f4(o + 7) !== "0000") begin bad = bad + 1; $display("region %0d: err field %s", r, f4(o + 7)); end
        end
        $write("report:"); for (r = 0; r < 141; r = r + 1) if (chars[r] != 8'h0D) $write("%c", (chars[r] == 8'h0A) ? 8'h7C : chars[r]); $write("\n");
        if (bad == 0 && led === 6'b100000) $display("SD TIER TEST PASS"); else $display("SD TIER TEST FAIL led=%b", led);
        $finish;
    end
    initial begin #900000000; $display("SD TIER TEST FAIL: timeout, %0d characters, led=%b", n, led); $finish; end
endmodule
