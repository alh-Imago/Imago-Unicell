`timescale 1ns/1ps
// tb_fz.v - testbench for uc_core_v2w: RAM models of WHOLE 32-BIT WORDS; the core's {word, digit k} address picks bits [WE*k +: WE]
// (a width-independent data layout, like the pool's 32-bit-wide block RAM with a mux).  Parameter FZ = 0 / 1 sets the width (1 / 2).
module tb_fz;
    parameter FZ = 0;
    parameter DMEM_WORDS = 1024;
    localparam WE = FZ ? 2 : 1;
    localparam [1:0] LM = FZ ? 2'b11 : 2'b01;

    reg clk = 0, rst = 1;
    always #5 clk = ~clk;

    wire halted, trap;
    wire [29:0] imem_addr;
    reg  [31:0] imem [0:4095];
    wire [31:0] imem_data = imem[imem_addr[11:0]];

    wire [9:0] ra_addr, rb_addr, rw_addr;
    wire [1:0] rw_data, d_wdata;
    wire       rw_en;
    reg  [31:0] rf [0:31];
    wire [31:0] ra_w = rf[ra_addr[9:5]], rb_w = rf[rb_addr[9:5]];
    wire [1:0] ra_data = (ra_w >> (WE * ra_addr[4:0])) & LM;
    wire [1:0] rb_data = (rb_w >> (WE * rb_addr[4:0])) & LM;
    always @(posedge clk) if (rw_en)
        rf[rw_addr[9:5]] <= (rf[rw_addr[9:5]] & ~({30'b0, LM} << (WE * rw_addr[4:0]))) | ({30'b0, rw_data & LM} << (WE * rw_addr[4:0]));

    wire [34:0] d_addr;
    wire        d_we;
    reg  [31:0] dm [0:DMEM_WORDS-1];
    wire [31:0] d_w = dm[d_addr[14:5]];
    wire [1:0]  d_rdata = (d_w >> (WE * d_addr[4:0])) & LM;
    always @(posedge clk) if (d_we)
        dm[d_addr[14:5]] <= (dm[d_addr[14:5]] & ~({30'b0, LM} << (WE * d_addr[4:0]))) | ({30'b0, d_wdata & LM} << (WE * d_addr[4:0]));

    uc_core_v2w dut (
        .clk(clk), .rst(rst), .fz(FZ[0]), .halted(halted), .trap(trap),
        .imem_addr(imem_addr), .imem_data(imem_data),
        .ra_addr(ra_addr), .ra_data(ra_data),
        .rb_addr(rb_addr), .rb_data(rb_data),
        .rw_en(rw_en), .rw_addr(rw_addr), .rw_data(rw_data),
        .d_addr(d_addr), .d_we(d_we), .d_wdata(d_wdata), .d_rdata(d_rdata));

    integer cycles = 0, instret = 0, i, fd;
    reg [1023:0] progname, outname;

    always @(posedge clk) if (!rst) begin
        cycles = cycles + 1;
        if (dut.state == 3'd1) instret = instret + 1;
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
        $fdisplay(fd, "pc %0d", dut.pc);
        for (i = 0; i < 32; i = i + 1) $fdisplay(fd, "r %0d %0d", i, rf[i]);
        for (i = 0; i < DMEM_WORDS; i = i + 1) $fdisplay(fd, "m %0d %0d", i, dm[i]);
        $fclose(fd);
        $finish;
    end
endmodule
