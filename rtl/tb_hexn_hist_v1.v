`timescale 1ns/1ps
// tb_hexn_hist_v1.v -- reads +stim=<hex file> (one 8-bit entry per clock: {ev, tick, 2'b0, cls[3:0]}) and +count=<clocks>; prints "hist dwell prev_dwell count" after every clock. D = 4, W = 4, DW = 6 (small so saturation is exercised).
module tb_hexn_hist_v1;
    reg clk = 0, rst = 1, ev = 0, tick = 0; reg [3:0] cls = 0; wire [15:0] hist; wire [5:0] dwell, prev_dwell; wire [2:0] count;
    reg [7:0] mem [0:65535]; integer i, count_n; reg [1023:0] fn;
    hexn_hist_v1 #(.W(4), .D(4), .DW(6)) dut(.clk(clk), .rst(rst), .ev(ev), .cls(cls), .tick(tick), .hist(hist), .dwell(dwell), .prev_dwell(prev_dwell), .count(count));
    always #5 clk = ~clk;
    initial begin
        if (!$value$plusargs("stim=%s", fn)) $finish; if (!$value$plusargs("count=%d", count_n)) $finish;
        $readmemh(fn, mem); repeat (3) @(posedge clk); #1 rst = 0;
        for (i = 0; i < count_n; i = i + 1) begin
            ev = mem[i][7]; tick = mem[i][6]; cls = mem[i][3:0]; @(posedge clk); #1; $display("%0d %0d %0d %0d", hist, dwell, prev_dwell, count);
        end
        $finish;
    end
endmodule
