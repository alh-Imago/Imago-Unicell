`timescale 1ns/1ps
module tb_unicell_tang_nano_20k_diag2_v1;
    reg clk = 0;
    wire led0, led1, led2, led3;
    always #18.5 clk = ~clk;

    unicell_tang_nano_20k_diag2_v1 dut (
        .BOARD_CLK(clk),
        .LED0_N(led0), .LED1_N(led1), .LED2_N(led2), .LED3_N(led3)
    );

    initial begin
        #15000;
        $display("cfg_valid_seen(LED1_N=%b) armed_seen(LED2_N=%b) fire_seen(LED3_N=%b) -- N means LED ON (active low)",
                  led1, led2, led3);
        if (led1 || led2 || led3) begin
            $display("FAIL: expected all three sticky LEDs asserted (driven low) by now");
            $finish;
        end
        $display("PASS: all three sticky diagnostics latched with pure power-on reset, no button needed");
        $finish;
    end
endmodule
