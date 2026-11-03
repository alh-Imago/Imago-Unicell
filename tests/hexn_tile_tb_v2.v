`timescale 1ns/1ps
// Test bench for hexn_tile_v2 (copy of hexn_tile_tb.v): NT tiles in a row, east face of tile i joined to west face of tile i+1 (tile i's E output -> tile i+1's W input, and back), chain input -> tile 0 -> ... -> chain output.
// Stimulus file (plusarg +stim=FILE), one line per clock, hex: {clear, cfg_en, cfg_in, n_f, n_d, s_f, s_d, w_f, w_d} of tile 0's N, S and W faces (external), and tile NT-1's E face is read out.
// Every other external face reads 0.  Each clock prints  {cfg_out, e_f, e_d, s_f(t0), s_d(t0)}.
module tb #(parameter NT = 1);
    reg clk = 0; always #5 clk = ~clk;
    reg [8:0] mem [0:65535]; integer n = 0, i; reg [1023:0] fn;
    reg clear = 0, cfg_en = 0, cfg_in = 0, nf = 0, nd = 0, sf = 0, sd = 0, wf = 0, wd = 0;
    wire [NT*4-1:0] fo_d, fo_f; wire [NT*4-1:0] fi_d, fi_f; wire [NT:0] cc;
    assign cc[0] = cfg_in;
    genvar g;
    generate for (g = 0; g < NT; g = g + 1) begin : t
        // faces: 0 N, 1 E, 2 S, 3 W
        wire [3:0] id = {(g == 0) ? wd : fo_d[(g-1)*4 + 1], 1'b0 | ((g == 0) ? sd : 1'b0), (g == NT-1) ? 1'b0 : fo_d[(g+1)*4 + 3], (g == 0) ? nd : 1'b0};
        wire [3:0] ifl = {(g == 0) ? wf : fo_f[(g-1)*4 + 1], 1'b0 | ((g == 0) ? sf : 1'b0), (g == NT-1) ? 1'b0 : fo_f[(g+1)*4 + 3], (g == 0) ? nf : 1'b0};
        // bit order of id is {face3, face2, face1, face0}
        hexn_tile_v2 #(.FACES(4)) u (.clk(clk), .clear(clear), .fi_d(id), .fi_f(ifl), .fo_d(fo_d[g*4 +: 4]), .fo_f(fo_f[g*4 +: 4]), .cfg_en(cfg_en), .cfg_in(cc[g]), .cfg_out(cc[g+1]));
    end endgenerate
    // chain order: the bit shifted in at cfg_in enters tile 0 and falls out of its cfg_out into tile 1, so the FARTHEST tile's word goes in first (the packer does that)
    initial begin
        if (!$value$plusargs("stim=%s", fn)) begin $display("FAIL no +stim"); $finish; end
        if (!$value$plusargs("n=%d", n)) begin $display("FAIL no +n"); $finish; end
        $readmemh(fn, mem, 0, n - 1);
        for (i = 0; i < n; i = i + 1) begin
            {clear, cfg_en, cfg_in, nf, nd, sf, sd, wf, wd} = mem[i][8:0] | 9'd0;
            #1;
            @(posedge clk); #1;
            $display("%b%b%b%b%b", cc[NT], fo_f[(NT-1)*4 + 1], fo_d[(NT-1)*4 + 1], fo_f[2], fo_d[2]);
        end
        $finish;
    end
endmodule
