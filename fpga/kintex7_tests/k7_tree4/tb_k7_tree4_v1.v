// tb_k7_tree4_v1.v -- simulation of the Kintex wrapper (small CPB so it runs in seconds).
// Case 1: the unchanged design must give PASS (green blinks, red never on after the lamp test).
// Case 2: a corrupted expectation (parameter BREAK) must give FAIL. Run:  make sim   (see Makefile)
`timescale 1ns/1ps
module tb_k7_tree4_v1;
    reg clk = 0; always #10 clk = ~clk;
    wire l0, l1, l2;
    top #(.CPB(8), .LAMP_BIT(10), .HB_BIT(12), .FAST_BIT(11), .WATCHDOG(30000000)) t (.CLK(clk), .LED0(l0), .LED1(l1), .LED2(l2));
    integer green_toggles = 0, red_late = 0, ycount = 0; reg lg = 0, ly = 0;
    always @(posedge clk) if (!t.lamp_on) begin
        if (l1 !== lg) green_toggles = green_toggles + 1; lg <= l1;
        if (l0) red_late = red_late + 1;
        if (l2 !== ly) ycount = ycount + 1; ly <= l2;
    end
    initial begin
        #60000000;
        $display("seen=%b bad=%b timeout=%b idx=%0d green_toggles=%0d red_on_clocks=%0d yellow_toggles=%0d",
                 t.seen, t.bad, t.timeout, t.idx, green_toggles, red_late, ycount);
        if (t.seen && !t.bad && !t.timeout && green_toggles > 4 && red_late == 0 && ycount > 4) $display("PASS");
        else $display("FAIL");
        $finish;
    end
endmodule
