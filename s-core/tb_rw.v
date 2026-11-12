`timescale 1ns/1ps
// Testbench for uc_core_rw: one core, started at runtime width log2(W).  Same dump format as tb.v.
module tb;
    parameter W  = 4;
    parameter N  = 32 / W;
    parameter DMEM_WORDS = 1024;
    localparam [31:0] MASK = (W == 32) ? 32'hFFFF_FFFF : ((32'd1 << W) - 1);

    reg clk = 0, rst = 1, start = 0;
    always #5 clk = ~clk;

    wire halted, trap;
    wire [2:0] lw_cur;
    wire [29:0] imem_addr;
    reg  [31:0] imem [0:4095];
    wire [31:0] imem_data = imem[imem_addr[11:0]];

    wire [9:0] ra_addr, rb_addr, rw_addr;
    wire [31:0] ra_data, rb_data, rw_data;
    wire rw_en;
    reg [31:0] rf [0:1023];
    assign ra_data = rf[ra_addr];
    assign rb_data = rf[rb_addr];
    always @(posedge clk) if (rw_en) rf[rw_addr] <= rw_data;

    wire [34:0] d_addr;
    wire d_we;
    wire [31:0] d_wdata, d_rdata;
    reg [31:0] dm [0:(DMEM_WORDS*32)-1];
    assign d_rdata = dm[d_addr[14:0]];
    always @(posedge clk) if (d_we) dm[d_addr[14:0]] <= d_wdata;

    uc_core_rw dut (.clk(clk), .rst(rst), .start(start), .entry(32'd0), .lw_in($clog2(W)),
        .halted(halted), .trap(trap), .lw_cur(lw_cur),
        .imem_addr(imem_addr), .imem_data(imem_data),
        .ra_addr(ra_addr), .ra_data(ra_data), .rb_addr(rb_addr), .rb_data(rb_data),
        .rw_en(rw_en), .rw_addr(rw_addr), .rw_data(rw_data),
        .d_addr(d_addr), .d_we(d_we), .d_wdata(d_wdata), .d_rdata(d_rdata));

    integer cycles = 0, instret = 0, i, d, fd;
    reg [1023:0] progname, outname;
    reg [31:0] v;
    reg running = 0;

    always @(posedge clk) if (running) begin
        cycles = cycles + 1;
        if (dut.state == 3'd1) instret = instret + 1;
    end

    initial begin
        for (i = 0; i < 4096; i = i + 1) imem[i] = 32'h0;
        for (i = 0; i < 1024; i = i + 1) rf[i] = 0;
        for (i = 0; i < DMEM_WORDS*32; i = i + 1) dm[i] = 0;
        if (!$value$plusargs("prog=%s", progname)) begin $display("need +prog"); $finish; end
        if (!$value$plusargs("out=%s", outname))  begin $display("need +out");  $finish; end
        $readmemh(progname, imem);
        repeat (4) @(posedge clk);
        rst <= 0;
        @(posedge clk);
        start <= 1; running <= 1;
        @(posedge clk);
        start <= 0;
        repeat (2) @(posedge clk);
        while (!halted && cycles < 20000000) @(posedge clk);
        @(posedge clk);
        fd = $fopen(outname, "w");
        $fdisplay(fd, "cycles %0d", cycles);
        $fdisplay(fd, "instret %0d", instret);
        $fdisplay(fd, "trap %0d", trap);
        $fdisplay(fd, "halted %0d", halted);
        $fdisplay(fd, "pc %0d", dut.pc);
        for (i = 0; i < 32; i = i + 1) begin
            v = 0;
            for (d = 0; d < N; d = d + 1) v = v | ((rf[{i[4:0], d[4:0]}] & MASK) << (d * W));
            $fdisplay(fd, "r %0d %0d", i, v);
        end
        for (i = 0; i < DMEM_WORDS; i = i + 1) begin
            v = 0;
            for (d = 0; d < N; d = d + 1) v = v | ((dm[{i[9:0], d[4:0]}] & MASK) << (d * W));
            $fdisplay(fd, "m %0d %0d", i, v);
        end
        $fclose(fd);
        $finish;
    end
endmodule
