`timescale 1ns/1ps
// tb_hexn_hold_v2.v -- reads +stim=<hex file> (one 13-bit entry per sample: {skip, n[7:0], din[3:0]}) and +count=<samples>; prints "dout valid chg" after every sample.
module tb_hexn_hold_v2;
    reg clk = 0, rst = 1, en = 0; reg [3:0] din = 0; reg [7:0] n = 1; reg skip = 0; wire [3:0] dout; wire valid, chg;
    reg [12:0] mem [0:65535]; integer i, count; reg [1023:0] fn;
    hexn_hold_v2 #(.W(4), .CW(8)) dut(.clk(clk), .rst(rst), .en(en), .din(din), .n(n), .skip_none(skip), .dout(dout), .valid(valid), .chg(chg));
    always #5 clk = ~clk;
    initial begin
        if (!$value$plusargs("stim=%s", fn)) $finish; if (!$value$plusargs("count=%d", count)) $finish;
        $readmemh(fn, mem); repeat (3) @(posedge clk); #1 rst = 0;
        for (i = 0; i < count; i = i + 1) begin
            din = mem[i][3:0]; n = mem[i][11:4]; skip = mem[i][12]; en = 1; @(posedge clk); #1 en = 0; $display("%0d %0d %0d", dout, valid, chg);
            if (i % 3 == 2) begin @(posedge clk); #1; end
        end
        $finish;
    end
endmodule
