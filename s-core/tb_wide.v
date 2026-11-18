`timescale 1ns/1ps
// tb_wide.v - testbench for the generated units uc_unitg<W> (and any core with the port list of uc_unit4): RAMs of WHOLE 32-bit words, the core's {word, digit k}
// address picks bits [WE*k +: WE].  Parameters: LW (log2 of the width, 0..4) and BW (number of lanes = bus width).
module tb_wide;
    parameter LW = 0;
    parameter BW = 4;
    parameter DMEM_WORDS = 1024;
    localparam WE = 1 << LW;
    localparam [31:0] LM = (32'd1 << WE) - 32'd1;

    reg clk = 0, rst = 1;
    always #5 clk = ~clk;

    wire halted, trap;
    wire [29:0] imem_addr;
    reg  [31:0] imem [0:4095];
    wire [31:0] imem_data = imem[imem_addr[11:0]];

    wire [9:0] ra_addr, rb_addr, rw_addr;
    wire [BW-1:0] rw_data, d_wdata;
    wire       rw_en;
    reg  [31:0] rf [0:31];
    wire [31:0] ra_w = rf[ra_addr[9:5]], rb_w = rf[rb_addr[9:5]];
    wire [BW-1:0] ra_data = (ra_w >> (WE * ra_addr[4:0])) & LM;
    wire [BW-1:0] rb_data = (rb_w >> (WE * rb_addr[4:0])) & LM;
    wire [31:0] rw_d32 = {{(32-BW){1'b0}}, rw_data};
    wire [31:0] dw_d32 = {{(32-BW){1'b0}}, d_wdata};
    always @(posedge clk) if (rw_en)
        rf[rw_addr[9:5]] <= (rf[rw_addr[9:5]] & ~(LM << (WE * rw_addr[4:0]))) | ((rw_d32 & LM) << (WE * rw_addr[4:0]));

    wire [34:0] d_addr;
    wire        d_we;
    reg  [31:0] dm [0:DMEM_WORDS-1];
    wire [31:0] d_w = dm[d_addr[14:5]];
    wire [BW-1:0] d_rdata = (d_w >> (WE * d_addr[4:0])) & LM;
    always @(posedge clk) if (d_we)
        dm[d_addr[14:5]] <= (dm[d_addr[14:5]] & ~(LM << (WE * d_addr[4:0]))) | ((dw_d32 & LM) << (WE * d_addr[4:0]));

    uc_core_dut dut (
        .clk(clk), .rst(rst), .lw(LW[2:0]), .halted(halted), .trap(trap),
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
