`timescale 1ns/1ps
// Test bench for hexn_tile_al_v1, ONE tile. Stimulus file (+stim, +n), hex per clock: bit0 cfg_in, bit1 cfg_en, then faces' data/flag inputs: N (bit2 d, bit3 f), E (4,5), S (6,7), W (8,9).
// Each clock prints  cfg_out, then E flag, E data, S flag, S data, N flag, N data, W flag, W data  (the output faces) as one 9-character binary string.
module tb;
    reg clk = 0; always #5 clk = ~clk;
    reg [15:0] mem [0:65535]; integer n = 0, i; reg [1023:0] fn;
    reg cfg_en = 0, cfg_in = 0; reg [3:0] fd = 0, ff = 0;
    wire [3:0] od, of; wire co;
    hexn_tile_al_v1 #(.FACES(4)) dut (.clk(clk), .fi_d(fd), .fi_f(ff), .fo_d(od), .fo_f(of), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("FAIL no +stim"); $finish; end
        if (!$value$plusargs("n=%d", n)) begin $display("FAIL no +n"); $finish; end
        $readmemh(fn, mem, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            cfg_in = mem[i][0]; cfg_en = mem[i][1];
            fd = {mem[i][8], mem[i][6], mem[i][4], mem[i][2]}; ff = {mem[i][9], mem[i][7], mem[i][5], mem[i][3]};
            #1; @(posedge clk); #1;
            $display("%b%b%b%b%b%b%b%b%b", co, of[1], od[1], of[2], od[2], of[0], od[0], of[3], od[3]);
        end
        $finish;
    end
endmodule
