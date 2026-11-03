`timescale 1ns/1ps
// Test bench for hexn_ramhold_v1, ONE cell. Stimulus file (+stim, +n), hex per clock: bit0 cfg_in, bit1 cfg_en, bit2 clear, then the face inputs data / flag: N (3,4), E (5,6), S (7,8), W (9,10).
// Each clock prints the output faces as 8 characters: N d,f  E d,f  S d,f  W d,f.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [15:0] mem [0:65535]; integer n = 0, i; reg [1023:0] fn;
    reg cfg_en = 0, cfg_in = 0, clear = 0; reg [3:0] fd = 0, ff = 0;
    wire [3:0] od, of; wire co;
    hexn_ramhold_v1 #(.FACES(4)) dut (.clk(clk), .clear(clear), .fi_d(fd), .fi_f(ff), .fo_d(od), .fo_f(of), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("FAIL no +stim"); $finish; end
        if (!$value$plusargs("n=%d", n)) begin $display("FAIL no +n"); $finish; end
        $readmemh(fn, mem, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            cfg_in = mem[i][0]; cfg_en = mem[i][1]; clear = mem[i][2];
            fd = {mem[i][9], mem[i][7], mem[i][5], mem[i][3]}; ff = {mem[i][10], mem[i][8], mem[i][6], mem[i][4]};
            #1; @(posedge clk); #1;
            $display("%b%b%b%b%b%b%b%b", od[0], of[0], od[1], of[1], od[2], of[2], od[3], of[3]);
        end
        $finish;
    end
endmodule
