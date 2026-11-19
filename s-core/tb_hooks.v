`timescale 1ns/1ps
// tb_hooks.v - testbench for uc_unitw<W> (ledger #1377, step I0): the unit with the pool hooks.  Word RAMs as tb_wordio.v.
// Parameters: LW (log2 of the width), CEM (clock-enable pattern: 0 = always 1, 1 = every other clock like the pool's cph, 2 = pseudo-random about 2 of 3 clocks),
// ABORTN (0 = none; N > 0: abort asserted for one clock after N steps).  `start` is held from reset until the core leaves HALT, as the pool does.
// Output file as tb_wide.v; `cycles` counts the clocks with ce = 1 while the core is not halted (the steps), which must equal uc_core_v2's cycles at the same width.
module tb_hooks;
    parameter LW = 0;
    parameter CEM = 0;
    parameter ABORTN = 0;
    parameter DMEM_WORDS = 1024;
    reg clk = 0, rst = 1;
    always #5 clk = ~clk;
    wire halted, trap, fetching, dmem_act, dmem_ld;
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
    reg start = 0, abort = 0;
    reg [31:0] lfsr = 32'h1ACE_B00C;
    integer cnt = 0;
    wire ce = (CEM == 0) ? 1'b1 : (CEM == 1) ? cnt[0] : (lfsr[3:2] != 2'b00);
    always @(posedge clk) begin cnt <= cnt + 1; lfsr <= {lfsr[30:0], lfsr[31] ^ lfsr[21] ^ lfsr[1] ^ lfsr[0]}; end
    uc_core_dut dut (.clk(clk), .rst(rst), .lw(LW[2:0]), .start(start), .entry(32'd0), .ce(ce), .abort(abort), .dblk(1'b0),
        .halted(halted), .trap(trap), .fetching(fetching), .dmem_act(dmem_act), .dmem_ld(dmem_ld), .imem_addr(imem_addr), .imem_data(imem_data),
        .ra_wa(ra_wa), .ra_word(ra_word), .rb_wa(rb_wa), .rb_word(rb_word), .rw_we(rw_we), .rw_wa(rw_wa), .rw_word(rw_word),
        .d_wa(d_wa), .d_word(d_word), .d_wwe(d_wwe), .d_wword(d_wword));
    integer cycles = 0, instret = 0, i, fd;
    reg [1023:0] progname, outname;
    reg running = 0, running_done = 0;
    always @(posedge clk) if (!rst) begin
        if (ce && (!halted || (start && !running))) begin
            cycles = cycles + 1;
            if (dut.core.state == 3'd1) instret = instret + 1;
            if (ABORTN != 0 && cycles == ABORTN) abort <= 1'b1;
        end
        if (abort) abort <= 1'b0;
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
        @(posedge clk); start <= 1'b1;
        while (halted && cycles < 20000000) @(posedge clk);   // start held until the core leaves HALT
        start <= 1'b0; running = 1;
        while (!halted && cycles < 20000000) @(posedge clk);
        running_done = 1; @(posedge clk); running_done = 0;
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
