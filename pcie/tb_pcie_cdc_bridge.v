`timescale 1ns / 1ps
// tb_pcie_cdc_bridge.v -- drives real write/read transactions from the fast
// (PCIe Hard IP, 250MHz) side, checks correctness on the slow (fabric) side
// and back.
//
// SLOW_PERIOD_NS is a parameter specifically so the IDENTICAL test sequence
// can be verified at both plausible fabric clock rates -- default here is
// 40.0ns (25MHz, the current real CLK_100M/4 value). Also verified at
// 20.0ns (50MHz, the stated target once the fabric's real Fmax is measured
// and confirmed -- see points.md #46) by temporarily changing this
// parameter and re-running: all 5 checks pass identically at both rates,
// confirming the bridge is genuinely frequency-ratio-independent rather
// than just claimed to be. Neither run required any change to
// pcie_cdc_bridge.v itself -- exactly the point of the design.
module tb_pcie_cdc_bridge;

parameter FAST_PERIOD_NS = 4.0;
parameter SLOW_PERIOD_NS = 40.0;

reg fast_clk = 0;
reg slow_clk = 0;
reg fast_rst = 1;
reg slow_rst = 1;

always #(FAST_PERIOD_NS/2.0) fast_clk = ~fast_clk;
always #(SLOW_PERIOD_NS/2.0) slow_clk = ~slow_clk;

reg  [15:0] fast_address = 16'h0;
reg  [3:0]  fast_byteenable = 4'hF;
reg  [31:0] fast_writedata = 32'h0;
reg         fast_write = 1'b0;
reg         fast_read = 1'b0;
wire [31:0] fast_readdata;
wire        fast_readdatavalid;
wire        fast_waitrequest;

wire [15:0] slow_address;
wire [3:0]  slow_byteenable;
wire [31:0] slow_writedata;
wire        slow_write;
wire        slow_read;
reg  [31:0] slow_readdata = 32'h0;
reg         slow_readdatavalid = 1'b0;
wire        slow_waitrequest;

pcie_cdc_bridge dut (
    .fast_clk(fast_clk), .fast_rst(fast_rst),
    .fast_address(fast_address), .fast_byteenable(fast_byteenable),
    .fast_writedata(fast_writedata), .fast_write(fast_write), .fast_read(fast_read),
    .fast_readdata(fast_readdata), .fast_readdatavalid(fast_readdatavalid),
    .fast_waitrequest(fast_waitrequest),

    .slow_clk(slow_clk), .slow_rst(slow_rst),
    .slow_address(slow_address), .slow_byteenable(slow_byteenable),
    .slow_writedata(slow_writedata), .slow_write(slow_write), .slow_read(slow_read),
    .slow_readdata(slow_readdata), .slow_readdatavalid(slow_readdatavalid),
    .slow_waitrequest(slow_waitrequest)
);

assign slow_waitrequest = 1'b0;

reg [31:0] slow_mem [0:3];
always @(posedge slow_clk) begin
    if (slow_write) slow_mem[slow_address[3:2]] <= slow_writedata;
    slow_readdatavalid <= slow_read;
    if (slow_read) slow_readdata <= slow_mem[slow_address[3:2]];
end

integer errors = 0;
task check(input [255:0] label, input cond);
    begin
        if (!cond) begin
            $display("FAIL [SLOW_PERIOD=%0.1fns]: %0s", SLOW_PERIOD_NS, label);
            errors = errors + 1;
        end else begin
            $display("PASS [SLOW_PERIOD=%0.1fns]: %0s", SLOW_PERIOD_NS, label);
        end
    end
endtask

task fast_write_word(input [15:0] addr, input [31:0] data);
    begin
        @(posedge fast_clk);
        fast_address = addr; fast_writedata = data; fast_write = 1'b1;
        @(posedge fast_clk);
        #1;
        fast_write = 1'b0;
        while (fast_waitrequest) @(posedge fast_clk);
        #1;
    end
endtask

task fast_read_word(input [15:0] addr);
    begin
        @(posedge fast_clk);
        fast_address = addr; fast_read = 1'b1;
        @(posedge fast_clk);
        #1;
        fast_read = 1'b0;
        while (fast_waitrequest) @(posedge fast_clk);
        #1;
    end
endtask

initial begin
    #100000;  // watchdog: if we're still running after 100us, something's stuck
    $display("WATCHDOG TIMEOUT -- simulation did not complete, likely a stuck handshake");
    $finish;
end

initial begin
    #23.7 fast_rst = 0; slow_rst = 0;   // deliberately off-grid timing, avoids
                                          // coinciding with either clock's edge
    #20;

    fast_write_word(16'h0, 32'hAAAA1111);
    #1;
    check("write value correctly latched in slow domain", slow_mem[0] === 32'hAAAA1111);

    fast_write_word(16'h4, 32'hBBBB2222);
    #1;
    check("second write correctly latched, first register unaffected",
          slow_mem[1] === 32'hBBBB2222 && slow_mem[0] === 32'hAAAA1111);

    fast_read_word(16'h0);
    #1;
    check("read of register 0 returns the correct value", fast_readdata === 32'hAAAA1111);

    fast_read_word(16'h4);
    #1;
    check("read of register 1 returns the correct value", fast_readdata === 32'hBBBB2222);

    fast_write_word(16'h8, 32'hCCCC3333);
    fast_write_word(16'hC, 32'hDDDD4444);
    #1;
    check("back-to-back writes both landed correctly, in order",
          slow_mem[2] === 32'hCCCC3333 && slow_mem[3] === 32'hDDDD4444);

    $display("");
    if (errors == 0)
        $display("ALL CHECKS PASSED (0 errors) at SLOW_PERIOD=%0.1fns (%0.1fMHz)",
                  SLOW_PERIOD_NS, 1000.0/SLOW_PERIOD_NS);
    else
        $display("%0d CHECK(S) FAILED at SLOW_PERIOD=%0.1fns", errors, SLOW_PERIOD_NS);

    $finish;
end

endmodule
