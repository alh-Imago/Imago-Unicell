// tb_k7_tree4_jtag_v1.v -- simulation: let the wrapper finish its compare, then do a USER1-style scan through a
// behavioural BSCANE2 (defined HERE, for simulation only; the real primitive is a blackbox for the synthesiser).
`timescale 1ns/1ps
module BSCANE2 #(parameter JTAG_CHAIN = 1) (
    output reg CAPTURE = 0, output reg DRCK = 0, output reg RESET = 0, output reg RUNTEST = 0, output reg SEL = 0,
    output reg SHIFT = 0, output reg TCK = 0, output reg TDI = 0, output reg TMS = 0, output reg UPDATE = 0, input TDO);
endmodule

module tb_k7_tree4_jtag_v1;
    reg clk = 0; always #10 clk = ~clk;
    wire l0, l1, l2;
    top #(.CPB(8), .LAMP_BIT(10), .HB_BIT(12), .FAST_BIT(11), .WATCHDOG(30000000)) t (.CLK(clk), .LED0(l0), .LED1(l1), .LED2(l2));
    reg [95:0] got; integer i;
    task tck_pulse; begin #50 t.bscan.TCK = 1; #50 t.bscan.TCK = 0; end endtask
    initial begin
        #6000000;                                   // 6 ms: the compare has finished
        t.bscan.SEL = 1;
        t.bscan.CAPTURE = 1; tck_pulse; t.bscan.CAPTURE = 0;
        t.bscan.SHIFT = 1;
        for (i = 0; i < 96; i = i + 1) begin
            #10 got[i] = t.bscan.TDO;               // bit i leaves before the clock that shifts it
            tck_pulse;
        end
        t.bscan.SHIFT = 0; t.bscan.SEL = 0;
        $display("scan word0=%08X word1=%08X word2=%08X", got[31:0], got[63:32], got[95:64]);
        if (got[31:0] === 32'h554E4943 && got[63:32] !== 32'd0 && got[64] === 1'b1 && got[65] === 1'b0 && got[66] === 1'b0 && got[95:80] === 16'h0)
            $display("PASS");
        else $display("FAIL");
        $finish;
    end
endmodule
