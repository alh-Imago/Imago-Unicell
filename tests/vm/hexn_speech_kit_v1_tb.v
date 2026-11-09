// Testbench for fpga/ypcb/hexn_speech/hexn_speech.v (generated ROM and chain from prebuild.py): runs until the replay is finished and prints the result.
`timescale 1ns/1ps
module tbk;
    reg clk = 0; wire [2:0] led; integer n;
    hexn_speech dut (.SYS_CLK(clk), .led(led));
    always #5 clk = ~clk;
    initial begin
        n = 0;
        while (!led[1] && n < 3000000) begin @(posedge clk); n = n + 1; end
        $display("KIT done=%0d pass=%0d correct=%0d total=%0d clocks=%0d", led[1], led[2], dut.correct, dut.total, n);
        $finish;
    end
endmodule
