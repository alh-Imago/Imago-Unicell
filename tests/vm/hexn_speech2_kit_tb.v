// Testbench for fpga/ypcb/hexn_speech2/hexn_speech2.v: runs the replay to the end, then reads the 64-bit JTAG register the way a host scan does (one capture, 64 shifts, bit 0 first) through the BSCANE2 simulation model, once while the replay is still running (early) and once after it finished.
`timescale 1ns/1ps
module tbk2;
    reg clk = 0; wire [2:0] led; integer n, i; reg [63:0] v;
    hexn_speech2 dut (.SYS_CLK(clk), .led(led));
    always #5 clk = ~clk;
    task scan; begin
        dut.bscan.r_sel = 1; dut.bscan.r_capture = 1; dut.bscan.r_drck = 1; #7; dut.bscan.r_drck = 0; #7; dut.bscan.r_capture = 0; dut.bscan.r_shift = 1;
        for (i = 0; i < 64; i = i + 1) begin v[i] = dut.sr[0]; dut.bscan.r_tdi = 0; dut.bscan.r_drck = 1; #7; dut.bscan.r_drck = 0; #7; end
        dut.bscan.r_shift = 0; dut.bscan.r_sel = 0;
    end endtask
    initial begin
        n = 0;
        repeat (20000) @(posedge clk);
        scan; $display("EARLY %h", v);
        while (!led[1] && n < 3000000) begin @(posedge clk); n = n + 1; end
        repeat (10) @(posedge clk);
        scan; $display("LATE %h", v);
        $display("KIT done=%0d pass=%0d correct=%0d total=%0d", led[1], led[2], dut.correct, dut.total);
        $finish;
    end
endmodule
