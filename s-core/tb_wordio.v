`timescale 1ns/1ps
// tb_wordio.v - testbench for uc_unitr<W> (ledger #1369): RAMs of WHOLE 32-bit words, read as words, written as words (the unit's own digit select and accumulator do the rest).
// Parameter LW (log2 of the width, 0..4).  Output file format as tb_wide.v.
module tb_wordio;
    parameter LW = 0;
    parameter DMEM_WORDS = 1024;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;
    wire halted, trap;
    wire [29:0] imem_addr;
    reg  [31:0] imem [0:4095];
    wire [31:0] imem_data = imem[imem_addr[11:0]];
    wire [4:0] ra_wa, rb_wa, rw_wa;
    wire rw_we, d_wwe;
    wire [31:0] rw_word, d_wword;
    reg  [31:0] rf [0:31];
    wire [31:0] ra_word = rf[ra_wa], rb_word = rf[rb_wa];
    always @(posedge clk) if (rw_we) rf[rw_wa] <= rw_word;
    wire [29:0] d_wa;
    reg  [31:0] dm [0:DMEM_WORDS-1];
    wire [31:0] d_word = dm[d_wa[9:0]];
    always @(posedge clk) if (d_wwe) dm[d_wa[9:0]] <= d_wword;
    uc_core_dut dut (.clk(clk), .rst(rst), .lw(LW[2:0]), .halted(halted), .trap(trap), .imem_addr(imem_addr), .imem_data(imem_data),
        .ra_wa(ra_wa), .ra_word(ra_word), .rb_wa(rb_wa), .rb_word(rb_word), .rw_we(rw_we), .rw_wa(rw_wa), .rw_word(rw_word),
        .d_wa(d_wa), .d_word(d_word), .d_wwe(d_wwe), .d_wword(d_wword));
    integer cycles = 0, instret = 0, i, fd;
    reg [1023:0] progname, outname;
    always @(posedge clk) if (!rst) begin
        cycles = cycles + 1;
        if (dut.core.state == 3'd1) instret = instret + 1;
    end
    initial begin
        for (i = 0; i < 4096; i = i + 1) imem[i] = 32'h0;
        for (i = 0; i < 32; i = i + 1) rf[i] = 0;
        for (i = 0; i < DMEM_WORDS; i = i + 1) dm[i] = 0;
        if (!$value$plusargs("prog=%s", progname)) begin $display("need +prog"); $finish; end
        if (!$value$plusargs("out=%s", outname))  begin $display("need +out");  $finish; end
        $readmemh(progname, imem);
        repeat (4) @(posedge clk);
        rst <= 0;
        while (!halted && cycles < 20000000) @(posedge clk);
        @(posedge clk);
        fd = $fopen(outname, "w");
        $fdisplay(fd, "cycles %0d", cycles);
        $fdisplay(fd, "instret %0d", instret);
        $fdisplay(fd, "trap %0d", trap);
        $fdisplay(fd, "halted %0d", halted);
        $fdisplay(fd, "pc %0d", dut.core.pc);
        for (i = 0; i < 32; i = i + 1) $fdisplay(fd, "r %0d %0d", i, rf[i]);
        for (i = 0; i < DMEM_WORDS; i = i + 1) $fdisplay(fd, "m %0d %0d", i, dm[i]);
        $fclose(fd);
        $finish;
    end
endmodule
