`timescale 1ns/1ps
// Test bench for hexn_tilegrid_v1. Stimulus file (+stim=FILE, +n=LINES), one hex word per clock: bit0 = cfg_in, bit1 = cfg_en, bit2 = clear, then for row r: bit 3+2r = w_d, bit 4+2r = w_f.
// Each clock prints  cfg_out, e_f (ROWS bits, row ROWS-1 first), e_d (same order)  as one binary string of 1 + 2*ROWS characters.
module tb #(parameter ROWS = 7, parameter COLS = 7);
    reg clk = 0; always #5 clk = ~clk;
    reg [31:0] mem [0:65535]; integer n = 0, i, r; reg [1023:0] fn;
    reg clear = 0, cfg_en = 0, cfg_in = 0; reg [ROWS-1:0] wd = 0, wf = 0;
    wire [ROWS-1:0] ed, ef; wire co;
    hexn_tilegrid_v1 #(.ROWS(ROWS), .COLS(COLS)) dut (.clk(clk), .clear(clear), .w_d(wd), .w_f(wf), .e_d(ed), .e_f(ef), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("FAIL no +stim"); $finish; end
        if (!$value$plusargs("n=%d", n)) begin $display("FAIL no +n"); $finish; end
        $readmemh(fn, mem, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            cfg_in = mem[i][0]; cfg_en = mem[i][1]; clear = mem[i][2];
            for (r = 0; r < ROWS; r = r + 1) begin wd[r] = mem[i][3 + 2 * r]; wf[r] = mem[i][4 + 2 * r]; end
            #1; @(posedge clk); #1;
            $display("%b%b%b", co, ef, ed);
        end
        $finish;
    end
endmodule
