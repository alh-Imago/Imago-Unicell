`timescale 1ns/1ps
// Test bench for hexn_xtop_v1 around a generated hexn_pattern_top. +stim=FILE +n=LINES (one hex word per clock: bit0 cfg_in, bit1 cfg_en, bit2 clear, bit 3+r in_valid of row r), +data=FILE (ROWS hex words, the parallel inputs held constant).
// Each clock prints: out_valid (ROWS bits, row ROWS-1 first), then the ROWS out_data words (row 0 first, 8 hex digits each), separated by a space.
module tb #(parameter ROWS = 7, parameter COLS = 7);
    reg clk = 0; always #5 clk = ~clk;
    reg [31:0] mem [0:65535]; reg [31:0] dat [0:ROWS-1]; integer n = 0, i, r; reg [1023:0] fn, fd;
    reg clear = 0, cfg_en = 0, cfg_in = 0; reg [ROWS-1:0] iv = 0; reg [32*ROWS-1:0] idat = 0;
    wire [ROWS-1:0] busy, ov; wire [32*ROWS-1:0] od; wire co;
    hexn_xtop_v1 #(.ROWS(ROWS)) dut (.clk(clk), .clear(clear), .in_data(idat), .in_valid(iv), .in_busy(busy), .out_data(od), .out_valid(ov), .cfg_en(cfg_en), .cfg_in(cfg_in), .cfg_out(co));
    initial begin
        if (!$value$plusargs("stim=%s", fn) || !$value$plusargs("data=%s", fd) || !$value$plusargs("n=%d", n)) begin $display("FAIL args"); $finish; end
        $readmemh(fn, mem, 0, n - 1); $readmemh(fd, dat, 0, ROWS - 1);
        for (r = 0; r < ROWS; r = r + 1) idat[32*r +: 32] = dat[r];
        for (i = 0; i < n; i = i + 1) begin
            cfg_in = mem[i][0]; cfg_en = mem[i][1]; clear = mem[i][2];
            for (r = 0; r < ROWS; r = r + 1) iv[r] = mem[i][3 + r];
            #1; @(posedge clk); #1;
            $write("%b", ov); for (r = 0; r < ROWS; r = r + 1) $write(" %08x", od[32*r +: 32]); $write("\n");
        end
        $finish;
    end
endmodule
